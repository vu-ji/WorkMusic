# W2 · Prompt 工程

YAML 驱动的 prompt 模板引擎 + 版本管理 + A/B 测试。

## 目录

```
src/
├── prompt_render.py  # PromptRenderer · YAML → 变量替换 → 纯文本
├── prompt_manager.py # PromptManager · 版本列表 + 加载 + 切换
├── schema.py         # CatalogResponse · Pydantic 字段校验
├── token_counter.py  # estimate_cost() · 按 tier 定价
├── test_ab.py        # v0 vs v1_fewshot A/B 对比
├── test_prompt.py    # 单版本 + Pydantic 校验 + 成本日志
└── test_manager.py   # PromptManager 单元测试
prompts/
├── catalog_radar/
│   ├── v0.yaml           # 纯约束（V1 起跑）
│   ├── v1_fewshot.yaml   # 约束 + few-shot 示例（V4 最终版）
│   ├── music-library.md          # V1 版 markdown 草稿
│   └── music-library-few-shot.md # V4 版 markdown 草稿
└── contract_guard/
    └── v0.yaml           # 合同哨兵初始版
```

## 跑

```bash
make run          # test_prompt.py（单版本 + 校验 + 成本）
```

## A/B 结论

| 模型 | v0（纯约束） | v1_fewshot |
|---|---|---|
| qwen2.5:7b | 编 10 首 | **分裂**：开头复刻拒推话术，后半段仍编造 |
| deepseek-r1:32b | 编+免责 | 完全拒推+格式正确 |

Few-shot 有用，但模型能力决定天花板。7b 学不会克制，32b 完全受控。阈值在 7B→8B 之间跨过。
