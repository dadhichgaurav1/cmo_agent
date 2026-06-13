"""Transactional email via Resend. No-op (returns False) when RESEND_API_KEY is unset."""
import httpx

from app import config

RESEND_ENDPOINT = "https://api.resend.com/emails"


def enabled() -> bool:
    return bool(config.RESEND_API_KEY)


async def send(to: str, subject: str, html: str) -> bool:
    if not enabled() or not to:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                RESEND_ENDPOINT,
                headers={"Authorization": f"Bearer {config.RESEND_API_KEY}",
                         "Content-Type": "application/json"},
                json={"from": config.RESEND_FROM, "to": [to], "subject": subject, "html": html},
            )
            return r.status_code < 300
    except Exception:
        return False
