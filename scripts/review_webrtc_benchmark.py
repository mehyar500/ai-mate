"""Summarize isolated transport runs and inspect every archival video frame.

Archives precede RTC compression. Screenshots cover only selected receiver
pictures. Neither artifact proves receiver lip synchronization or audible sound.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.review_call_frames import inspect_video


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentiles(values):
    ordered = sorted(values)
    if not ordered or not all(math.isfinite(v) and v >= 0 for v in ordered):
        raise ValueError('Expected finite, nonnegative observations.')
    return {'n': len(ordered), 'median': statistics.median(ordered),
            'p95_nearest_rank': ordered[math.ceil(.95*len(ordered))-1]}


def review(label):
    folder = ROOT/'generated/local-app/audit'/('webrtc-'+label)
    browser_path, server_path = folder/'browser-results.json', folder/'server-results.json'
    browser = json.loads(browser_path.read_text(encoding='utf-8'))
    server = json.loads(server_path.read_text(encoding='utf-8'))
    turns = browser['turns']
    if not browser.get('complete') or len(turns) != 12:
        raise ValueError('A completed twelve-reply run is required.')
    diagnostics = []
    for turn in turns:
        path = folder/f"reply-{turn['index']:02}.mp4"
        frames, rows, summary = inspect_video(path)
        if len(frames) != turn['server']['frame_count']:
            raise ValueError('Archive frame count differs from the producer.')
        # The receiver timing marker must never mutate source/archival frames.
        marker_frames = [i for i, frame in enumerate(frames)
                         if frame[-8, 8, 1] > 200 and frame[-8, 8, 0] < 60]
        diagnostics.append({'index': turn['index'], 'sha256': digest(path),
                            'summary': summary, 'marker_frames': marker_frames, 'frames': rows})
        del frames
    (folder/'frame-review.json').write_text(json.dumps({
        'scope': 'Every archival frame: face count, luma, adjacent pixel change and timing-marker isolation only. Archives are not receiver media. No anatomy, identity or perceptual certification.',
        'reviews': diagnostics}, indent=2)+'\n', encoding='utf-8')
    inbound = [s for s in browser.get('receiverStats', []) if s['type']=='inbound-rtp']
    receiver = []
    for stat in inbound:
        codec = next(s for s in browser['receiverStats'] if s['id']==stat['codecId'])
        receiver.append({'kind': stat['kind'], 'codec': codec['mimeType'],
            **{k: stat[k] for k in ['packetsLost','framesDecoded','framesDropped','freezeCount',
                                   'concealedSamples','concealmentEvents'] if k in stat},
            'mean_jitter_buffer_ms': stat['jitterBufferDelay']/stat['jitterBufferEmittedCount']*1000})
    cancelled = browser.get('cancelledReply')
    cancel_evidence = None
    if cancelled:
        row = next(r for r in server['rows'] if r['index']==cancelled['index'])
        cancel_evidence = {'index': row['index'], 'producer_done': row['producer_done'],
                           'error': row.get('error'),
                           'partial_archive_removed': not (folder/f"reply-{row['index']:02}.mp4").exists()}
    result = {'label': label, 'source_hashes': {'browser': digest(browser_path), 'server': digest(server_path)},
        'transport': browser.get('transport', 'mse' if label=='mse-comparison' else 'webrtc'),
        'timings_s': {key: percentiles([t[key] for t in turns]) for key in
                      ['firstVideo_s','firstAdvancingVideo_s','firstAudio_s'] if all(key in t for t in turns)},
        'first_generated_frame_s': percentiles([t['server']['first_frame_ready_s'] for t in turns]),
        'archive_frames': sum(r['summary']['decoded_frames'] for r in diagnostics),
        'archive_flagged_frames': sum(len(r['summary']['flagged_frames']) for r in diagnostics),
        'archive_timing_marker_frames': sum(len(r['marker_frames']) for r in diagnostics),
        'reply_callback_gaps_over_100ms': sum(t['longFrameGaps'] for t in turns),
        'renderer_underflows': sum(t['server']['underflows'] for t in turns),
        'page_errors': browser.get('pageErrors', []), 'media_errors': browser.get('errors', []),
        'signaling_checks': browser.get('signalingChecks', []), 'receiver': receiver,
        'jitter_targets': browser.get('jitterTargets', []), 'cancellation': cancel_evidence,
        'fixture_audio_sha256': sorted({t['server']['audio_sha256'] for t in turns}),
        'source_video_sha256': server['source_video_sha256'],
        'screenshots': {p.name: digest(p) for p in sorted(folder.glob('received-*.png'))}}
    (folder/'summary.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', nargs='+', required=True)
    args = parser.parse_args()
    if len(args.labels)>6 or any(not re.fullmatch(r'[a-z0-9-]{1,32}', label) for label in args.labels):
        parser.error('Select at most six bounded local run labels.')
    for label in args.labels:
        result = review(label)
        print(json.dumps(result), flush=True)
