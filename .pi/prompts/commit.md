---
description: 按 Conventional Commits 规范提交本次改动
argument-hint: "[提交信息]"
---
检查当前 git 状态（`git status` + `git diff --stat`），确认改动与提交信息相符后执行：

1. 提交信息格式：`<type>(<scope>): <description>`，type ∈ feat|fix|refactor|docs|chore|test
2. scope 用模块名（如 data-pipeline、rag、agent-runtime、ui）
3. 若用户提供了 $1 则用之；否则根据改动内容生成
4. **提交前确认**：无 .env 等敏感文件、无 __pycache__/node_modules 等垃圾文件、测试已通过
5. 执行 `git add` + `git commit`，报告提交结果
