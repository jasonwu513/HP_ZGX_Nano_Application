"""
聲紋註冊工具 — 錄製家人語音並儲存 embedding profile。

使用方式:
    python -m edge.enroll_speaker 阿公
    python -m edge.enroll_speaker 阿嬤 --duration 8
    python -m edge.enroll_speaker 媽媽 --device 12

錄完後 profile 存在 models/diarization/profiles/{名字}.npy
下次啟動 edge pipeline 會自動載入。
"""
import argparse
import logging
import os
import struct
import sys
import time

import numpy as np
import sounddevice as sd

from edge.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


def record_audio(duration: float, device: int | None = None) -> bytes:
    """錄製指定秒數的音訊，回傳 PCM int16 bytes。"""
    print(f"\n準備錄音 {duration} 秒，請開始說話...")
    print("3...", end=" ", flush=True)
    time.sleep(1)
    print("2...", end=" ", flush=True)
    time.sleep(1)
    print("1...", end=" ", flush=True)
    time.sleep(1)
    print("開始！\n")

    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        device=device,
    )
    sd.wait()
    print("錄音完成！")
    return audio.tobytes()


def main():
    parser = argparse.ArgumentParser(description="聲紋註冊工具")
    parser.add_argument("name", help="說話者名稱（如：阿公、媽媽、姊姊）")
    parser.add_argument("--duration", type=float, default=5.0, help="錄音秒數（預設 5 秒）")
    parser.add_argument("--device", type=int, default=None, help="麥克風裝置索引")
    parser.add_argument("--model-path", default=None, help="Diarization 模型路徑")
    args = parser.parse_args()

    model_path = args.model_path or settings.diarize_model_path
    profiles_dir = os.path.join(model_path, "profiles")
    profile_path = os.path.join(profiles_dir, f"{args.name}.npy")

    device = args.device if args.device is not None else settings.audio_device

    # 顯示裝置資訊
    print(f"\n=== 聲紋註冊: {args.name} ===")
    print(f"麥克風裝置: {device or '系統預設'}")
    print(f"儲存位置: {profile_path}")

    if os.path.exists(profile_path):
        resp = input(f"\n{args.name} 的聲紋已存在，要覆蓋嗎？(y/N) ")
        if resp.lower() != "y":
            print("取消。")
            return

    # 載入 diarization engine
    from edge.modules.diarization import DiarizationEngine
    engine = DiarizationEngine(model_path=model_path)

    # 錄音
    pcm_data = record_audio(args.duration, device=device)

    # 檢查能量
    n_samples = len(pcm_data) // 2
    samples = struct.unpack(f"<{n_samples}h", pcm_data)
    avg_energy = sum(abs(s) for s in samples) / n_samples
    if avg_energy < 100:
        print(f"\n警告：錄音能量偏低 ({avg_energy:.0f})，可能沒有收到聲音。")
        resp = input("是否仍要儲存？(y/N) ")
        if resp.lower() != "y":
            print("取消。")
            return

    # 提取 embedding
    embedding = engine.extract_embedding(pcm_data, SAMPLE_RATE)

    # 儲存
    os.makedirs(profiles_dir, exist_ok=True)
    np.save(profile_path, embedding)

    print(f"\n聲紋已儲存: {profile_path}")
    print(f"Embedding 維度: {embedding.shape}")
    print(f"錄音能量: {avg_energy:.0f}")
    print(f"\n下次啟動 edge pipeline 將自動載入 {args.name} 的聲紋。")


if __name__ == "__main__":
    main()
