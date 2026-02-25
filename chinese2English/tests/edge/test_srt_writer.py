import os
import tempfile
from datetime import date
from unittest.mock import patch

from edge.srt_writer import SRTWriter


def _get_rel_files(tmpdir):
    """取得相對時間版 SRT 檔案（不含 _wallclock）。"""
    return sorted(f for f in os.listdir(tmpdir) if f.endswith(".srt") and "_wallclock" not in f)


def _get_wall_files(tmpdir):
    """取得 wall-clock 版 SRT 檔案。"""
    return sorted(f for f in os.listdir(tmpdir) if "_wallclock.srt" in f)


class TestSRTTimestampFormat:
    def test_format_timestamp_zero(self):
        writer = SRTWriter()
        assert writer._format_timestamp(0) == "00:00:00,000"

    def test_format_timestamp_seconds(self):
        writer = SRTWriter()
        assert writer._format_timestamp(1.2) == "00:00:01,200"

    def test_format_timestamp_minutes(self):
        writer = SRTWriter()
        assert writer._format_timestamp(65.5) == "00:01:05,500"

    def test_format_timestamp_hours(self):
        writer = SRTWriter()
        assert writer._format_timestamp(3661.123) == "01:01:01,123"

    def test_format_timestamp_negative_clamps_to_zero(self):
        writer = SRTWriter()
        assert writer._format_timestamp(-5.0) == "00:00:00,000"


class TestSRTWriteEntry:
    def test_creates_both_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SRTWriter(output_dir=tmpdir)
            writer.start_session(100.0)
            writer.write_entry(101.0, 103.0, "你好", "Hello")
            writer.close()

            rel_files = _get_rel_files(tmpdir)
            wall_files = _get_wall_files(tmpdir)
            assert len(rel_files) == 1
            assert len(wall_files) == 1

    def test_relative_file_has_relative_timestamps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SRTWriter(output_dir=tmpdir)
            writer.start_session(100.0)
            writer.write_entry(101.0, 103.0, "你好世界", "Hello world")
            writer.close()

            rel_files = _get_rel_files(tmpdir)
            content = open(os.path.join(tmpdir, rel_files[0]), encoding="utf-8").read()
            assert "1\n" in content
            assert "00:00:01,000 --> 00:00:03,000" in content
            assert "你好世界" in content
            assert "Hello world" in content

    def test_wallclock_file_has_wall_timestamps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SRTWriter(output_dir=tmpdir)
            writer.start_session(100.0)
            writer.write_entry(101.0, 103.0, "你好世界", "Hello world")
            writer.close()

            wall_files = _get_wall_files(tmpdir)
            content = open(os.path.join(tmpdir, wall_files[0]), encoding="utf-8").read()
            assert "1\n" in content
            assert "你好世界" in content
            # Wall-clock 時間不會是 00:00:01（除非剛好午夜測試）
            # 只驗證格式正確：HH:MM:SS,mmm --> HH:MM:SS,mmm
            import re
            assert re.search(r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}", content)

    def test_single_entry_with_speaker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SRTWriter(output_dir=tmpdir)
            writer.start_session(100.0)
            writer.write_entry(101.5, 103.5, "你好世界", "Hello world", speaker="Speaker 1")
            writer.close()

            # 兩個檔案都應有 speaker 標記
            for f in os.listdir(tmpdir):
                if f.endswith(".srt"):
                    content = open(os.path.join(tmpdir, f), encoding="utf-8").read()
                    assert "Speaker 1：你好世界" in content
                    assert "Speaker 1: Hello world" in content

    def test_multiple_entries_sequential_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SRTWriter(output_dir=tmpdir)
            writer.start_session(0.0)
            writer.write_entry(1.0, 2.0, "第一句", "First")
            writer.write_entry(3.0, 4.0, "第二句", "Second")
            writer.close()

            rel_files = _get_rel_files(tmpdir)
            content = open(os.path.join(tmpdir, rel_files[0]), encoding="utf-8").read()
            lines = content.strip().split("\n")
            assert lines[0] == "1"
            assert "2" in content.split("Second")[0].split("First")[-1]

    def test_no_write_before_start_session(self):
        writer = SRTWriter()
        # Should not raise, just do nothing
        writer.write_entry(1.0, 2.0, "test", "test")
        writer.close()


class TestSRTDateRollover:
    def test_date_change_creates_new_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SRTWriter(output_dir=tmpdir)
            writer.start_session(0.0)

            writer.write_entry(1.0, 2.0, "今天", "Today")

            tomorrow = date(2099, 12, 31)
            with patch.object(writer, "_today", return_value=tomorrow):
                writer.write_entry(3.0, 4.0, "明天", "Tomorrow")

            writer.close()

            # 跨日後各產生 2 個檔案（rel + wall）× 2 天 = 4 檔
            rel_files = _get_rel_files(tmpdir)
            wall_files = _get_wall_files(tmpdir)
            assert len(rel_files) == 2
            assert len(wall_files) == 2

    def test_date_rollover_resets_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = SRTWriter(output_dir=tmpdir)
            writer.start_session(0.0)

            writer.write_entry(1.0, 2.0, "第一句", "First")
            writer.write_entry(3.0, 4.0, "第二句", "Second")

            tomorrow = date(2099, 12, 31)
            with patch.object(writer, "_today", return_value=tomorrow):
                writer.write_entry(5.0, 6.0, "新一天", "New day")

            writer.close()

            # 第二個 rel 檔案 index 應該從 1 開始
            rel_files = _get_rel_files(tmpdir)
            content = open(os.path.join(tmpdir, rel_files[1]), encoding="utf-8").read()
            assert content.strip().startswith("1\n")
