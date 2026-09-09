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
        self.playback_pending = False
        self.generation = 0
        self.models = None
        self.ready = False
        self.error = None
        self.visual_error = None
        self.startup_s = None
        self.visual_warmup = None
        self.factory = model_factory
        self.scene = self.store.current_scene()
        self.pose = None  # (scene, private PNG), committed only after successful video completion.
        from .idle import load_reviewed_idle
        self.idle_video = load_reviewed_idle(self.directory)
        self.near_idle_video = load_reviewed_idle(self.directory, 'near')
        from .performance import load_reviewed_performance
        self.performance = load_reviewed_performance(self.directory)
        self.performance_state = 'base'
        self.visual_cursor = None  # Partial progress along the reviewed base -> near footage.
        self.return_motion = None  # One approach, valid until the next successful video turn.
        for path in self.directory.glob('*-pose.png'):
            if re.fullmatch(r'[a-f0-9]{32}-\d+-pose\.png',path.name):
                path.unlink(missing_ok=True)
        for path in self.directory.glob('*-return.mp4'):
            if re.fullmatch(r'[a-f0-9]{32}-\d+-return\.mp4', path.name):
                path.unlink(missing_ok=True)
        for path in self.directory.glob('playback-*'):
            if re.fullmatch(r'playback-[a-f0-9]{32}\.(mp4|png)', path.name):
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
                    self.prime_reviewed_visual(renderer, event)
                except Exception as error:
                    self.visual_error = "Video warm-up failed. Voice and text remain available; check the terminal."
                    print(f"Video startup error: {type(error).__name__}: {error}", flush=True)
            self.ready = True
            self.startup_s = round(time.perf_counter()-started, 3)
            print(f"Local dialogue, speech and microphone models are ready in {self.startup_s}s.", flush=True)
        except Exception as error:
            self.error = "Local model startup failed. Check the terminal and model setup."
            print(f"Startup error: {type(error).__name__}: {error}", flush=True)

    def prime_reviewed_visual(self, renderer, event):
        """Only constructor-verified character footage enters this cache."""
        paths = [self.idle_video, self.near_idle_video]
        paths += [row['path'] for row in (self.performance or {}).values()]
        paths = list(dict.fromkeys(path for path in paths if path is not None))
        if paths:
            self.visual_warmup = renderer.prime_motion(paths, event)

    def listening_asset(self, scene, pose):
        if scene != 'fullbody':
            return None
        return self.idle_video if pose == 'base' else self.near_idle_video if pose == 'near' else None

    def listening_url(self):
        asset = self.listening_asset(self.scene, self.performance_state)
        return '/idle/near.mp4' if asset and self.performance_state == 'near' else '/idle/fullbody.mp4' if asset else None

    def status(self):
        with self.lock:
            return {"app_version": "0.2", "ready": self.ready, "error": self.error, "busy": self.busy or self.playback_pending,
                    "startup_s": self.startup_s,
                    "visual_warmup": self.visual_warmup,
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
            if self.busy or self.playback_pending:
                raise BlockingIOError("One reply is already running. Stop it or wait.")
            self.busy = True
            self.generation += 1
            key = uuid.uuid4().hex
            event = threading.Event()
            self.jobs[key] = {"id": key, "state": "transcribing" if raw else "thinking", "text": "", "user": text,
                              "chunks": [], "metrics": {}, "cancel": event, "error": None,
                              "_generation": self.generation, "_playback": {}}
            while len(self.jobs) > 20:
                self.jobs.pop(next(iter(self.jobs)))
            threading.Thread(target=self.run, args=(key, text, mode, scene, raw), daemon=True).start()
            return key

    def job(self, key):
        with self.lock:
            if key not in self.jobs:
                raise KeyError("Reply not found.")
            return copy.deepcopy({k: v for k, v in self.jobs[key].items() if k != "cancel" and not k.startswith('_')})

    def cancel(self, key=None, playback=None):
        if playback is not None:
            return self.stop_playback(key, playback)
        with self.lock:
            for job_id, job in self.jobs.items():
                if key is None or key == job_id:
                    job["cancel"].set()
        return {'ok': True}

    def stop_playback(self, key, playback):
        from .playback import capture_playback_frame, stopped_pose, validate_playback
        index, seconds = validate_playback(playback)
        if not isinstance(key, str) or not re.fullmatch(r'[a-f0-9]{32}', key):
            raise ValueError('Invalid reply identifier.')
        snapshot = self.directory / ('playback-' + uuid.uuid4().hex + '.mp4')
        candidate = snapshot.with_suffix('.png')
        with self.lock:
            job = self.jobs.get(key)
            if not job or job.get('_generation') != self.generation:
                raise BlockingIOError('This playback belongs to an older reply.')
            if self.playback_pending:
                raise BlockingIOError('Playback is already stopping.')
            if '_stopped' in job:
                return copy.deepcopy(job['_stopped'])
            metadata = job['_playback'].get(index)
            if metadata is None:
                raise ValueError('That video part is not registered.')
            source = self.directory / f'{key}-{index}.mp4'
            self.playback_pending = True
            generation = self.generation
        started = time.perf_counter()
        try:
            # Copy before cancellation can remove the file. Keep this short local
            # read under the lock shared with reset and the generation worker.
            with self.lock:
                try:
                    with source.open('rb') as incoming:
                        data = incoming.read(40_000_001)
                    if not 0 < len(data) <= 40_000_000:
                        raise ValueError('Playback snapshot is unavailable.')
                    snapshot.write_bytes(data)
                finally:
                    job['cancel'].set()
            actual = capture_playback_frame(snapshot, candidate, seconds)
            source_time = actual['frame'] / metadata['fps']
            pose, cursor = stopped_pose(metadata, source_time)
            with self.lock:
                if generation != self.generation:
                    return {'ok': True, 'pose_preserved': False, 'superseded': True}
                previous = self.pose
                self.pose = (metadata['scene'], candidate)
                self.scene = metadata['scene']
                self.store.set_scene(self.scene)
                self.performance_state, self.visual_cursor = pose, cursor
                if previous and previous[1] != candidate:
                    previous[1].unlink(missing_ok=True)
                if self.return_motion:
                    self.return_motion[1].unlink(missing_ok=True)
                    self.return_motion = None
                result = {'ok': True, 'pose_preserved': True, 'time_s': actual['time_s'],
                          'source_time_s': source_time,
                          'idle_video': self.listening_url(), 'prepared_pose': pose,
                          'capture_s': round(time.perf_counter() - started, 3)}
                job['_stopped'] = result
                job['metrics']['playback_stop'] = {k: v for k, v in result.items() if k != 'ok'}
                return copy.deepcopy(result)
        except (OSError, ValueError, RuntimeError):
            return {'ok': True, 'pose_preserved': False,
                    'warning': 'Reply stopped, but its position could not be saved. Please retry the movement.'}
        finally:
            with self.lock:
                snapshot.unlink(missing_ok=True)
                if not self.pose or self.pose[1] != candidate:
                    candidate.unlink(missing_ok=True)
                self.playback_pending = False

    def reset(self):
        with self.lock:
            self.cancel()
            self.generation += 1
            self.store.reset()
            self.scene = "mira"
            self.performance_state = 'base'
            self.visual_cursor = None
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
        cursor_candidate = None
        speech_prefetch = None
        candidate_poses = set()
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
                    cursor_candidate = self.visual_cursor if scene == self.scene else None
                    listening_video = self.listening_asset(scene, performance_candidate)
                    prepared_transition = self.performance.get((performance_candidate, plan.get('action'))) if scene == 'fullbody' and plan else None
                    if scene == 'fullbody' and cursor_candidate is not None and plan:
                        origin = 'base' if plan.get('action') == 'closer' else 'near'
                        prepared_transition = self.performance.get((origin, plan.get('action')))
                if not prepared_transition and not (listening_video and (not plan or plan.get('action','none') == 'none')):
                    renderer.prepare(scene, **({"reference_path":pose_reference} if pose_reference else {}))
                check_cancel(event)
            with self.lock:
                job["state"] = "thinking"
            parts = []
            from .speech import SpeechPrefetch, speech_phrases
            if plan:
                phrases = speech_phrases(plan['reply']) if mode != 'text' else [plan['reply']]
            else:
                phrases = self.models.stream_reply(messages_for(self.store.snapshot(), text), event)
            if plan and mode != 'text':
                speech_prefetch = SpeechPrefetch(self.models, phrases, self.directory, key, event)
            listening_offset = 0.0
            for phrase in phrases:
                check_cancel(event)
                parts.append(phrase)
                with self.lock:
                    job["text"] = plan['reply'] if plan else " ".join(parts)
                    job["metrics"].setdefault("first_text_s", round(time.perf_counter()-started, 3))
                    job["state"] = "speaking" if mode != "text" else "thinking"
                if mode != "text":
                    index = len(parts) - 1
                    filename = f"{key}-{index}"
                    audio_path = self.directory / (filename + ".wav")
                    if speech_prefetch:
                        audio_path, audio_duration, speech_seconds = speech_prefetch.take(index)
                    else:
                        speech_started = time.perf_counter()
                        audio_duration = self.models.speech(phrase, audio_path)
                        speech_seconds = round(time.perf_counter()-speech_started, 3)
                    check_cancel(event)
                    chunk = {"index": index, "text": phrase, "audio": "/media/"+filename+".wav", "duration_s": audio_duration,
                             "speech_s":speech_seconds}
                    if mode == "video":
                        action = plan.get('action', 'none') if plan and index == 0 else 'none'
                        if index:
                            prepared_transition = None
                            listening_video = self.listening_asset(scene, performance_candidate)
                            if not listening_video:
                                renderer.prepare(scene, **({'reference_path': pose_reference} if pose_reference else {}))
                        chunk['prepared_motion'] = bool(prepared_transition or (listening_video and action == 'none'))
                        chunk["video"] = "/media/"+filename+".mp4"
                        chunk["stream"] = "/api/streams/"+filename+".mp4"
                        with self.lock:
                            job["state"] = "rendering"
                            job["chunks"].append(chunk)
                        motion_path = None
                        motion_metrics = {}
                        prepared_idle = False
                        motion_start = 0.0
                        try:
                            if action != 'none':
                                from .motion import generate, reverse_approach
                                motion_path = self.directory / (filename+"-motion.mp4")
                                with self.lock:
                                    previous_approach = self.return_motion[1] if self.return_motion and self.return_motion[0] == scene else None
                                if prepared_transition:
                                    if cursor_candidate is not None:
                                        from .playback import video_duration
                                        fraction = cursor_candidate if prepared_transition['to'] == 'near' else 1 - cursor_candidate
                                        motion_start = fraction * video_duration(prepared_transition['path'])
                                    shutil.copyfile(prepared_transition['path'], motion_path)
                                    performance_candidate = prepared_transition['to']
                                    cursor_candidate = None
                                    motion_metrics = {'action':plan['action'], 'motion_source':'reviewed_prepared_transition',
                                                      'fresh_body_generation':False, 'target_pose':performance_candidate,
                                                      'transition_start_s': motion_start}
                                elif plan['action'] == 'farther' and previous_approach and pose_reference:
                                    performance_candidate = None
                                    cursor_candidate = None
                                    motion_metrics = reverse_approach(previous_approach, motion_path, event)
                                else:
                                    performance_candidate = None
                                    cursor_candidate = None
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
                            with self.lock:
                                job['_playback'][index] = {'scene': scene, 'pose': performance_candidate,
                                    'cursor': cursor_candidate, 'transition': prepared_transition,
                                    'start_s': motion_start, 'fps': 20}
                            metrics = renderer.render(audio_path, self.directory / (filename+".mp4"), event,
                                                      scene, streaming=True, **({"motion_path":motion_path, "loop_motion":prepared_idle,
                                                          "motion_start_s":listening_offset if prepared_idle else motion_start,
                                                          "reuse_motion":bool(prepared_transition or prepared_idle)} if motion_path else {}))
                            metrics.update(motion_metrics)
                            metrics['looped_prepared_body'] = prepared_idle
                            if prepared_idle:
                                listening_offset += metrics.get('duration_s', audio_duration)
                            else:
                                listening_offset = 0.0
                            if not prepared_idle and (motion_path or pose_reference) and hasattr(renderer,"capture_last_frame"):
                                previous_candidate = pose_candidate
                                pose_candidate = self.directory / (filename+"-pose.png")
                                candidate_poses.add(pose_candidate)
                                renderer.capture_last_frame(self.directory/(filename+".mp4"),pose_candidate)
                                metrics["continues_previous_pose"] = bool(pose_reference)
                                pose_reference = pose_candidate
                                if previous_candidate:
                                    previous_candidate.unlink(missing_ok=True)
                        finally:
                            if motion_path:
                                motion_path.unlink(missing_ok=True)
                    check_cancel(event)
                    with self.lock:
                        if mode == 'video':
                            chunk['render'] = metrics
                        chunk['complete'] = True
                        if mode != "video":
                            job["chunks"].append(chunk)
                        job["metrics"].setdefault("first_media_ready_s", round(time.perf_counter()-started, 3))
                if not plan and len(parts) >= 2:
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
                    self.visual_cursor = cursor_candidate
                elif self.scene != scene:
                    self.performance_state = 'base'
                    self.visual_cursor = None
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
            if speech_prefetch:
                speech_prefetch.close()
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
            if speech_prefetch:
                speech_prefetch.close()
                published = {item['audio'].rsplit('/', 1)[-1] for item in job['chunks']}
                for candidate in self.directory.glob(key + '-*.wav'):
                    if candidate.name not in published:
                        candidate.unlink(missing_ok=True)
            with self.lock:
                for candidate in candidate_poses:
                    if not self.pose or self.pose[1] != candidate:
                        candidate.unlink(missing_ok=True)
                if return_candidate and (not self.return_motion or self.return_motion[1] != return_candidate):
                    return_candidate.unlink(missing_ok=True)
                self.busy = False
            # Bound generated media growth. Keep the latest 100 files, never scene assets.
            files = sorted([p for p in self.directory.iterdir() if re.fullmatch(r"[a-f0-9]{32}-\d+\.(wav|mp4)", p.name)], key=lambda p: p.stat().st_mtime)
            for path in files[:-100]:
                path.unlink(missing_ok=True)
