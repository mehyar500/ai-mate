"""One optional fixed-audio recognition warm-up; never queues user utterances."""
from concurrent.futures import ThreadPoolExecutor
import os
import threading
import time


def pause_warm_enabled(environ=None):
    value = (os.environ if environ is None else environ).get('AI_MATE_ASR_PAUSE_WARM', '0')
    if value not in {'0', '1'}:
        raise ValueError('AI_MATE_ASR_PAUSE_WARM must be 0 or 1.')
    return value == '1'


class RecognitionWarmup:
    def __init__(self, prepare, *, now=time.monotonic, cooldown_s=2):
        self.prepare, self.now, self.cooldown_s = prepare, now, cooldown_s
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='recognition-warm')
        self.lock = threading.Lock()
        self.future = None
        self.next_allowed = 0.
        self.enabled = True

    def request(self):
        with self.lock:
            if not self.enabled or self.now() < self.next_allowed or (self.future and not self.future.done()):
                return False
            self.next_allowed = self.now() + self.cooldown_s
            self.future = self.pool.submit(self.run)
            return True

    def run(self):
        started = time.perf_counter()
        try:
            self.prepare()  # Fixed startup-generated audio; ignore the transcript.
            return {'warm_s': time.perf_counter() - started, 'ok': True}
        except Exception as error:
            # An optimization failure must not replace the real utterance or
            # expose transcripts/provider details. Disable until restart.
            with self.lock:
                self.enabled = False
            return {'warm_s': time.perf_counter() - started, 'ok': False,
                    'error_type': type(error).__name__}

    def finish(self):
        with self.lock:
            future = self.future
        if future is None:
            return None
        started = time.perf_counter()
        result = dict(future.result())
        result['wait_s'] = time.perf_counter() - started
        with self.lock:
            if self.future is future:
                self.future = None
        return result

    def close(self):
        with self.lock:
            self.enabled = False
        self.pool.shutdown(wait=True, cancel_futures=True)
