# 日记 MCP App

包名：`im.polaris.diary`。Bot 通过显式工具保存、读取自己的日记；App 不调用模型，不直接写 Host 世界日志。

## 工具

| raw name | 参数 | 返回 |
| --- | --- | --- |
| write_diary | date: YYYY-MM-DD；content: 非空文本，最多 100000 字符 | saved、date |
| read_diary | date | found、date、content |
| list_dates | 无 | dates、count |

write_diary 完整替换当天内容。日期必须真实存在；拒绝路径穿越与符号链接目标。
同日同内容可重复提交；使用同目录临时文件、flush/fsync、原子 replace，写入失败不主动破坏原文件。
数据是 YYYY-MM-DD.json 文件中的 UTF-8 纯文本；扩展名不意味着内容被按 JSON 解码。

## 配置和数据

只读取 `AURORA_DIARY_DATA_DIR`；未设置时使用 App 目录下 `data/diaries/`。
相对目录以子进程 working_dir 为基准，建议配置绝对路径。Host 的 env 白名单必须包含该变量。
需要使用已有日记时，把该变量指向已有日记目录；不会自动搜索或搬动你的日记。
一个数据目录只能由一个 Server 进程写入；不承诺跨进程锁或断电恢复。

例子：`write_diary(date="2026-09-04", content="今天完成了三个 MCP 应用的联调。")`。
最终领域 ID：`aur.mcp.im.polaris.diary.write_diary`。
event_mode 为 disabled；写入结果走已有 Tool 因果通道，不额外生成重复事件。

## 运行与接入

需要 Python 3.12–3.14 和官方 MCP Python SDK 2.x。在 App 目录运行：

```powershell
uv run python mcp_server.py
```

也可以使用已安装依赖的 Python 直接运行入口。本机 AuroraBot 的个人
`config/apps.toml` 已使用 `D:/AuroraBot/.venv/Scripts/python.exe`，
因此不会因为 App 有自己的 pyproject.toml 而意外切换环境。移动仓库后需同步更新个人启动路径。
测试：在 App 目录运行 `uv run --group dev pytest -q -p no:cacheprovider`。
主仓库的 `aurora check` 不包含被忽略的 extensions，需要单独运行这些测试。

Host 通过 tools/list 获取定义，不读取 manifest.yaml 或 config.example.json；
这两个文件不负责启动配置。个人配置只放在 config，不修改主仓库 config.example。
Agent 必须在 config/agents.toml 的 tools 中获得对应 `aur.mcp.<package>.*`。
仅 builtin.worker 被授予本组业务工具，root 可以委派给它。

stdout 只输出 MCP JSON-RPC；日志走 stderr。工具返回 CallToolResult 的文本和 structuredContent。
Server 声明 `org.aurorabot/tool-contract: {"version":1}`：
参数/业务拒绝为 failed；无法确认写入结果时返回 unknown，不能自动重试。
SDK 和 Host 自动协商协议，代码不手写握手或伪装协议版本。
