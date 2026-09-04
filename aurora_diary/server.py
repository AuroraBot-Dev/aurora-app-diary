"""日记的 MCP 2 工具定义与启动配置。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from mcp.server import MCPServer
from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from aurora_diary.protocol import ToolContract, invoke
from aurora_diary.service import MAX_CONTENT_LENGTH, DiaryService

PACKAGE = "im.polaris.diary"
DateText = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="真实日期，格式 YYYY-MM-DD")]
Content = Annotated[str, Field(min_length=1, max_length=MAX_CONTENT_LENGTH, description="当天完整日记内容")]


def create_server(service: DiaryService) -> MCPServer:
    """用显式服务构造 Server，测试不读取个人环境或数据。"""
    server = MCPServer("aurora-diary", version="2.0.0", extensions=(ToolContract(),))

    @server.tool(
        description="完整写入指定日期的日记；已有内容会被替换。", annotations=ToolAnnotations(idempotent_hint=True)
    )
    async def write_diary(date: DateText, content: Content) -> CallToolResult:
        return invoke(lambda: service.write_diary(date, content), mutating=True)

    @server.tool(
        description="读取指定日期的日记，不存在时返回 found=false。", annotations=ToolAnnotations(read_only_hint=True)
    )
    async def read_diary(date: DateText) -> CallToolResult:
        return invoke(lambda: service.read_diary(date))

    @server.tool(description="按日期升序列出全部已有日记。", annotations=ToolAnnotations(read_only_hint=True))
    async def list_dates() -> CallToolResult:
        return invoke(service.list_dates)

    return server


def main() -> None:
    """默认目录属于 App；可由白名单环境变量覆盖。"""
    default = Path(__file__).resolve().parent.parent / "data" / "diaries"
    directory = Path(os.environ.get("AURORA_DIARY_DATA_DIR", str(default)))
    create_server(DiaryService(directory)).run(transport="stdio")
