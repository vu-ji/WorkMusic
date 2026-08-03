# Dify 插件：RetryTool（重试工具）

把 W5 的 RetryController 封装成 Dify 插件，让 Dify 工作流里的节点调用
可以获得指数退避重试能力。

## 目录

```
dify-plugin-retry/
├── provider/           # 插件声明（W11 补 SDK 适配）
├── tools/
│   └── retry_tool.py   # RetryTool 逻辑（复用 W5 RetryController）
└── README.md
```

## 独立测试（不依赖 Dify）

```bash
cd ../w1-env && source .venv/bin/activate && cd ../w10-graduation
python -c "
import sys; sys.path.insert(0, 'dify-plugin-retry')
from tools.retry_tool import RetryTool
t = RetryTool()
r = t.invoke(operation='llm_call', max_retries=3, simulate_failures=2)
print(r)  # 期望：success=True, attempts=3（前 2 次失败后重试成功）
"
```

## W11 TODO

- [ ] 适配 Dify 插件 SDK（plugin.yaml + provider 注册）
- [ ] 远程调试接入（Dify SaaS 转发到本地）
- [ ] 发布到 Dify Marketplace（可选）
