# W8 ai-trace

> AI 生成代码 → 人工 Review → 修改后的痕迹。

## memory.py · 多轮记忆

- AI 生成：ShortTermMemory + LongTermMemory 骨架
- 人工 Review 修复：
  - `self.path = self.path` 引用未定义属性 → `self.path = path`（必崩 bug）
  - `__init__` 补文件加载逻辑——否则重开实例丢数据，跨会话持久失效
- 验证：5 测试全绿（含 test_persistence 重开实例数据还在）

## react.py · ReAct 范式

- AI 生成：完整 ReAct 循环（Thought→Action→Observation→Final Answer）
- 关键设计：
  - MAX_STEPS=6（比 W4 的 MAX_TURNS=3 大——ReAct 可能连续调多个工具）
  - 解析失败 → 提示 LLM 重来（不 crash）
  - 复用 W4 ToolExecutor + W5 RetryController
- 实测发现：7b 重复调用工具（浪费一轮），MAX_STEPS 兜住不死循环

## plan_execute.py · Plan-Execute 范式

- AI 生成：先计划再执行
- **人工 Review 修的真 bug：qwen2.5:7b 输出非法 JSON**
  - 现象：`["步骤1": "内容"]` 数组元素带键值对，json.loads 直接抛错
  - 根因：模型对 prompt 示例 `["步骤1", "步骤2"]` 过度模仿，把序号当对象键
  - 解法：`_repair_plan_json` 正则剥掉 `"步骤N": ` 前缀
  - 教训：永远别指望小模型输出严格 JSON，解析层必须容错

## mcp_server.py + mcp_tool_adapter.py · MCP 接入

- AI 生成：MCP server（@server.tool 注册 search_catalog）+ 工具适配器
- 新版 SDK API 踩坑（旧版 fastmcp/Client(read,write) 全变）：
  - `MCPServer` + `@tool()` 装饰器（新版）
  - `Client`（in-memory/URL 高层封装）vs `ClientSession`（stdio 流低层）
  - **ClientSession 必须显式 `await client.initialize()`**，否则 tools/list 报 Invalid request parameters
  - `list_tools()` 返回 ListToolsResult，工具在 `.tools` 属性
- **关键修复：schema 必须传给 LLM**
  - 不传 input_schema：模型瞎猜参数名（genre/bpm_range/budget_per_song）连错 4 次
  - 传了之后：一次猜对（style/bpm_min/bpm_max/budget）
- 验证：in-memory + stdio 双传输通过，MCP 版 ReActAgent 真实跑通

## 模型选型（middle tier）

- 7b：快（5.8s）但 JSON 不稳、ReAct 重复调工具
- deepseek-r1:8b：CoT 拖到 >113s 不可用（任务形态不匹配——ReAct 的思考已写死在 prompt）
- **qwen2.5:14b：16.6s，JSON 稳定，定为 W8 默认**（router.py middle 已改）
