"""Inspect only the two isolated synthetic playback-continuity trials."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT/'generated/local-app/audit'


def main():
    rows = []
    for label in ['interruption', 'interruption-middle']:
        folder = AUDIT/('speech-' + label)
        result = json.loads((folder/'browser-results.json').read_text())
        browser = cv2.imread(str(folder/'browser-held.png'))
        saved = cv2.imread(str(folder/'interrupted-pose.png'))
        if browser is None or saved is None or browser.shape != saved.shape:
            raise ValueError('The browser and engine must both have a saved frame.')
        row = {'case': label, 'stop': result['stopped'], 'approach_state': result['approachState'],
               'held_vs_saved_channel_mae_0_255': float(np.abs(browser.astype(float)-saved).mean()),
               'page_errors': result['pageErrors'], 'turns': {}}
        for name in ['ordinary', 'return']:
            job = result[name]
            row['turns'][name] = {'state': job['state'], 'action': job['action'],
                'prepared_pose': job['prepared_pose'], 'server_s': job['metrics']['total_s'],
                'browser_metrics': result.get('ordinaryMetrics' if name == 'ordinary' else 'movementMetrics'),
                'transition_start_s': job['chunks'][0]['render'].get('transition_start_s')}
        names = ['browser-results.json', 'engine-results.json', 'browser-held.png', 'interrupted-pose.png',
                 'stopped-screen.png', 'reply-from-stopped-pose.png', 'return-from-stopped-pose.png']
        row['sha256'] = {name: hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in names}
        rows.append(row)
    report = {'samples': rows, 'limits': [
        'Synthetic ASR and planner; real CPU Kokoro, GPU MuseTalk, HTTP, MSE and browser cancellation.',
        'Two stop positions, not p50/p95, arbitrary movement acceptance or acoustic device testing.',
        'Low image difference checks saved position, not facial realism. Mouth artifacts and crop remain.',
        'First two harness attempts awaited the whole submit promise; they stopped in phrase 2 and did not qualify mid-motion interruption.'
    ]}
    (AUDIT/'playback-continuity-review.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
