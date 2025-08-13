"""
任务生成相关的提示词模板
"""


class TaskPrompts:
    """任务生成提示词模板"""
    
    TASK_GENERATION = """你是一个智能任务设计专家，需要为指定的智能体生成多轮对话任务和对应的评分检查点。

## 智能体信息
- 可用工具: {available_tools}

## 工具详细信息
{tools_details}

## 任务设计要求
1. **多轮对话**: 任务必须需要多轮对话才能完成，涉及2-4个工具的顺序调用
2. **能力匹配**: 任务只能使用智能体现有的工具，不能超出其能力范围
3. **难度递进**: 生成{difficulty}难度的任务
4. **实际场景**: 任务应该基于真实的使用场景，具有实用性

## 难度级别说明
- **simple**: 使用2-3个工具，步骤简单直接，操作流程清晰
- **medium**: 使用3-4个工具，需要一定的逻辑推理，可能涉及条件判断
- **complex**: 使用4-6个工具，涉及复杂的业务逻辑，需要多步骤协调

## 输出格式
请以JSON格式输出，包含以下字段：

```json
{{
    "task": {{
        "title": "任务标题",
        "description": "详细的任务描述，包含用户身份、背景信息、具体目标。描述应该像示例中一样，采用第二人称视角，为用户设定明确的身份和情境",
        "difficulty": "{difficulty}",
        "expected_turns": "预期对话轮数(4-8轮)",
        "user_context": {{
            "identity": "用户身份",
            "background": "背景信息",
            "constraints": ["约束条件1", "约束条件2"],
            "goals": ["目标1", "目标2"]
        }}
    }},
    "rubric": {{
        "checkpoints": [
            "tool_name1(param1=value1, param2=value2)",
            "tool_name2(param1=value1, param2=value2)",
            "tool_name3(param1=value1, param2=value2)"
        ],
        "checkpoint_descriptions": [
            "检查点1：详细描述第一步需要做什么",
            "检查点2：详细描述第二步需要做什么",
            "检查点3：详细描述第三步需要做什么"
        ],
        "success_criteria": [
            "成功标准1",
            "成功标准2",
            "成功标准3"
        ],
        "tool_usage_expectations": [
            "工具使用期望1",
            "工具使用期望2"
        ]
    }}
}}
```
"""
