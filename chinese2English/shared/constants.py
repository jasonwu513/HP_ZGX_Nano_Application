SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # int16 = 2 bytes
FRAME_SIZE = 256  # TEN-VAD hop_size
TRAILING_SILENCE_FRAMES = 30  # ~480ms at 16kHz/256 samples
VAD_SPEAKING_THRESHOLD = 3  # consecutive voiced frames to start speaking

WS_CHUNK_SIZE = 4096
BATCH_MAX_DURATION_SEC = 300  # 5 minutes max for batch mode

DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 8000
