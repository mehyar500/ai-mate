"""Constrained MuseTalk 1.5 portrait lip-sync, not full-body/live video synthesis.

Inference equations follow TMElyralab/MuseTalk (MIT, Copyright 2024 Tencent).
The local adapter uses a fixed reviewed crop and feathered mask, avoiding the
upstream training/pose stack. Dependencies and model licenses remain separate.
"""
import json
import math
from pathlib import Path
import subprocess
import time

from .models import CACHE, ROOT, check_cancel


class PortraitRenderer:
    def __init__(self):
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

    def prepare(self, scene="mira"):
        if self.portrait is not None and self.scene == scene:
            return
        cv, np, torch = self.cv, self.np, self.torch
        path = ROOT / "generated/local-app" / (scene + ".png")
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
            mid_face = nose_y - .04*h
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

    def render(self, audio_path, destination, cancel, scene="mira", fps=25, batch_size=8):
        cv, np, torch = self.cv, self.np, self.torch
        import soundfile as sf
        from scipy.signal import resample_poly
        if self.portrait is None or self.scene != scene:
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
        nframes = max(1, math.ceil(len(data) / 16000 * fps))
        if nframes > 30 * fps:
            raise ValueError("Visual replies are limited to 30 seconds.")
        inputs = self.features(data, sampling_rate=16000, return_tensors="pt").input_features.to("cuda", self.dtype)
        height, width = self.portrait.shape[:2]
        # Pipe raw frames to one local encoder; no per-frame PNG disk round trips.
        encoding = ["-c:v", "h264_nvenc", "-preset", "p1", "-tune", "ll"] if self.encoder == "h264_nvenc" else ["-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-crf", "20", "-threads", "2"]
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                   "-s", f"{width}x{height}", "-r", str(fps), "-i", "pipe:0", "-i", str(audio_path),
                   *encoding, "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(destination)]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            neural_seconds = 0
            composite_seconds = 0
            with torch.inference_mode():
                hidden = torch.stack(self.whisper(inputs, output_hidden_states=True).hidden_states, dim=2)
                hidden = hidden[:, :max(1, int(len(data) / 16000 * 50))]
                hidden = torch.cat((torch.zeros_like(hidden[:, :4]), hidden,
                                    torch.zeros((1, 24, 5, 384), device="cuda", dtype=self.dtype)), dim=1)
                chunks = torch.cat([hidden[:, i*2:i*2+10] for i in range(nframes)], dim=0).reshape(nframes, 50, 384)
                torch.cuda.synchronize()
                features_seconds = time.perf_counter()-start
                for offset in range(0, nframes, batch_size):
                    check_cancel(cancel)
                    neural_start = time.perf_counter()
                    count = min(batch_size, nframes-offset)
                    conditioning = chunks[offset:offset+count] + self.pe
                    pred = self.unet(self.latent.expand(count, -1, -1, -1), torch.tensor(0, device="cuda"), encoder_hidden_states=conditioning).sample
                    images = self.vae.decode(pred / self.vae.config.scaling_factor).sample
                    images = ((images / 2 + .5).clamp(0, 1).permute(0, 2, 3, 1).float().cpu().numpy() * 255).round().astype("uint8")
                    neural_seconds += time.perf_counter()-neural_start
                    composite_start = time.perf_counter()
                    for img in images:
                        x1, y1, x2, y2 = self.box
                        result = self.portrait.copy()
                        patch = cv.resize(img[:, :, ::-1], (x2-x1, y2-y1), interpolation=cv.INTER_LANCZOS4)
                        result[y1:y2, x1:x2] = (patch * self.mask + result[y1:y2, x1:x2] * (1-self.mask)).astype("uint8")
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
                "duration_s": len(data) / 16000, "resolution": f"{width}x{height}", "face_region": "256x256",
                "torch_peak_allocated_mib": torch.cuda.max_memory_allocated()/1048576,
                "torch_peak_reserved_mib": torch.cuda.max_memory_reserved()/1048576,
                "audio_features_s": features_seconds, "neural_s": neural_seconds,
                "composite_pipe_s": composite_seconds,
                "encoder": self.encoder}
