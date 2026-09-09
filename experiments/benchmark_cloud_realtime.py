"""Bounded Cloudflare SFU transport test; synthetic CPU media, no camera or GPU.

Creates one temporary SFU app, connects two peers for five seconds, then closes
the peers and deletes only the app created by this invocation. No public UI.
Session IDs, SDP, IP addresses and credentials never enter the evidence file.
"""
import asyncio
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
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


async def measure(auth, result, media='both'):
    import av
    import numpy as np
    from aiortc import (RTCPeerConnection, RTCConfiguration, RTCIceServer, RTCBundlePolicy, RTCRtpSender,
                        RTCSessionDescription, VideoStreamTrack, AudioStreamTrack)

    sent_frames = {}
    transit_ms = []

    class Video(VideoStreamTrack):
        async def recv(self):
            pts, base = await self.next_timestamp()
            pixels = np.zeros((180, 320, 3), dtype=np.uint8)
            pixels[:, (pts // 3000 * 5) % 300:][:, :20] = (40, 180, 80)
            # Codec-tolerant frame counter: 16 grayscale cells, sampled centrally.
            counter = (pts // 3000) % 65536
            for bit in range(16):
                pixels[:20, bit*20:(bit+1)*20] = 240 if counter & (1 << bit) else 16
            sent_frames[counter] = time.monotonic()
            if len(sent_frames) > 1800:
                del sent_frames[next(iter(sent_frames))]
            frame = av.VideoFrame.from_ndarray(pixels, format='rgb24')
            frame.pts, frame.time_base = pts, base
            return frame

    class Tone(AudioStreamTrack):
        async def recv(self):
            frame = await super().recv()
            t = (np.arange(frame.samples) + frame.pts) / frame.sample_rate
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
        for track in tracks:
            transceiver = sender.addTransceiver(track, direction='sendonly')
            if track.kind == 'video':
                transceiver.setCodecPreferences([c for c in RTCRtpSender.getCapabilities('video').codecs
                                                if c.mimeType == 'video/H264'])
        counts = {track.kind: 0 for track in tracks}
        peaks = []

        async def receive(track):
            while True:
                frame = await track.recv()
                counts[track.kind] += 1
                if track.kind == 'audio':
                    peaks.append(int(np.abs(frame.to_ndarray().astype(np.int32)).max()))
                elif track.kind == 'video':
                    pixels = frame.to_ndarray(format='rgb24')
                    counter = sum(1 << bit for bit in range(16)
                                  if pixels[5:15, bit*20+5:bit*20+15].mean() > 128)
                    sent = sent_frames.get(counter)
                    if sent is not None:
                        transit_ms.append((time.monotonic()-sent)*1000)

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
        while not all(counts.values()) and time.monotonic() - began < 15:
            await asyncio.sleep(.05)
        result['first_both_media_after_renegotiation_s'] = round(time.monotonic() - began, 3)
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
        result['stage'] = 'finished'
    finally:
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
    args = parser.parse_args()
    configure_runtime()
    result = {'time': datetime.now(timezone.utc).isoformat(), 'passed': False, 'media': args.media,
              'scope': 'Synthetic CPU peers through Cloudflare SFU; no remote GPU, browser, model, microphone or end-to-end call latency test.'}
    try:
        asyncio.run(measure(Conversation(''), result, args.media))
    except Exception as error:
        result['error_type'] = type(error).__name__
        if isinstance(error, urllib.error.HTTPError):
            result['http_status'] = error.code
            result['diagnostic'] = getattr(error, 'transport_diagnostic', 'unknown')
    target = ROOT / f'generated/local-app/audit/cloud-realtime-transport-{args.media}.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    return 0 if result['passed'] and result.get('temporary_app_deleted') else 1


if __name__ == '__main__':
    raise SystemExit(main())
