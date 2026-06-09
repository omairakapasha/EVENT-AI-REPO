import re
import json
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(\+92|0092|0)?[\s\-]?([0-9]{3})[\s\-]?([0-9]{7,8})")
_CNIC_RE  = re.compile(r"\b\d{5}-\d{7}-\d\b")

_OFF_TOPIC_PATTERNS = [
    re.compile(r"\b(write|generate|create).{0,30}(code|program|script|scraper|bot|app|website)\b", re.I),
    re.compile(r"\b(explain|tell me about)\s+(physics|chemistry|history|math|geography|biology)\b", re.I),
    re.compile(r"\b(stock|crypto|bitcoin|investment|trading|forex)\b", re.I),
    re.compile(r"\b(medical|diagnosis|symptoms|treatment|medicine|prescription)\b", re.I),
    re.compile(r"\b(political|politics|election|government|president|parliament)\b", re.I),
    re.compile(r"\b(hack|exploit|vulnerability|malware|phishing)\b", re.I),
]

_EVENT_KEYWORDS = [
    "event", "wedding", "birthday", "party", "venue", "vendor", "book", "booking",
    "catering", "photography", "decor", "music", "plan", "schedule", "invite",
    "guest", "rsvp", "mehndi", "baraat", "walima", "corporate", "conference",
    "budget", "cost", "available", "recommend", "find", "search",
    "hi", "hello", "thanks", "help", "yes", "no", "ok", "okay",
]


@dataclass
class GuardrailResult:
    blocked: bool
    message: str
    reason: str
    guardrail_triggered: bool = False


class GuardrailService:

    def __init__(self, firewall=None):
        # firewall is injected — PromptFirewall instance or None
        self._firewall = firewall

    async def run_input_pipeline(self, message: str, user_id: str, settings) -> GuardrailResult:
        # 1. Length check
        if len(message) > settings.max_input_chars:
            return GuardrailResult(
                blocked=True,
                message="Message too long. Please keep it under 2000 characters.",
                reason="input_too_long",
                guardrail_triggered=True,
            )

        # 2. Empty check
        if not message.strip():
            return GuardrailResult(
                blocked=True,
                message="Please enter a message.",
                reason="empty_message",
                guardrail_triggered=True,
            )

        # 3. PromptFirewall (if available)
        if self._firewall is not None:
            result = self._firewall.classify(message)
            if result.blocked:
                self.audit("injection_blocked", None, user_id, {
                    "threat_type": result.threat_type,
                    "confidence": result.confidence,
                    "message_hash": hashlib.sha256(message.encode()).hexdigest()[:16],
                })
                return GuardrailResult(
                    blocked=True,
                    message="I can only help with event planning. Please describe your event.",
                    reason=f"firewall:{result.threat_type}",
                    guardrail_triggered=True,
                )
            # Use sanitized message going forward
            message = result.sanitized_message

        # 4. Topic scope check
        if not self._is_on_topic(message):
            return GuardrailResult(
                blocked=True,
                message="I'm specialized in event planning. What event would you like help with? 🎉",
                reason="off_topic",
                guardrail_triggered=True,
            )

        return GuardrailResult(
            blocked=False,
            message=message.strip(),
            reason="",
            guardrail_triggered=False,
        )

    def _is_on_topic(self, message: str) -> bool:
        for pattern in _OFF_TOPIC_PATTERNS:
            if pattern.search(message):
                lower = message.lower()
                if any(kw in lower for kw in _EVENT_KEYWORDS):
                    return True
                return False
        if len(message.split()) <= 5:
            return True
        return True

    def filter_output(self, text: str, max_chars: int = 5000) -> str:
        text = _CNIC_RE.sub("[CNIC REDACTED]", text)  # Before phone — CNIC is more specific
        text = _EMAIL_RE.sub("[EMAIL REDACTED]", text)
        text = _PHONE_RE.sub("[PHONE REDACTED]", text)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n*[Response truncated.]*"
        return text

    def audit(self, event_type: str, session_id: str | None, user_id: str | None, metadata: dict) -> None:
        entry = {
            "audit": True,
            "event_type": event_type,
            "session_id": session_id,
            "user_id_hash": hashlib.sha256(user_id.encode()).hexdigest()[:16] if user_id else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
        }
        logger.info(json.dumps(entry))
