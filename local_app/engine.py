"""Central companion engine: turn routing, model flow, media and memory lifecycle.

HTTP transport lives in server.py; model-specific inference stays in adapters.
Text -> plan -> optional speech -> optional body motion/lips -> successful commit.
Microphone input is transcribed before the same turn flow. Cancellation never commits.
"""
import copy
import os
from pathlib import Path
import re
import secrets
import shutil
import threading
import time
import uuid

from .core import Store, messages_for
from .models import Cancelled, Models, ROOT, check_cancel

MEDIA = ROOT / "generated/local-app"


def configure_runtime(path=ROOT / ".env", environ=None):
    """Load only non-secret startup choices; process/launcher overrides win.

    Credentials remain in the existing provider adapter and its selected file.
    No interpolation, shell execution, credential discovery or model downloads.
    """
    environ = os.environ if environ is None else environ
    path = Path(path)
    if not path.is_file():
        return
    allowed = {"AI_MATE_LLM_PROVIDER", "AI_MATE_LLM_MODEL", "AI_MATE_ENV_FILE"}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.strip().removeprefix("export ").partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if sep and key in allowed and value:
            if key == "AI_MATE_ENV_FILE" and not Path(value).is_absolute():
                value = str((path.parent / value).resolve())
            environ.setdefault(key, value)


class CompanionEngine:
    def __init__(self, directory=MEDIA, model_factory=Models):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.store = Store(self.directory / "memory.sqlite3")
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.jobs = {}
        self.busy = False
        self.models = None
        self.ready = False
        self.error = None
        self.visual_error = None
        self.startup_s = None
        self.factory = model_factory
        self.scene = self.store.current_scene()
        self.pose = None  # (scene, private PNG), committed only after successful video completion.
        from .idle import load_reviewed_idle
        self.idle_video = load_reviewed_idle(self.directory)
        self.near_idle_video = load_reviewed_idle(self.directory, 'near')
        from .performance import load_reviewed_performance
        self.performance = load_reviewed_performance(self.directory)
        self.performance_state = 'base'
        self.return_motion = None  # One approach, valid until the next successful video turn.
        for path in self.directory.glob('*-pose.png'):
            if re.fullmatch(r'[a-f0-9]{32}-\d+-pose\.png',path.name):
                path.unlink(missing_ok=True)
        for path in self.directory.glob('*-return.mp4'):
            if re.fullmatch(r'[a-f0-9]{32}-\d+-return\.mp4', path.name):
                path.unlink(missing_ok=True)

    def warm(self):
        started = time.perf_counter()
        try:
            self.models = self.factory()
            event = threading.Event()
            self.models.plan({"memory": "", "turns": []}, "Say hello briefly.", "auto", "mira", ["mira"], event)
            if (self.directory/"mira.png").exists():
                try:
                    renderer = self.models.load_visual()
                    renderer.prepare("mira")
                    warm_audio = ROOT/".cache/local-poc/renderer-warm.wav"
                    self.models.speech("Hello there.", warm_audio)
                    renderer.render(warm_audio, warm_audio.with_suffix(".mp4"), event)
                except Exception as error:
                    self.visual_error = "Video warm-up failed. Voice and text remain available; check the terminal."
                    print(f"Video startup error: {type(error).__name__}: {error}", flush=True)
            self.ready = True
            self.startup_s = round(time.perf_counter()-started, 3)
            print(f"Local dialogue, speech and microphone models are ready in {self.startup_s}s.", flush=True)
        except Exception as error:
            self.error = "Local model startup failed. Check the terminal and model setup."
            print(f"Startup error: {type(error).__name__}: {error}", flush=True)

    def listening_asset(self, scene, pose):
        if scene != 'fullbody':
            return None
        return self.idle_video if pose == 'base' else self.near_idle_video if pose == 'near' else None

    def listening_url(self):
        asset = self.listening_asset(self.scene, self.performance_state)
        return '/idle/near.mp4' if asset and self.performance_state == 'near' else '/idle/fullbody.mp4' if asset else None

    def status(self):
        with self.lock:
            return {"app_version": "0.2", "ready": self.ready, "error": self.error, "busy": self.busy,
                    "startup_s": self.startup_s,
                    "visual_loaded": bool(self.models and self.models.visual is not None and self.visual_error is None),
                    "visual_error": self.visual_error,
                    "scene": self.scene,
                    "idle_video": self.listening_url(),
                    "provider": getattr(getattr(self.models, "conversation", None), "provider", "ollama"),
                    "scenes": [s for s in ["mira", "garden", "cafe", "fullbody"] if (self.directory / (s+".png")).exists()],
                    **self.store.snapshot()}

    def submit(self, text, mode, scene, raw=None):
        if mode not in {"auto", "text", "voice", "video"}:
            raise ValueError("Select text, voice or video.")
        if scene not in {"auto", "mira", "garden", "cafe", "fullbody"}:
            raise ValueError("Unknown scene.")
        if raw is None and (not isinstance(text, str) or not text.strip() or len(text) > 1000):
            raise ValueError("Enter a message between 1 and 1,000 characters.")
        with self.lock:
            if not self.ready:
                raise RuntimeError("The local models are still loading or unavailable.")
            if self.busy:
                raise BlockingIOError("One reply is already running. Stop it or wait.")
            self.busy = True
            key = uuid.uuid4().hex
            event = threading.Event()
            self.jobs[key] = {"id": key, "state": "transcribing" if raw else "thinking", "text": "", "user": text,
                              "chunks": [], "metrics": {}, "cancel": event, "error": None}
            while len(self.jobs) > 20:
                self.jobs.pop(next(iter(self.jobs)))
            threading.Thread(target=self.run, args=(key, text, mode, scene, raw), daemon=True).start()
            return key

    def job(self, key):
        with self.lock:
            if key not in self.jobs:
                raise KeyError("Reply not found.")
            return copy.deepcopy({k: v for k, v in self.jobs[key].items() if k != "cancel"})

    def cancel(self, key=None):
        with self.lock:
            for job_id, job in self.jobs.items():
                if key is None or key == job_id:
                    job["cancel"].set()

    def reset(self):
        with self.lock:
            self.cancel()
            self.store.reset()
            self.scene = "mira"
            self.performance_state = 'base'
            if self.pose:
                self.pose[1].unlink(missing_ok=True)
                self.pose = None
            if self.return_motion:
                self.return_motion[1].unlink(missing_ok=True)
                self.return_motion = None
            # In-flight files belong to the cancelling worker. Also clear replies
            # from previous process lifetimes, whose jobs are no longer in RAM.
            active_keys = {job["id"] for job in self.jobs.values()
                           if job["state"] not in {"done", "failed", "cancelled"}}
            for path in self.directory.iterdir():
                if re.fullmatch(r"[a-f0-9]{32}-\d+\.(wav|mp4)", path.name):
                    if path.name.split("-", 1)[0] not in active_keys:
                        path.unlink(missing_ok=True)
            self.jobs = {k: v for k, v in self.jobs.items() if v["state"] not in {"done", "failed", "cancelled"}}

    def remove_media(self, key):
        for path in self.directory.glob(key + "-*"):
            if path.suffix in {".wav", ".mp4"}:
                path.unlink(missing_ok=True)

    def run(self, key, text, mode, scene, raw):
        job = self.jobs[key]
        event = job["cancel"]
        started = time.perf_counter()
        pose_candidate = None
        return_candidate = None
        performance_candidate = None
        try:
            if raw is not None:
                text = self.models.transcribe(raw)
                check_cancel(event)
                if not text:
                    raise ValueError("No speech detected. Try again or type a message.")
                if len(text) > 1000:
                    raise ValueError("Recording was too long. Try a shorter message.")
                with self.lock:
                    job["user"] = text
                    job["metrics"]["asr_s"] = round(time.perf_counter()-started, 3)
            scene = self.scene if scene == "auto" else scene
            plan = None
            if hasattr(self.models, "plan"):
                available = [s for s in ("mira", "garden", "cafe", "fullbody") if (self.directory/(s+".png")).exists()]
                context = self.store.snapshot()
                context['visual_pose'] = (self.performance_state or 'unknown') if self.scene == 'fullbody' else 'portrait'
                plan = self.models.plan(context, text, mode, scene, available, event)
                check_cancel(event)
                selected_mode = mode
                mode, scene = (mode if mode in {"text", "voice", "video"} else plan["presentation"]), plan["scene"]
                if selected_mode in {"text", "voice"}:
                    plan["action"] = "none"
                    scene = self.scene
                with self.lock:
                    job["presentation"], job["scene"], job["action"] = mode, scene, plan.get("action", "none")
                    job["text"] = plan["reply"]
                    job["metrics"]["first_text_s"] = round(time.perf_counter()-started, 3)
                    job["metrics"]["decision_source"] = plan.get("decision_source", "model")
                    if mode == "portrait":
                        job["portrait"] = "/portrait/" + scene + ".png"
                if mode == "portrait":
                    mode = "text"
            if mode == "video":
                with self.lock:
                    job["state"] = "warming_video"
                renderer = self.models.load_visual()
                with self.lock:
                    pose_reference = self.pose[1] if self.pose and self.pose[0] == scene else None
                    performance_candidate = self.performance_state if scene == self.scene else 'base'
                    listening_video = self.listening_asset(scene, performance_candidate)
                    prepared_transition = self.performance.get((performance_candidate, plan.get('action'))) if scene == 'fullbody' and plan else None
                if not prepared_transition and not (listening_video and (not plan or plan.get('action','none') == 'none')):
                    renderer.prepare(scene, **({"reference_path":pose_reference} if pose_reference else {}))
                check_cancel(event)
            with self.lock:
                job["state"] = "thinking"
            parts = []
            phrases = [plan["reply"]] if plan else self.models.stream_reply(messages_for(self.store.snapshot(), text), event)
            for phrase in phrases:
                check_cancel(event)
                parts.append(phrase)
                with self.lock:
                    job["text"] = " ".join(parts)
                    job["metrics"].setdefault("first_text_s", round(time.perf_counter()-started, 3))
                    job["state"] = "speaking" if mode != "text" else "thinking"
                if mode != "text":
                    index = len(parts) - 1
                    filename = f"{key}-{index}"
                    audio_path = self.directory / (filename + ".wav")
                    speech_started = time.perf_counter()
                    audio_duration = self.models.speech(phrase, audio_path)
                    speech_seconds = round(time.perf_counter()-speech_started, 3)
                    check_cancel(event)
                    chunk = {"index": index, "text": phrase, "audio": "/media/"+filename+".wav", "duration_s": audio_duration,
                             "speech_s":speech_seconds}
                    if mode == "video":
                        chunk['prepared_motion'] = bool(prepared_transition or (listening_video and (not plan or plan.get('action','none') == 'none')))
                        chunk["video"] = "/media/"+filename+".mp4"
                        chunk["stream"] = "/api/streams/"+filename+".mp4"
                        with self.lock:
                            job["state"] = "rendering"
                            job["chunks"].append(chunk)
                        motion_path = None
                        motion_metrics = {}
                        prepared_idle = False
                        try:
                            if plan and plan.get("action", "none") != "none":
                                from .motion import generate, reverse_approach
                                motion_path = self.directory / (filename+"-motion.mp4")
                                with self.lock:
                                    previous_approach = self.return_motion[1] if self.return_motion and self.return_motion[0] == scene else None
                                if prepared_transition:
                                    shutil.copyfile(prepared_transition['path'], motion_path)
                                    performance_candidate = prepared_transition['to']
                                    motion_metrics = {'action':plan['action'], 'motion_source':'reviewed_prepared_transition',
                                                      'fresh_body_generation':False, 'target_pose':performance_candidate}
                                elif plan['action'] == 'farther' and previous_approach and pose_reference:
                                    performance_candidate = None
                                    motion_metrics = reverse_approach(previous_approach, motion_path, event)
                                else:
                                    performance_candidate = None
                                    motion_metrics = generate(scene, plan["action"], audio_duration, event, motion_path,
                                                              reference_path=pose_reference)
                                if plan['action'] == 'closer' and not prepared_transition:
                                    return_candidate = self.directory / (filename+'-return.mp4')
                                    shutil.copyfile(motion_path, return_candidate)
                            elif listening_video:
                                motion_path = self.directory / (filename+'-motion.mp4')
                                shutil.copyfile(listening_video, motion_path)
                                prepared_idle = True
                                motion_metrics = {'motion_source':'prepared_listening_loop', 'fresh_body_generation':False}
                            metrics = renderer.render(audio_path, self.directory / (filename+".mp4"), event,
                                                      scene, streaming=True, **({"motion_path":motion_path, "loop_motion":prepared_idle,
                                                          "reuse_motion":bool(prepared_transition or prepared_idle)} if motion_path else {}))
                            metrics.update(motion_metrics)
                            metrics['looped_prepared_body'] = prepared_idle
                            if not prepared_idle and (motion_path or pose_reference) and hasattr(renderer,"capture_last_frame"):
                                pose_candidate = self.directory / (filename+"-pose.png")
                                renderer.capture_last_frame(self.directory/(filename+".mp4"),pose_candidate)
                                metrics["continues_previous_pose"] = bool(pose_reference)
                        finally:
                            if motion_path:
                                motion_path.unlink(missing_ok=True)
                        chunk["render"] = metrics
                    check_cancel(event)
                    with self.lock:
                        if mode != "video":
                            job["chunks"].append(chunk)
                        job["metrics"].setdefault("first_media_ready_s", round(time.perf_counter()-started, 3))
                if len(parts) >= 2:
                    break
            if not parts:
                raise RuntimeError("The model did not return a complete reply. Please retry.")
            with self.lock:
                check_cancel(event)
                message = plan.get("message") if plan and mode in {"voice", "video"} else None
                self.store.append(text, " ".join(parts), **({"message": message} if message else {}))
                if message:
                    job["message"] = message
                if plan:
                    self.store.learn(plan["facts"])
                    job["remembered"] = plan["facts"]
                if mode == 'video':
                    self.performance_state = performance_candidate
                elif self.scene != scene:
                    self.performance_state = 'base'
                self.scene = scene
                self.store.set_scene(scene)
                if mode == 'video' or (self.return_motion and self.return_motion[0] != scene):
                    previous_return = self.return_motion
                    self.return_motion = (scene, return_candidate) if return_candidate else None
                    if previous_return:
                        previous_return[1].unlink(missing_ok=True)
                if pose_candidate:
                    previous = self.pose
                    self.pose = (scene, pose_candidate)
                    if previous and previous[1] != pose_candidate:
                        previous[1].unlink(missing_ok=True)
                elif self.pose and self.pose[0] != scene:
                    self.pose[1].unlink(missing_ok=True)
                    self.pose = None
                job["metrics"]["total_s"] = round(time.perf_counter()-started, 3)
                job['prepared_pose'] = self.performance_state
                job['idle_video'] = self.listening_url()
                job["state"] = "done"
        except Cancelled:
            with self.lock:
                job["state"] = "cancelled"
                job["chunks"] = []
                job["user"] = ""
                job["text"] = ""
            self.remove_media(key)
        except Exception as error:
            with self.lock:
                job["state"] = "failed"
                job["error"] = str(error) if isinstance(error, (ValueError, RuntimeError)) else "Local inference failed. Check the terminal; you can retry."
                if isinstance(error, ValueError) and str(error).startswith("No speech detected."):
                    job["error_code"] = "no_speech"
            # Third-party exception messages can contain supplied text. Keep
            # details in the local job response, never in persistent logs.
            print(f"Reply failed: {type(error).__name__}", flush=True)
        finally:
            with self.lock:
                if pose_candidate and (not self.pose or self.pose[1] != pose_candidate):
                    pose_candidate.unlink(missing_ok=True)
                if return_candidate and (not self.return_motion or self.return_motion[1] != return_candidate):
                    return_candidate.unlink(missing_ok=True)
                self.busy = False
            # Bound generated media growth. Keep the latest 100 files, never scene assets.
            files = sorted([p for p in self.directory.iterdir() if re.fullmatch(r"[a-f0-9]{32}-\d+\.(wav|mp4)", p.name)], key=lambda p: p.stat().st_mtime)
            for path in files[:-100]:
                path.unlink(missing_ok=True)
