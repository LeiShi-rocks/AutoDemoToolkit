from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class Config:
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)

    @property
    def project_root(self) -> Path:
        return self.base_dir.parent

    @property
    def output_dir(self) -> Path:
        return self.base_dir / "output"

    @property
    def audio_dir(self) -> Path:
        return self.output_dir / "audio"

    @property
    def video_dir(self) -> Path:
        return self.output_dir / "video"

    @property
    def final_dir(self) -> Path:
        return self.output_dir / "final"

    @property
    def snapshot_dir(self) -> Path:
        return self.output_dir / "snapshots"

    # App
    app_port: int = 8501
    app_startup_timeout: int = 45
    snapshot_server_port: int = 8502  # local HTTP server for snapshot HTML files

    # Command to start the app process (optional — set in plan YAML or via start_command)
    start_command: Optional[str] = None
    # Extra environment variables to pass to the app process
    app_env: Dict[str, str] = field(default_factory=dict)

    @property
    def app_url(self) -> str:
        return f"http://localhost:{self.app_port}"

    # Video
    video_width: int = 1280
    video_height: int = 800

    # TTS
    tts_voice: str = "en-US-JennyNeural"
    tts_rate: str = "+0%"
    tts_pitch: str = "+0Hz"

    # Timing
    llm_wait_ms: int = 20_000  # max wait for slow-loading panels (LLM-driven or async)

    def ensure_dirs(self):
        for d in (self.audio_dir, self.video_dir, self.final_dir, self.snapshot_dir):
            d.mkdir(parents=True, exist_ok=True)
