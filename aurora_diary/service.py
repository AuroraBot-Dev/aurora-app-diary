"""按日期存取文本；路径和写入结果不依赖宿主项目。"""

from __future__ import annotations

import os
import re
import tempfile
from datetime import date as Date
from pathlib import Path

MAX_CONTENT_LENGTH = 100_000
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)


def validate_date(value: str) -> str:
    """仅接受真实的 YYYY-MM-DD 日期，拒绝路径成分。"""
    if not isinstance(value, str) or _DATE.fullmatch(value) is None:
        raise ValueError("日期必须是 YYYY-MM-DD 格式")
    try:
        Date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("日期不存在") from error
    return value


class DiaryService:
    """同一目录只由一个 Server 进程写入；.json 文件内容为 UTF-8 文本。"""

    def __init__(self, data_dir: Path) -> None:
        self.diary_dir = data_dir.expanduser().resolve()

    def _path(self, date: str) -> Path:
        path = self.diary_dir / f"{validate_date(date)}.json"
        if path.is_symlink() or path.resolve().parent != self.diary_dir:
            raise ValueError("日记路径不允许符号链接或越出数据目录")
        return path

    def write_diary(self, date: str, content: str) -> dict[str, object]:
        """完整替换当天内容；先写临时文件再原子替换。"""
        path = self._path(date)
        if not isinstance(content, str) or not content.strip() or len(content) > MAX_CONTENT_LENGTH:
            raise ValueError("日记内容必须非空且不超过 100000 字符")
        self.diary_dir.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.diary_dir, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return {"saved": True, "date": date}

    def read_diary(self, date: str) -> dict[str, object]:
        path = self._path(date)
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {"found": False, "date": date, "content": ""}
        return {"found": True, "date": date, "content": content}

    def list_dates(self) -> dict[str, object]:
        dates: list[str] = []
        for path in self.diary_dir.glob("*.json"):
            try:
                validate_date(path.stem)
            except ValueError:
                continue
            if path.is_file() and not path.is_symlink():
                dates.append(path.stem)
        dates.sort()
        return {"dates": dates, "count": len(dates)}
