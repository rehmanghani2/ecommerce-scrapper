"""
Detect CAPTCHA and anti-bot challenge pages without attempting to solve or bypass them.

The detector intentionally requires multiple signals so that ordinary product pages
containing a CAPTCHA widget (for example, a contact form) are not treated as blocked.
"""
import re
from html import unescape
from typing import Any, Dict, Optional


_PROVIDER_MARKERS = {
    "cloudflare": (
        "cf-chl-", "__cf_chl", "challenge-platform",
        "cloudflare ray id", "cdn-cgi/challenge-platform",
        "cf-browser-verification",
    ),
    "datadome": (
        "datadome", "captcha-delivery.com", "ddc.js",
    ),
    "perimeterx": (
        "perimeterx", "px-captcha", "humansecurity",
        "captcha.perimeterx.net", "_pxcaptcha",
    ),
    "recaptcha": (
        "g-recaptcha", "google.com/recaptcha", "grecaptcha",
    ),
    "hcaptcha": (
        "h-captcha", "hcaptcha.com", "js.hcaptcha.com",
    ),
    "imperva": (
        "incapsula", "imperva", "incap_ses", "visid_incap",
    ),
}

_CHALLENGE_PHRASES = (
    "verify you are human",
    "verify that you are human",
    "checking your browser",
    "checking if the site connection is secure",
    "complete the security check",
    "security check",
    "unusual traffic",
    "automated requests",
    "confirm you are not a robot",
    "are you a human",
    "please verify",
    "attention required",
    "enable javascript and cookies to continue",
    "performing security verification",
    "one more step",
    "just a moment",
    "complete the captcha",
    "solve the captcha",
    "enter the characters",
    "verify you are not a robot",
)

_BLOCK_STATUSES = {403, 429, 503}


def detect_challenge(
    url: str,
    status: Optional[int],
    html: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Return structured challenge evidence, or None for an ordinary page.

    This is detection only. It does not interact with challenge controls, request
    tokens, solve CAPTCHAs, or attempt to evade access controls.
    """
    if not html:
        return None

    source = unescape(html).lower()
    visible_text = re.sub(r"<[^>]+>", " ", source)
    visible_text = re.sub(r"\\s+", " ", visible_text)

    matched_provider = None
    for provider, markers in _PROVIDER_MARKERS.items():
        if any(marker in source for marker in markers):
            matched_provider = provider
            break

    matched_phrase = next(
        (phrase for phrase in _CHALLENGE_PHRASES if phrase in visible_text or phrase in source),
        None,
    )
    has_captcha_widget = any(
        marker in source
        for marker in ("captcha", "g-recaptcha", "h-captcha", "px-captcha")
    )
    blocked_status = status in _BLOCK_STATUSES

    # Provider-specific markup alone is insufficient: many sites load CAPTCHA
    # libraries for optional forms. Require challenge wording or a blocking status.
    provider_challenge = bool(matched_provider and (matched_phrase or (blocked_status and has_captcha_widget)))
    generic_challenge = bool(
        matched_phrase and (has_captcha_widget or blocked_status)
    )

    if not (provider_challenge or generic_challenge):
        return None

    signals = []
    if matched_provider:
        signals.append(f"provider_signature:{matched_provider}")
    if matched_phrase:
        signals.append(f"challenge_text:{matched_phrase}")
    if has_captcha_widget:
        signals.append("captcha_widget")
    if blocked_status:
        signals.append(f"http_status:{status}")

    if matched_provider and matched_phrase:
        confidence = 0.98
    elif matched_provider and has_captcha_widget and blocked_status:
        confidence = 0.94
    elif matched_phrase and has_captcha_widget:
        confidence = 0.90
    else:
        confidence = 0.84

    return {
        "detected": True,
        "provider": matched_provider or "generic",
        "confidence": confidence,
        "signals": signals,
        "url": url,
        "http_status": status,
    }
