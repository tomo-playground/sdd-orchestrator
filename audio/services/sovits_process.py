"""GPT-SoVITS subprocess lifecycle manager.

Audio Server가 GPT-SoVITS를 subprocess로 기동/관리한다.
Python 3.12 독립 venv를 그대로 사용하며, HTTP 프록시로 통합 제공.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess

import httpx

logger = logging.getLogger("audio-server")


class SoVITSProcessManager:
    """GPT-SoVITS subprocess lifecycle manager."""

    def __init__(
        self,
        sovits_dir: str,
        venv_path: str,
        port: int,
        config_path: str,
        startup_timeout: int = 120,
    ):
        self._process: subprocess.Popen | None = None
        self._sovits_dir = sovits_dir
        self._venv_python = f"{venv_path}/bin/python3"
        self._port = port
        self._config_path = config_path
        self._startup_timeout = startup_timeout
        self._base_url = f"http://127.0.0.1:{port}"

    @property
    def is_running(self) -> bool:
        """프로세스가 존재하고 살아있는지 확인."""
        if self._process is None:
            return False
        return self._process.poll() is None

    async def start(self) -> bool:
        """subprocess로 SoVITS 시작. health check로 준비 대기."""
        if self.is_running:
            logger.info("[SoVITS] Already running (PID %d)", self._process.pid)
            return True

        import pathlib  # noqa: PLC0415

        sovits_path = pathlib.Path(self._sovits_dir)
        if not sovits_path.exists():
            logger.warning("[SoVITS] Directory not found: %s", self._sovits_dir)
            return False

        log_dir = sovits_path / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "sovits.log"

        cmd = [
            self._venv_python,
            "api_v2.py",
            "-a",
            "127.0.0.1",
            "-p",
            str(self._port),
        ]

        from config import CUDA_HOME  # noqa: PLC0415

        env = {
            "PYTHONPATH": f".:{sovits_path / 'GPT_SoVITS'}",
            "PATH": f"{pathlib.Path(self._venv_python).parent}:/usr/bin:/bin",
            "HOME": str(pathlib.Path.home()),
            "CUDA_HOME": CUDA_HOME,
        }

        logger.info("[SoVITS] Starting: %s (port %d)", " ".join(cmd), self._port)

        with open(log_file, "a") as lf:
            self._process = subprocess.Popen(
                cmd,
                cwd=str(sovits_path),
                env=env,
                stdout=lf,
                stderr=lf,
            )

        logger.info("[SoVITS] PID: %d, waiting for ready...", self._process.pid)
        return await self._wait_ready()

    async def _wait_ready(self) -> bool:
        """health poll로 SoVITS 준비 대기."""
        for i in range(self._startup_timeout // 2):
            if not self.is_running:
                logger.error("[SoVITS] Process died during startup")
                return False
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(self._base_url, timeout=2)
                    # SoVITS에는 /health가 없으므로 GET / → 404/200 모두 ready 판정
                    if resp.status_code < 500:
                        logger.info("[SoVITS] Ready after %ds", (i + 1) * 2)
                        return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            await asyncio.sleep(2)

        logger.error("[SoVITS] Startup timeout (%ds)", self._startup_timeout)
        return False

    async def stop(self) -> None:
        """SIGTERM → SIGKILL graceful shutdown."""
        if not self.is_running:
            return

        pid = self._process.pid
        logger.info("[SoVITS] Stopping PID %d...", pid)
        self._process.terminate()

        try:
            self._process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("[SoVITS] SIGTERM timeout, sending SIGKILL")
            self._process.kill()
            self._process.wait(timeout=5)

        self._process = None
        logger.info("[SoVITS] Stopped (PID %d)", pid)

    async def health_check(self) -> bool:
        """SoVITS HTTP 응답 가능 여부."""
        if not self.is_running:
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self._base_url, timeout=3)
                return resp.status_code < 500
        except Exception:
            return False

    async def synthesize(
        self,
        text: str,
        ref_audio_path: str,
        prompt_text: str = "",
        prompt_lang: str = "ko",
        text_lang: str = "ko",
        speed_factor: float = 1.0,
    ) -> bytes:
        """SoVITS /tts 호출. raw WAV bytes 반환."""
        if not self.is_running:
            raise RuntimeError("GPT-SoVITS is not running")

        payload = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_lang": prompt_lang,
            "speed_factor": speed_factor,
            "media_type": "wav",
            "streaming_mode": False,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/tts",
                json=payload,
                timeout=180,
            )
            if not resp.is_success:
                detail = resp.text[:200]
                raise RuntimeError(f"SoVITS synthesis failed: {detail}")

        return resp.content


def _create_manager() -> SoVITSProcessManager:
    """config 기반 매니저 인스턴스 생성."""
    from config import SOVITS_CONFIG, SOVITS_DIR, SOVITS_PORT, SOVITS_STARTUP_TIMEOUT, SOVITS_VENV

    venv = SOVITS_VENV or f"{SOVITS_DIR}/.venv"
    return SoVITSProcessManager(
        sovits_dir=SOVITS_DIR,
        venv_path=venv,
        port=SOVITS_PORT,
        config_path=SOVITS_CONFIG,
        startup_timeout=SOVITS_STARTUP_TIMEOUT,
    )


sovits_manager = _create_manager()
