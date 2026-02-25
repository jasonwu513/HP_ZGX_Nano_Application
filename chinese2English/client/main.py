import argparse
import asyncio
import logging
import sys


def main():
    parser = argparse.ArgumentParser(description="中英學習工具 - 客戶端")
    parser.add_argument(
        "--mode",
        choices=["realtime", "batch"],
        default="realtime",
        help="執行模式: realtime (即時翻譯) 或 batch (批次翻譯)",
    )
    parser.add_argument("--log-level", default="INFO", help="日誌等級")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.mode == "realtime":
        from client.realtime_mode import run_realtime
        asyncio.run(run_realtime())
    elif args.mode == "batch":
        from client.batch_mode import run_batch
        asyncio.run(run_batch())
    else:
        print(f"未知模式: {args.mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
