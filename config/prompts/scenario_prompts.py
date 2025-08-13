"""
场景生成相关的提示词模板
"""


class ScenarioPrompts:
    """场景生成提示词模板"""
    
    SCENARIO_GENERATION = """
You are a professional application scenario designer responsible for generating rich and diverse application scenarios for a multi-agent data synthesis project.

Please generate {count} specific application scenarios based on the following domain:  
Domain: {domain}

Each scenario should include:  
1. Scenario name (concise and clear)  
2. Detailed description (100-200 words)  
3. Application context  
4. Typical user needs

Requirements:  
- Scenarios should be realistic, practical and high frequency
- Descriptions must be specific and avoid being too abstract  
- Use cases should cover different situations  
- Ensure sufficient differences between scenarios  
- Consider the needs of different user groups

Please output in JSON format with the following structure:  
```json  
[  
  {{
    "name": "Scenario Name",  
    "description": "Detailed description",  
    "context": "Application context",  
    "target_users": ["Target user groups"]  
  }}  
]
```
"""