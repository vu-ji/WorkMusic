
"""tests/test_graduation.py — 毕业项目测试

覆盖：
- agent：解析、偏好提取接口、工具 schema
- tools：search_catalog 过滤逻辑（纯函数，无需 ollama）
- memory：短期/长期记忆（W8 复用）
- plugin：RetryTool 逻辑层（无需 Dify 运行时）

e2e（需 ollama）单独标记：pytest -m e2e
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
# 插件目录也在 path 里（RetryTool 逻辑层）
sys.path.insert(0, str(Path(__file__).parent.parent / "dify-plugin-retry"))

from app.agent import GraduationAgent  # noqa: E402
from app.memory import build_memory  # noqa: E402
from app.tools import build_tools  # noqa: E402


@pytest.fixture
def agent():
    """构造一个带 mock 工具的 agent（不触发 LLM）。"""
    a = GraduationAgent(tools={})
    return a


class TestAgentParse:
    """解析逻辑测试（纯函数）"""

    def test_parse_tool_call(self, agent):
        parsed = agent._parse_step(
            '{"thought": "查曲库", "action": "search_catalog", "action_input": {"style": "电子摇滚"}}'
        )
        assert parsed["action"] == "search_catalog"
        assert parsed["action_input"]["style"] == "电子摇滚"

    def test_parse_final_answer(self, agent):
        parsed = agent._parse_step(
            '{"thought": "够了", "action": "Final Answer", "action_input": "推荐这首"}'
        )
        assert parsed["action"] == "Final Answer"

    def test_parse_markdown(self, agent):
        parsed = agent._parse_step('```json\n{"thought": "x", "action": "Final Answer", "action_input": "ok"}\n```')
        assert parsed is not None
        assert parsed["action"] == "Final Answer"

    def test_parse_invalid(self, agent):
        assert agent._parse_step("不是 JSON") is None

    def test_safe_call_dict_result(self, agent):
        """handler 返回自带 success 结构的 dict"""

        async def handler(args):
            return {"success": True, "result": [1, 2]}

        import asyncio
        r = asyncio.run(agent._safe_call(handler, {}))
        assert r["success"] is True
        assert r["result"] == [1, 2]

    def test_safe_call_bare_result(self, agent):
        """handler 返回裸 list → 自动包一层"""

        async def handler(args):
            return [1, 2]

        import asyncio
        r = asyncio.run(agent._safe_call(handler, {}))
        assert r["success"] is True
        assert r["result"] == [1, 2]


class TestTools:
    """工具逻辑测试（search_catalog 纯函数，无需 ollama）"""

    def test_build_tools_has_both(self):
        tools = build_tools()
        assert set(tools.keys()) == {"search_catalog", "knowledge_search"}
        # schema 有参数定义
        props = tools["search_catalog"]["schema"]["properties"]
        assert "style" in props and "bpm_min" in props

    def test_search_catalog_filter(self):
        tools = build_tools()
        result = tools["search_catalog"]["handler"](
            {"style": "电子摇滚", "bpm_min": 130, "bpm_max": 150, "budget": 3000}
        )
        assert result["success"] is True
        songs = result["result"]
        assert len(songs) >= 1
        # 所有结果符合过滤条件
        for s in songs:
            assert s["style"] == "电子摇滚"
            assert 130 <= s["bpm"] <= 150

    def test_search_catalog_no_match(self):
        tools = build_tools()
        result = tools["search_catalog"]["handler"](
            {"style": "不存在风格", "bpm_min": 0, "bpm_max": 200, "budget": 100}
        )
        assert result["success"] is True
        assert result["result"] == []


class TestMemory:
    """记忆测试（W8 复用验证）"""

    def test_short_memory(self, tmp_path):
        mem = build_memory(data_dir=str(tmp_path))
        mem.short.add_user("你好")
        assert len(mem.short.get_messages()) == 1
        mem.reset_session()
        assert mem.short.get_messages() == []

    def test_long_memory_persistence(self, tmp_path):
        mem = build_memory(data_dir=str(tmp_path))
        mem.long.remember("偏好", {"style": "电子摇滚"})
        mem2 = build_memory(data_dir=str(tmp_path))
        assert mem2.long.recall() == [{"key": "偏好", "value": {"style": "电子摇滚"}}]


class TestRetryPlugin:
    """Dify 插件逻辑层测试（无需 Dify 运行时）"""

    def test_retry_success_after_failures(self):
        from tools.retry_tool import RetryTool as Core

        t = Core(base_backoff=0.01)
        r = t.invoke(operation="llm_call", max_retries=3, simulate_failures=2)
        assert r["success"] is True
        assert r["attempts"] == 3

    def test_retry_exhausted(self):
        from tools.retry_tool import RetryTool as Core

        t = Core(base_backoff=0.01)
        r = t.invoke(operation="http_call", max_retries=2, simulate_failures=5)
        assert r["success"] is False
        assert r["attempts"] == 3

    def test_retry_no_failure(self):
        from tools.retry_tool import RetryTool as Core

        t = Core(base_backoff=0.01)
        r = t.invoke(operation="db_query", max_retries=3, simulate_failures=0)
        assert r["success"] is True
        assert r["attempts"] == 1


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_agent_e2e_knowledge():
    """e2e：知识库检索工具（需 ollama + qwen2.5:14b）"""
    from app.agent import GraduationAgent
    from app.memory import build_memory
    from app.tools import build_tools

    memory = build_memory(data_dir="/tmp/grad_test_mem")
    agent = GraduationAgent(tools=build_tools(), short_memory=memory.short, long_memory=memory.long)
    result = await agent.run("电子摇滚适合什么运动场景？")
    assert "reply" in result
    assert result["steps"] >= 1
