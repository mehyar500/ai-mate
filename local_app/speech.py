"""Bounded speech phrases and one-ahead synthesis for call playback."""
from concurrent.futures import ThreadPoolExecutor
import re
import time

from .models import check_cancel


def speech_phrases(text):
    """Preserve every word; prefer punctuation and keep the first phrase short."""
    remaining = ' '.join(text.split())
    result = []
    while remaining:
        limit = 72 if not result else 120
        if len(remaining) <= limit:
            result.append(remaining)
            break
        # Punctuation followed by whitespace avoids splitting decimals/initials.
        boundaries = list(re.finditer(r'[.!?;,](?=\s)', remaining[:limit + 1]))
        candidates = [m.end() for m in boundaries if m.end() >= 24]
        cut = candidates[-1] if candidates else remaining.rfind(' ', 0, limit + 1)
        if cut <= 0:
            # Never split a long word or pronounce its two halves separately.
            cut = remaining.find(' ', limit)
            if cut < 0:
                cut = len(remaining)
        result.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    return result


class SpeechPrefetch:
    """Only one TTS call runs at once; finish it before cancellation cleanup."""
    def __init__(self, models, phrases, directory, key, event):
        self.models, self.phrases = models, phrases
        self.directory, self.key, self.event = directory, key, event
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='speech')
        self.future = self.pool.submit(self.synthesize, 0) if phrases else None

    def synthesize(self, index):
        check_cancel(self.event)
        path = self.directory / f'{self.key}-{index}.wav'
        start = time.perf_counter()
        duration = self.models.speech(self.phrases[index], path)
        check_cancel(self.event)
        return path, duration, round(time.perf_counter() - start, 3)

    def take(self, index):
        result = self.future.result()
        check_cancel(self.event)
        self.future = (self.pool.submit(self.synthesize, index + 1)
                       if index + 1 < len(self.phrases) else None)
        return result

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=True)
