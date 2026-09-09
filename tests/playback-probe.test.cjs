const test = require('node:test');
const assert = require('node:assert/strict');
const {installFrameProbe} = require('../scripts/playback_probe.cjs');

class Media extends EventTarget {
  constructor() {super(); Object.assign(this, {hidden:false, paused:false, ended:false,
    currentSrc:'synthetic.mp4', currentTime:0, duration:10});}
  requestVideoFrameCallback(callback) {this.callback = callback;}
  tick(at, count, mediaTime = at / 1000) {
    this.callback(at, {presentedFrames:count, mediaTime});
  }
  event(name) {this.dispatchEvent(new Event(name));}
}
function fixture(Observer) {
  const root = new EventTarget(); root.hidden = false;
  if (Observer) root.defaultView = {MutationObserver: Observer};
  const media = {video:new Media(), 'idle-video':new Media(), audio:new Media()};
  root.getElementById = id => media[id];
  const result = {frames:{}, avClockSkewMs:[]};
  installFrameProbe(root, result);
  return {root, media:media['idle-video'], video:media.video, audio:media.audio, result,
    stats:result.frames['idle-video']};
}

test('continuous playback records cadence and genuine long gaps', () => {
  const {media, stats} = fixture();
  media.tick(10, 1); media.tick(60, 2); media.tick(360, 3);
  assert.equal(stats.intervalSamples, 2);
  assert.equal(stats.continuousIntervalMs, 350);
  assert.equal(stats.continuousPresentedFrames, 2);
  assert.equal(stats.longGaps, 1);
  assert.equal(stats.gapSamples[0].gap_ms, 300);
});

test('pause and resume between callbacks is not a playback stall', () => {
  const {media, stats} = fixture();
  media.tick(10, 1); media.tick(60, 2);
  media.paused = true; media.event('pause'); media.paused = false;
  media.tick(5060, 3); media.tick(5110, 4);
  assert.equal(stats.longGaps, 0);
  assert.equal(stats.continuousIntervalMs, 100);
  assert.equal(stats.resets.pause, 1);
});

test('source changes and intentional seeks start new measurement intervals', () => {
  const {media, stats} = fixture();
  media.tick(10, 1); media.currentSrc = 'next.mp4'; media.tick(1000, 1);
  media.event('seeking'); media.tick(2000, 2); media.tick(2050, 3);
  assert.equal(stats.longGaps, 0);
  assert.equal(stats.intervalSamples, 1);
});

test('backgrounding and hidden frames do not inflate gap counts', () => {
  const {root, media, stats} = fixture();
  media.tick(10, 1); root.hidden = true; root.dispatchEvent(new Event('visibilitychange'));
  root.hidden = false; root.dispatchEvent(new Event('visibilitychange'));
  media.tick(1000, 2); media.hidden = true; media.tick(2000, 3);
  media.hidden = false; media.tick(3000, 4); media.tick(3050, 5);
  assert.equal(stats.longGaps, 0);
  assert.equal(stats.intervalSamples, 1);
});

test('skipped callbacks retain the browser-reported presented frame count', () => {
  const {media, stats} = fixture();
  media.tick(10, 1); media.tick(160, 4);
  assert.equal(stats.continuousPresentedFrames, 3);
  assert.equal(stats.continuousIntervalMs, 150);
  assert.equal(stats.longGaps, 0);
});

test('clock samples require simultaneously playing speech and visible video', () => {
  const {video, audio, result} = fixture();
  audio.currentTime = .95; video.tick(1000, 1, 1);
  audio.paused = true; video.tick(1050, 2, 1.05);
  audio.paused = false; video.hidden = true; video.tick(1100, 3, 1.1);
  assert.equal(result.avClockSkewMs.length, 1);
  assert.ok(Math.abs(result.avClockSkewMs[0] - 50) < .001);
});

test('redundant hidden assignments do not erase a genuine continuous gap', () => {
  const observers = new Map();
  class Observer {
    constructor(callback) {this.callback = callback;}
    observe(media, options) {observers.set(media, this.callback);assert.equal(options.attributeOldValue, true);}
  }
  const {media, stats} = fixture(Observer);
  media.tick(10, 1);
  observers.get(media)([{oldValue: null}]); // hidden=false while already visible.
  media.tick(310, 2);
  assert.equal(stats.longGaps, 1);
  // Hide/show within one microtask still marks an intentional discontinuity.
  observers.get(media)([{oldValue: null}, {oldValue: ''}]);
  media.tick(1310, 3);media.tick(1360, 4);
  assert.equal(stats.longGaps, 1);
  assert.equal(stats.resets.element_visibility, 1);
});
