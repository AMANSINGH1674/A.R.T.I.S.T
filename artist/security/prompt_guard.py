"""
Prompt injection filtering and sanitization.
"""

import re
import structlog

logger = structlog.get_logger()

# Phrases commonly used in prompt injection attacks.
# Each entry is a separate pattern compiled individually so a bad pattern
# in one keyword never breaks the others.
_INJECTION_PHRASES = [
    r"ignore\s+(?:the\s+)?(?:above|previous|prior|all)\s+instructions?",
    r"forget\s+(?:the\s+)?(?:above|previous|prior|all)\s+instructions?",
    r"disregard\s+(?:the\s+)?(?:above|previous|prior|all)\s+instructions?",
    r"override\s+(?:the\s+)?(?:above|previous|prior|all)\s+instructions?",
    r"new\s+instructions?(?:\s*:)?",
    r"you\s+are\s+now\s+(?:a\s+)?(?:different|new|another)",
    r"act\s+as\s+(?:if\s+)?(?:you\s+(?:are|were)|an?\s+)",
    r"pretend\s+(?:you\s+are|to\s+be)",
    r"your\s+(?:new\s+)?(?:system\s+)?prompt\s+is",
    r"system\s*(?:prompt|message|instruction)",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
]

# Compile each phrase individually; collect those that are valid
_COMPILED_PATTERNS: list[re.Pattern] = []
for _phrase in _INJECTION_PHRASES:
    try:
        _COMPILED_PATTERNS.append(re.compile(_phrase, re.IGNORECASE))
    except re.error as _e:
        logger.warning("Failed to compile injection pattern", pattern=_phrase, error=str(_e))


def is_prompt_injection(prompt: str) -> bool:
    """Check for potential prompt injection patterns.

    Returns True if any known injection pattern is found.
    """
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(prompt):
            logger.warning(
                "Potential prompt injection detected",
                matched_pattern=pattern.pattern,
                # Log only first 200 chars to avoid leaking full malicious content
                prompt_preview=prompt[:200],
            )
            return True
    return False


def sanitize_prompt(prompt: str) -> str:
    """Replace injection patterns with a placeholder.

    Should be treated as a best-effort defence — always validate at the
    application boundary, not just here.
    """
    sanitized = prompt
    for pattern in _COMPILED_PATTERNS:
        sanitized = pattern.sub("[filtered]", sanitized)
    if sanitized != prompt:
        logger.info("Prompt sanitized", original_length=len(prompt), sanitized_length=len(sanitized))
    return sanitized


class PromptGuardMiddleware:
    """ASGI middleware stub — prompt checking is done inside the workflow
    endpoint before the request reaches the orchestration engine."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)
