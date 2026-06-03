import asyncio
from pathlib import Path
from typing import Dict, List

import edge_tts
from mutagen.mp3 import MP3

from config import Config
from steps import DemoStep


async def generate_audio_files(steps: List[DemoStep], config: Config) -> Dict[str, dict]:
    """
    Generate TTS audio for each step.
    Returns: {step_id: {"path": Path, "duration": float}}
    """
    config.audio_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, dict] = {}

    for step in steps:
        audio_path = config.audio_dir / f"{step.id}.mp3"
        print(f"  [{step.id}] generating audio...", end=" ", flush=True)

        communicate = edge_tts.Communicate(
            step.script,
            config.tts_voice,
            rate=config.tts_rate,
            pitch=config.tts_pitch,
        )
        await communicate.save(str(audio_path))

        duration = _mp3_duration(audio_path)
        results[step.id] = {"path": audio_path, "duration": duration}
        print(f"{duration:.1f}s")

    return results


def _mp3_duration(path: Path) -> float:
    return MP3(str(path)).info.length
