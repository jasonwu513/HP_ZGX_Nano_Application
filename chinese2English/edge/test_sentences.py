"""
測試腳本：用 10 個中文句子驗證 翻譯 → TTS → 播放 流程。
用法：python -m edge.test_sentences
"""

import logging
import sys
import time

from edge.config import settings

TEST_SENTENCES = [
    "你好，今天天氣很好。",
    "我喜歡吃蘋果和香蕉。",
    "這隻小貓很可愛。",
    "媽媽正在廚房做飯。",
    "我們一起去公園玩吧。",
    "弟弟在學校學了很多東西。",
    "天空是藍色的，雲是白色的。",
    "謝謝你幫助我。",
    "我的爸爸是一位老師。",
    "晚安，做個好夢。",
]


def main():
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    from edge.modules import translation, tts
    from edge.audio_player import AudioPlayer

    player = AudioPlayer()

    print("載入模型中...")
    translation.load()
    tts.load()
    print("模型載入完成\n")

    for i, sentence in enumerate(TEST_SENTENCES, 1):
        print(f"--- 第 {i}/10 句 ---")
        print(f"中文: {sentence}")

        t0 = time.perf_counter()
        english = translation.translate(sentence)
        t_trans = time.perf_counter() - t0

        print(f"英文: {english}")
        print(f"翻譯耗時: {t_trans:.1f}s")

        t0 = time.perf_counter()
        wav_bytes = tts.synthesize(english)
        t_tts = time.perf_counter() - t0
        print(f"TTS 耗時: {t_tts:.1f}s")

        player.play_wav_bytes(wav_bytes)
        print()

    print("測試完成！")


if __name__ == "__main__":
    main()
