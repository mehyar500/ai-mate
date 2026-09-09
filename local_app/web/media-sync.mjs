// iPhone exposes ManagedMediaSource instead of the desktop MediaSource API.
export function streamingSource(media, mime, scope = globalThis) {
  for (const Source of [scope.MediaSource, scope.ManagedMediaSource]) {
    if (!Source?.isTypeSupported?.(mime)) continue;
    // WebKit requires either an AirPlay alternative or explicit remote-playback
    // disabling. This private live stream has no separate AirPlay rendition.
    if (Source === scope.ManagedMediaSource) media.disableRemotePlayback = true;
    return new Source();
  }
  return null;
}

// The video clock drives the separate PCM/WAV speech track, including stalls.
export function synchronizeSpeech(video, audio, {signal, onBlocked = () => {}} = {}) {
  let disposed = false, starting = false;
  const listeners = [];
  const listen = (event, fn) => { video.addEventListener(event, fn); listeners.push([event, fn]); };
  const align = () => {
    if (!Number.isFinite(audio.duration)) return;
    const target = Math.min(video.currentTime, audio.duration);
    // A gesture can continue after speech. Re-seeking an ended WAV to its end
    // on every video tick produces repeated ended events in Chromium.
    if (Math.abs(audio.currentTime - target) > .12) audio.currentTime = target;
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
