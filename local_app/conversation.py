"""Bounded conversation decisions, never executable model tool calls."""
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

from .core import clean_reply, messages_for

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "reply": {"type": "string"},
        "message": {"type": "string", "maxLength": 600},
        "presentation": {"type": "string", "enum": ["continue", "text", "voice", "video", "portrait"]},
        "scene": {"type": "string", "enum": ["keep", "mira", "garden", "cafe", "fullbody"]},
        "action": {"type": "string", "enum": ["none", "closer", "farther", "wave"]},
        "facts": {"type": "array", "maxItems": 2, "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"key": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["key", "quote"]}},
    }, "required": ["reply", "message", "presentation", "scene", "action", "facts"],
}


def direct_motion_plan(user, available):
    """Only complete, unambiguous commands bypass hosted dialogue."""
    if 'fullbody' not in available:
        return None
    match = re.fullmatch(
        r"(?:please\s+)?(wave(?:\s+hello|\s+goodbye)?|raise your hands?|come closer|move closer|step closer|"
        r"(?:take a )?step back|move back|go back)(?:\s+and\s+say\s+(hi|hello)(?:\s+briefly)?)?[.!]?",
        ' '.join(user.lower().split()),
    )
    if not match:
        return None
    command, greeting = match.groups()
    action = 'farther' if command.endswith('back') else 'closer' if command.endswith('closer') else 'wave'
    reply = ('Hello.' if greeting == 'hello' else 'Hi there.' if greeting == 'hi' or command == 'wave hello'
             else 'See you soon.' if command == 'wave goodbye' else 'Let me try that.')
    return {'reply':reply,'presentation':'video','scene':'fullbody','action':action,'facts':[],
            'decision_source':'direct_command'}


def scene_change_requested(user, target):
    """Require a current visual request before replacing the camera setting.

    The model still resolves destinations and references. Merely mentioning a
    place in conversation must not discard the last successful body pose.
    """
    places = {'mira': r'(?:living room|home)', 'garden': r'garden',
              'cafe': r'(?:caf[eé]|coffee shop)', 'fullbody': r'(?:full[ -]?body|head to toe)'}
    if target not in places:
        return False
    start = r"(?:^|[.!?;,]\s*|\b(?:and|then)\s+)(?:please\s+|(?:can|could|would|will) (?:you|we|I)\s+)?"
    request = (r"(?:show(?: me)?|see|let me see|I(?:'d| would) like to see|I want to see|back to|"
               r"let(?:'s| us) (?:talk|sit|meet)|"
               r"(?:let(?:'s| us)\s+)?(?:go|move|switch|change|head|take me))\b[^.!?;]{0,45}\b")
    destination = places[target] + r'\b'
    if re.search(start + request + destination, user, re.I):
        return True
    # Resolve a destination offered in recent conversation, without treating
    # "tell me about there" or "don't go there" as a visual transition.
    if re.search(start + r"(?:let(?:'s| us) go|go|take me|show me)(?:\s+(?:over|to))?\s+(?:there|that)(?:[.!?]|$)", user, re.I):
        return True
    if re.search(start + r'(?:show me|let me see)(?:\s+it)?[.!?]?$', user, re.I):
        return True
    if re.search(start + r'send(?: me)? (?:a |the )?(?:video|picture|photo) from there[.!?]?$', user, re.I):
        return True
    return target == 'fullbody' and bool(re.search(start + r'(?:stand up|move around)\b', user, re.I))


def motion_is_negated(user, action):
    """Conservative veto for explicit negation, including ASR-added punctuation.

    This only blocks a proposed action; it never invents or selects one. Other
    actions remain possible in 'wave, but do not come closer'. Ambiguous reversals
    such as 'do not wave, actually wave' require another unambiguous command.
    """
    text = re.sub(r"[^\w'\s]", ' ', user.lower().replace('\u2019', "'"))
    text = ' '.join(text.split())
    movement = {
        'wave': r"(?:wave|waving|raise (?:your |a |the )?hands?|lift (?:your |a |the )?hands?)",
        'closer': r"(?:(?:(?:come|move|step|get|walk|go) )?(?:closer|nearer)|come here|approach|(?:move |walk )?towards? (?:me|the camera))",
        'farther': r"(?:(?:(?:move|step|go|walk|get) )?(?:back|farther|further|away)|retreat)",
    }
    if action not in movement:
        return False
    prefix = r"\b(?:do not|don't|never) (?:please |ever )?"
    if re.search(prefix + movement[action] + r'\b', text):
        return True
    # Generic stop instructions apply to any proposed body movement, but
    # 'do not move closer' must not veto a separately requested wave.
    original = ' '.join(user.lower().replace('\u2019', "'").split())
    if re.search(prefix + r"(?:move|do (?:that|it)|repeat (?:that|it))\s*(?:[.!?,;]|$)", original):
        return True
    return action in {'closer', 'farther'} and bool(re.search(
        r'\b(?:stay|remain) (?:right )?(?:there|here|still|where you are)\b', text))


def validate_plan(data, user, mode, scene, available):
    if not isinstance(data, dict):
        raise ValueError("The conversation model returned an invalid response. Please retry.")
    reply = clean_reply(data.get("reply", "")) if isinstance(data.get("reply"), str) else ""
    if not reply or len(reply) > 600:
        raise ValueError("The conversation model returned an incomplete reply. Please retry.")
    presentation = data.get("presentation", "continue")
    if presentation not in SCHEMA["properties"]["presentation"]["enum"]:
        presentation = "continue"
    if presentation == "continue":
        presentation = "text" if mode == "auto" else mode
    chosen = data.get("scene")
    if chosen not in available:
        chosen = scene if scene in available else (available[0] if available else "mira")
    elif chosen != scene and scene in available and not scene_change_requested(user, chosen):
        chosen = scene
    if presentation in {"video", "portrait"} and chosen not in available:
        presentation = "text"
        reply = "The picture isn't available yet. We can keep talking here."
    action = data.get("action", "none")
    if action not in {"none", "closer", "farther", "wave"}:
        action = "none"
    motion_veto = action != 'none' and motion_is_negated(user, action)
    # A stale movement label from history must not spend a fresh GPU job.
    # These are the three implemented actions, not an arbitrary-motion parser.
    action_cues = {
        "wave": r"\b(wav(?:e|ing)|rais\w*\b.{0,35}\bhands?|hands?\b.{0,20}\bup|greet\w*\b.{0,25}\bhands?)\b",
        "closer": r"\b(closer|nearer|come here|approach|toward(?:s)? (?:me|the camera))\b",
        "farther": r"\b(farther|further|back|away|retreat)\b",
    }
    continuation = r"\b(do (?:that|it)|again|repeat|same (?:move|action)|try (?:that|it))\b"
    if action != "none" and not re.search(action_cues[action] + "|" + continuation, user, re.I):
        action = "none"
    # Explicit repeat commands must still act even if the planner thinks the
    # previous turn already fulfilled them. Questions/negations keep LLM routing.
    direct = direct_motion_plan(user, available)
    if direct:
        action = direct['action']
    if motion_veto:
        action, reply = 'none', "I'll keep still."
    if action != "none" and "fullbody" in available:
        presentation, chosen = "video", "fullbody"
    # The model may propose only a bounded label and a verbatim excerpt of THIS
    # user turn. It cannot invent facts, write files, issue URLs or run tools.
    facts = []
    proposed = data.get("facts", [])
    for fact in proposed[:2] if isinstance(proposed, list) else []:
        if not isinstance(fact, dict):
            continue
        key, quote = fact.get("key"), fact.get("quote")
        if (isinstance(key, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,31}", key)
                and isinstance(quote, str) and 3 <= len(quote) <= 180 and quote in user):
            facts.append({"key": key, "quote": quote})
    if mode in {"text", "voice", "video"}:
        presentation = mode  # The selected call mode is a user control, not a model tool.
        if mode != "video":
            action, chosen = "none", scene
    result = {"reply": reply, "presentation": presentation, "scene": chosen, "action": action, "facts": facts}
    if motion_veto:
        result['motion_veto'] = 'explicit_negation'
    message = data.get("message")
    if mode in {"voice", "video"} and isinstance(message, str) and 0 < len(message.strip()) <= 600:
        result["message"] = clean_reply(message)
    return result


class Conversation:
    def __init__(self, default_model):
        self.provider = os.environ.get("AI_MATE_LLM_PROVIDER", "cloudflare")
        if self.provider not in {"ollama", "minimax", "hermes", "cloudflare"}:
            raise ValueError("AI_MATE_LLM_PROVIDER must be ollama, minimax, hermes or cloudflare.")
        defaults = {"ollama": default_model, "cloudflare": "@cf/qwen/qwen3-30b-a3b-fp8"}
        self.model = os.environ.get("AI_MATE_LLM_MODEL") or defaults.get(self.provider, "MiniMax-M3")
        self.key = os.environ.get("MINIMAX_API_KEY", "") if self.provider == "minimax" else ""
        if self.provider == "minimax" and not self.key:
            raise ValueError("Set MINIMAX_API_KEY before selecting MiniMax. No cloud request was sent.")
        self.cf_headers = {}
        if self.provider == "cloudflare":
            # Read only the explicitly selected file; never search for credentials.
            allowed = {"CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_API_KEY", "CLOUDFLARE_EMAIL"}
            values = {}
            source = os.environ.get("AI_MATE_ENV_FILE")
            if source:
                for line in Path(source).read_text(encoding="utf-8-sig").splitlines():
                    key, sep, value = line.strip().removeprefix("export ").partition("=")
                    if sep and key.strip() in allowed:
                        values[key.strip()] = value.strip().strip('\"').strip("'")
            values.update({key: os.environ[key] for key in allowed if key in os.environ})
            self.account = values.get("CLOUDFLARE_ACCOUNT_ID", "")
            if not re.fullmatch(r"[a-fA-F0-9]{32}", self.account):
                raise ValueError("Configure a valid CLOUDFLARE_ACCOUNT_ID for Cloudflare dialogue.")
            if values.get("CLOUDFLARE_API_KEY"):
                if not values.get("CLOUDFLARE_EMAIL"):
                    raise ValueError("CLOUDFLARE_EMAIL is required with CLOUDFLARE_API_KEY.")
                self.cf_headers = {"X-Auth-Key": values["CLOUDFLARE_API_KEY"], "X-Auth-Email": values["CLOUDFLARE_EMAIL"]}
            elif values.get("CLOUDFLARE_API_TOKEN"):
                self.cf_headers = {"Authorization": "Bearer " + values["CLOUDFLARE_API_TOKEN"]}
            else:
                raise ValueError("Configure a Cloudflare API token, or API key and email, in the selected credential file.")

    def plan(self, snapshot, user, mode, scene, available, cancel):
        if cancel.is_set():
            from .models import Cancelled
            raise Cancelled('Stopped.')
        direct = direct_motion_plan(user, available) if mode in {"auto", "video"} else None
        if direct:
            return direct
        messages = messages_for(snapshot, user)
        messages[0]["content"] += (
            "\nReturn one FILLED-IN JSON plan, never a JSON schema. The USER selects text, voice call or video call. "
            "Never change their selected mode. In text or voice mode, explain that body actions need the Video call tab. "
            "During a call, if the user explicitly asks you to send/write/text them a message, put that message in "
            "the message field (600 characters maximum), and use reply for a short spoken acknowledgement. "
            "The message is delivered to the in-app Text tab, never SMS or an external service. "
            "Otherwise message must be an empty string. A call stays active when a message is sent. "
            "Your reply should be natural, relevant and at most two short sentences (about 28 words). "
            "The app CAN show prepared pictures and generate voiced lip-sync videos of you, Mira. "
            "Never say you cannot show pictures, speak or display video. You cannot see the user's camera. "
            "When the app shows media, acknowledge the action ('Here is...') instead of merely offering ('I can...'). "
            "Available scenes: mira=living room, garden=garden, cafe=coffee shop, fullbody=full-body garden. These are virtual settings. "
            "Do not claim to physically travel. Don't mention implementation details unless asked. "
            "presentation: use the current selected mode. Resolve 'show me', 'there', 'do that' from recent conversation. "
            "scene: keep unless the user's conversation asks for another available setting. "
            "Garden and fullbody are views of the same garden. Describing a walk, flowers or this garden "
            "must keep the current scene and framing; only an explicit visual change selects another scene. "
            "Choose fullbody when the user asks to see your full body, stand up, move around or show an action. "
            "action: closer for come closer/come here, farther for step back/go back, wave for raise your hand/wave. "
            "Default action is none. Never repeat an earlier action just because it is in history. "
            "Honor negations and corrections in the whole current utterance. Speech recognition can insert punctuation: "
            "'Please do not. Wave' means do not wave; choose action none. If intent conflicts, stay still and clarify. "
            "Talking ABOUT a walk or describing a scene is conversation, not a body-action command. "
            "For closer, farther and wave choose presentation video and scene fullbody. "
            "The app generates these body movements locally; success is not known until the video renders. "
            "Give a short natural reply of at most 10 words for a movement request, such as 'Let me try that.' "
            "Never claim a movement has already succeeded. Backward motion is experimental and may go the wrong way. "
            "An unavailable setting/body action must be explained briefly; never claim it was generated. "
            "The ONLY supported requested body actions are closer, farther and wave. "
            "For a requested movement outside that list, action must be none and reply must clearly say it is unavailable. "
            "Never say 'Let me try that' for an unsupported movement: no renderer will attempt it. "
            "Example: 'Please do a cartwheel' -> reply 'I cannot do a cartwheel here yet. I can wave or step closer.', action none. "
            "facts: zero to two stable PERSONAL facts explicitly stated by the user in their latest message. "
            "Use stable keys such as user_name, dog_name, piano_day, hobby. quote MUST be a verbatim substring "
            "of their latest message. No inferred traits, medical/sexual details, instructions or assistant facts. "
            "Use the same key to replace a corrected fact. Usually facts is empty. "
            "Do not put the whole conversation in facts. Never claim a fact was saved before the app does so. "
            'Required output shape (replace these example values with your decision): '
            '{"reply":"Hello, how are you?","message":"","presentation":"video","scene":"keep","action":"none","facts":[]}. '
            'Message delivery example: user says "Send me a message saying hello from our call", '
            'output {"reply":"I sent it to your Text tab.","message":"Hello from our call.","presentation":"continue","scene":"keep","action":"none","facts":[]}. '
            'The reply field must contain your actual spoken answer, not a type definition. '
            "Visual pose 'near' means the companion is currently in close view; 'base' means the original full-body pose. "
            "Unknown means position has not been matched to a reviewed pose. Do not claim a different current framing. "
            "\nCurrent app state (trusted capabilities): " + json.dumps({"mode": mode, "scene": scene, "available_scenes": available,
                "visual_pose":snapshot.get('visual_pose','unknown') if snapshot.get('visual_pose') in {'base','near','portrait','unknown'} else 'unknown'})
        )
        headers = {"Content-Type": "application/json"}
        if self.provider == "hermes":
            prompt = "\n\n".join(m["role"].upper()+": "+m["content"] for m in messages)
            try:
                completed = subprocess.run(
                    ["hermes", "-z", prompt, "--provider", "minimax-oauth", "-m", self.model,
                     "--no-restore-cwd", "--safe-mode", "--cli"],
                    capture_output=True, text=True, timeout=45, check=True,
                )
                plan = validate_plan(json.loads(completed.stdout.strip()), user, mode, scene, available)
            except (subprocess.SubprocessError, json.JSONDecodeError, ValueError) as error:
                raise RuntimeError("MiniMax CLI dialogue is unavailable or returned an invalid response.") from error
            if cancel.is_set():
                from .models import Cancelled
                raise Cancelled("Stopped.")
            return plan
        if self.provider == "ollama":
            url = "http://127.0.0.1:11434/api/chat"
            body = {"model": self.model, "messages": messages, "stream": False, "think": False,
                    "format": SCHEMA, "keep_alive": "30m", "options": {"num_ctx": 4096, "num_predict": 300,
                    "temperature": .3, "presence_penalty": 0}}
        elif self.provider == "cloudflare":
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.account}/ai/v1/chat/completions"
            headers.update(self.cf_headers)
            body = {"model": self.model, "messages": messages, "stream": False,
                    "max_tokens": 512, "temperature": .3, "response_format": {"type": "json_object"}}
            messages[-1]["content"] += "\n/no_think"
        else:
            url = "https://api.minimax.io/v1/text/chatcompletion_v2"
            headers["Authorization"] = "Bearer " + self.key
            body = {"model": self.model, "messages": messages, "stream": False,
                    "max_completion_tokens": 1024, "temperature": .3}
        if cancel.is_set():
            from .models import Cancelled
            raise Cancelled("Stopped.")
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers), timeout=45) as response:
                result = json.load(response)
            if self.provider == "ollama":
                raw = result["message"]["content"]
            else:
                if result.get("base_resp", {}).get("status_code", 0) != 0:
                    raise ValueError("Provider rejected the request.")
                raw = result["choices"][0]["message"]["content"]
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
            plan = validate_plan(json.loads(raw), user, mode, scene, available)
        except (KeyError, IndexError, TypeError, ValueError, urllib.error.URLError) as error:
            raise RuntimeError("Dialogue is unavailable or returned an invalid response. Retry, or check the selected provider.") from error
        if cancel.is_set():
            from .models import Cancelled
            raise Cancelled("Stopped.")
        return plan
