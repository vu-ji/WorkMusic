# WorkMusic 项目工作法（APPEND_SYSTEM · 追加到系统提示）

你在 WorkMusic 仓库中工作。这是一个被清空重建的毕业项目（W10–W12），由 harness 规格驱动，你负责按规格完成代码。

## 硬性规则

1. **先读后做**：每轮工作开始，先读 `AGENTS.md` 与 `docs/milestones.md`，确认当前任务（T-编号）再动手。禁止跳过上下文直接写代码。
2. **任务执行循环**：每个任务按 `PLAN → IMPLEMENT → VERIFY → COMMIT` 四步走：
   - PLAN：写明「做什么 / 改哪些文件 / 怎么验收 / 风险」，不超过 10 行
   - IMPLEMENT：动手写代码。**从零实现为主**；除非必要，不引入历史代码
   - VERIFY：跑测试（`cd backend && python -m pytest`），逐条核对验收标准
   - COMMIT：Conventional Commits，并在 `docs/milestones.md` 勾选完成
3. **完成即汇报**：一个任务完成后，用 3–5 行汇报（做了什么 / 验收结果 / 下一步），再进入下一个任务。禁止一次性闷头做多个任务不汇报。
4. **遇到阻塞不硬编**：写进 `docs/milestones.md` 备注（现象 / 尝试过的方案 / 卡点），继续下一个可解任务。
5. **规范铁律**：中文注释与汇报、技术名词保留英文；测试通过才算完成；`.env.example` 必须存在；禁止提交真实密钥。
6. **版权红线**：歌词对外只展示片段（≤2 句）；README 声明数据来源与版权立场。
