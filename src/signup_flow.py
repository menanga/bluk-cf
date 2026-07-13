"""
Cloudflare Signup Flow — Automated account creation via headless browser.

Handles:
1. Navigate to sign-up page
2. Fill email + password
3. Solve Turnstile CAPTCHA
4. Submit form
5. Extract Account ID from redirect URL
"""

import asyncio
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

import nodriver as uc

from .turnstile_bypass import verify_cf, is_turnstile_present


CLOUDFLARE_SIGNUP_URL = "https://dash.cloudflare.com/sign-up"


class SignupResult:
    """Result of a signup attempt."""

    def __init__(
        self,
        success: bool,
        email: str = "",
        password: str = "",
        account_id: str = "",
        error: str = "",
        page_url: str = "",
    ):
        self.success = success
        self.email = email
        self.password = password
        self.account_id = account_id
        self.error = error
        self.page_url = page_url

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "email": self.email,
            "password": self.password,
            "account_id": self.account_id,
            "error": self.error,
        }


async def signup(
    page: uc.Tab,
    email: str,
    password: str,
    max_wait: int = 30,
    retry_turnstile: bool = True,
) -> SignupResult:
    """
    Execute the Cloudflare signup flow.

    Args:
        page: nodriver Tab (already navigated to sign-up or will navigate)
        email: Email address for the new account
        password: Password for the new account
        max_wait: Max seconds to wait for redirect after submit
        retry_turnstile: Whether to retry Turnstile if first attempt fails

    Returns:
        SignupResult with account_id on success
    """
    # Navigate to signup
    await page.get(CLOUDFLARE_SIGNUP_URL)
    await asyncio.sleep(8)

    # Fill email
    email_input = await page.select('input[name="email"]', timeout=15)
    if not email_input:
        return SignupResult(False, email=email, error="Email input not found")
    await email_input.click()
    await asyncio.sleep(0.5)
    await email_input.send_keys(email)
    await asyncio.sleep(1)

    # Fill password
    pw_input = await page.select('input[name="password"]', timeout=5)
    if not pw_input:
        return SignupResult(False, email=email, error="Password input not found")
    await pw_input.click()
    await asyncio.sleep(0.5)
    await pw_input.send_keys(password)
    await asyncio.sleep(1)

    # Verify password value in DOM
    pw_value = await pw_input.apply("el => el.value")
    logger.info(f"Password field value length: {len(pw_value) if pw_value else 0}")
    if not pw_value or len(pw_value) < 8:
        logger.warning(f"Password not entered correctly. Retrying...")
        await pw_input.clear_input()
        await asyncio.sleep(0.5)
        await pw_input.send_keys(password)
        await asyncio.sleep(1)

    # Wait for validation to clear
    await asyncio.sleep(2)

    # Scroll to make Turnstile visible
    await page.evaluate("window.scrollBy(0, 400)")
    await asyncio.sleep(3)

    # Solve Turnstile
    turnstile_present = await is_turnstile_present(page)
    if turnstile_present:
        try:
            token = await verify_cf(page, timeout=60)
            print(f"    ✅ Turnstile solved: {token[:20]}...")
        except (TimeoutError, RuntimeError) as e:
            if retry_turnstile:
                # Retry once
                await asyncio.sleep(5)
                try:
                    token = await verify_cf(page, timeout=60)
                    print(f"    ✅ Turnstile solved (retry): {token[:20]}...")
                except Exception as e2:
                    return SignupResult(False, email=email, error=f"Turnstile failed: {e2}")
            else:
                return SignupResult(False, email=email, error=f"Turnstile failed: {e}")
    await asyncio.sleep(5)

    # Submit form
    submit_btn = await page.select('button[type="submit"]', timeout=5)
    if not submit_btn:
        return SignupResult(False, email=email, error="Submit button not found")
    await submit_btn.scroll_into_view()
    await asyncio.sleep(1)
    await submit_btn.click()

    # Wait for redirect
    for i in range(max_wait):
        await asyncio.sleep(1)
        url = await page.evaluate("location.href")
        if "/sign-up" not in url:
            break
        # Debug: log every 10s
        if i > 0 and i % 10 == 0:
            print(f"[DEBUG] Still on signup page after {i}s, URL: {url}")

    await asyncio.sleep(10)  # Extra wait for dashboard to load

    # Check if still on signup after max_wait
    final_url = await page.evaluate("location.href")
    if "/sign-up" in final_url:
        # Capture error messages or page state
        error_text = await page.evaluate("""
            Array.from(document.querySelectorAll('p, [role="alert"], .error'))
                .map(el => el.textContent.trim())
                .filter(t => t.length > 0)
                .join(' | ')
        """)
        return SignupResult(False, email=email, error=f"Redirect failed: {final_url}. Errors: {error_text or 'none'}")

    # Extract Account ID from URL
    url = await page.evaluate("location.href")
    match = re.search(r"/([a-f0-9]{32})", url)
    if match:
        account_id = match.group(1)
        return SignupResult(
            True,
            email=email,
            password=password,
            account_id=account_id,
            page_url=url,
        )

    # Check for error messages
    error_msgs = await page.evaluate("""
        Array.from(document.querySelectorAll('p, [role="alert"]'))
            .map(e => e.textContent.trim())
            .filter(t => t.includes('unable') || t.includes('limit') || t.includes('Incorrect'))
    """)
    error = error_msgs if error_msgs else f"Redirect failed: {url[:80]}"

    return SignupResult(False, email=email, error=str(error))
