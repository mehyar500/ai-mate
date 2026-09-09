"""Isolated Moonshine English ASR comparison; no microphone or cloud inference."""
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import statistics
import sys
import time
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_call_asr import word_errors, words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=['tiny-streaming','small-streaming'], required=True)
    parser.add_argument('--download-only', action='store_true')
    args = parser.parse_args()
    if importlib.metadata.version('moonshine-voice') != '0.1.5':
        raise ValueError('Use the isolated pinned Moonshine 0.1.5 environment.')
    from moonshine_voice import Transcriber
    from moonshine_voice.moonshine_api import ModelArch, moonshine_get_stt_dependencies_string
    from moonshine_voice.download import find_model_info, download_model_from_info
    from moonshine_voice.utils import load_wav_file
    arch = ModelArch.TINY_STREAMING if args.model == 'tiny-streaming' else ModelArch.SMALL_STREAMING
    cache = ROOT/'.cache/moonshine-models'
    record_path = cache/(args.model+'-manifest.json')
    if args.download_only:
        info = find_model_info('en', arch)
        manifest = json.loads(moonshine_get_stt_dependencies_string('en', {'model_arch':int(arch)}))
        files = [f for g in manifest['groups'] for f in g['files']]
        if not files or sum(f['size'] for f in files)>2_000_000_000:
            raise ValueError('Model exceeds benchmark download bound.')
        for item in files:
            url = urlparse(item['url'])
            if url.scheme != 'https' or url.hostname != 'download.moonshine.ai' or '..' in Path(item['name']).parts:
                raise ValueError('Unexpected model source.')
        model_path, _ = download_model_from_info(info, cache_root=cache,
            on_progress=lambda fraction, name: None)
        folder = Path(model_path).resolve()
        if not folder.is_relative_to(cache.resolve()):
            raise ValueError('Download is outside the benchmark cache.')
        hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
        record_path.write_text(json.dumps({'sdk':'0.1.5','model':args.model,'language':'en',
            'path':folder.relative_to(ROOT).as_posix(),'manifest':manifest,'sha256':hashes,
            'license_source':'https://github.com/moonshine-ai/moonshine/blob/main/LICENSE'},indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'downloaded':args.model,'bytes':sum(f['size'] for f in files)}),flush=True)
        return
    record = json.loads(record_path.read_text(encoding='utf-8'))
    folder = (ROOT/record['path']).resolve()
    if not folder.is_relative_to(cache.resolve()):
        raise ValueError('Invalid model cache location.')
    for name, expected in record['sha256'].items():
        if Path(name).name != name or hashlib.sha256((folder/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Model checksum mismatch.')
    corpus = ROOT/'generated/local-app/audit/asr-calls-cpu-comparison'
    fixtures = json.loads((corpus/'fixtures.json').read_text(encoding='utf-8'))
    target = corpus/('moonshine-'+args.model+'.json')
    if target.exists():
        raise ValueError('Benchmark evidence already exists.')
    began = time.perf_counter()
    with Transcriber(model_path=folder, model_arch=arch) as transcriber:
        loaded = time.perf_counter()-began
        audio, rate = load_wav_file(corpus/(fixtures[0]['name']+'.wav'))
        transcriber.transcribe_without_streaming(audio,rate)
        rows=[]
        for fixture in fixtures:
            audio, rate = load_wav_file(corpus/(fixture['name']+'.wav'))
            began = time.perf_counter()
            transcript=transcriber.transcribe_without_streaming(audio,rate)
            text=' '.join(line.text for line in transcript.lines).strip()
            rows.append(dict(fixture,text=text,seconds=time.perf_counter()-began,
                word_errors=word_errors(fixture['expected'],text),words=len(words(fixture['expected']))))
    latencies = sorted(r['seconds'] for r in rows if r['expected'])
    result = dict(model=args.model,sdk='0.1.5',load_s=loaded,samples=len(rows),
        median_s=statistics.median(latencies),p95_s=latencies[math.ceil(len(latencies)*.95)-1],
        word_error_rate=sum(r['word_errors'] for r in rows)/sum(r['words'] for r in rows),
        critical_negation_failures=sum(not (set(words(r['text'])) & {'dont','not','never'}) for r in rows if r['case'] in {'negated_wave','negated_return'}),
        non_speech_hallucinations=sum(bool(r['text']) for r in rows if not r['expected']),rows=rows,
        scope='Complete synthetic utterances, default native CPU configuration; no streaming overlap, microphone or active app change.')
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)


if __name__=='__main__':main()
