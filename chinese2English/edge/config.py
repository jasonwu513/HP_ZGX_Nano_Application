from pydantic_settings import BaseSettings


class EdgeSettings(BaseSettings):
    model_config = {"env_prefix": "C2E_EDGE_", "env_file": ".env", "extra": "ignore"}

    # ASR (Sherpa-ONNX) — backend: sensevoice / breeze
    asr_backend: str = "sensevoice"
    asr_model_path: str = "models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
    asr_num_threads: int = 4

    # Translation (llama.cpp)
    translation_model_path: str = "models/Qwen3-1.7B-Q4_K_M.gguf"
    translation_num_threads: int = 4
    translation_ctx_size: int = 2048

    # TTS (Piper)
    piper_voice: str = "en_US-lessac-medium"
    piper_data_dir: str = "models/piper"
    piper_length_scale: float = 1.0    # 語速: <1 加快, >1 放慢
    piper_noise_scale: float = 0.667   # 語調變化: 越高越多變化
    piper_noise_w: float = 0.8         # 音素長度變化

    # Audio
    audio_device: int | None = None  # 麥克風裝置索引，None = 系統預設
    audio_output_device: int | None = None  # 播放裝置索引，None = 系統預設
    vad_energy_threshold: int = 500
    min_segment_duration: float = 0.5

    # SRT
    srt_enabled: bool = True
    srt_output_dir: str = "output"

    # Audio saving
    audio_save_enabled: bool = True
    audio_save_dir: str = "output/audio"
    audio_save_format: str = "ogg"  # "ogg" 或 "wav"

    # Speaker Diarization
    diarize_enabled: bool = False
    diarize_model_path: str = "models/diarization"
    diarize_num_speakers: int | None = None
    diarize_cosine_threshold: float = 0.38

    # Logging
    log_level: str = "INFO"


settings = EdgeSettings()
