# W2 ai-trace

> 记录 AI 生成代码 → 人工 Review → 修改后的痕迹。

## PromptRenderer · YAML 模板引擎

- 文件：`w2-prompts/src/prompt_render.py`
- AI 生成：`_replace()` 递归替换 `{{变量}}` 逻辑
- 人工 Review：确认 YAML 加载 + 变量替换的递归深度限制（prompt 模板不会超过 5 层嵌套，够用）
- 人工修改：`render()` 方法按 6 个 section（identity/goal/constraints/input/output/tone）拼接纯文本，加 examples 区块支持 few-shot

## PromptManager · 版本管理器

- 文件：`w2-prompts/src/prompt_manager.py`
- AI 生成：`list_versions()` 用 glob 扫描 *.yaml
- 人工修改：`load()` 方法拼接路径 → PromptRenderer → render，缺后缀自动补 .yaml

## CatalogResponse · Pydantic Schema

- 文件：`w2-prompts/src/schema.py`
- AI 生成：`TrackCandidate` / `CatalogResponse` 类定义
- 人工修改：添加 `model_config = {"extra": "forbid"}`——多余字段直接抛 ValidationError

## token_counter · 成本估算

- 文件：`w2-prompts/src/token_counter.py`
- AI 生成：`FEE_Config` 三层定价表（light/middle/heavy，元/百万 token）
- 人工修改：根据 DeepSeek 官方定价校准，input 和 output 价格分开

## Prompt 模板 · YAML 版

- 目录：`w2-prompts/prompts/catalog_radar/`
- 文件：`v0.yaml`（纯约束）、`v1_fewshot.yaml`（约束+few-shot 示例）
- AI 生成：初始结构（identity/goal/constraints/input/output/tone/format）
- 人工修改：七版迭代措辞——
  - V1：纯基础约束 → 模型什么都没拦
  - V2：加"禁止编造" → 模型编了但加免责声明
  - V3：加"没有来源=不可用" → 模型自创歌名+假设说明
  - V4：加 few-shot 示例 → 7b 分裂（开头拒推+后半段编造），32b 完全服从

## A/B 测试

- 文件：`w2-prompts/src/test_ab.py`
- AI 生成：v0 vs v1_fewshot 并行调用框架
- 人工修改：接入 RouterClient、同一 query 跑两版 prompt、对比输出

**关键发现**：few-shot 对 32b 有效，对 7b 出现"分裂"——开头复刻示例拒推话术，后半段仍然编造。根因：7b 参数不够，in-context learning 只偏移了前几个 token 就衰减。
