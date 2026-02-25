import logging
import os
import time as _time
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)


class SRTWriter:
    def __init__(self, output_dir: str = "output"):
        self._output_dir = output_dir
        self._file_rel = None       # 相對時間版
        self._file_wall = None      # wall-clock 版
        self._index = 0
        self._session_start_mono: float = 0.0
        self._session_start_wall: datetime | None = None
        self._current_date: date | None = None

    def start_session(self, session_start_mono: float):
        self._session_start_mono = session_start_mono
        self._session_start_wall = datetime.now()
        os.makedirs(self._output_dir, exist_ok=True)
        self._open_new_file()

    def _today(self) -> date:
        return date.today()

    def _open_new_file(self):
        if self._file_rel is not None:
            self._file_rel.close()
        if self._file_wall is not None:
            self._file_wall.close()
        self._current_date = self._today()
        self._index = 0
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")

        path_rel = os.path.join(self._output_dir, f"{timestamp}.srt")
        path_wall = os.path.join(self._output_dir, f"{timestamp}_wallclock.srt")
        self._file_rel = open(path_rel, "w", encoding="utf-8")
        self._file_wall = open(path_wall, "w", encoding="utf-8")
        logger.info("開啟 SRT 檔案: %s (+ wallclock)", path_rel)

    def _format_timestamp(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0.0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = round((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _mono_to_wall(self, mono: float) -> str:
        offset = mono - self._session_start_mono
        wall = self._session_start_wall + timedelta(seconds=offset)
        return f"{wall.hour:02d}:{wall.minute:02d}:{wall.second:02d},{wall.microsecond // 1000:03d}"

    def _build_text_lines(self, chinese: str, english: str, speaker: str | None) -> list[str]:
        if speaker:
            return [f"{speaker}：{chinese}", f"{speaker}: {english}"]
        return [chinese, english]

    def write_entry(
        self,
        segment_start_mono: float,
        segment_end_mono: float,
        chinese: str,
        english: str,
        speaker: str | None = None,
    ):
        if self._file_rel is None:
            return

        # 跨日偵測
        today = self._today()
        if today != self._current_date:
            logger.info("偵測到跨日，建立新 SRT 檔案")
            self._open_new_file()

        self._index += 1
        text_lines = self._build_text_lines(chinese, english, speaker)

        # 相對時間版
        start_rel = self._format_timestamp(segment_start_mono - self._session_start_mono)
        end_rel = self._format_timestamp(segment_end_mono - self._session_start_mono)
        entry_rel = "\n".join([str(self._index), f"{start_rel} --> {end_rel}"] + text_lines + [""]) + "\n"
        self._file_rel.write(entry_rel)
        self._file_rel.flush()

        # Wall-clock 版
        start_wall = self._mono_to_wall(segment_start_mono)
        end_wall = self._mono_to_wall(segment_end_mono)
        entry_wall = "\n".join([str(self._index), f"{start_wall} --> {end_wall}"] + text_lines + [""]) + "\n"
        self._file_wall.write(entry_wall)
        self._file_wall.flush()

    def close(self):
        if self._file_rel is not None:
            self._file_rel.close()
            self._file_rel = None
        if self._file_wall is not None:
            self._file_wall.close()
            self._file_wall = None
            logger.info("SRT 檔案已關閉")
