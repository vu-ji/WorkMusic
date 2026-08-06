---
description: 实现指定任务（按 PLAN → 写代码 → 测试）
argument-hint: "<任务编号>"
---
执行任务 $1 的实现。步骤：

1. 重读 `docs/milestones.md` 中该任务的规格与验收标准
2. 若未输出过 PLAN，先按 /plan 的格式补一个简短 PLAN
3. 写代码：遵守 `docs/conventions.md`；**从零实现为主**；中文注释、技术名词保留英文
4. 补最小测试，跑 `cd backend && python -m pytest`，全绿才算完成
5. 更新 `docs/milestones.md` 勾选该任务，标注完成日期

完成后 3–5 行汇报：做了什么 / 测试结果 / 验收标准逐条打勾情况。
