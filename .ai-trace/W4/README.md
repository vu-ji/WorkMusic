# W4 ai-trace

> AI 生成代码 → 人工 Review → 修改后的痕迹。

## tool_schema.py · 工具定义

- AI 生成：JSON Schema 框架、search_catalog 接口签名
- 人工 Review + 修改：
  - `get_search_catalog_schema()` 的 JSON Schema 类型从 Python `str` 对象改成 `"string"` 字符串（JSON Schema 规范要求）
  - `search_catalog` 从无过滤返回全量改成按 style/BPM/budget 过滤
  - TOOLS 字典 key `"search_catlog"` → `"search_catalog"`（拼写更正）
  - 补充 5 条 mock 曲库数据

## tool_registry.py · 注册表

- AI 生成：ToolRegistry 类框架
- 人工修改：添加 `register_defaults()` 批量注册方法

## tool_executor.py · 执行器

- AI 生成：execute/validate_params 基本逻辑
- 人工 Review + 修改：
  - `execute` → `async def`，添加 `inspect.iscoroutinefunction` 兼容同步/异步工具
  - `validate_params` 的 `isinstance(True, int)` 坑 → 改 `type(value) is not int` 精确匹配
  - `format_error_for_llm` 从乱码重写为结构化的错误提示

## agent.py · Agent Loop

- AI 生成：Agent 类框架、build_system_prompt 结构
- 人工修改：
  - Agent Loop 手写 think→act→observe 循环（不依赖框架）
  - `_parse_action` 加固：支持 markdown 代码块剥离、前后文字 JSON 提取
  - 添加 fallback：已调过工具后返回自然语言 → 当作最终回复

## parse_action 容错

LLM 返回格式不可控：
- 纯 JSON ✓
- markdown 代码块包装 ✓
- JSON 前后带说明文字 ✓
- 完全无法解析 → None ✓
