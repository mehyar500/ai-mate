"""Reviewed media assets and playback continuity for the local call engine."""
import hashlib
import json
import math


def load_reviewed_idle(directory, pose='base'):
    if pose not in {'base','near'}:
        return None
    name='fullbody' if pose=='base' else 'near'
    reference='fullbody.png' if pose=='base' else 'performance-near.png'
    try:
        manifest = json.loads((directory/f'idle-{name}.json').read_text())
        if not isinstance(manifest, dict):
            return None
        video = directory/f'idle-{name}.mp4'
        if (manifest.get('version') != 1 or manifest.get('scene') != 'fullbody'
                or manifest.get('pose','base') != pose
                or manifest.get('reviewed') is not True or video.stat().st_size > 10_000_000):
            return None
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        if sha(video) != manifest.get('sha256') or sha(directory/reference) != manifest.get('reference_sha256'):
            return None
        return video
    except (OSError, ValueError, TypeError):
        return None




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
        for pose, reference in [('base', 'fullbody.png'), ('near', 'performance-near.png')]:
            wave = load_reviewed_wave(directory, hashes[reference], pose=pose)
            if wave:
                result[(pose, 'wave')] = wave
        return result
    except (OSError,ValueError,TypeError):
        return {}


def load_reviewed_wave(directory, reference_hash, *, pose='base'):
    if pose not in {'base', 'near'}:
        return None
    stem = 'performance-wave' if pose == 'base' else 'performance-near-wave'
    reference = 'fullbody.png' if pose == 'base' else 'performance-near.png'
    try:
        record = directory/(stem+'.json')
        if record.stat().st_size > 16384:
            return None
        manifest = json.loads(record.read_text())
        if not isinstance(manifest, dict) or manifest.get('version') != 1 or manifest.get('reviewed') is not True:
            return None
        if pose == 'near' and manifest.get('pose') != 'near':
            return None
        hashes = manifest.get('sha256', {})
        path = directory/(stem+'.mp4')
        if not isinstance(hashes, dict) or hashes.get(reference) != reference_hash:
            return None
        if not 0 < path.stat().st_size <= 40_000_000 or hashlib.sha256(path.read_bytes()).hexdigest() != hashes.get(path.name):
            return None
        return {'path': path, 'from': pose, 'to': pose, 'kind': 'gesture'}
    except (OSError, ValueError, TypeError):
        return None




def validate_playback(value):
    if not isinstance(value, dict) or set(value) != {'index', 'time_s'}:
        raise ValueError('Use a playback index and time in seconds.')
    index, seconds = value['index'], value['time_s']
    if type(index) is not int or not 0 <= index < 100:
        raise ValueError('Invalid playback index.')
    if type(seconds) not in {int, float} or not math.isfinite(seconds) or not 0 <= seconds <= 30:
        raise ValueError('Invalid playback time.')
    return index, seconds


def video_duration(path):
    import cv2
    capture = cv2.VideoCapture(str(path))
    try:
        fps, frames = capture.get(cv2.CAP_PROP_FPS), capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if not 1 <= fps <= 60 or not 1 <= frames <= 1800 or frames / fps > 30:
            raise ValueError('Prepared movement has invalid timing.')
        return frames / fps
    except cv2.error:
        raise ValueError('Prepared movement could not be inspected.') from None
    finally:
        capture.release()


def capture_playback_frame(source, destination, seconds):
    """Decode a bounded fMP4 prefix; its container frame estimate can be wrong."""
    import cv2
    capture = cv2.VideoCapture(str(source))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not 1 <= fps <= 60:
            raise ValueError('Playback timing is unavailable.')
        frame = None
        actual = -1
        selected_index = -1
        previous = -1
        for index in range(1800):
            ok, candidate = capture.read()
            if not ok:
                break
            timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if not math.isfinite(timestamp) or timestamp < 0 or (index and timestamp <= previous):
                raise ValueError('Decoded playback timestamps are unavailable.')
            previous = timestamp
            if timestamp > seconds + .001:
                break
            if candidate.shape[0] * candidate.shape[1] > 1920 * 1920:
                raise ValueError('Playback frame is too large.')
            frame, actual, selected_index = candidate, timestamp, index
        # Permit one frame's rounding or a short AAC tail, never an unseen endpoint.
        if frame is None or seconds - actual > max(.15, 1 / fps):
            raise ValueError('That playback position is not available yet.')
        if not cv2.imwrite(str(destination), frame):
            raise RuntimeError('Could not preserve the playback position.')
        return {'time_s': actual, 'frame': selected_index}
    except cv2.error:
        raise ValueError('Playback frame could not be decoded or saved.') from None
    finally:
        capture.release()


def stopped_pose(metadata, seconds):
    """Retain approach progress; an interrupted gesture is an unknown held pose."""
    transition = metadata.get('transition')
    if transition:
        progress = min(1.0, (metadata['start_s'] + seconds) / video_duration(transition['path']))
        if transition.get('kind') == 'gesture':
            # A raised hand is not a position on the approach/return path. Keep
            # the captured frame, and only resume the idle after full completion.
            return (transition['to'], None) if progress >= 1 else (None, None)
        cursor = progress if transition['to'] == 'near' else 1.0 - progress
        pose = 'base' if cursor <= 0 else 'near' if cursor >= 1 else None
        return pose, cursor
    return metadata['pose'], metadata['cursor']
