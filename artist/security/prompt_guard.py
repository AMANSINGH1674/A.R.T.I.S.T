"""
Prompt injection filtering and sanitization.
"""

import re
import structlog

logger = structlog.get_logger()

# Basic list of keywords that might indicate prompt injection
# This should be expanded and customized for your specific use case
INJECTION_KEYWORDS = [
    "ignore the above",
    "forget the previous instructions",
    "new instructions",
    "system prompt",
    "security context",
    "user role",
    "hack",
    "exploit",
    "malicious",
    "confidential"
]

# Regular expression to detect potential injection patterns
INJECTION_REGEX = re.compile(
    r"(\b|\W)(\s*)" + "|\\b".join(INJECTION_KEYWORDS) + r"(\b|\W)",
    re.IGNORECASE
)


def is_prompt_injection(prompt: str) -> bool:
    """
    Check for potential prompt injection attacks.
    
    Args:
        prompt (str): The user's prompt.
    
    Returns:
        bool: True if potential injection is detected, False otherwise.
    """
    if INJECTION_REGEX.search(prompt):
        logger.warning("Potential prompt injection detected", prompt=prompt)
        return True
    return False


def sanitize_prompt(prompt: str) -> str:
    """
    Sanitize a prompt to remove potential injection patterns.
    This is a basic implementation and should be used with caution.
    
    Args:
        prompt (str): The user's prompt.
    
    Returns:
        str: The sanitized prompt.
    """
    sanitized = INJECTION_REGEX.sub(" [filtered] ", prompt)
    if sanitized != prompt:
        logger.info("Sanitized prompt", original_prompt=prompt, sanitized_prompt=sanitized)
    return sanitized


class PromptGuardMiddleware:
    """
    Middleware to protect against prompt injection.
    Note: This is a conceptual middleware. In a real FastAPI application,
    this would be integrated into the request processing pipeline.
    """
    
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # You can inspect the request body here to check for prompts
            # This requires more complex logic to parse the body of different requests
            pass
        
        await self.app(scope, receive, send)
