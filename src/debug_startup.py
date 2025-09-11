#!/usr/bin/env python3
import os
import sys
import logging
import time
import platform
from pathlib import Path
import httpx
import shutil
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("debug-startup")

def mask(tok: str):
    if not tok:
        return "<missing>"
    tok = tok.strip()
    if len(tok) <= 10:
        return tok[0:2] + "..." + tok[-2:]
    return tok[0:6] + "..." + tok[-4:]

def list_dir(path: Path, depth=1):
    try:
        return [p.name + ("/" if p.is_dir() else "") for p in sorted(path.iterdir())]
    except Exception as e:
        return [f"error listing {path}: {e}"]

def check_ffmpeg():
    try:
        res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=8)
        if res.returncode == 0:
            first = res.stdout.splitlines()[0]
            return f"ffmpeg present: {first}"
        return f"ffmpeg returned code {res.returncode}"
    except FileNotFoundError:
        return "ffmpeg: NOT FOUND"
    except Exception as e:
        return f"ffmpeg check error: {e}"

def main():
    log.info("=== START debug_startup ===")

    # Basic environment
    log.info("Python: %s", platform.python_version())
    log.info("Platform: %s", platform.platform())
    cwd = Path.cwd()
    log.info("Working dir: %s", str(cwd))
    log.info("Repo top-level listing: %s", list_dir(cwd))

    # Show src folder
    src = cwd / "src"
    log.info("src exists: %s", src.exists())
    if src.exists():
        log.info("src listing: %s", list_dir(src))

    # Show BOT file presence
    bot_py = src / "bot.py"
    debug_py = src / "debug_startup.py"
    log.info("src/bot.py exists: %s", bot_py.exists())
    log.info("src/debug_startup.py exists: %s", debug_py.exists())

    # Env var checks (mask values)
    env_candidates = {k: v for k, v in os.environ.items() if "TELEGRAM" in k.upper() or "TOKEN" in k.upper() or "BOT" in k.upper()}
    if not env_candidates:
        log.warning("No environment vars found that look like tokens (TELEGRAM_TOKEN, TELEGRAM_BOT_TOKEN, etc).")
    for k, v in env_candidates.items():
        log.info("ENV: %s = %s (len=%d)", k, mask(v), len(v))

    # Check specifically for TELEGRAM_TOKEN and TELEGRAM_BOT_TOKEN
    token_keys = ["TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT", "BOT_TOKEN"]
    found = False
    for tk in token_keys:
        val = os.getenv(tk)
        if val:
            found = True
            log.info("Found %s = %s", tk, mask(val))
            token = val.strip()
            break
    if not found:
        token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
        if token:
            log.info("Found fallback token = %s", mask(token))
            found = True

    # Network check: call Telegram getMe
    if found and token:
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            log.info("Calling Telegram getMe to validate token and network...")
            with httpx.Client(timeout=8.0) as client:
                r = client.get(url)
            log.info("Telegram getMe status: %s", r.status_code)
            # show small part of response safely
            try:
                j = r.json()
                ok = j.get("ok")
                log.info("Telegram getMe ok: %s", ok)
                if ok:
                    result = j.get("result", {})
                    log.info("Bot info: id=%s, username=%s, first_name=%s", result.get("id"), result.get("username"), result.get("first_name"))
                else:
                    log.warning("getMe returned not ok: %s", j)
            except Exception as e:
                log.warning("Failed to parse Telegram response JSON: %s", e)
        except Exception as e:
            log.exception("Error calling Telegram API: %s", e)
    else:
        log.error("No token found in env for Telegram. Confirm TELEGRAM_TOKEN is set in Render service Environment Variables.")

    # Check ffmpeg presence
    log.info("FFMPEG check: %s", check_ffmpeg())

    # Disk space
    try:
        total, used, free = shutil.disk_usage("/")
        log.info("Disk usage (bytes) total=%d used=%d free=%d", total, used, free)
    except Exception as e:
        log.warning("Disk usage check failed: %s", e)

    log.info("=== debug_startup finished — sleeping to keep container alive for inspection ===")
    # Keep alive so you can inspect logs; exit only if TELEGRAM_TOKEN missing earlier
    for i in range(600):  # sleep 10 minutes maximum
        time.sleep(1)

if __name__ == "__main__":
    main()
