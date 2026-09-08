"""Bounded CPU inspection of engine-owned video, never client-supplied media."""
import math


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
    """Normalized progress through the reviewed base-to-near performance."""
    transition = metadata.get('transition')
    if transition:
        progress = min(1.0, (metadata['start_s'] + seconds) / video_duration(transition['path']))
        cursor = progress if transition['to'] == 'near' else 1.0 - progress
        pose = 'base' if cursor <= 0 else 'near' if cursor >= 1 else None
        return pose, cursor
    return metadata['pose'], metadata['cursor']
