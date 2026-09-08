"""Bounded conversation decisions, never executable model tool calls."""
import json
import os
import re
import urllib.error
import urllib.request

from .core import clean_reply, messages_for

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "reply": {"type": "string"},
        "presentation": {"type": "string", "enum": ["continue", "text", "voice", "video", "portrait"]},
        "scene": {"type": "string", "enum": ["keep", "mira", "garden", "cafe"]},
        "facts": {"type": "array", "maxItems": 2, "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"key": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["key", "quote"]}},
    }, "required": ["reply", "presentation", "scene", "facts"],
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
    return {"reply": reply, "presentation": presentation, "scene": chosen, "facts": facts}


class Conversation:
    def __init__(self, default_model):
        self.provider = os.environ.get("AI_MATE_LLM_PROVIDER", "ollama")
        if self.provider not in {"ollama", "minimax"}:
            raise ValueError("AI_MATE_LLM_PROVIDER must be ollama or minimax.")
        self.model = os.environ.get("AI_MATE_LLM_MODEL") or (default_model if self.provider == "ollama" else "MiniMax-M2.7")
        self.key = os.environ.get("MINIMAX_API_KEY", "") if self.provider == "minimax" else ""
        if self.provider == "minimax" and not self.key:
            raise ValueError("Set MINIMAX_API_KEY before selecting MiniMax. No cloud request was sent.")

    def plan(self, snapshot, user, mode, scene, available, cancel):
        messages = messages_for(snapshot, user)
        messages[0]["content"] += (
            "\nYou control this app's conversation presentation. Return only the requested JSON object. "
            "Your reply should be natural, relevant and at most two short sentences (about 28 words). "
            "The app CAN show prepared pictures and generate voiced lip-sync videos of you, Mira. "
            "Never say you cannot show pictures, speak or display video. You cannot see the user's camera. "
            "When the app shows media, acknowledge the action ('Here is...') instead of merely offering ('I can...'). "
            "Available scenes: mira=living room, garden=garden, cafe=coffee shop. These are virtual settings. "
            "Do not claim to physically travel. Don't mention implementation details unless asked. "
            "presentation: continue for ordinary conversation; portrait when asked to show yourself/a picture; "
            "video when asked for a video, FaceTime or video call; voice when asked to speak aloud or phone; "
            "text when asked to stop voice/video and just text. Resolve 'show me', 'there', 'do that' from recent conversation. "
            "scene: keep unless the user's conversation asks for another available setting. "
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
        if self.provider == "ollama":
            url = "http://127.0.0.1:11434/api/chat"
            body = {"model": self.model, "messages": messages, "stream": False, "think": False,
                    "format": SCHEMA, "keep_alive": "30m", "options": {"num_ctx": 4096, "num_predict": 300,
                    "temperature": .3, "presence_penalty": 0}}
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
