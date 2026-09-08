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
        return {('base','closer'):{'path':assets['performance-closer.mp4'],'to':'near'},
                ('near','farther'):{'path':assets['performance-farther.mp4'],'to':'base'}}
    except (OSError,ValueError,TypeError):
        return {}
