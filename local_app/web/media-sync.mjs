// The video clock drives the separate PCM/WAV speech track, including stalls.
export function synchronizeSpeech(video, audio, {signal, onBlocked = () => {}} = {}) {
  let disposed = false, starting = false;
  const listeners = [];
  const listen = (event, fn) => { video.addEventListener(event, fn); listeners.push([event, fn]); };
  const align = () => {
    if (Number.isFinite(audio.duration) && Math.abs(audio.currentTime - video.currentTime) > .12)
      audio.currentTime = Math.min(video.currentTime, audio.duration);
  };
  const start = async () => {
    if (disposed || starting || video.paused || video.ended) return;
    align();
    if (audio.ended) return;
    starting = true;
    try {
      await audio.play();
      if (disposed || video.paused || video.ended || video.readyState < 3) audio.pause();
    } catch (error) {
      if (!disposed && error.name !== 'AbortError') { video.pause(); onBlocked(error); }
    } finally { starting = false; }
  };
  listen('playing', start);
  listen('waiting', () => audio.pause());
  listen('pause', () => audio.pause());
  listen('seeking', () => { audio.pause(); align(); });
  listen('seeked', start);
  listen('timeupdate', align);
  listen('ratechange', () => { audio.playbackRate = video.playbackRate; });
  const dispose = () => {
    disposed = true;
    for (const [event, fn] of listeners) video.removeEventListener(event, fn);
    signal?.removeEventListener('abort', dispose);
    audio.pause();
  };
  signal?.addEventListener('abort', dispose, {once: true});
  if (signal?.aborted) dispose();
  return dispose;
}
