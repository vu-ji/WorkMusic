"""chunker.py — 文本切分策略

W6 核心实验对象。RAG 的第一步：把长文档切成小块，每块单独做 embedding。
切分策略直接影响检索质量——切得太粗检索不精确，切得太细丢失上下文。

三种经典策略：
1. 固定长度切分：textwrap 按字符数硬切，简单但会切断句子
2. 段落切分：按 \n\n 分块，保留语义单元，但块大小不均匀
3. 滑动窗口：固定大小 + 重叠（overlap），保留边界上下文

前端类比：这就像把一篇文章拆成可索引的卡片。
- 固定切分 = 每 1000 字符一刀切（可能切断句子）
- 段落切分 = 按空行分段（保留完整段落，但长短不一）
- 滑动窗口 = 卡片之间留 10% 重叠（检索到边界时上下文不丢）

TODO: 完成下面的 TODO 标记项。
"""

from typing import Any


def chunk_by_fixed_size(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    """固定长度切分 + 重叠。

    Args:
        text: 原始文本
        chunk_size: 每块目标字符数
        overlap: 相邻块的重叠字符数（保留边界上下文）

    Returns:
        切分后的文本块列表

    规则：
    - 从 0 开始，每步前进 chunk_size - overlap
    - 最后一块不足 chunk_size 也要保留
    - text 为空 → 返回 []
    """
    # TODO: 实现固定长度 + 重叠切分
    # 参考实现骨架：
    # chunks = []
    # start = 0
    # while start < len(text):
    #     end = min(start + chunk_size, len(text))
    #     chunks.append(text[start:end])
    #     if end == len(text):
    #         break
    #     start += chunk_size - overlap
    # return chunks
    pass


def chunk_by_paragraph(
    text: str,
    min_chunk_size: int = 200,
) -> list[str]:
    """段落切分：按空行分块，小块合并到前一块。

    Args:
        text: 原始文本
        min_chunk_size: 小于该长度的块会合并到前一块

    Returns:
        段落块列表

    规则：
    - 先按 \n\n 拆段
    - 某段太短 → 合并到前一段（避免孤立的碎片块）
    - 无段落（整个文本无空行）→ 退回固定切分
    """
    # TODO: 实现段落切分 + 小块合并
    pass


def chunk_by_sentences(
    text: str,
    max_chunk_size: int = 500,
) -> list[str]:
    """句子切分：按句号/问号/感叹号断句，累积到 max 封顶。

    Args:
        text: 原始文本
        max_chunk_size: 单块最大字符数

    Returns:
        句子块列表

    规则：
    - 按 [。！？] 断句（中文标点）
    - 句子累积到 max_chunk_size 附近封顶
    - 单句超长（无标点）→ 按固定大小硬切
    """
    # TODO: 实现句子切分
    pass


def chunk_document(text: str, strategy: str = "paragraph") -> list[str]:
    """统一入口：按策略选择切分方式。

    Args:
        text: 原始文本
        strategy: "fixed" | "paragraph" | "sentence"

    Returns:
        切分后的块列表
    """
    # TODO: 策略分发
    pass
