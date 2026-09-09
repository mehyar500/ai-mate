"""Bounded Cloudflare SFU test; synthetic or reviewed generated media, no camera.

Creates one temporary SFU app, connects two peers for five seconds, then closes
the peers and deletes only the app created by this invocation. No public UI.
Session IDs, SDP, IP addresses and credentials never enter the evidence file.
"""
import asyncio
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import sys
import time
import shutil
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.cache/webrtc-deps'), str(ROOT)]

from local_app.engine import configure_runtime
from local_app.conversation import Conversation
from scripts.check_cloud_gateway import NoRedirect


def exchange(url, headers, method='POST', body=None):
    address = urlsplit(url)
    if (address.scheme != 'https' or address.netloc not in {'api.cloudflare.com', 'rtc.live.cloudflare.com'}
            or address.username or address.password or address.fragment):
        raise ValueError('Use the fixed Cloudflare API hosts')
    request = urllib.request.Request(url, headers={**headers, 'Content-Type': 'application/json',
        'User-Agent': 'AI-Mate-Transport-Probe/1.0'},
        method=method, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as response:
            raw = response.read(100_001)
    except urllib.error.HTTPError as error:
        raw = error.read(4096).lower()
        error.transport_diagnostic = ('invalid_token' if b'invalid token' in raw else
            'forbidden' if b'forbidden' in raw else 'other_http_rejection')
        raise
    if len(raw) > 100_000:
        raise ValueError('Oversized response')
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('errorCode') or data.get('success') is False:
        raise ValueError('Provider rejected request')
    tracks = data.get('tracks', [])
    if not isinstance(tracks, list) or any(not isinstance(t, dict) or t.get('errorCode') for t in tracks):
        raise ValueError('Provider rejected track')
    return data


def fixture_path(value):
    path = Path(value).resolve(strict=True)
    root = (ROOT / 'generated/local-app/audit').resolve()
    if not path.is_relative_to(root) or path.suffix != '.mp4' or path.stat().st_size > 50_000_000:
        raise ValueError('Use a bounded generated audit MP4 with a matching synthetic speech WAV')
    audio = path.with_suffix('.wav').resolve(strict=True)
    if not audio.is_relative_to(root) or audio.stat().st_size > 2_000_000:
        raise ValueError('Invalid audit speech fixture')
    return path


def live_session(engine_turns=False):
    """Reuse the existing GPU stream experiment; no new server or private data."""
    import threading
    import cv2
    from scripts.serve_webrtc_benchmark import Session, PortraitRenderer, load_reviewed_idle, preview_idle
    preview_idle()
    source = ROOT / 'generated/local-app/audit/voice-video-qualification-lip-crop-selected'
    qualification = json.loads((source/'qualification.json').read_text())
    fixtures = []
    for row in qualification['results']:
        if row['case'] in {'description', 'unsupported', 'conversation'}:
            job = row['job']
            fixtures.append({'case': row['case'], 'wav': source/'retained-media'/(job['id']+'-0.wav'),
                             'source': load_reviewed_idle(source, job['prepared_pose'])})
    if len(fixtures) != 3 or not all(f['source'] for f in fixtures):
        raise ValueError('Three reviewed synthetic fixtures required')
    renderer = PortraitRenderer(decoder_backend='tensorrt')
    renderer.prime_motion(list({f['source'] for f in fixtures}), threading.Event())
    capture = cv2.VideoCapture(str(load_reviewed_idle(source, 'base')))
    idle = []
    try:
        while len(idle) < 144:
            ok, frame = capture.read()
            if not ok:
                break
            idle.append(frame)
    finally:
        capture.release()
    if not idle:
        raise ValueError('No reviewed idle')
    folder = ROOT/'generated/local-app/audit'/('cloud-live-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(exist_ok=False)
    session = Session(renderer, idle, fixtures, folder)
    if engine_turns:
        attach_test_engine(session)
    return session


def attach_test_engine(session):
    folder, renderer = session.folder, session.renderer
    from local_app.engine import CompanionEngine, configure_runtime
    configure_runtime()
    from local_app.models import Models
    directory = folder/'engine'
    directory.mkdir()
    for name in ['fullbody.png', 'performance-near.png', 'performance.json', 'performance-closer.mp4',
                 'performance-farther.mp4', 'performance-wave.mp4', 'performance-wave.json',
                 'performance-near-wave.mp4', 'performance-near-wave.json',
                 'idle-fullbody.mp4', 'idle-fullbody.json', 'idle-near.mp4', 'idle-near.json']:
        asset = ROOT/'generated/local-app'/name
        if asset.is_file():
            shutil.copyfile(asset, directory/name)
    session.engine = CompanionEngine(directory, frame_output=session.output)
    session.engine.models = Models()
    session.engine.models.visual = renderer
    session.engine.ready = True


async def measure(auth, result, media='both', clip=None, session=None, interrupt=False):
    import av
    import numpy as np
    from aiortc import (RTCPeerConnection, RTCConfiguration, RTCIceServer, RTCBundlePolicy, RTCRtpSender,
                        RTCSessionDescription, VideoStreamTrack, AudioStreamTrack)

    sent_frames = {}
    transit_ms = []
    interrupted = None
    first_stopped_video = None
    first_silent_audio = None
    silent_frames = 0
    images, speech = [], None
    if clip:
        with av.open(str(clip)) as source:
            fps = float(source.streams.video[0].average_rate)
            for frame in source.decode(video=0):
                images.append(frame.reformat(width=384, height=576).to_ndarray(format='rgb24'))
                if len(images) > 300:
                    raise ValueError('Fixture must be at most 300 frames')
        with av.open(str(clip.with_suffix('.wav'))) as source:
            resampler = av.AudioResampler(format='s16', layout='mono', rate=48000)
            chunks = [out.to_ndarray().reshape(-1) for frame in source.decode(audio=0)
                      for out in resampler.resample(frame)]
            chunks.extend(out.to_ndarray().reshape(-1) for out in resampler.resample(None))
            speech = np.concatenate(chunks) if chunks else np.array([], dtype=np.int16)
        if not images or not len(speech) or not 1 <= fps <= 60:
            raise ValueError('Empty or invalid fixture')
        result['fixture'] = {'video_frames': len(images), 'fps': fps, 'transport_resolution': '384x576',
                             'scope': 'Previously generated clothed character and synthetic speech; replayed, then held/silenced on the same tracks.'}

    class Video(VideoStreamTrack):
        async def recv(self):
            pts, base = await self.next_timestamp()
            if images:
                index = min(len(images)-1, int(float(pts*base)*fps) % len(images))
                pixels = images[-1 if interrupted is not None else index].copy()
            else:
                pixels = np.zeros((180, 320, 3), dtype=np.uint8)
                pixels[:, (pts // 3000 * 5) % 300:][:, :20] = (40, 180, 80)
            # Codec-tolerant frame counter: 16 grayscale cells, sampled centrally.
            counter = (pts // 3000) % 65536
            for bit in range(16):
                pixels[:20, bit*20:(bit+1)*20] = 240 if counter & (1 << bit) else 16
            sent_frames[counter] = (time.monotonic(), interrupted is not None)
            if len(sent_frames) > 1800:
                del sent_frames[next(iter(sent_frames))]
            frame = av.VideoFrame.from_ndarray(pixels, format='rgb24')
            frame.pts, frame.time_base = pts, base
            return frame

    class Tone(AudioStreamTrack):
        async def recv(self):
            frame = await super().recv()
            t = (np.arange(frame.samples) + frame.pts) / frame.sample_rate
            if speech is not None:
                # Keep the base track's 20ms pacing while emitting Opus-rate PCM.
                timestamp = frame.pts * 48000 // frame.sample_rate
                frame = av.AudioFrame(format='s16', layout='mono', samples=960)
                frame.pts, frame.sample_rate, frame.time_base = timestamp, 48000, Fraction(1, 48000)
                pcm = speech[(np.arange(frame.samples)+frame.pts) % len(speech)].copy()
                if interrupted is not None:
                    pcm[:] = 0
            else:
                pcm = (3000 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
            frame.planes[0].update(pcm.tobytes())
            return frame

    api = f'https://api.cloudflare.com/client/v4/accounts/{auth.account}/calls/apps'
    app_id = None
    peers, tasks = [], []
    try:
        result['stage'] = 'create_temporary_app'
        created = await asyncio.to_thread(exchange, api, auth.cf_headers, 'POST',
                                         {'name': 'AI Mate temporary transport probe'})
        app_id = created['result']['uid']
        headers = {'Authorization': 'Bearer ' + created['result']['secret']}
        base = f'https://rtc.live.cloudflare.com/v1/apps/{app_id}'
        config = RTCConfiguration(iceServers=[RTCIceServer('stun:stun.cloudflare.com:3478')],
                                  bundlePolicy=RTCBundlePolicy.BALANCED)
        sender, receiver = RTCPeerConnection(config), RTCPeerConnection(config)
        peers.extend([sender, receiver])
        tracks = [Tone(), Video()] if media == 'both' else [Video()] if media == 'video' else [Tone()]
        if session:
            from scripts.serve_webrtc_benchmark import Picture, Speech
            tracks = [Speech(session), Picture(session)]
        for track in tracks:
            transceiver = sender.addTransceiver(track, direction='sendonly')
            if track.kind == 'video':
                transceiver.setCodecPreferences([c for c in RTCRtpSender.getCapabilities('video').codecs
                                                if c.mimeType == 'video/H264'])
        counts = {track.kind: 0 for track in tracks}
        peaks = []

        async def receive(track):
            nonlocal first_stopped_video, first_silent_audio, silent_frames
            while True:
                frame = await track.recv()
                counts[track.kind] += 1
                if track.kind == 'audio':
                    peak = int(np.abs(frame.to_ndarray().astype(np.int32)).max())
                    peaks.append(peak)
                    if interrupted is not None:
                        silent_frames = silent_frames+1 if peak < 100 else 0
                        if silent_frames >= 3 and first_silent_audio is None:
                            first_silent_audio = time.monotonic()
                elif track.kind == 'video':
                    pixels = frame.to_ndarray(format='rgb24')
                    if session:
                        marker = pixels[-12:-4, 4:12].mean(axis=(0, 1))
                        row = session.clip
                        if row and marker[1] > 200 and marker[2] < 40 and abs(marker[0]-row['index']*9) < 5:
                            row.setdefault('first_decoded_frame_s', time.perf_counter()-row['started'])
                        continue
                    counter = sum(1 << bit for bit in range(16)
                                  if pixels[5:15, bit*20+5:bit*20+15].mean() > 128)
                    sent = sent_frames.get(counter)
                    if sent is not None:
                        transit_ms.append((time.monotonic()-sent[0])*1000)
                        if sent[1] and first_stopped_video is None:
                            first_stopped_video = time.monotonic()

        @receiver.on('track')
        def on_track(track):
            tasks.append(asyncio.create_task(receive(track)))

        result['stage'] = 'create_publisher_session'
        publisher = await asyncio.to_thread(exchange, base + '/sessions/new', headers)
        result['stage'] = 'publish_tracks'
        await sender.setLocalDescription(await sender.createOffer())
        published = await asyncio.to_thread(exchange, base + '/sessions/' + publisher['sessionId'] + '/tracks/new',
            headers, 'POST', {'sessionDescription': {'type': 'offer', 'sdp': sender.localDescription.sdp},
            'tracks': [{'location': 'local', 'mid': t.mid, 'trackName': t.sender.track.id}
                       for t in sender.getTransceivers()]})
        await sender.setRemoteDescription(RTCSessionDescription(**published['sessionDescription']))
        deadline = time.monotonic() + 15
        while sender.connectionState != 'connected' and time.monotonic() < deadline:
            await asyncio.sleep(.05)
        if sender.connectionState != 'connected':
            raise TimeoutError('Publisher connection failed')
        result['stage'] = 'subscribe'
        subscriber = await asyncio.to_thread(exchange, base + '/sessions/new', headers)
        pulled = await asyncio.to_thread(exchange, base + '/sessions/' + subscriber['sessionId'] + '/tracks/new',
            headers, 'POST', {'tracks': [{'location': 'remote', 'sessionId': publisher['sessionId'],
                                         'trackName': t.id} for t in tracks]})
        await receiver.setRemoteDescription(RTCSessionDescription(**pulled['sessionDescription']))
        await receiver.setLocalDescription(await receiver.createAnswer())
        await asyncio.to_thread(exchange, base + '/sessions/' + subscriber['sessionId'] + '/renegotiate',
            headers, 'PUT', {'sessionDescription': {'type': 'answer', 'sdp': receiver.localDescription.sdp}})
        result['stage'] = 'receive_media'
        began = time.monotonic()
        last_keyframe_request = began-1
        while not all(counts.values()) and time.monotonic() - began < 15:
            if (clip or session) and receiver.connectionState == 'connected' and time.monotonic()-last_keyframe_request >= 1:
                # Experimental aiortc hook: force an IDR for a late subscriber.
                for transceiver in sender.getTransceivers():
                    if transceiver.kind == 'video':
                        transceiver.sender._send_keyframe()
                last_keyframe_request = time.monotonic()
            await asyncio.sleep(.05)
        result['first_both_media_after_renegotiation_s'] = round(time.monotonic() - began, 3)
        if session:
            if not all(counts.values()):
                raise TimeoutError('Live stream receiver unavailable')
            session.receiver_ready = True
            for index in range(len(session.fixtures)):
                if getattr(session, 'engine', None):
                    command = ['Wave hello.', 'Stop moving.', 'Wave hello.'][index]
                    started = time.perf_counter()
                    first_row = len(session.rows)
                    key = session.engine.submit(command, 'video', 'fullbody')
                    deadline = time.monotonic()+30
                    while time.monotonic() < deadline:
                        if not session.engine.busy and len(session.rows) > first_row and session.clip['finished']:
                            break
                        if not session.engine.busy and session.engine.job(key)['state'] != 'done':
                            raise RuntimeError('Engine reply failed')
                        await asyncio.sleep(.02)
                    if session.engine.busy or not session.clip['finished']:
                        session.engine.cancel(key)
                        raise TimeoutError('Engine playback did not finish')
                    row = session.rows[first_row]
                    job = session.engine.job(key)
                    result.setdefault('engine_turns', []).append({'command': command, 'state': job['state'],
                        'action': job['action'], 'metrics': job['metrics'],
                        'first_decoded_from_submit_s': round(row['started']-started+row['first_decoded_frame_s'], 3)})
                    continue
                await asyncio.to_thread(session.begin, index)
                deadline = time.monotonic()+30
                while not session.clip['finished'] and time.monotonic() < deadline:
                    if interrupt and index == 2 and session.clip.get('first_decoded_frame_s') is not None:
                        session.cancel.set()
                        queued = session.clip['queue'].qsize()
                        await asyncio.sleep(.5)
                        result['live_cancellation'] = {'queued_at_stop': queued,
                            'queued_after_stop': session.clip['queue'].qsize(),
                            'last_five_audio_peak': max(peaks[-5:], default=32767),
                            'renegotiated': False}
                        break
                    await asyncio.sleep(.02)
                if not session.clip['finished'] and not session.cancel.is_set():
                    raise TimeoutError('GPU stream did not finish')
                await asyncio.sleep(.3)
            result['live_rows'] = session.safe_rows()
        elif clip:
            await asyncio.sleep(2)
            interrupted = time.monotonic()
            await asyncio.sleep(3)
            result['interruption_ms'] = {
                'first_held_video': round((first_stopped_video-interrupted)*1000, 1) if first_stopped_video else None,
                'three_quiet_audio_frames': round((first_silent_audio-interrupted)*1000, 1) if first_silent_audio else None,
                'renegotiated': False}
        else:
            await asyncio.sleep(5)
        result.update(received_frames=counts, audio_peak=max(peaks, default=0),
            sender_connected=sender.connectionState == 'connected',
            receiver_connected=receiver.connectionState == 'connected')
        result['sent_packets'] = {s.kind: s.packetsSent for s in (await sender.getStats()).values()
                                  if s.type == 'outbound-rtp'}
        result['received_packets'] = {s.kind: s.packetsReceived for s in (await receiver.getStats()).values()
                                      if s.type == 'inbound-rtp'}
        result['video_codec'] = 'H264'
        if transit_ms:
            result['video_encode_transport_decode_ms'] = {
                'samples': len(transit_ms),
                'median': round(float(np.median(transit_ms)), 1),
                'p95': round(float(np.percentile(transit_ms, 95)), 1),
                'max': round(max(transit_ms), 1),
                'scope': 'Same-process monotonic frame creation to received decoded frame; includes codec, SFU and jitter buffering, excludes inference, browser and physical display.'}
        result['bundle_policy'] = 'balanced'
        result['passed'] = (counts.get('video', 60) >= 60 and counts.get('audio', 100) >= 100
                            and ('audio' not in counts or max(peaks, default=0) > 100))
        if clip:
            result['passed'] = result['passed'] and first_stopped_video is not None and first_silent_audio is not None
        if session:
            result['passed'] = result['passed'] and all(
                row.get('first_decoded_frame_s') is not None and not row.get('error')
                for row in result['live_rows'] if not (interrupt and row['index'] == 3))
            if interrupt:
                stopped = result.get('live_cancellation', {})
                result['passed'] = result['passed'] and stopped.get('last_five_audio_peak', 32767) < 100
        result['stage'] = 'finished'
    finally:
        if session:
            session.cancel.set()
            for row in session.rows:
                await asyncio.to_thread(row['worker'].join, 10)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for peer in peers:
            await peer.close()
        if app_id:
            try:
                await asyncio.to_thread(exchange, api + '/' + app_id, auth.cf_headers, 'DELETE')
                result['temporary_app_deleted'] = True
            except (OSError, ValueError):
                result['temporary_app_deleted'] = False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--media', choices=['audio', 'video', 'both'], default='both')
    parser.add_argument('--clip', type=fixture_path, help='Reviewed generated audit MP4 plus matching synthetic WAV; sends both through Cloudflare')
    parser.add_argument('--live-render', action='store_true', help='Stream new GPU lip frames for three retained synthetic speech fixtures')
    parser.add_argument('--interrupt', action='store_true', help='Cancel the third live-render reply during playback')
    parser.add_argument('--engine-turns', action='store_true', help='Use isolated real dialogue/speech engine turns with --live-render')
    args = parser.parse_args()
    if args.clip and args.media != 'both':
        parser.error('--clip requires --media both')
    if args.live_render and (args.clip or args.media != 'both'):
        parser.error('--live-render requires both media and no --clip')
    if args.interrupt and not args.live_render:
        parser.error('--interrupt requires --live-render')
    if args.engine_turns and (not args.live_render or args.interrupt):
        parser.error('--engine-turns requires --live-render without --interrupt')
    configure_runtime()
    result = {'time': datetime.now(timezone.utc).isoformat(), 'passed': False, 'media': args.media,
              'scope': 'CPU peers through Cloudflare SFU; synthetic media or prerecorded generated fixture. No live inference, browser, microphone or end-to-end call latency test.'}
    if args.live_render:
        result['scope'] = ('Live local GPU lip rendering over reviewed body clips and retained synthetic speech through Cloudflare SFU. '
                           'No ASR, dialogue, TTS, browser display, private conversation or arbitrary-motion test.')
    if args.engine_turns:
        result['scope'] = ('Isolated text commands through real engine planning, TTS, GPU lip rendering and Cloudflare SFU. '
                           'Prepared body motion; no microphone, browser presentation or unrestricted-motion acceptance.')
    try:
        session = live_session(args.engine_turns) if args.live_render else None
        asyncio.run(measure(Conversation(''), result, args.media, args.clip, session, args.interrupt))
    except Exception as error:
        result['error_type'] = type(error).__name__
        if isinstance(error, urllib.error.HTTPError):
            result['http_status'] = error.code
            result['diagnostic'] = getattr(error, 'transport_diagnostic', 'unknown')
    target = ROOT / f'generated/local-app/audit/cloud-realtime-transport-{"engine" if args.engine_turns else "live-cancel" if args.interrupt else "live" if args.live_render else "fixture" if args.clip else args.media}.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    return 0 if result['passed'] and result.get('temporary_app_deleted') else 1


if __name__ == '__main__':
    raise SystemExit(main())
