from pydantic_settings import BaseSettings


class ClientSettings(BaseSettings):
    model_config = {"env_prefix": "C2E_CLIENT_"}

    server_url: str = "ws://192.168.1.100:8000"
    server_http_url: str = "http://192.168.1.100:8000"

    audio_device_index: int | None = None  # None = system default
    sample_rate: int = 16000
    channels: int = 1
    frame_size: int = 256  # TEN-VAD hop_size

    min_segment_duration: float = 0.5   # 秒，短於此的片段丟棄
    min_segment_energy: int = 300       # 平均能量低於此的片段丟棄 (0=不過濾)

    # Audio saving
    audio_save_enabled: bool = True
    audio_save_dir: str = "output/audio"
    audio_save_format: str = "ogg"  # "ogg" 或 "wav"


client_settings = ClientSettings()
