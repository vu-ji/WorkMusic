# W5 · MCP SDK 工具调用链路精读

> 项目约定：Phase 2 读 MCP SDK 的 tool 调用链路，产出架构图解笔记。

## 要读的仓库

https://github.com/modelcontextprotocol/python-sdk

## 要追踪的调用链路

从 Client 发起 tool call 到 Server 返回结果，完整链路：

```
Client.call_tool("search_catalog", {args})
    ↓
[序列化] JSON-RPC 请求
    ↓
[传输层] stdio / SSE / WebSocket
    ↓
Server 接收
    ↓
[反序列化] JSON-RPC 请求
    ↓
[路由] 匹配 tool name → handler function
    ↓
[执行] handler(args) → result
    ↓
[序列化] JSON-RPC 响应
    ↓
[传输层] 返回
    ↓
Client 接收 → 解析 → 返回给 LLM
```

## 要回答的问题

1. MCP 的 JSON-RPC 消息格式是什么？tool call 在协议层长什么样？
2. stdio 传输和 SSE 传输的 tradeoff——什么场景用哪个？
3. Server 端怎么注册 tool？和 W4 的 ToolRegistry 比有什么不同？
4. MCP 如何处理 tool call 失败？有没有内置的重试机制？
5. 如果让你用 MCP SDK 替换 W4 的手写 ToolRegistry，改多少代码？

## 产出

- 一张架构图（Lucidchart / Excalidraw / mermaid）
- 200 字笔记：MCP vs 手写 ToolRegistry 的设计取舍
