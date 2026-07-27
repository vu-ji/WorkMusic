"""Prompt 模板渲染引擎 —— 加载 YAML，替换变量，拼成文本"""
import yaml
from pathlib import Path
from typing import Any

def load_prompt(template_path: Path, **variables: dict[str, Any]) -> str:
    return PromptRenderer(template_path).render(variables)

class PromptRenderer:
    """加载一个 prompt 模板，填入变量，渲染为纯文本 system prompt"""

    def __init__(self, template_path: Path) -> None:
        """加载 YAML，存模板数据"""
        self.template = yaml.safe_load(template_path.read_text())

    def _replace(self, value: any, vars: dict[str, Any]) -> Any:
        """递归替换任意嵌套结构中的 {{变量}}"""
        if isinstance(value, str):
            result = value
            for key, val in vars.items():
                result = result.replace("{{" + key + "}}", str(val))
            return result
        elif isinstance(value, dict): # 如果是dic，遍历每个 k, v 进行处理
            return {k: self._replace(v, vars) for k, v in value.items()}
        elif isinstance(value, list): # 如果是list，遍历每个 value 进行处理
            return [self._replace(item, vars) for item in value]
        else:
            return value

    def render(self, variables: dict[str, Any]) -> str:
        s = self._replace(self.template['system'], variables)
        
        lines =  []

         # identity + goal
        lines.append(s['identity'])
        lines.append("")
        lines.append("## 目标")
        lines.append(s["goal"])
        lines.append("")

        # constraints
        lines.append("## 能力边界")
        for v in s['constraints']:
            lines.append("- " + v)
        lines.append("")

        # input
        lines.append("## 输入")
        for inp in s["input"]:
            lines.append(inp)
        lines.append("")

        # output
        lines.append("## 输出格式")
        for i, step in enumerate(s['output']["steps"]):
            lines.append(f"{i + 1}. {step['title']}：{step['content']}")
            if "rule" in step and step["rule"]:
                lines.append(f"   （{step['rule']}）")
        lines.append("")

        # tone
        lines.append("## 语气")
        lines.append(s["tone"])
        lines.append("")

        if "examples" in s:
            lines.append("")
            lines.append("## 示例（请严格参照以下格式和风格）")
            for ex in s["examples"]:
                lines.append("")
                lines.append("【用户需求】")
                lines.append(ex["input"])
                lines.append("")
                lines.append("【正确答案】")
                lines.append(ex["output"])

        return "\n".join(lines)
        
