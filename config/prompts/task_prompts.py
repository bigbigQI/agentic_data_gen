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
        "description": "详细的任务描述，包含用户身份、背景信息、具体目标。描述请采用第二人称视角，为用户设定明确的身份和情境",
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
        "tool_usage_expectations": [
            "工具使用期望1",
            "工具使用期望2"
        ],
        "checkpoints": [
            "tool_name1(param1=value1, param2=value2)",
            "tool_name2(param1=value1, param2=value2)",
            "tool_name3(param1=value1, param2=value2)"
        ],
        "success_criteria": [
            "成功标准1",
            "成功标准2",
            "成功标准3"
        ]
    }}
}}
```
"""



    TASK_GENERATION = """
You are an **intelligent task design expert**. Your job is to create a **multi-turn conversation task** for a given AI agent with specific tool capabilities, and to design **evaluation rubrics and checkpoints** for assessing its performance.  

---
**Agent Information:**  
- Available tools: `{available_tools}`  
- Tool details:  
`{tools_details}`  

---
**Task Design Requirements:**  
1. **Multi-Turn Conversation**  
   - The task must require **4–8 conversation turns** to complete.  
   - It should involve **2–4 available tools** in sequential usage (depending on difficulty).  
2. **Capability Match**  
   - Only use tools that the agent currently has access to; do not go beyond its capabilities.  
3. **Difficulty Level** — `{difficulty}` should follow these definitions:  
      - `simple`: 2–3 tools, straightforward flow, minimal steps  
      - `medium`: 3–4 tools, requires conditional reasoning  
      - `complex`: 4–6 tools, involves multi-step coordination and planning  
4. **Realistic Scenario**  
   - The task must be based on real-world or business scenarios with clear practical application.  

---
**Output Format (MUST be in JSON):**
```json
{{
    "task": {{
        "title": "Task title",
        "description": "A detailed second-person-perspective description including the user's role, background, and objectives",
        "difficulty": "{difficulty}",
        "expected_turns": "Expected number of turns (4-8)"
    }},
    "rubric": {{
        "tool_usage_expectations": [
            "Describe expectations for tool usage order and process"
        ],
        "checkpoints": [
            "tool_name(param1=value1, param2=value2)"
        ],
        "success_criteria": [
            "List clear, measurable criteria for task success"
        ]
    }}
}}
```
---
**Important Notes:**  
- The description must be detailed and immersive.  
- Checkpoints should allow objective validation of whether the AI followed correct steps.  
- Success criteria should be specific, measurable, and unambiguous.  

"""