"""Environment diagnostics for Selenium Python.

Answers the questions that must be settled before writing or debugging any
Selenium code: which Selenium is installed, which browsers exist, whether
Selenium Manager can resolve a driver, and whether a real session starts.

    python selenium_doctor.py                # inspect only, no browser launched
    python selenium_doctor.py --launch       # also start and quit a headless session
    python selenium_doctor.py --launch --browser firefox --json

Exit codes: 0 all checks passed, 1 a check failed.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

WINDOWS_BROWSER_PATHS = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "firefox": [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ],
}

POSIX_BROWSER_COMMANDS = {
    "chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
    "edge": ["microsoft-edge", "microsoft-edge-stable"],
    "firefox": ["firefox"],
}


def _run(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    output = (result.stdout or result.stderr or "").strip()
    return output.splitlines()[0] if output else None


def find_browsers() -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    if platform.system() == "Windows":
        for name, paths in WINDOWS_BROWSER_PATHS.items():
            for candidate in paths:
                if Path(candidate).exists():
                    version = _run(
                        [
                            "powershell",
                            "-NoProfile",
                            "-Command",
                            f"(Get-Item '{candidate}').VersionInfo.ProductVersion",
                        ]
                    )
                    found[name] = {"path": candidate, "version": version}
                    break
    else:
        for name, commands in POSIX_BROWSER_COMMANDS.items():
            for command in commands:
                path = shutil.which(command)
                if path:
                    found[name] = {"path": path, "version": _run([path, "--version"])}
                    break
    return found


def selenium_info() -> dict[str, Any]:
    info: dict[str, Any] = {}
    try:
        import selenium

        info["version"] = getattr(selenium, "__version__", "unknown")
        info["location"] = str(Path(selenium.__file__).parent)
    except ImportError as exc:
        info["error"] = f"selenium is not installed: {exc}"
        return info

    try:
        from selenium.webdriver.common.selenium_manager import SeleniumManager

        binary = SeleniumManager().get_binary()
        info["selenium_manager"] = str(binary)
        info["selenium_manager_exists"] = Path(binary).exists()
    except Exception as exc:  # noqa: BLE001 - internal API, version-sensitive
        info["selenium_manager"] = f"<not resolvable: {type(exc).__name__}>"
    return info


def launch_check(browser: str) -> dict[str, Any]:
    """Start a real headless session, read one capability set, and quit."""
    result: dict[str, Any] = {"browser": browser, "ok": False}
    try:
        from selenium import webdriver
    except ImportError as exc:
        result["error"] = str(exc)
        return result

    options_factory = {
        "chrome": webdriver.ChromeOptions,
        "edge": webdriver.EdgeOptions,
        "firefox": webdriver.FirefoxOptions,
    }
    driver_factory = {
        "chrome": webdriver.Chrome,
        "edge": webdriver.Edge,
        "firefox": webdriver.Firefox,
    }
    if browser not in driver_factory:
        result["error"] = f"unsupported browser {browser!r}"
        return result

    options = options_factory[browser]()
    options.add_argument("-headless" if browser == "firefox" else "--headless=new")
    driver = None
    try:
        driver = driver_factory[browser](options=options)
        driver.get("data:text/html,<title>sentinel</title><h1>ok</h1>")
        caps = driver.capabilities or {}
        result.update(
            ok=driver.title == "sentinel",
            browser_version=caps.get("browserVersion"),
            platform=caps.get("platformName"),
            session_id=driver.session_id,
        )
    except Exception as exc:  # noqa: BLE001 - report, never raise, from a doctor
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:  # noqa: BLE001
                pass
    return result


def collect(launch: bool, browser: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "python": {
            "version": sys.version.split()[0],
            "executable": sys.executable,
            "supported": sys.version_info >= (3, 10),
        },
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "selenium": selenium_info(),
        "browsers": find_browsers(),
        "proxy_env": {
            key: os.environ[key]
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy")
            if key in os.environ
        },
        "selenium_manager_env": {
            key: value for key, value in os.environ.items() if key.startswith("SE_")
        },
    }
    if launch:
        report["launch"] = launch_check(browser)
    return report


def render(report: dict[str, Any]) -> None:
    python = report["python"]
    print(f"Python        {python['version']}  ({'supported' if python['supported'] else 'TOO OLD: need 3.10+'})")
    selenium = report["selenium"]
    if "error" in selenium:
        print(f"Selenium      MISSING - {selenium['error']}")
    else:
        print(f"Selenium      {selenium['version']}")
        print(f"  manager     {selenium.get('selenium_manager')}")
    print(f"OS            {report['os']['system']} {report['os']['release']} ({report['os']['machine']})")
    if report["browsers"]:
        for name, data in report["browsers"].items():
            print(f"Browser       {name:<8} {data.get('version') or 'unknown version'}  {data['path']}")
    else:
        print("Browser       none detected in the standard locations")
    if report["proxy_env"]:
        print(f"Proxy env     {', '.join(report['proxy_env'])}")
    if report["selenium_manager_env"]:
        print(f"SE_* env      {', '.join(report['selenium_manager_env'])}")
    if "launch" in report:
        launch = report["launch"]
        if launch["ok"]:
            print(f"Launch        OK - {launch['browser']} {launch.get('browser_version')} headless session started and quit")
        else:
            print(f"Launch        FAILED - {launch.get('error')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose the local Selenium environment")
    parser.add_argument("--launch", action="store_true", help="Start and quit a headless session")
    parser.add_argument("--browser", default="chrome", choices=["chrome", "firefox", "edge"])
    parser.add_argument("--json", action="store_true", help="Emit the raw report as JSON")
    args = parser.parse_args()

    report = collect(args.launch, args.browser)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        render(report)

    healthy = report["python"]["supported"] and "error" not in report["selenium"]
    if args.launch:
        healthy = healthy and report["launch"]["ok"]
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
