"""test_agent_arch.py — W8 pytest 测试"""

import pytest

from react import ReActAgent
from plan_execute import PlanExecuteAgent
from memory import ShortTermMemory, LongTermMemory


class TestShortTermMemory:
    def test_add_and_get_messages(self):
        """添加消息后可取回"""
        st = ShortTermMemory()
        st.add_system("你是助手")
        st.add_user("你好")
        st.add_assistant("你好！")
        msgs = st.get_messages()
        assert len(msgs) == 3
        assert msgs[0] == {"role": "system", "content": "你是助手"}
        assert msgs[1] == {"role": "user", "content": "你好"}
        assert msgs[2] == {"role": "assistant", "content": "你好！"}

    def test_clear(self):
        """清空后无消息"""
        st = ShortTermMemory()
        st.add_user("x")
        st.clear()
        assert st.get_messages() == []


class TestLongTermMemory:
    def test_remember_and_recall(self, tmp_path):
        """写入后可读回"""
        p = str(tmp_path / "memory.json")
        lt = LongTermMemory(path=p)
        lt.remember("偏好", {"style": "电子摇滚"})
        assert lt.recall() == [{"key": "偏好", "value": {"style": "电子摇滚"}}]

    def test_persistence(self, tmp_path):
        """重新实例化后数据还在（跨会话）"""
        p = str(tmp_path / "memory.json")
        lt = LongTermMemory(path=p)
        lt.remember("预算", 5000)
        lt2 = LongTermMemory(path=p)
        assert lt2.recall() == [{"key": "预算", "value": 5000}]

    def test_forget(self, tmp_path):
        """删除指定 key"""
        p = str(tmp_path / "memory.json")
        lt = LongTermMemory(path=p)
        lt.remember("a", 1)
        lt.remember("b", 2)
        lt.forget("a")
        facts = lt.recall()
        assert len(facts) == 1
        assert facts[0]["key"] == "b"


class TestReActAgent:
    def test_parse_step_use_tool(self):
        """解析工具调用步骤"""
        agent = ReActAgent()
        parsed = agent._parse_step(
            '{"thought": "需要查曲库", "action": "search_catalog", "action_input": {"style": "电子摇滚"}}'
        )
        assert parsed["action"] == "search_catalog"
        assert parsed["action_input"]["style"] == "电子摇滚"
        assert "thought" in parsed

    def test_parse_step_final_answer(self):
        """解析 Final Answer"""
        agent = ReActAgent()
        parsed = agent._parse_step(
            '{"thought": "信息够了", "action": "Final Answer", "action_input": "推荐这几首"}'
        )
        assert parsed["action"] == "Final Answer"
        assert parsed["action_input"] == "推荐这几首"

    def test_parse_step_markdown(self):
        """markdown 包装解析"""
        agent = ReActAgent()
        parsed = agent._parse_step(
            '```json\n{"thought": "x", "action": "Final Answer", "action_input": "ok"}\n```'
        )
        assert parsed is not None
        assert parsed["action"] == "Final Answer"

    def test_parse_step_invalid(self):
        """非法输出 → None"""
        agent = ReActAgent()
        assert agent._parse_step("不是 JSON") is None

    @pytest.mark.asyncio
    async def test_run_end_to_end(self):
        """真实 e2e：搜索工具 → 返回结果（需 ollama）"""
        agent = ReActAgent(tier="middle")
        result = await agent.run("给健身房找 1 首电子摇滚 BPM 130-150 的歌")
        assert "reply" in result
        assert result["steps"] >= 1
        assert "trace" in result
        # ReAct 应该调了工具（拿到真实数据回答）
        tool_steps = [t for t in result["trace"] if t.get("action") != "Final Answer"]
        assert len(tool_steps) >= 1


class TestPlanExecuteAgent:
    def test_parse_plan(self):
        """解析计划"""
        agent = PlanExecuteAgent()
        plan = agent._parse_plan('{"plan": ["查曲库", "筛选 BPM", "报价"]}')
        assert plan == ["查曲库", "筛选 BPM", "报价"]

    def test_parse_plan_markdown(self):
        """markdown 包装解析计划"""
        agent = PlanExecuteAgent()
        plan = agent._parse_plan('```json\n{"plan": ["步骤1", "步骤2"]}\n```')
        assert plan == ["步骤1", "步骤2"]

    def test_parse_execution(self):
        """解析执行结果"""
        agent = PlanExecuteAgent()
        r = agent._parse_execution('{"done": true, "result": "完成"}')
        assert r == {"done": True, "result": "完成"}

    def test_parse_invalid(self):
        """非法输出 → None"""
        agent = PlanExecuteAgent()
        assert agent._parse_plan("不是 JSON") is None
        assert agent._parse_execution("xxx") is None

    @pytest.mark.asyncio
    async def test_run_end_to_end(self):
        """真实 e2e：计划 → 执行（需 ollama）"""
        agent = PlanExecuteAgent(tier="middle")
        result = await agent.run("推荐 3 首适合健身房的电子摇滚，并给出每首的预估授权价")
        assert len(result["plan"]) >= 2
        assert len(result["results"]) == len(result["plan"])
        assert "reply" in result
