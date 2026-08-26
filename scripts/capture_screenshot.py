#!/usr/bin/env python
"""Capture a browser screenshot of the running CodeGraph UI."""
import pathlib
import sys

QUESTION = "What would break if I removed the Depends() helper?"
OUT = pathlib.Path("docs/screenshot.png")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print(
        "playwright not installed — skipping screenshot. "
        "Run: uv pip install playwright && playwright install chromium"
    )
    sys.exit(0)

OUT.parent.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto("http://localhost:5173", wait_until="networkidle")
    # Type the question and submit
    page.fill("input[placeholder]", QUESTION)  # ChatPanel input has a placeholder
    page.keyboard.press("Enter")
    # Wait up to 45s for streaming to complete (status chip or just timeout)
    try:
        page.wait_for_selector("[data-status='done']", timeout=45_000)
    except Exception:
        page.wait_for_timeout(30_000)  # fallback: wait 30s regardless
    page.screenshot(path=str(OUT), full_page=False)
    browser.close()

print(f"Screenshot saved: {OUT}")
