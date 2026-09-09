"""Local-only inference adapters. Weights must be downloaded explicitly beforehand."""
import io
import json
import os
from pathlib import Path
import time
import urllib.request
import wave

from .core import clean_reply

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache/local-poc"
LLM = "qwen3.5:9b-q4_K_M"


class Cancelled(Exception):
    pass


def check_cancel(event):
    if event.is_set():
        raise Cancelled("Stopped.")


class Models:
    def __init__(self):
        from .conversation import Conversation
        self.conversation = Conversation(LLM)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["ONNX_PROVIDER"] = "CPUExecutionProvider"
        import onnxruntime as ort
        from kokoro_onnx import Kokoro
        from faster_whisper import WhisperModel
        options = ort.SessionOptions()
        # Same Kokoro weights and preset; eight threads reduced warm synthesis
        # time on the demo i9. The isolated call suite qualifies CPU contention.
        self.speech_threads = 8
        options.intra_op_num_threads = self.speech_threads
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(str(CACHE / "kokoro-v1.0.onnx"), sess_options=options,
                                       providers=["CPUExecutionProvider"])
        self.tts = Kokoro.from_session(session, str(CACHE / "voices-v1.0.bin"))
        # Eight CPU threads reduced recognition time on the demo i9 without
        # changing any word in the 83-fixture comparison. Keep GPU for visuals.
        self.asr = WhisperModel(str(CACHE / "asr-base-en"), device="cpu", compute_type="int8", cpu_threads=8, num_workers=1, local_files_only=True)
        self.tts.create("Hello there.", voice="af_sarah", speed=1, lang="en-us")
        self.visual = None

    def plan(self, snapshot, user, mode, scene, available, cancel):
        return self.conversation.plan(snapshot, user, mode, scene, available, cancel)

    def stream_reply(self, messages, cancel, options=None):
        settings = {"num_ctx": 4096, "num_predict": 100, "temperature": 0.5, "presence_penalty": 0.0}
        if options:
            settings.update(options)
        body = dict(model=LLM, messages=messages, stream=True, think=False, keep_alive="30m",
                    options=settings)
        request = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                         data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=45) as response:
            pending = ""
            for line in response:
                check_cancel(cancel)
                item = json.loads(line)
                if "error" in item:
                    raise RuntimeError("The local dialogue model could not complete this reply.")
                pending += item.get("message", {}).get("content", "")
                # Yield whole phrases early, while Ollama continues producing the next one.
                if pending.strip() and pending.rstrip().endswith((".", "!", "?")):
                    result = clean_reply(pending)
                    if result:
                        yield result
                    pending = ""
                if item.get("done"):
                    if item.get("done_reason") == "length" and pending:
                        # A complete earlier sentence is usable; a cut-off fragment is not.
                        pending = ""
                    break
            if clean_reply(pending):
                yield clean_reply(pending)

    def speech(self, text, destination):
        import soundfile as sf
        audio, rate = self.tts.create(text, voice="af_sarah", speed=1, lang="en-us")
        sf.write(str(destination), audio, rate, subtype="PCM_16")
        return len(audio) / rate

    def transcribe(self, raw):
        # WAV only; no shell conversion of user-supplied files or cloud browser ASR.
        try:
            with wave.open(io.BytesIO(raw), "rb") as wav:
                if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                    raise ValueError("Record mono 16-bit WAV audio.")
                rate, frames = wav.getframerate(), wav.getnframes()
                if not 8000 <= rate <= 96000 or not 0.15 <= frames / rate <= 30:
                    raise ValueError("Recording must be between 0.15 and 30 seconds.")
                pcm = wav.readframes(frames)
                if len(pcm) != frames * 2:
                    raise ValueError("Incomplete recording.")
        except (wave.Error, EOFError) as error:
            raise ValueError("Recording is not a valid WAV file.") from error
        import numpy as np
        if np.max(np.abs(np.frombuffer(pcm, dtype=np.int16).astype(np.float32))) < 100:
            return ""
        segments, _ = self.asr.transcribe(io.BytesIO(raw), language="en", beam_size=1,
                                         vad_filter=True, condition_on_previous_text=False)
        return " ".join(segment.text.strip() for segment in segments).strip()

    def load_visual(self):
        if self.visual is None:
            from .visual import PortraitRenderer
            self.visual = PortraitRenderer(decoder_backend=os.environ.get('AI_MATE_VISUAL_DECODER','torch'))
        return self.visual
