"""Load only the locally reviewed, fixed-scene listening asset; no generation."""
import hashlib
import json


def load_reviewed_idle(directory):
    try:
        manifest = json.loads((directory/'idle-fullbody.json').read_text())
        if not isinstance(manifest, dict):
            return None
        video = directory/'idle-fullbody.mp4'
        if (manifest.get('version') != 1 or manifest.get('scene') != 'fullbody'
                or manifest.get('reviewed') is not True or video.stat().st_size > 10_000_000):
            return None
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        if sha(video) != manifest.get('sha256') or sha(directory/'fullbody.png') != manifest.get('reference_sha256'):
            return None
        return video
    except (OSError, ValueError, TypeError):
        return None
