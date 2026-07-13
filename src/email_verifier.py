"""Cloudflare email verification via Gmail IMAP."""

from __future__ import annotations

import asyncio
import email
import html
import imaplib
import re
import time
from email.parser import BytesParser
from typing import Any
from urllib.parse import unquote

import nodriver as uc


class EmailVerifyResult:
    def __init__(self, success: bool, error: str = "", link: str = "", otp: str = ""):
        self.success = success
        self.error = error
        self.link = link
        self.otp = otp


CF_VERIFY_PATTERNS = [
    # Common Cloudflare dashboard/email verification links.
    r'https://dash\.cloudflare\.com/[^\"><\s]+',
    r'https://www\.cloudflare\.com/[^\"><\s]+',
    r'https://cloudflare\.com/[^\"><\s]+',
]


def extract_verification_link(body: str) -> str:
    """Extract the most likely Cloudflare verification link from email body."""
    blob = html.unescape(body)
    blob = blob.replace("\\/", "/")

    candidates: list[str] = []
    for pattern in CF_VERIFY_PATTERNS:
        candidates.extend(re.findall(pattern, blob, flags=re.I))

    cleaned = []
    for url in candidates:
        url = url.rstrip("').,;]>\"\\")
        url = unquote(url)
        low = url.lower()
        if any(k in low for k in ("verify", "confirm", "activation", "email", "token", "challenge")):
            cleaned.append(url)

    if not cleaned:
        for url in candidates:
            url = url.rstrip("').,;]>\"\\")
            if "dash.cloudflare.com" in url.lower():
                cleaned.append(unquote(url))

    return cleaned[0] if cleaned else ""


async def verify_cloudflare_email(
    email_address: str,
    gmail_user: str,
    gmail_password: str,
    timeout: int = 180,
    check_interval: int = 5,
) -> EmailVerifyResult:
    """
    Verify Cloudflare account by polling Gmail inbox for verification email.

    Args:
        email_address: Email address to search for in To: header
        gmail_user: Gmail username
        gmail_password: Gmail app password
        timeout: Maximum seconds to wait for email (default: 180)
        check_interval: Seconds between inbox checks (default: 5)

    Returns:
        EmailVerifyResult with verification link and OTP if found
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            result = await asyncio.to_thread(
                _check_gmail_inbox, email_address, gmail_user, gmail_password
            )
            if result.success:
                return result

            await asyncio.sleep(check_interval)

        except Exception as e:
            return EmailVerifyResult(success=False, error=f"IMAP error: {e}")

    return EmailVerifyResult(success=False, error="Verification email timeout")


def _check_gmail_inbox(
    target_email: str, gmail_user: str, gmail_password: str
) -> EmailVerifyResult:
    """Check Gmail inbox via IMAP for Cloudflare verification email."""
    mail = None
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, gmail_password)
        mail.select("inbox")

        _, search_data = mail.search(None, f'TO "{target_email}"')
        mail_ids = search_data[0].split()

        if not mail_ids:
            return EmailVerifyResult(success=False)

        parser = BytesParser()
        for mail_id in reversed(mail_ids):
            _, msg_data = mail.fetch(mail_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = parser.parsebytes(raw_email)

            subject = msg.get("Subject", "").lower()
            if "cloudflare" not in subject and "verify" not in subject:
                continue

            body = _extract_body(msg)
            link = extract_verification_link(body)
            otp = _extract_otp(body)

            if link:
                return EmailVerifyResult(success=True, link=link, otp=otp)

        return EmailVerifyResult(success=False)

    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
            except:
                pass


def _extract_body(msg: email.message.Message) -> str:
    """Extract text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return part.get_payload(decode=True).decode(errors="ignore")
            elif part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")
    return ""


def _extract_otp(body: str) -> str:
    """Extract 6-digit OTP from email body."""
    match = re.search(r'\b(\d{6})\b', body)
    return match.group(1) if match else ""


__all__ = ["EmailVerifyResult", "verify_cloudflare_email", "extract_verification_link"]
