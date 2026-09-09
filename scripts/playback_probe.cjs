// Self-contained browser instrumentation for synthetic call qualifications.
// Deliberate pause/source/visibility changes start a new continuous interval;
// a slow callback during uninterrupted playback remains a measured gap.
function installFrameProbe(root = document, target = window.qual) {
  const audio = root.getElementById('audio');
  for (const id of ['video', 'idle-video']) {
    const media = root.getElementById(id);
    const stats = target.frames[id] = {
      callbacks: 0, intervalSamples: 0, continuousIntervalMs: 0,
      continuousPresentedFrames: 0, longGaps: 0, maxGapMs: 0,
      intervalHistogramMs: {}, gapSamples: [], resets: {},
      scope: 'Presented-frame callbacks during uninterrupted visible playback. '
        + 'Intentional pauses/source/visibility changes excluded; physical display not measured.'
    };
    let previous = null;
    const reset = reason => {
      previous = null;
      stats.resets[reason] = (stats.resets[reason] || 0) + 1;
    };
    for (const event of ['pause', 'emptied', 'loadstart', 'seeking'])
      media.addEventListener(event, () => reset(event));
    root.addEventListener('visibilitychange', () => reset('document_visibility'));
    const Observer = root.defaultView?.MutationObserver;
    if (Observer) new Observer(records => {
      if (records.some(record => (record.oldValue !== null) !== media.hidden))
        reset('element_visibility');
    }).observe(media, {
      attributes: true, attributeFilter: ['hidden'], attributeOldValue: true
    });
    const frame = (now, metadata) => {
      stats.callbacks++;
      const visible = !root.hidden && !media.hidden && !media.paused && !media.ended;
      if (id === 'video' && visible && !audio.paused && !audio.ended && Number.isFinite(audio.duration))
        target.avClockSkewMs.push(Math.abs(metadata.mediaTime - audio.currentTime) * 1000);
      if (visible && previous && previous.source === media.currentSrc) {
        const elapsed = now - previous.at;
        const presented = metadata.presentedFrames - previous.presented;
        if (elapsed > 0 && Number.isFinite(elapsed) && presented > 0) {
          stats.intervalSamples++;
          stats.continuousIntervalMs += elapsed;
          stats.continuousPresentedFrames += presented;
          const bin = Math.min(5000, Math.round(elapsed / 5) * 5);
          stats.intervalHistogramMs[bin] = (stats.intervalHistogramMs[bin] || 0) + 1;
          stats.maxGapMs = Math.max(stats.maxGapMs, elapsed);
          if (elapsed > 250) {
            stats.longGaps++;
            if (stats.gapSamples.length < 100) stats.gapSamples.push({
              at_ms: now, gap_ms: elapsed, frames_delta: presented,
              media_delta_s: metadata.mediaTime - previous.mediaTime
            });
          }
        }
      }
      previous = visible ? {at: now, source: media.currentSrc,
        presented: metadata.presentedFrames, mediaTime: metadata.mediaTime} : null;
      media.requestVideoFrameCallback(frame);
    };
    media.requestVideoFrameCallback(frame);
  }
}

module.exports = {installFrameProbe};
