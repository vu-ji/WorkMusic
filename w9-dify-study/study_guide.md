# W9 · Dify Workflow 引擎精读

> 项目约定：Phase 4 读 Dify 的 workflow 引擎，产出架构图解笔记。
> 对比对象：自己 W8 手写的 ReAct / Plan-Execute 范式。

## 要读的仓库

https://github.com/langgenius/dify（已 clone 到 `dify-src/`）

## 要追踪的核心问题

Dify 的 workflow 是一个**可视化节点图**：用户拖拽节点（LLM、工具、条件、循环）连线成图，
引擎按图执行。这和手写 ReAct 的差异在于——**执行逻辑从"代码"变成了"数据"**。

## 精读路线（按依赖顺序）

### 第一站：Graph —— 图的定义
- 节点（node）有哪些类型？每个节点长什么样（type/data/title）？
- 边（edge）怎么定义？source → target 怎么连？
- 对比：你的 Plan-Execute 的 plan 列表 vs Dify 的图，差在哪？

### 第二站：WorkflowRunner —— 执行引擎
- 图怎么被执行的？按什么顺序跑节点？（拓扑排序？递归？）
- 节点的输入输出怎么在节点间传递？
- 条件分支（IF/ELSE）怎么实现？
- 对比：你的 ReAct 循环 vs Dify 引擎，谁更灵活？

### 第三站：节点执行 —— 单个节点怎么跑
- LLM 节点怎么调模型？
- 工具节点怎么调用工具？（对比 W8 的 MCP）
- 变量怎么在节点间引用（`{{#node_id.output#}}`）？

### 第四站：状态管理 —— 图执行的中途状态
- 节点执行失败怎么办？重试？跳过？
- 循环（iteration）节点怎么实现？
- 中断/恢复怎么处理？

## 要回答的问题（对照 W8）

1. Dify 的 workflow 引擎和手写 ReAct 的执行模型，本质区别是什么？
2. 如果把你的毕业项目（Phase 5）搭在 Dify 上，哪些部分复用、哪些部分手写？
3. Dify 的节点抽象（LLM/工具/条件/循环）和你 W8 的组件（RouterClient/ToolExecutor/ReAct）怎么对应？
4. 如果要你在 Dify 的引擎里加一个"重试"节点（复用 W5 的 RetryController），你会怎么设计？

## 产出

- 一张架构图（mermaid）：Graph → WorkflowRunner → Node 执行 → 状态管理 的完整链路
- 300 字取舍笔记：Dify workflow 引擎 vs 手写范式
- 一张对应表：Dify 概念 ↔ 自己 W8 的组件
