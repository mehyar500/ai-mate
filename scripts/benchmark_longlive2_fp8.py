"""Actual trained weight / synthetic activation FP8 probe, including conversion overhead."""
import argparse
import gc
import json
from pathlib import Path
import re
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_longlive2 import checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,47}', args.label):
        parser.error('Use a new lowercase label.')
    with urllib.request.urlopen('http://127.0.0.1:8765/api/bootstrap', timeout=5) as response:
        if json.load(response).get('busy'):
            raise RuntimeError('Preview call is active; postpone the probe.')
    path = ROOT / '.cache/local-poc/longlive2-models/generator/model_bf16.pt'
    manifest = json.loads((ROOT / 'config/longlive2-benchmark.json').read_text(encoding='utf-8'))
    if checksum(path) != manifest['files'][0]['sha256']:
        raise ValueError('Unverified model checkpoint.')
    import torch
    from scripts.longlive2_fp8 import FP8Linear
    torch.set_grad_enabled(False)
    torch.manual_seed(123)
    state = torch.load(path, map_location='cpu', mmap=True, weights_only=True)['generator']
    output = ROOT / 'generated/local-app/audit' / ('longlive2-fp8-' + args.label)
    output.mkdir(exist_ok=False)
    record = {'scope': 'three actual trained linears with synthetic activations; no model/video quality acceptance', 'rows': []}
    for suffix in ['self_attn.q', 'ffn.0', 'ffn.2']:
        key = 'model.blocks.0.' + suffix
        weight, bias = state[key + '.weight'], state.get(key + '.bias')
        layer = torch.nn.Linear(weight.shape[1], weight.shape[0], bias=bias is not None, device='meta', dtype=torch.bfloat16)
        layer.load_state_dict({'weight': weight, **({'bias': bias} if bias is not None else {})}, assign=True)
        layer = layer.to('cuda').eval()
        x = torch.randn(1, 1200, weight.shape[1], device='cuda', dtype=torch.bfloat16)
        reference = layer(x)
        for scaling in ['bf16', 'tensor', 'row']:
            row = {'layer': suffix, 'scaling': scaling, 'shape': [1200, weight.shape[1], weight.shape[0]]}
            try:
                module = layer if scaling == 'bf16' else FP8Linear(layer, scaling)
                predicted = module(x)
                error = predicted.float() - reference.float()
                row['relative_rms_error'] = float((error.square().mean() / reference.float().square().mean()).sqrt())
                for _ in range(5): module(x)
                torch.cuda.synchronize()
                start = time.perf_counter()
                for _ in range(30): module(x)
                torch.cuda.synchronize()
                row['complete_ms'] = (time.perf_counter() - start) / 30 * 1000
                row['finite'] = bool(torch.isfinite(predicted).all())
                del module, predicted, error
            except Exception as error:
                row.update({'error_type': type(error).__name__, 'error': str(error)[:800]})
            record['rows'].append(row)
            print(json.dumps(row), flush=True)
        del layer, x, reference
        gc.collect()
        torch.cuda.empty_cache()
    (output / 'benchmark.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
