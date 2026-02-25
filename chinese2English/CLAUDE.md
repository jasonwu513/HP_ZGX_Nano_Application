# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chinese-to-English learning tool with two deployment modes:

1. **Client/Server** (GPU): Raspberry Pi client records Chinese speech → streams to GPU server for ASR → Translation → TTS → returns English audio and text. Supports real-time (WebSocket) and batch (HTTP).
2. **Edge** (CPU-only): Standalone x86 device runs the full pipeline offline using Sherpa-ONNX (ASR) + llama.cpp (Translation) + Piper (TTS). No network required.

## Commands

```bash
# Run server
python -m server.main

# Run client
python -m client.main --mode realtime
python -m client.main --mode batch

# Run all tests
PYTHONPATH=. python -m pytest tests/ -v

# Run a single test file
PYTHONPATH=. python -m pytest tests/server/test_pipeline.py -v

# Debug server with verbose logging
C2E_LOG_LEVEL=DEBUG python -m server.main

# Install dependencies
pip install -r requirements-server.txt   # GPU server
pip install -r requirements-client.txt   # Raspberry Pi client
pip install -r requirements-edge.txt     # Edge (x86 CPU offline)

# Run edge (standalone, no server needed)
python -m edge.main

# Debug edge with verbose logging
C2E_EDGE_LOG_LEVEL=DEBUG python -m edge.main
```

## Architecture

**Pipeline flow** (server/pipeline.py): `PipelineManager` orchestrates ASR → Translation → TTS through an async priority queue. Realtime requests (priority 0) preempt batch requests (priority 10). A single worker processes the queue sequentially to prevent GPU memory thrashing.

**GPU concurrency control**: Both `asr.py` and `translation.py` use independent `asyncio.Lock()` (`_gpu_lock`) and run inference in thread executors via `loop.run_in_executor()`. The pipeline's single-worker design ensures only one pipeline runs at a time, but the locks also guard against any concurrent `transcribe()` or `translate_*()` calls.

**TTS backend dispatch** (server/modules/tts/): Pluggable backends implementing `TTSBackend` ABC (`_base.py`). The `__init__.py` dispatch layer selects backend from `C2E_TTS_BACKEND` setting. Each backend provides `synthesize()` (streaming async iterator) and `synthesize_full()` (complete bytes).

**Client VAD state machine** (client/vad_processor.py): IDLE → SPEAKING → TRAILING_SILENCE → SEGMENT_READY. Uses TEN-VAD library if available, falls back to energy-based detection. After playback, the realtime mode drains the audio buffer and resets VAD to suppress echo.

**Edge pipeline** (edge/pipeline.py): Synchronous, single-threaded pipeline: VAD → ASR → Translation → TTS → Playback. Audio capture runs in a sounddevice callback thread feeding a `queue.Queue`. No asyncio, no GPU locks needed. After playback, the audio buffer is drained and VAD reset to suppress echo.

**Edge modules**: `edge/modules/asr.py` uses Sherpa-ONNX OfflineRecognizer (SenseVoice), `edge/modules/translation.py` uses llama-cpp-python (Qwen3-1.7B GGUF, CPU-only), `edge/modules/tts.py` uses Piper TTS. All are synchronous with module-level `load()` / inference functions.

## Configuration

All settings use Pydantic Settings with environment variable prefixes:
- Server: `C2E_*` (e.g., `C2E_TTS_BACKEND=piper`, `C2E_PIPELINE_TIMEOUT=120`)
- Client: `C2E_CLIENT_*` (e.g., `C2E_CLIENT_MIN_SEGMENT_ENERGY=300`)
- Edge: `C2E_EDGE_*` (e.g., `C2E_EDGE_ASR_MODEL_PATH=models/sherpa-onnx-sense-voice-zh-en`)

See `.env.example` for all available variables.

## Key Conventions

- Audio format throughout: 16kHz, 16-bit PCM, mono. Constants in `shared/constants.py`.
- All log messages are in Chinese (Traditional/Simplified mix).
- Translation model (Qwen3) may emit `<think>` blocks even with `enable_thinking=False`; these are stripped in `_generate_sync`.
- `app.py` at project root is a legacy file (pre-refactor); the active server entry point is `server/main.py`.
- Models are loaded once during FastAPI lifespan startup (`server/main.py`), not on first request.
- GPU memory: ASR ~1.2GB + Translation ~1.5GB ≈ 2.7GB minimum VRAM (with Piper TTS on CPU).
- Edge memory: Sherpa-ONNX ~300MB + Qwen3 Q4_K_M ~2.5GB + Piper ~200MB ≈ 3GB RAM. Recommend 8GB+ x86 device.
- Edge models must be downloaded manually to `models/` (Sherpa-ONNX SenseVoice, Qwen3-1.7B GGUF, Piper voice).
