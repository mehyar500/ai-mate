"""Verified prepared body transitions; only the engine chooses a pose/action pair."""
import hashlib
import json


def load_reviewed_performance(directory):
    try:
        record=directory/'performance.json'
        if record.stat().st_size>16384:
            return {}
        manifest=json.loads(record.read_text())
        if not isinstance(manifest,dict) or manifest.get('version')!=1 or manifest.get('reviewed') is not True:
            return {}
        assets={name:directory/name for name in ['fullbody.png','performance-near.png',
                                                 'performance-closer.mp4','performance-farther.mp4']}
        hashes=manifest.get('sha256',{})
        if not isinstance(hashes,dict):
            return {}
        for name,path in assets.items():
            if not 0<path.stat().st_size<=40_000_000 or hashlib.sha256(path.read_bytes()).hexdigest()!=hashes.get(name):
                return {}
        result = {('base','closer'):{'path':assets['performance-closer.mp4'],'to':'near'},
                  ('near','farther'):{'path':assets['performance-farther.mp4'],'to':'base'}}
        # A gesture needs its own review and matching identity reference. Failure
        # disables only that optional gesture, not the verified approach/return.
        wave = load_reviewed_wave(directory, hashes['fullbody.png'])
        if wave:
            result[('base','wave')] = wave
        return result
    except (OSError,ValueError,TypeError):
        return {}


def load_reviewed_wave(directory, reference_hash):
    try:
        record = directory/'performance-wave.json'
        if record.stat().st_size > 16384:
            return None
        manifest = json.loads(record.read_text())
        if not isinstance(manifest, dict) or manifest.get('version') != 1 or manifest.get('reviewed') is not True:
            return None
        hashes = manifest.get('sha256', {})
        path = directory/'performance-wave.mp4'
        if not isinstance(hashes, dict) or hashes.get('fullbody.png') != reference_hash:
            return None
        if not 0 < path.stat().st_size <= 40_000_000 or hashlib.sha256(path.read_bytes()).hexdigest() != hashes.get(path.name):
            return None
        return {'path': path, 'from': 'base', 'to': 'base', 'kind': 'gesture'}
    except (OSError, ValueError, TypeError):
        return None
