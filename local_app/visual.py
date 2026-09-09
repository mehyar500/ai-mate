"""Constrained MuseTalk 1.5 portrait lip-sync, not full-body/live video synthesis.

Inference equations follow TMElyralab/MuseTalk (MIT, Copyright 2024 Tencent).
The local adapter uses a fixed reviewed crop and feathered mask, avoiding the
upstream training/pose stack. Dependencies and model licenses remain separate.
"""
from collections import OrderedDict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time

from .models import CACHE, ROOT, check_cancel


def audio_left_padding(fps):
    """MuseTalk v1.5 uses two video frames of Whisper context, rounded up."""
    if not math.isfinite(fps) or not 1 <= fps <= 60:
        raise ValueError('Invalid video frame rate.')
    return 2 * math.ceil(50 / fps)


def motion_duration(speech_seconds, source_frames, source_fps, *, loop=False, start_s=0):
    """Ambient footage follows speech; deliberate gestures must finish."""
    if not math.isfinite(speech_seconds) or not 0 < speech_seconds <= 30:
        raise ValueError("Visual replies need nonempty speech of at most 30 seconds.")
    if not 1 <= source_fps <= 60 or not 1 <= source_frames <= 1800:
        raise RuntimeError("The generated movement has invalid timing.")
    if not math.isfinite(start_s) or start_s < 0 or (not loop and start_s > source_frames/source_fps):
        raise ValueError('Invalid movement starting position.')
    duration = speech_seconds if loop else max(speech_seconds, source_frames/source_fps - start_s)
    if duration > 30:
        raise ValueError("Visual replies are limited to 30 seconds.")
    return duration


class PortraitRenderer:
    def __init__(self, face_shift=-.10):
        if not math.isfinite(face_shift) or not -.2 <= face_shift <= .05:
            raise ValueError('Face crop adjustment is out of range.')
        self.face_shift = face_shift
        import cv2
        import numpy as np
        import torch
        from diffusers import AutoencoderKL, UNet2DConditionModel
        from transformers import WhisperFeatureExtractor, WhisperModel
        self.cv, self.np, self.torch = cv2, np, torch
        if not torch.cuda.is_available():
            raise RuntimeError("Portrait rendering needs the local CUDA GPU.")
        torch.set_num_threads(4)
        # Autotuning introduced a 47-second cold render with little warm benefit.
        torch.backends.cudnn.benchmark = False
        self.dtype = torch.float16
        self.vae = AutoencoderKL.from_pretrained(str(CACHE / "sd-vae"), torch_dtype=self.dtype, local_files_only=True).to("cuda").to(memory_format=torch.channels_last).eval()
        config = json.loads((CACHE / "musetalk/musetalkV15/musetalk.json").read_text())
        self.unet = UNet2DConditionModel.from_config(config)
        weights = torch.load(CACHE / "musetalk/musetalkV15/unet.pth", map_location="cpu", weights_only=True)
        self.unet.load_state_dict(weights)
        del weights
        self.unet = self.unet.to("cuda", self.dtype).to(memory_format=torch.channels_last).eval()
        self.whisper = WhisperModel.from_pretrained(str(CACHE / "whisper-tiny"), local_files_only=True).encoder.to("cuda", self.dtype).eval()
        self.features = WhisperFeatureExtractor.from_pretrained(str(CACHE / "whisper-tiny"), local_files_only=True)
        pos = torch.arange(50, dtype=torch.float32).unsqueeze(1)
        div = torch.exp(torch.arange(0, 384, 2).float() * (-math.log(10000) / 384))
        pe = torch.zeros(50, 384)
        pe[:, 0::2], pe[:, 1::2] = torch.sin(pos * div), torch.cos(pos * div)
        self.pe = pe.unsqueeze(0).to("cuda", self.dtype)
        self.portrait = None
        probe = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                                "color=c=gray:s=64x64:r=25:d=0.04", "-c:v", "h264_nvenc", "-f", "null", "-"],
                               capture_output=True, timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.encoder = "h264_nvenc" if probe.returncode == 0 else "libx264"
        if self.encoder == "libx264":
            print("NVENC is unavailable with this FFmpeg/driver pair; using CPU H.264 encoding.", flush=True)

    def prepare(self, scene="mira", reference_path=None):
        path = Path(reference_path) if reference_path else ROOT / "generated/local-app" / (scene + ".png")
        reference_key = (str(path), path.stat().st_mtime_ns, self.face_shift)
        if self.portrait is not None and getattr(self, "reference_key", None) == reference_key:
            return
        cv, np, torch = self.cv, self.np, self.torch
        frame = cv.imread(str(path))
        if frame is None:
            raise RuntimeError("Prepare the local portrait before starting video replies.")
        detector = cv.FaceDetectorYN.create(str(CACHE / "yunet.onnx"), "", (frame.shape[1], frame.shape[0]), .8, .3, 5000)
        _, faces = detector.detect(frame)
        if faces is None or len(faces) != 1:
            raise RuntimeError("The prepared scene needs one clear frontal face.")
        face = faces[0]
        x, y, w, h = map(float, face[:4])
        nose_y = float(face[9])
        mouth_x = float(face[10]+face[12])/2
        mouth_y = float(face[11]+face[13])/2
        crop_config = path.with_suffix(".json")
        if crop_config.exists() and "crop" in json.loads(crop_config.read_text()):
            box = json.loads(crop_config.read_text())["crop"]
        else:
            mid_face = nose_y + self.face_shift*h
            box = [max(0, int(x)), max(0, int(2*mid_face-(y+h))), min(frame.shape[1], int(x+w)), min(frame.shape[0], int(y+h+10))]
        x1, y1, x2, y2 = map(int, box)
        if not (0 <= x1 < x2 <= frame.shape[1] and 0 <= y1 < y2 <= frame.shape[0]):
            raise RuntimeError("Portrait crop falls outside the image.")
        crop = cv.resize(frame[y1:y2, x1:x2], (256, 256), interpolation=cv.INTER_LANCZOS4)
        rgb = cv.cvtColor(crop, cv.COLOR_BGR2RGB)
        original = torch.from_numpy(rgb.copy()).permute(2, 0, 1).unsqueeze(0).to("cuda", self.dtype) / 255
        masked = original.clone()
        masked[:, :, 128:, :] = 0
        with torch.inference_mode():
            torch.manual_seed(42)
            a = self.vae.encode(masked * 2 - 1).latent_dist.sample() * self.vae.config.scaling_factor
            b = self.vae.encode(original * 2 - 1).latent_dist.sample() * self.vae.config.scaling_factor
            self.latent = torch.cat((a, b), dim=1).contiguous(memory_format=torch.channels_last)
        mask = np.zeros((256, 256), np.float32)
        center = (int((mouth_x-x1)/(x2-x1)*256), int((mouth_y-y1)/(y2-y1)*256)+5)
        mouth_width = abs(float(face[12]-face[10]))/(x2-x1)*256
        cv.ellipse(mask, center, (max(50,min(95,int(mouth_width*.8))), 43), 0, 0, 360, 1, -1)
        mask = cv.GaussianBlur(mask, (17, 17), 0)
        self.mask = cv.resize(mask, (x2-x1, y2-y1))[:, :, None]
        self.portrait, self.box, self.scene = frame, (x1, y1, x2, y2), scene
        self.reference_key = reference_key

    def capture_last_frame(self, video, destination):
        capture = self.cv.VideoCapture(str(video))
        try:
            # Fragmented MP4's estimated frame count may include AAC padding.
            # Decode this bounded short clip instead of seeking past its last frame.
            frame = None
            for _ in range(1801):
                ok, next_frame = capture.read()
                if not ok:
                    break
                frame = next_frame
            else:
                raise RuntimeError("The completed video exceeds the pose capture limit.")
            if frame is None:
                raise RuntimeError("The completed video has no pose to continue from.")
            if not self.cv.imwrite(str(destination), frame):
                raise RuntimeError("Could not preserve the completed video pose.")
        finally:
            capture.release()

    def motion_frames(self, path, nframes, fps, cancel, lip_frames=None, loop=False, reuse=False, start_s=0):
        """Track the face on generated body footage; never move a static cutout."""
        if not math.isfinite(start_s) or start_s < 0:
            raise ValueError('Motion offset must be finite and nonnegative.')
        cv, np = self.cv, self.np
        check_cancel(cancel)
        if not hasattr(self, '_motion_cache'):
            self._motion_cache = OrderedDict()
        key = (hashlib.sha256(path.read_bytes()).digest(), getattr(self, 'face_shift', -.10)) if reuse and path.stat().st_size <= 40_000_000 else None
        cached = self._motion_cache.get(key) if key else None
        self.motion_cache_hit = cached is not None
        if cached:
            self._motion_cache.move_to_end(key)
            frames, source_fps = cached['frames'], cached['fps']
        else:
            capture = cv.VideoCapture(str(path))
            source_fps = capture.get(cv.CAP_PROP_FPS)
            frames = []
            try:
                while len(frames) <= 30 * 60:
                    check_cancel(cancel)
                    ok, frame = capture.read()
                    if not ok:
                        break
                    frames.append(frame)
            finally:
                capture.release()
        if not frames or not 1 <= source_fps <= 60 or len(frames) > 1800:
            raise RuntimeError("The motion clip is missing or has an invalid duration/frame rate.")
        height, width = frames[0].shape[:2]
        # Cache only short, reviewed, speech-free source footage. At most four
        # 384x576/144-frame entries; no generated mouths or user audio survives.
        if not cached and key and len(frames) <= 144 and width*height <= 384*576:
            cached = {'frames':frames, 'fps':source_fps, 'tracked':{}, 'latents':{}}
            self._motion_cache[key] = cached
            while len(self._motion_cache) > 4:
                self._motion_cache.popitem(last=False)
        self._appearance_latents = cached['latents'] if cached else None
        detector = cv.FaceDetectorYN.create(str(CACHE / "yunet.onnx"), "", (width, height), .65, .3, 5000)
        tracked = cached['tracked'] if cached else {}
        result = []
        for i in range(nframes):
            check_cancel(cancel)
            position = int((start_s + i / fps) * source_fps + 1e-7)
            index = position % len(frames) if loop else min(len(frames)-1, position)
            if lip_frames is not None and i >= lip_frames:
                result.append((frames[index], None, None, None))
                continue
            if index not in tracked:
                frame = frames[index]
                _, faces = detector.detect(frame)
                if faces is None or len(faces) != 1:
                    raise RuntimeError("The generated movement lost its clear face. Please retry the movement.")
                face = faces[0]
                x, y, w, h = map(float, face[:4])
                mid = float(face[9]) + getattr(self, 'face_shift', -.10)*h
                x1, y1 = max(0, int(x)), max(0, int(2*mid-(y+h)))
                x2, y2 = min(width, int(x+w)), min(height, int(y+h+.12*h))
                if x2 <= x1 or y2 <= y1:
                    raise RuntimeError("The moving face crop is invalid.")
                crop = cv.resize(frame[y1:y2,x1:x2], (256,256), interpolation=cv.INTER_LANCZOS4)
                mask = np.zeros((256,256), np.float32)
                mx, my = float(face[10]+face[12])/2, float(face[11]+face[13])/2
                center = (int((mx-x1)/(x2-x1)*256), int((my-y1)/(y2-y1)*256)+5)
                mouth_width = abs(float(face[12]-face[10]))/(x2-x1)*256
                cv.ellipse(mask, center, (max(50,min(95,int(mouth_width*.8))),43),0,0,360,1,-1)
                mask = cv.resize(cv.GaussianBlur(mask,(17,17),0),(x2-x1,y2-y1))[:,:,None]
                tracked[index] = (frame, (x1,y1,x2,y2), mask, cv.cvtColor(crop,cv.COLOR_BGR2RGB))
            result.append(tracked[index])
        return result

    def encode_appearance(self, crops):
        """Cache source appearance only; speech conditioning remains per reply."""
        torch, np = self.torch, self.np
        appearance = self._appearance_latents
        missing = [crop for crop in crops if appearance is None or id(crop) not in appearance]
        if missing:
            originals = torch.from_numpy(np.stack(missing)).permute(0,3,1,2).to('cuda',self.dtype)/255
            masked = originals.clone()
            masked[:,:,128:,:] = 0
            a = self.vae.encode(masked*2-1).latent_dist.mode()*self.vae.config.scaling_factor
            b = self.vae.encode(originals*2-1).latent_dist.mode()*self.vae.config.scaling_factor
            encoded = torch.cat((a,b),dim=1)
            if appearance is not None:
                for crop, value in zip(missing, encoded):
                    appearance[id(crop)] = value.unsqueeze(0).clone()
        return torch.cat([appearance[id(crop)] for crop in crops]) if appearance is not None else encoded

    def prime_motion(self, paths, cancel):
        """Prepare at most four verified sources before admitting a call."""
        if len(paths)>4:
            raise ValueError('Motion warm-up is limited to four reviewed sources.')
        started=time.perf_counter()
        with self.torch.inference_mode():
            for path in paths:
                check_cancel(cancel)
                probe=self.cv.VideoCapture(str(path))
                try:
                    fps=probe.get(self.cv.CAP_PROP_FPS)
                    count=probe.get(self.cv.CAP_PROP_FRAME_COUNT)
                finally:
                    probe.release()
                if not math.isfinite(count) or not 1<=count<=144 or not 1<=fps<=60:
                    raise ValueError('Invalid reviewed source for motion warm-up.')
                rows=self.motion_frames(path,int(count),fps,cancel,loop=True,reuse=True)
                if self._appearance_latents is None:
                    raise ValueError('Motion warm-up requires a cache-eligible reviewed source.')
                for offset in range(0,len(rows),8):
                    check_cancel(cancel)
                    self.encode_appearance([row[3] for row in rows[offset:offset+8]])
            self.torch.cuda.synchronize()
        return {'sources':len(paths),'seconds':round(time.perf_counter()-started,3),
                'torch_allocated_mib':round(self.torch.cuda.memory_allocated()/1048576,3)}

    def render(self, audio_path, destination, cancel, scene="mira", fps=25, batch_size=8, streaming=False, motion_path=None, face_encode_stride=2, loop_motion=False, reuse_motion=False, motion_start_s=0):
        if streaming:
            fps = 20
        cv, np, torch = self.cv, self.np, self.torch
        if face_encode_stride not in {1,2}:
            raise ValueError("Face encoding stride must be one or two frames.")
        import soundfile as sf
        from scipy.signal import resample_poly
        if motion_path is None and (self.portrait is None or self.scene != scene):
            self.prepare(scene)
        check_cancel(cancel)
        start = time.perf_counter()
        torch.cuda.reset_peak_memory_stats()
        data, rate = sf.read(str(audio_path), dtype="float32")
        if data.ndim == 2:
            data = data.mean(axis=1)
        if rate != 16000:
            common = math.gcd(rate, 16000)
            data = resample_poly(data, 16000 // common, rate // common)
        speech_duration = len(data) / 16000
        if motion_path:
            probe = cv.VideoCapture(str(motion_path))
            try:
                source_fps = probe.get(cv.CAP_PROP_FPS)
                source_frames = probe.get(cv.CAP_PROP_FRAME_COUNT)
            finally:
                probe.release()
            duration = motion_duration(speech_duration, source_frames, source_fps, loop=loop_motion, start_s=motion_start_s)
            # Finish gestures, but do not keep the mic paused for a whole ambient
            # loop after a short sentence. Its silent playback resumes in the UI.
            samples = math.ceil(math.ceil(duration*fps)/fps*16000)
            data = np.pad(data,(0,max(0,samples-len(data))))
        nframes = max(1, math.ceil(len(data) / 16000 * fps))
        if nframes > 30 * fps:
            raise ValueError("Visual replies are limited to 30 seconds.")
        inputs = self.features(data, sampling_rate=16000, return_tensors="pt").input_features.to("cuda", self.dtype)
        tracking_start = time.perf_counter()
        lip_frames = min(nframes, math.ceil((speech_duration+.15)*fps/batch_size)*batch_size) if motion_path else nframes
        movement = self.motion_frames(motion_path, nframes, fps, cancel, lip_frames, loop=loop_motion, reuse=reuse_motion, start_s=motion_start_s) if motion_path else None
        tracking_seconds = time.perf_counter()-tracking_start
        height, width = (movement[0][0] if movement else self.portrait).shape[:2]
        # Pipe raw frames to one local encoder; no per-frame PNG disk round trips.
        encoding = ["-c:v", "h264_nvenc", "-preset", "p1", "-tune", "ll"] if self.encoder == "h264_nvenc" else ["-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-crf", "20", "-threads", "2"]
        delivery = (["-g", "4", "-bf", "0", "-profile:v", "baseline", "-level:v", "3.0",
                     "-movflags", "+frag_keyframe+empty_moov+default_base_moof", "-frag_duration", "200000", "-flush_packets", "1"]
                    if streaming else ["-movflags", "+faststart"])
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                   "-s", f"{width}x{height}", "-r", str(fps), "-i", "pipe:0", "-i", str(audio_path),
                   *encoding, "-pix_fmt", "yuv420p",
                   "-c:a", "aac", *(["-af", "apad", "-t", str(nframes/fps)] if motion_path else []),
                   "-shortest", *delivery, str(destination)]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            neural_seconds = 0
            composite_seconds = 0
            with torch.inference_mode():
                hidden = torch.stack(self.whisper(inputs, output_hidden_states=True).hidden_states, dim=2)
                hidden = hidden[:, :max(1, int(len(data) / 16000 * 50))]
                hidden = torch.cat((torch.zeros((1, audio_left_padding(fps), 5, 384), device='cuda', dtype=self.dtype), hidden,
                                    torch.zeros((1, 24, 5, 384), device="cuda", dtype=self.dtype)), dim=1)
                chunks = torch.cat([hidden[:, int(i*50/fps):int(i*50/fps)+10] for i in range(nframes)], dim=0).reshape(nframes, 50, 384)
                torch.cuda.synchronize()
                features_seconds = time.perf_counter()-start
                for offset in range(0, nframes, batch_size):
                    check_cancel(cancel)
                    if movement and offset >= lip_frames:
                        # Speech has finished: deliver real LTX body frames, including
                        # their natural facial expression, without inventing silent speech.
                        composite_start = time.perf_counter()
                        for item in movement[offset:offset+batch_size]:
                            process.stdin.write(item[0].tobytes())
                        composite_seconds += time.perf_counter()-composite_start
                        continue
                    neural_start = time.perf_counter()
                    count = min(batch_size, nframes-offset)
                    conditioning = chunks[offset:offset+count] + self.pe
                    if movement:
                        # Reuse appearance for at most 50ms; body frames, tracking and
                        # audio-conditioned mouth synthesis still update every frame.
                        crops = [item[3] for item in movement[offset:offset+count:face_encode_stride]]
                        latent = self.encode_appearance(crops)
                        latent = latent.repeat_interleave(face_encode_stride,dim=0)[:count].contiguous(memory_format=torch.channels_last)
                    else:
                        latent = self.latent.expand(count, -1, -1, -1)
                    pred = self.unet(latent, torch.tensor(0, device="cuda"), encoder_hidden_states=conditioning).sample
                    images = self.vae.decode(pred / self.vae.config.scaling_factor).sample
                    images = ((images / 2 + .5).clamp(0, 1).permute(0, 2, 3, 1).float().cpu().numpy() * 255).round().astype("uint8")
                    neural_seconds += time.perf_counter()-neural_start
                    composite_start = time.perf_counter()
                    for local_index, img in enumerate(images):
                        if movement:
                            frame, box, mask, _ = movement[offset+local_index]
                        else:
                            frame, box, mask = self.portrait, self.box, self.mask
                        x1, y1, x2, y2 = box
                        result = frame.copy()
                        patch = cv.resize(img[:, :, ::-1], (x2-x1, y2-y1), interpolation=cv.INTER_LANCZOS4)
                        result[y1:y2, x1:x2] = (patch * mask + result[y1:y2, x1:x2] * (1-mask)).astype("uint8")
                        process.stdin.write(result.tobytes())
                    composite_seconds += time.perf_counter()-composite_start
            process.stdin.close()
            error = process.stderr.read().decode(errors="replace")
            if process.wait(timeout=20) != 0:
                raise RuntimeError("Local video encoding failed: " + error[-300:])
        except BaseException as error:
            if process.poll() is None:
                process.kill()
            process.wait()
            diagnostic = process.stderr.read().decode(errors="replace")
            destination.unlink(missing_ok=True)
            if isinstance(error, OSError):
                raise RuntimeError("Local video encoder stopped: " + diagnostic[-1500:]) from error
            raise
        finally:
            process.stderr.close()
            if not process.stdin.closed:
                process.stdin.close()
        elapsed = time.perf_counter() - start
        return {"render_s": elapsed, "frames": nframes, "fps": nframes / elapsed,
                "duration_s": len(data) / 16000, "speech_duration_s":speech_duration,
                "lip_sync_frames":lip_frames,
                "resolution": f"{width}x{height}", "face_region": "256x256",
                "torch_peak_allocated_mib": torch.cuda.max_memory_allocated()/1048576,
                "torch_peak_reserved_mib": torch.cuda.max_memory_reserved()/1048576,
                "audio_features_s": features_seconds, "neural_s": neural_seconds,
                "composite_pipe_s": composite_seconds,
                "encoder": self.encoder, "body_motion": bool(movement), "face_tracking_s": tracking_seconds,
                "face_encode_stride": face_encode_stride if movement else None,
                "prepared_appearance_cache_hit": self.motion_cache_hit if movement else False,
                "motion_start_s": motion_start_s}
