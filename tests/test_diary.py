from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp.client.client import Client

from aurora_diary.protocol import CONTRACT, invoke
from aurora_diary.server import create_server
from aurora_diary.service import DiaryService


def test_roundtrip_and_restart(tmp_path: Path) -> None:
    service = DiaryService(tmp_path)
    assert service.read_diary("2026-09-04")["found"] is False
    assert service.write_diary("2026-09-04", "今天完成了 MCP 2 日记工具。") == {"saved": True, "date": "2026-09-04"}
    assert DiaryService(tmp_path).read_diary("2026-09-04")["content"] == "今天完成了 MCP 2 日记工具。"
    service.write_diary("2026-09-04", "替换后的内容")
    assert service.list_dates() == {"dates": ["2026-09-04"], "count": 1}


@pytest.mark.parametrize("date", ["../outside", "2026-02-30", "2026-9-4", "/absolute", "２０２６-０９-０４"])
def test_bad_dates_cannot_write(tmp_path: Path, date: str) -> None:
    with pytest.raises(ValueError):
        DiaryService(tmp_path).write_diary(date, "内容")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("content", ["", "  ", "字" * 100_001], ids=["empty", "blank", "too-long"])
def test_bad_content(tmp_path: Path, content: str) -> None:
    with pytest.raises(ValueError):
        DiaryService(tmp_path).write_diary("2026-09-04", content)


def test_replace_failure_preserves_previous_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = DiaryService(tmp_path)
    service.write_diary("2026-09-04", "原内容")

    def reject(*_args: object) -> None:
        raise OSError("测试写入故障")

    monkeypatch.setattr("aurora_diary.service.os.replace", reject)
    result = invoke(lambda: service.write_diary("2026-09-04", "新内容"), mutating=True)
    assert result.is_error and result.meta == {CONTRACT: {"status": "unknown"}}
    assert service.read_diary("2026-09-04")["content"] == "原内容"
    assert len(list(tmp_path.iterdir())) == 1


def test_official_mcp2_discover_and_call(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with Client(create_server(DiaryService(tmp_path)), mode="auto") as client:
            assert client.protocol_version == "2026-07-28"
            assert client.server_capabilities.extensions[CONTRACT] == {"version": 1}
            catalog = await client.list_tools()
            assert {tool.name for tool in catalog.tools} == {"write_diary", "read_diary", "list_dates"}
            result = await client.call_tool("write_diary", {"date": "2026-09-04", "content": "离线协议测试"})
            assert not result.is_error
            assert result.structured_content == {"saved": True, "date": "2026-09-04"}
            bad = await client.call_tool("write_diary", {"date": "2026-02-30", "content": "拒绝"})
            assert bad.is_error

    asyncio.run(scenario())
