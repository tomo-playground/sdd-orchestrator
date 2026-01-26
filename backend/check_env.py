import pathlib
import subprocess

import httpx
from dotenv import load_dotenv

from config import (
    API_PUBLIC_URL,
    AUDIO_DIR,
    FONTS_DIR,
    GEMINI_API_KEY,
    OUTPUT_DIR,
    OVERLAY_DIR,
    SD_BASE_URL,
    TEMPLATES_DIR,
)


# ANSI colors for better visibility
class Colors:
    OK = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"

def print_result(msg, status="OK"):
    if status == "OK":
        print(f"{Colors.OK}[OK]{Colors.ENDC} {msg}")
    elif status == "WARNING":
        print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} {msg}")
    else:
        print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} {msg}")

def check_env():
    # Get current script directory
    script_dir = pathlib.Path(__file__).parent.resolve()
    print(f"{Colors.BOLD}--- Shorts Producer Environment Diagnostic ---{Colors.ENDC}\n")

    # 1. Check .env file
    env_path = script_dir / ".env"
    if not env_path.exists():
        print_result(f".env file not found at {env_path}", "FAIL")
        return
    load_dotenv(env_path)
    print_result(".env file exists")

    # 2. Check Required Configs
    configs = {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "SD_BASE_URL": SD_BASE_URL,
        "API_PUBLIC_URL": API_PUBLIC_URL
    }
    for key, val in configs.items():
        if val:
            # Mask sensitive info
            masked = str(val)[:6] + "..." + str(val)[-4:] if len(str(val)) > 10 else "***"
            print_result(f"Config {key}: {masked}")
        else:
            print_result(f"Config {key} is missing", "FAIL")

    # 3. Check System Tools (FFmpeg)
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print_result("FFmpeg is installed and accessible")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_result("FFmpeg is NOT installed or not in PATH", "FAIL")

    # 4. Check External Connections (Stable Diffusion)
    print(f"Checking Stable Diffusion WebUI at {SD_BASE_URL}...")
    try:
        # Use a short timeout for diagnostic
        response = httpx.get(f"{SD_BASE_URL}/sdapi/v1/options", timeout=5.0)
        if response.status_code == 200:
            print_result("Stable Diffusion WebUI API is responsive")
        else:
            print_result(f"Stable Diffusion WebUI returned status {response.status_code}", "WARNING")
    except Exception as e:
        print_result(f"Stable Diffusion WebUI is unreachable: {e}", "FAIL")

    # 5. Check Critical Directories & Assets
    critical_paths = [
        AUDIO_DIR,
        FONTS_DIR / "BlackHanSans-Regular.ttf",
        OVERLAY_DIR / "overlay_bold.png",
        TEMPLATES_DIR / "create_storyboard.j2",
        OUTPUT_DIR
    ]

    for p in critical_paths:
        if p.exists():
            print_result(f"Asset/Path exists: {p}")
        else:
            print_result(f"Asset/Path missing: {p}", "FAIL")

    print(f"\n{Colors.BOLD}--- Diagnostic Complete ---{Colors.ENDC}")

    print(f"\n{Colors.BOLD}--- Diagnostic Complete ---{Colors.ENDC}")

if __name__ == "__main__":
    check_env()
