# Multi-Agent Data Generation 大规模智能体数据合成项目

这是一个基于大语言模型的多智能体数据合成系统，用于自动生成高质量的智能体训练数据。通过模拟真实的多轮对话场景，系统可以大规模生成多样化的智能体交互轨迹。

## 🎯 项目概述

本项目实现了一个完整的数据合成流水线，旨在解决智能体训练数据稀缺的问题。系统通过以下步骤自动化生成高质量的训练数据：

1. **场景生成** - 基于不同领域生成多样化的应用场景
2. **工具设计** - 为每个场景设计专用的工具集
3. **智能体合成** - 组合不同的系统提示词和工具集生成多样化智能体
4. **任务生成** - 为每个智能体生成从简单到复杂的任务
5. **多轮轨迹生成** - 模拟用户与智能体的多轮交互
6. **质量评估** - 基于评分标准筛选高质量轨迹
7. **训练数据转换** - 将轨迹转换为标准训练格式

## 🚀 核心特性

- **🔧 模块化设计** - 每个组件都是独立的模块，便于扩展和维护
- **⚡ 高并发处理** - 支持多线程并发生成，提高数据生成效率
- **🎭 多样化生成** - 支持多种场景、工具、智能体和用户人格的组合
- **📊 质量控制** - 内置质量评估机制，确保生成数据的高质量
- **🛠️ 灵活配置** - 通过配置文件和环境变量灵活控制生成参数
- **📈 可扩展性** - 易于添加新的场景、工具和评估标准

## 📁 项目结构

```
agent_data_gen/
├── config/                    # 配置文件
│   ├── prompts/              # 各模块的提示词模板
│   └── settings.py           # 全局配置
├── core/                     # 核心模块
│   ├── base_module.py        # 基础模块类
│   ├── models.py             # 数据模型定义
│   └── exceptions.py         # 异常定义
├── modules/                  # 功能模块
│   ├── domain_tool_generator/ # 场景和工具生成
│   ├── agent_synthesizer/     # 智能体合成
│   ├── task_generator/        # 任务生成
│   ├── user_simulator/        # 用户模拟
│   ├── agent_simulator/       # 智能体模拟
│   ├── tool_execution/        # 工具执行模拟
│   ├── interaction_coordinator/ # 交互协调
│   └── quality_judge/         # 质量评估
├── scripts/                  # 执行脚本
│   ├── tool/                 # 工具相关脚本
│   ├── agent/                # 智能体相关脚本
│   ├── task/                 # 任务相关脚本
│   └── trajectory/           # 轨迹相关脚本
├── utils/                    # 工具类
├── data/                     # 数据存储
└── logs/                     # 日志文件
```

## 🛠️ 安装与配置

### 环境要求

- Python 3.8+
- 支持 OpenAI API 或其他兼容的 LLM 服务

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd agent_data_gen
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**

创建 `.env` 文件并配置以下变量：

```bash
# LLM 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7
DEFAULT_LLM_PROVIDER=openai

# 生成配置
SCENARIO_TARGET_COUNT=50
AGENT_TARGET_COUNT=1000
USER_PERSONA_TARGET_COUNT=500
TRAJECTORY_MAX_COUNT=1000

# 并发配置
MAX_WORKERS=4
TRAJECTORY_MAX_WORKERS=64

# 质量阈值
QUALITY_PASS_THRESHOLD=4.0
QUALITY_HIGH_THRESHOLD=4.5

# 日志级别
LOG_LEVEL=INFO
```

## 🎮 快速开始

### 完整流水线执行

按顺序执行以下脚本来运行完整的数据生成流水线：

1. **生成场景**
```bash
python scripts/tool/generate_scenarios.py
```

2. **生成工具**
```bash
python scripts/tool/generate_tools.py
```

3. **构建工具图**
```bash
python scripts/agent/build_tool_graph.py
```

4. **生成智能体**
```bash
python scripts/agent/generate_agents.py
```

5. **生成任务**
```bash
python scripts/task/generate_tasks.py
```

6. **生成轨迹**
```bash
python scripts/trajectory/generate_trajectory.py
```

7. **评估轨迹**
```bash
python scripts/trajectory/score_trajectory.py
```

8. **筛选高质量轨迹**
```bash
python scripts/trajectory/filter_high_quality_trajectories.py
```

9. **转换为训练数据**
```bash
python scripts/convert_to_training_data.py
```

```

## 📊 数据流程详解

### 1. 场景生成
- 基于预定义的领域（外卖、社交媒体、电商、旅游、机器人控制等）
- 生成详细的应用场景描述
- 每个场景包含背景、用例和上下文信息

### 2. 工具设计
- 为每个场景设计 8-10 个专用工具
- 每个工具包含完整的参数定义和功能描述
- 支持复杂的参数类型和约束

### 3. 智能体合成
- 通过组合不同的系统提示词和工具集
- 每个智能体配备 3-6 个不同的工具
- 生成具有不同专长和行为模式的智能体

### 4. 任务生成
- 为每个智能体生成简单、中等、复杂三个难度级别的任务
- 每个任务都有明确的评分标准和成功指标
- 包含预期的工具使用模式

### 5. 轨迹生成
- 模拟用户与智能体的多轮对话
- 用户具有不同的人格特征和交互风格
- 工具执行通过模拟器提供真实反馈

### 6. 质量评估
- 基于多维度评分标准评估轨迹质量
- 自动筛选出符合标准的高质量轨迹
- 支持自定义评估规则

## 🔧 核心模块说明

### BaseModule
所有功能模块的基类，提供统一的初始化、配置和日志接口。

### 数据模型 (models.py)
- `Scenario`: 场景数据模型
- `Tool`: 工具定义模型
- `AgentConfig`: 智能体配置模型
- `Task`: 任务数据模型
- `UserPersona`: 用户人格模型
- `Trajectory`: 交互轨迹模型

### LLM 客户端
支持多种 LLM 提供商的统一接口，包括 OpenAI、Anthropic 等。

### 工具执行模拟器
模拟真实的工具执行环境，支持：
- 状态持久化
- 随机性控制
- 成功/失败/部分失败模拟

## 📈 配置与优化

### 生成规模配置
```python
GENERATION_CONFIG = {
    "scenarios": {"target_count": 50},
    "agents": {"target_count": 1000},
    "trajectories": {"max_count": 1000}
}
```

### 质量控制配置
```python
QUALITY_CONFIG = {
    "score_thresholds": {
        "pass_threshold": 4.0,
        "high_quality_threshold": 4.5
    }
}
```

### 并发性能配置
```python
CONCURRENCY_CONFIG = {
    "max_workers": 4,
    "batch_processing": True,
    "timeout": 300
}
```

## 🎯 支持的场景领域

- **外卖配送** (food_delivery) - 点餐、配送、客服等场景
- **机器人控制** (robot_control) - 工业机器人、服务机器人控制
- **社交媒体** (social_media) - 发布、互动、内容管理
- **电商购物** (ecommerce) - 商品搜索、购买、售后
- **旅游出行** (travel) - 行程规划、预订、导航

可通过修改 `config/settings.py` 中的 `domains` 配置来添加新领域。

## 📊 输出数据格式

### 训练数据格式
```json
{
  "trajectory_id": "uuid",
  "task_id": "uuid", 
  "agent_id": "uuid",
  "messages": [
    {
      "role": "user",
      "content": "用户消息内容",
      "recipient": "agent"
    },
    {
      "role": "assistant", 
      "content": "智能体回复内容",
      "recipient": "user"
    }
  ],
  "score": 4.5,
  "metadata": {
    "quality_tags": ["high_quality"],
    "is_high_quality": true
  }
}
```

## 🚀 扩展开发

### 添加新的场景领域
1. 在 `config/settings.py` 中的 `domains` 列表中添加新领域
2. 在 `config/prompts/scenario_prompts.py` 中添加相应的提示词模板

### 添加新的工具类型
1. 在 `modules/domain_tool_generator/tool_designer.py` 中扩展工具生成逻辑
2. 在 `modules/tool_execution/tool_execution_simulator.py` 中添加执行逻辑

### 自定义评估标准
1. 修改 `modules/quality_judge/trajectory_evaluator.py` 中的评估逻辑
2. 更新 `config/prompts/evaluation_prompts.py` 中的评估提示词

## 📝 日志与调试

系统提供详细的日志记录，日志文件位于 `logs/` 目录下：

- **INFO 级别** - 记录主要的处理步骤和进度
- **DEBUG 级别** - 记录详细的调试信息
- **ERROR 级别** - 记录错误和异常信息

可通过设置 `LOG_LEVEL` 环境变量来控制日志级别。

## ⚠️ 注意事项

1. **API 限制** - 注意 LLM API 的调用频率限制
2. **存储空间** - 大量数据生成需要充足的存储空间
3. **内存使用** - 高并发处理时注意内存使用情况
4. **数据质量** - 建议定期检查生成数据的质量

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来改进项目。在提交代码前，请确保：

1. 遵循项目的代码风格
2. 添加必要的测试用例
3. 更新相关文档
4. 确保所有测试通过

## 📄 许可证

[请添加适当的许可证信息]

## 🙏 致谢

感谢所有为该项目做出贡献的开发者和研究人员。

---

如有任何问题或建议，请提交 Issue 或联系项目维护者。
