"""W4 pytest 测试 —— 工具注册 + 参数校验 + 执行 + 错误处理"""

import pytest
from tool_schema import search_catalog, get_search_catalog_schema, TOOLS
from tool_registry import ToolRegistry
from tool_executor import ToolExecutor, format_error_for_llm


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        registry.register_defaults()
        tool = registry.get("search_catalog")
        assert tool is not None
        assert "schema" in tool
        assert "fn" in tool
        assert tool["fn"] is search_catalog

    def test_get_nonexistent(self):
        registry = ToolRegistry()
        assert registry.get("not_exist") is None

    def test_list_schemas(self):
        registry = ToolRegistry()
        registry.register_defaults()
        schemas = registry.list_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "search_catalog"

    def test_list_names(self):
        registry = ToolRegistry()
        registry.register_defaults()
        names = registry.list_names()
        assert names == ["search_catalog"]


class TestToolExecutor:
    @pytest.mark.asyncio
    async def test_execute_success(self):
        registry = ToolRegistry()
        registry.register_defaults()
        executor = ToolExecutor(registry)
        result = await executor.execute(
            "search_catalog",
            {"style": "电子摇滚", "bpm_min": 120, "bpm_max": 150, "budget": 5000},
        )
        assert result["success"] is True
        songs = result["result"]
        assert len(songs) >= 1
        for s in songs:
            assert s["style"] == "电子摇滚"
            assert 120 <= s["bpm"] <= 150
            assert s["estimated_price"] <= 5000

    @pytest.mark.asyncio
    async def test_execute_budget_too_low_returns_empty(self):
        registry = ToolRegistry()
        registry.register_defaults()
        executor = ToolExecutor(registry)
        result = await executor.execute(
            "search_catalog",
            {"style": "电子摇滚", "bpm_min": 100, "bpm_max": 200, "budget": 500},
        )
        assert result["success"] is True
        assert result["result"] == []

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        registry = ToolRegistry()
        registry.register_defaults()
        executor = ToolExecutor(registry)
        result = await executor.execute("ghost_tool", {})
        assert result["success"] is False
        assert "未知工具" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_missing_required(self):
        registry = ToolRegistry()
        registry.register_defaults()
        executor = ToolExecutor(registry)
        result = await executor.execute("search_catalog", {"style": "流行"})
        assert result["success"] is False
        assert "缺少必填参数" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_wrong_type(self):
        registry = ToolRegistry()
        registry.register_defaults()
        executor = ToolExecutor(registry)
        result = await executor.execute(
            "search_catalog",
            {
                "style": "电子",
                "bpm_min": "fast",
                "bpm_max": 150,
                "budget": 5000,
            },
        )
        assert result["success"] is False
        assert "bpm_min" in result["error"]
        assert "整数" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_extra_unknown_param(self):
        registry = ToolRegistry()
        registry.register_defaults()
        executor = ToolExecutor(registry)
        result = await executor.execute(
            "search_catalog",
            {
                "style": "电子",
                "bpm_min": 100,
                "bpm_max": 150,
                "budget": 5000,
                "vibe": "chill",
            },
        )
        assert result["success"] is False
        assert "未知参数" in result["error"]
        assert "vibe" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_async_tool_function(self):
        """验证异步工具函数也能正常执行——对应 W6 真实数据库查询场景"""
        registry = ToolRegistry()

        async def async_mock_fn(x: int) -> dict:
            return {"value": x * 2}

        registry.register("async_tool", {
            "name": "async_tool",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"],
            }
        }, async_mock_fn)

        executor = ToolExecutor(registry)
        result = await executor.execute("async_tool", {"x": 5})
        assert result["success"] is True
        assert result["result"]["value"] == 10


class TestValidateParams:
    def test_valid_params(self):
        registry = ToolRegistry()
        registry.register_defaults()
        executor = ToolExecutor(registry)
        schema = get_search_catalog_schema()
        error = executor.validate_params(
            {"style": "流行", "bpm_min": 100, "bpm_max": 150, "budget": 3000},
            schema,
        )
        assert error is None

    def test_missing_required(self):
        registry = ToolRegistry()
        registry.register_defaults()
        executor = ToolExecutor(registry)
        schema = get_search_catalog_schema()
        error = executor.validate_params(
            {"style": "流行", "bpm_min": 100},
            schema,
        )
        assert error is not None
        assert "缺少必填参数" in error

    def test_integer_type_check(self):
        registry = ToolRegistry()
        registry.register_defaults()
        executor = ToolExecutor(registry)
        schema = get_search_catalog_schema()
        error = executor.validate_params(
            {"style": "流行", "bpm_min": "abc", "bpm_max": 150, "budget": 3000},
            schema,
        )
        assert error is not None
        assert "bpm_min" in error
        assert "整数" in error

    def test_bool_is_not_int(self):
        """Python 的 bool 是 int 子类——True==1, isinstance(True,int)==True。
        校验必须用 type() 精确匹配，否则 True 会通过 integer 校验。"""
        registry = ToolRegistry()
        registry.register_defaults()
        executor = ToolExecutor(registry)
        schema = get_search_catalog_schema()
        error = executor.validate_params(
            {"style": "流行", "bpm_min": True, "bpm_max": 150, "budget": 3000},
            schema,
        )
        assert error is not None
        assert "bpm_min" in error
        assert "整数" in error


class TestFormatErrorForLLM:
    def test_format_includes_tool_name(self):
        msg = format_error_for_llm("search_catalog", {}, "缺少参数")
        assert "search_catalog" in msg

    def test_format_includes_field_name(self):
        msg = format_error_for_llm(
            "search_catalog", {"bpm_min": "abc"}, "参数 bpm_min 必须是整数"
        )
        assert "bpm_min" in msg
        assert "整数" in msg

    def test_format_includes_original_args(self):
        args = {"style": "电子", "bpm_min": 100}
        msg = format_error_for_llm("search_catalog", args, "test error")
        assert "style" in msg
        assert "bpm_min" in msg

    def test_format_asks_to_retry(self):
        msg = format_error_for_llm("search_catalog", {}, "test")
        assert "重新" in msg or "修正" in msg or "重试" in msg


class TestParseAction:
    """测试 Agent._parse_action 的容错能力"""

    def test_pure_json_use_tool(self):
        from agent import Agent
        agent = Agent()
        result = agent._parse_action(
            '{"action": "use_tool", "tool": "search_catalog", "arguments": {"style": "电子"}}'
        )
        assert result["action"] == "use_tool"
        assert result["tool"] == "search_catalog"

    def test_pure_json_reply(self):
        from agent import Agent
        agent = Agent()
        result = agent._parse_action(
            '{"action": "reply", "content": "你好"}'
        )
        assert result["action"] == "reply"
        assert result["content"] == "你好"

    def test_markdown_code_block(self):
        from agent import Agent
        agent = Agent()
        result = agent._parse_action(
            '```json\n{"action": "reply", "content": "test"}\n```'
        )
        assert result is not None
        assert result["action"] == "reply"

    def test_extra_text_surrounding(self):
        from agent import Agent
        agent = Agent()
        result = agent._parse_action(
            '这是回复：{"action": "reply", "content": "好的"}'
        )
        assert result is not None
        assert result["content"] == "好的"

    def test_invalid_json_returns_none(self):
        from agent import Agent
        agent = Agent()
        result = agent._parse_action("不是 JSON")
        assert result is None
