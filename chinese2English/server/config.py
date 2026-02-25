from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "C2E_"}

    asr_model_id: str = "Qwen/Qwen3-ASR-0.6B"
    translation_model_id: str = "Qwen/Qwen3-1.7B"

    # TTS backend selection
    tts_backend: Literal["piper", "edge", "cosyvoice", "none"] = "piper"

    # CosyVoice settings
    cosyvoice_model_dir: str = "CosyVoice2-0.5B"
    cosyvoice_speaker: str = "default"

    # Piper TTS settings
    piper_voice: str = "en_US-lessac-medium"
    piper_data_dir: str = "models/piper"

    # edge-tts settings
    edge_tts_voice: str = "en-US-AriaNeural"

    pipeline_timeout: int = 120  # seconds

    server_host: str = "0.0.0.0"
    server_port: int = 8000

    log_level: str = "INFO"


settings = Settings()
