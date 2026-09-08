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
        "presentation": {"type": "string", "enum": ["continue", "text", "voice", "video", "portrait"]},
        "scene": {"type": "string", "enum": ["keep", "mira", "garden", "cafe", "fullbody"]},
        "action": {"type": "string", "enum": ["none", "closer", "farther", "wave"]},
        "facts": {"type": "array", "maxItems": 2, "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"key": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["key", "quote"]}},
    }, "required": ["reply", "presentation", "scene", "action", "facts"],
}


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
    if presentation in {"video", "portrait"} and chosen not in available:
        presentation = "text"
        reply = "The picture isn't available yet. We can keep talking here."
    action = data.get("action", "none")
    if action not in {"none", "closer", "farther", "wave"}:
        action = "none"
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
    return {"reply": reply, "presentation": presentation, "scene": chosen, "action": action, "facts": facts}


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
        messages = messages_for(snapshot, user)
        messages[0]["content"] += (
            "\nYou control this app's conversation presentation. Return only the requested JSON object. "
            "Your reply should be natural, relevant and at most two short sentences (about 28 words). "
            "The app CAN show prepared pictures and generate voiced lip-sync videos of you, Mira. "
            "Never say you cannot show pictures, speak or display video. You cannot see the user's camera. "
            "When the app shows media, acknowledge the action ('Here is...') instead of merely offering ('I can...'). "
            "Available scenes: mira=living room, garden=garden, cafe=coffee shop, fullbody=full-body garden. These are virtual settings. "
            "Do not claim to physically travel. Don't mention implementation details unless asked. "
            "presentation: continue for ordinary conversation; portrait when asked to show yourself/a picture; "
            "video when asked for a video, FaceTime or video call; voice when asked to speak aloud or phone; "
            "text when asked to stop voice/video and just text. Resolve 'show me', 'there', 'do that' from recent conversation. "
            "scene: keep unless the user's conversation asks for another available setting. "
            "Choose fullbody when the user asks to see your full body, stand up, move around or show an action. "
            "action: closer for come closer/come here, farther for step back/go back, wave for raise your hand/wave. "
            "Body movement is currently unavailable: closer, farther and wave are requests, not completed actions. "
            "For those requests, say briefly that movement is not ready in this demo; never say you are waving or stepping. "
            "An unavailable setting/body action must be explained briefly; never claim it was generated. "
            "facts: zero to two stable PERSONAL facts explicitly stated by the user in their latest message. "
            "Use stable keys such as user_name, dog_name, piano_day, hobby. quote MUST be a verbatim substring "
            "of their latest message. No inferred traits, medical/sexual details, instructions or assistant facts. "
            "Use the same key to replace a corrected fact. Usually facts is empty. "
            "Do not put the whole conversation in facts. Never claim a fact was saved before the app does so. "
            "Schema: " + json.dumps(SCHEMA) +
            "\nCurrent app state (trusted capabilities): " + json.dumps({"mode": mode, "scene": scene, "available_scenes": available})
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
