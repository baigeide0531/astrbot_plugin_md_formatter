"""
AstrBot 插件：MD 格式清理
========================

把 LLM 输出的 markdown 转成 QQ 可读的纯文本，解决 AstrBot + OneBot v11
(NapCat) 接入 QQ 时 markdown 无法渲染的问题。

原理：注册 on_decorating_result 事件（发送消息前），遍历消息链中所有
Plain 组件，把其中的 markdown 语法转成 QQ 可直接阅读的纯文本：
- 加粗 / 斜体 / 删除线 → 去掉符号
- 标题 # ## → 去掉井号
- 列表 - 1. → 换成 · 序号
- 表格 | a | b | → 转成行列文本
- 代码块 ``` ``` → 保留原文并加边框
- 链接 [文字](url) → 文字 (url)
- 引用 > → 换成 │
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.event.filter import on_decorating_result
from astrbot.api.message_components import Plain
from astrbot.api.star import Context, Star

if TYPE_CHECKING:
    pass

PLUGIN_NAME = "astrbot_plugin_md_formatter"


def convert_md_to_plain(text: str, config: dict) -> str:
    """把一段 markdown 文本转成 QQ 可读的纯文本。"""
    if not text:
        return text

    keep_code = config.get("keep_code_block", True)

    # ------------------------------------------------------------
    # 1. 代码块：先"保护"起来，避免块内内容被后续规则误伤
    # ------------------------------------------------------------
    code_blocks: list[str] = []

    def _protect_code(m: re.Match) -> str:
        code_blocks.append(m.group(1))
        return f"\x00CODE{len(code_blocks) - 1}\x00"

    text = re.sub(
        r"```[^\n]*\n(.*?)```",
        _protect_code,
        text,
        flags=re.DOTALL,
    )

    # 2. 行内代码
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # 3. 表格：转成"单元格 | 单元格"的行列文本
    text = _convert_tables(text)

    # 4. 标题
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)

    # 5. 加粗 / 斜体 / 删除线（先长后短，避免误伤）
    text = re.sub(r"\*\*([^*]+?)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"\1", text)
    text = re.sub(r"~~([^~]+?)~~", r"\1", text)

    # 6. 图片 / 链接
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)",
        r"[图片]",
        text,
    )

    def _link(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        return f"{label} ({url})" if label else url

    text = re.sub(
        r"\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)",
        _link,
        text,
    )

    # 7. 任务列表（先于无序列表，因为 - [x] 以 - 开头）
    text = re.sub(r"^\s*[-*+]\s+\[[xX]\]\s*", "☑ ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+\[ \]\s*", "☐ ", text, flags=re.MULTILINE)

    # 8. 无序列表 / 有序列表
    text = re.sub(r"^\s*[-*+]\s+", "· ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*(\d{1,3})\.\s+", r"\1. ", text, flags=re.MULTILINE)

    # 9. 引用
    text = re.sub(r"^\s{0,3}>\s?", "│ ", text, flags=re.MULTILINE)

    # 10. 分割线
    text = re.sub(r"^\s*([-*_]\s*){3,}\s*$", "━━━━━━━━", text, flags=re.MULTILINE)

    # 11. 恢复代码块
    def _restore_code(m: re.Match) -> str:
        code = code_blocks[int(m.group(1))].rstrip()
        if keep_code:
            return f"\n┌─ 代码 ────────\n{code}\n└──────────────\n"
        return code

    text = re.sub(r"\x00CODE(\d+)\x00", _restore_code, text)

    # 12. 清理
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def _convert_tables(text: str) -> str:
    """把 markdown 表格块转成『单元格 │ 单元格』形式的纯文本。"""
    lines = text.split("\n")
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if "|" in line and i + 1 < len(lines) and _is_sep_line(lines[i + 1]):
            # 收集整张表（以 | 开头的连续行）
            table_lines = [line]
            i += 1
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i])
                i += 1

            rows: list[list[str]] = []
            for tl in table_lines:
                if _is_sep_line(tl):
                    continue
                cells = [c.strip() for c in tl.strip().strip("|").split("|")]
                rows.append(cells)

            if rows:
                out.append("｜".join(rows[0]))
                for r in rows[1:]:
                    out.append("｜".join(r))
            continue

        out.append(line)
        i += 1

    return "\n".join(out)


def _is_sep_line(line: str) -> bool:
    """判断是否为表格分隔行，如 | --- | :--: |"""
    s = line.strip()
    if not s.startswith("|") and not s.endswith("|"):
        return False
    cells = [c.strip() for c in s.strip().strip("|").split("|")]
    return all(c and set(c) <= {"-", ":", " "} for c in cells)


class MDFormatterPlugin(Star):
    """在发送前把 LLM 输出的 markdown 转成 QQ 可读的纯文本。"""

    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config: dict = config if isinstance(config, dict) else {}
        logger.info(
            f"[{PLUGIN_NAME}] 已加载。适用平台: "
            f"{self.config.get('apply_to_platforms', ['aiocqhttp'])}"
        )

    @on_decorating_result(desc="把 markdown 输出转成 QQ 可读的纯文本")
    async def md_to_plain_on_send(self, event: AstrMessageEvent):
        """在消息发送前，把消息链中所有 Plain 文本做 markdown → 纯文本 转换。"""
        if not self.config.get("enabled", True):
            return

        # 只处理配置中指定的平台（默认 aiocqhttp = OneBot v11 / NapCat）
        platforms = self.config.get("apply_to_platforms", ["aiocqhttp"])
        platform_name = event.get_platform_name()
        if platform_name not in platforms:
            return

        result = event.get_result()
        if result is None or not result.chain:
            return

        for comp in result.chain:
            if isinstance(comp, Plain) and comp.text:
                try:
                    comp.text = convert_md_to_plain(comp.text, self.config)
                except Exception as e:
                    logger.error(f"[{PLUGIN_NAME}] markdown 转换失败: {e}")
