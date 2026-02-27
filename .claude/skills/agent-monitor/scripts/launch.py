#!/usr/bin/env python3
"""
Agent Monitor — Auto-Launch Script
Called by SessionStart hook to start the monitor server and open the dashboard.
"""

import json
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

PORT = 3847
SKILL_DIR = Path(__file__).parent.parent
SERVER_SCRIPT = SKILL_DIR / "scripts" / "server.js"


def is_server_running(port: int = PORT) -> bool:
    """Check if the server is already listening on the given port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_server() -> None:
    """Start server.js as a detached background process."""
    node = "node"
    args = [node, str(SERVER_SCRIPT), "--port", str(PORT)]

    if platform.system() == "Windows":
        # DETACHED_PROCESS = 0x00000008
        subprocess.Popen(
            args,
            creationflags=0x00000008,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    else:
        subprocess.Popen(
            args,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )


def find_chrome() -> Optional[str]:
    """Find Chrome executable path for the current platform."""
    system = platform.system()
    if system == "Windows":
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
    elif system == "Darwin":
        mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.isfile(mac_path):
            return mac_path
    else:
        # Linux — try which
        try:
            result = subprocess.run(["which", "google-chrome"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            result = subprocess.run(["which", "chromium-browser"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except FileNotFoundError:
            pass
    # Check CHROME_PATH env var as fallback
    return os.environ.get("CHROME_PATH")


def open_dashboard() -> None:
    """Open Chrome in --app mode pointing to the dashboard."""
    chrome = find_chrome()
    if not chrome:
        return  # Chrome not found — silent fail (hooks must not crash)

    url = f"http://127.0.0.1:{PORT}"
    args = [chrome, f"--app={url}", "--window-size=360,500"]

    system = platform.system()
    if system == "Windows":
        subprocess.Popen(
            args,
            creationflags=0x00000008,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    else:
        subprocess.Popen(
            args,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )


def main():
    """Entry point — only act on SessionStart events."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        event = json.loads(raw)

        if event.get("hook_event_name") != "SessionStart":
            return

        if not is_server_running():
            start_server()
            # Wait briefly for server to start
            for _ in range(10):
                time.sleep(0.3)
                if is_server_running():
                    break

        open_dashboard()
    except Exception:
        # Hooks must never crash
        pass


if __name__ == "__main__":
    main()
