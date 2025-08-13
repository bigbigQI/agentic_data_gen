"""
工具生成相关的提示词模板
"""


class ToolPrompts:
    """工具生成提示词模板"""

    TOOL_GENERATION = """
You are a professional tool designer responsible for creating tools and functions tailored to a given application scenario.

Scenario:
- Name: {scenario_name}
- Description: {scenario_description}
- Domain: {scenario_domain}
- Context: {scenario_context}

Task:
Design exactly {count} tools that are highly relevant to the scenario. Cover both foundational capabilities (e.g., authentication, configuration, data access) and core scenario execution functions. Ensure tools are differentiated, broadly useful, and generalizable.

Strict requirements:
- Use English for all names, descriptions, categories, and examples.
- Tool names and parameter names must be snake_case and unique.
- Parameter types must be one of: string, integer, float, boolean, array, object.
- Return type must be one of: string, integer, float, boolean, array, object.
- Each tool must include exactly:
  1) name (concise, snake_case)
  2) description (1–3 sentences; purpose and when to use)
  3) parameters (array). Each parameter must include:
     - name (snake_case)
     - type (one of allowed types)
     - description (clear and specific; include units or format if relevant)
     - required (boolean)
     - default (null or a type-correct value; if required is true, default must be null)
     - enum (optional; include only if the set of allowed values is small and well-defined)
  4) return_type (one of allowed types)
  5) examples (array with exactly two items):
     - Example 1: a successful call
     - Example 2: an error case (e.g., missing/invalid parameter)
- In both examples:
  - input must be an object that matches the parameters (include all required params for the success example; violate a clear rule for the error example).
  - output must be an object. For success, include at least: result: "success" and data (type-consistent with return_type). For error, include at least: result: "error" and error with code and message; data may be null.
- Do not include placeholders like "TBD" or "lorem ipsum". Avoid secrets. Keep values realistic and consistent with the scenario.
- Ensure no duplicate tools and no contradictory behaviors.
- Validate that examples strictly align with defined parameter types and return types.

Output format:
- Return only a JSON array of tool objects. No prose, no comments, no trailing commas.

JSON structure (template)
[
  {{
    "name": "tool_name",
    "description": "Clear description of what the tool does and when to use it.",
    "parameters": [
      {{
        "name": "param_name",
        "type": "string",
        "description": "What this parameter controls; include format/units if relevant.",
        "required": true,
        "default": null,
        "enum": ["option1", "option2"]
      }}
    ],
    "return_type": "object",
    "examples": [
      {{
        "input": {{"param_name": "example_value"}},
        "output": {{"result": "success", "data": {{"example_field": "value"}}}}
      }},
      {{
        "input": {{"param_name": 123}},
        "output": {{"result": "error", "error": {{"code": "INVALID_TYPE", "message": "param_name must be a string"}}, "data": null}}
      }}
    ]
  }}
]

Final self-check before responding:
- Names and parameters are snake_case and unique.
- Parameter and return types are from the allowed set.
- Required params have default = null; optional params have sensible defaults.
- Examples comply with the parameter schema and return_type.
- Output is valid JSON array with no extra text.
"""

    TOOL_REFINEMENT = """
请优化以下工具的设计：

工具信息：
{tool_data}

优化要求：
1. 改进工具描述的清晰度
2. 优化参数设计和类型定义
3. 提供更好的使用示例
4. 确保工具的实用性
5. 改进参数验证规则
6. 优化返回数据结构

请返回优化后的工具JSON格式，保持原有结构：
```json
{{
  "id": "tool_id",
  "name": "tool_name",
  "description": "优化后的工具描述",
  "category": "工具类别",
  "scenario_ids": ["scenario_id"],
  "parameters": [
    {{
      "name": "param_name",
      "type": "string",
      "description": "优化后的参数描述",
      "required": true,
      "default": null,
      "enum": ["option1", "option2"],
    }}
  ],
  "return_type": "object",
  "examples": [
    {{
      "input": {{"param_name": "example_value"}},
      "output": {{"result": "success", "data": {{}}}}
    }}
  ],
}}
```
"""

    TOOL_VALIDATION = """
Evaluate the tool’s design quality and usefulness based only on the information below. Do not speculate about missing details.

Tool information:  
{tool_data}

Scoring scale (1=poor, 3=average, 5=excellent):  
- Clarity (clarity): Are descriptions, parameters, and inputs/outputs clear and consistent?  
- Utility (utility): Is the functionality valuable and relevant to typical scenarios/user needs?  
- Usability (usability): Are parameter names/types/defaults/error handling reasonable and easy to invoke?  
- Completeness (completeness): Are required fields, constraints, examples, and edge cases covered?  
- Compliance (compliance): Does it follow design conventions (naming, consistency, type constraints, security/permissions, error codes, etc.)?

Output: return JSON only (no extra text or code block), in this format:  
```json
{{
  "scores": {{ "clarity": n, "utility": n, "usability": n, "completeness": n, "compliance": n }},  
  "overall_score": x.x 
}}
```

Rules:  
- overall_score = average of the five scores, keep one decimal place.  
- If information is missing or ambiguous, deduct in completeness/clarity and note it in weaknesses/suggestions.  
"""
