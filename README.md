# 🌍 LangGraph 1.0 智能旅游规划系统

基于 **LangGraph 1.0** 的智能旅游规划系统，完整展示顺序执行、并行查询、循环优化、条件分支、持久化存储、文件写入和中断恢复的示例。

## 📋 项目概述

这是一个完整的 LangGraph 1.0 示例项目，演示如何构建复杂的 AI 工作流，包含：

- **🔄 顺序执行节点**：意图解析 → 并行查询 → 结果汇总 → 预算评估 → 行程生成 → 文件写入
- **⚡ 并行查询节点**：同时查询航班、酒店、景点信息，提高效率
- **🔁 循环优化节点**：预算优化循环（最多3次尝试）
- **🤔 条件分支路由**：根据预算状态进行智能路由决策
- **👤 人工干预机制**：预算超支时的用户决策点（接受优化/保持原方案/终止规划）
- **💾 持久化存储**：基于 aiosqlite 的异步数据库操作，支持会话管理
- **📝 文件写入功能**：使用 LangGraph 1.0 ToolNode 将旅游方案自动保存到output文件夹中
- **🔄 中断恢复机制**：支持从中断点继续执行，避免重新开始

## 🏗️ 系统架构

### 完整工作流程图

```
开始 → 解析意图 → 并行查询 → 汇总结果 → 预算评估
  ↓
预算优化循环（最多3次）←→ 人工干预（条件分支）
  ↓
生成最终行程 → 文件写入 → 结束
  ↓
中断恢复支持（任意节点可恢复）
```

### 核心组件

- **src/graph.py**: LangGraph 1.0 工作流定义和条件路由逻辑
- **src/node.py**: 各个节点的具体实现函数
- **src/tool.py**: 工具函数定义（文件写入工具）
- **src/database.py**: 6表数据库模式和异步操作
- **src/state.py**: TravelState 状态定义
- **src/persistence.py**: 持久化管理和中断恢复逻辑
- **src/main.py**: 主程序逻辑和用户交互界面
- **run.py**: 项目入口点

### LangGraph 1.0 技术架构

```python
# 核心导入 - LangGraph 1.0
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.aiosqlite import AsyncSqliteSaver

# 工作流构建
workflow = StateGraph(TravelState)

# 节点定义
workflow.add_node("parse_intent", node_parse_intent)
workflow.add_node("parallel_queries", node_parallel_queries)
workflow.add_node("aggregate_results", node_aggregate_results)
workflow.add_node("budget_evaluation", node_budget_evaluation)
workflow.add_node("budget_optimization", node_budget_optimization)
workflow.add_node("human_intervention", node_human_intervention)
workflow.add_node("generate_itinerary", node_generate_itinerary)

# ToolNode 集成 - LangGraph 1.0 新特性
all_tools = [query_flight_prices, query_hotel_prices, query_attractions, write_itinerary_to_file]
tool_node = ToolNode(all_tools)
workflow.add_node("tools", tool_node)

# 条件路由
workflow.add_conditional_edges(
    "budget_optimization",
    budget_router,
    {
        "continue": "budget_optimization",
        "human_intervention": "human_intervention", 
        "proceed": "generate_itinerary"
    }
)

# 持久化检查点 - LangGraph 1.0
checkpointer = AsyncSqliteSaver.from_conn_string("travel_planning.db")
graph = workflow.compile(checkpointer=checkpointer)
```

## 🚀 快速开始

### 环境要求

- **Python 3.10+** （LangGraph 1.0 必需）
- **推荐 Python 3.11+** （更好的性能和类型支持）
- 所有依赖已在 `requirements.txt` 中定义

### 核心依赖版本

```txt
# LangGraph 1.0 核心框架
langgraph==1.0.5
langgraph-checkpoint==3.0.1
langgraph-prebuilt==1.0.5
langgraph-sdk==0.3.0

# LangChain 集成
langchain-core==1.2.0
langchain-openai==1.1.3

# 数据库持久化
aiosqlite==0.22.0
```

### 安装运行

1. **检查Python版本**
   ```bash
   python --version
   # 确保版本 >= 3.10，推荐 3.11+
   ```

2. **克隆项目**
   ```bash
   git clone https://github.com/wafu7969/langgraph-workflow-demo
   cd langgraph-workflow-demo
   ```

3. **创建虚拟环境（推荐）**
   ```bash
   # Python 3.11 示例
   python -m venv venv_py311
   
   # Windows 激活
   venv_py311\Scripts\activate
   
   # Linux/Mac 激活
   source venv_py311/bin/activate
   ```

4. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

5. **配置环境变量**
   ```bash
   # 复制环境配置文件
   cp .env.example .env
   
   # 编辑 .env 文件，添加你的 OpenAI API Key
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4o
   ```

6. **运行程序**
   ```bash
   # 查看帮助
   python run.py --help
   
   # 交互模式
   python run.py --interactive
   
   # 直接查询（无持久化）
   python run.py --query "您的旅游需求" --no-persistence
   
   # 完整功能（包含持久化）
   python run.py --query "您的旅游需求"
   
   # 中断恢复模式
   python src/main.py resume
   ```

7. **运行测试**
   ```bash
   python -m pytest tests/ -v
   ```

### 使用示例

```bash
python run.py --interactive
请输入您的旅游需求: 日本豪华旅游7天，要住五星级酒店，坐头等舱，预算只有1000元
```

系统将自动：
1. **解析意图**：理解用户的旅游需求
2. **并行查询**：同时查询航班、酒店、景点信息
3. **汇总结果**：整合所有查询结果
4. **预算评估**：检查预算是否充足
5. **预算优化循环**：最多3次尝试优化预算
6. **人工干预**：预算超支时提供用户选择
7. **生成行程**：输出详细的旅游行程表
8. **文件写入**：自动保存旅游方案到文件
9. **状态持久化**：每步都保存到数据库，支持中断恢复

## 📊 核心功能特性

### 🔄 顺序执行模式

展示 LangGraph 中的线性节点链：

```python
# 顺序执行链 - 示例
workflow.add_edge("parse_intent", "parallel_queries")
workflow.add_edge("parallel_queries", "aggregate_results")
workflow.add_edge("aggregate_results", "budget_evaluation")
workflow.add_edge("budget_evaluation", "generate_itinerary")
```

**要点**：
- 每个节点依次执行，确保数据流的正确性
- 意图解析 → 并行查询 → 结果汇总 → 预算评估 → 行程生成
- 状态在节点间顺序传递和累积

### 🔁 循环执行模式

展示 LangGraph 中的条件循环：

```python
# 预算优化循环 - 示例
workflow.add_conditional_edges(
    "budget_optimization",
    budget_router,
    {
        "continue": "budget_optimization",      # 继续优化
        "human_intervention": "human_intervention",  # 人工干预
        "proceed": "generate_itinerary"         # 进入下一阶段
    }
)
```

**要点**：
- 最大循环次数限制（3次）
- 基于预算状态的退出条件
- 豪华需求时优化能力有限（最多节省30%）
- 状态累积和循环计数器管理

### 🤔 条件分支路由

展示 LangGraph 中的智能路由决策：

```python
# 预算路由 - 示例
def budget_router(state: TravelState) -> str:
    control = state.get("_control", {})
    if control.get("needs_human_intervention"):
        return "human_intervention"  # 需要人工干预
    elif control.get("budget_optimization_attempts", 0) >= 3:
        return "human_intervention"  # 达到最大尝试次数
    elif control.get("budget_satisfied", False):
        return "proceed"  # 预算满足，继续
    else:
        return "continue"  # 继续优化
```

**要点**：
- 根据状态动态路由决策
- 支持多种路由目标
- 循环控制和退出条件

### 👤 人工干预机制

预算不足时的用户决策点：

```python
# 3个用户选择
1. 接受优化建议（输入"接受"或"1"）
2. 保持原方案继续（输入"保持"或"2"）  
3. 终止规划（输入"终止"或"3"）

# 动态优化率
- 超支 < 50%：建议节省15%费用
- 超支 50-100%：建议节省20%费用  
- 超支 > 100%：建议节省25%费用
```

### 🗄️ 持久化存储

基于 aiosqlite 的异步数据库操作：

```python
# 6表数据库模式
- sessions: 会话管理和状态跟踪
- travel_states: 状态快照和版本控制
- query_results: 查询结果缓存（航班、酒店、景点）
- cost_analyses: 费用分析和优化历史
- messages: 消息历史和用户交互
- cache_entries: MD5缓存键和查询优化
```

**特性**：
- 异步数据库操作（aiosqlite）
- 会话状态持久化和恢复
- 查询结果智能缓存
- 完整的审计日志和版本控制

### 📝 文件写入功能

使用 ToolNode 实现旅游方案的自动文件保存：

```python
# 文件写入工具
@tool
def write_itinerary_to_file(content: str, filename: str = None) -> str:
    """将旅游行程写入文件"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"travel_itinerary_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    return f"✅ 旅游行程已保存到文件: {filename}"
```

**特性**：
- 自动生成带时间戳的文件名
- UTF-8 编码支持中文内容
- 集成到 LangGraph 工作流中
- 使用 ToolNode 进行工具调用

### 🔄 中断恢复机制

支持从任意中断点继续执行：

```python
# 恢复功能使用
# 1. 正常模式
python src/main.py

# 2. 恢复模式 - 交互式选择
python src/main.py resume

# 3. 演示恢复功能
python resume_demo.py demo

# 4. 测试恢复组件
python test_recovery.py
```

**核心特性**：
- **自动状态保存**：每个执行步骤都保存到数据库
- **智能恢复**：从最后保存的状态点继续执行
- **会话管理**：支持多个并发会话的独立恢复
- **交互式选择**：用户可选择要恢复的具体会话
- **状态完整性**：保持消息历史、控制状态和执行进度

**恢复流程**：
1. 系统列出所有可恢复的会话
2. 用户选择要恢复的会话ID
3. 系统恢复状态和步骤计数器
4. 从中断点继续执行工作流

## 🎯 重点

### 1. LangGraph 工作流设计

```python
# 节点定义 - 示例
workflow.add_node("parse_intent", node_parse_intent)
workflow.add_node("parallel_queries", node_parallel_queries)
workflow.add_node("budget_optimization", node_budget_optimization)
workflow.add_node("human_intervention", node_human_intervention)

# 边定义 - 示例
workflow.add_edge("parse_intent", "parallel_queries")
workflow.add_conditional_edges("budget_optimization", budget_router)
```

### 2. 状态管理和类型安全

```python
# TravelState 类型定义
class TravelState(TypedDict):
    query: str
    travel_info: Dict[str, Any]
    budget: float
    cost_analysis: Dict[str, Any]
    _control: Dict[str, Any]  # 控制信息
```

**要点**：
- 使用 TypedDict 确保类型安全
- 状态在节点间传递和累积
- `_control` 字段管理流程控制逻辑

### 3. 异步编程和数据库操作

```python
# 异步节点函数
async def node_budget_optimization(state: TravelState) -> TravelState:
    # 异步数据库操作
    await db.save_travel_state(session_id, state)
    return updated_state

# 异步数据库查询
async with aiosqlite.connect("travel_planning.db") as db:
    await db.execute("INSERT INTO sessions ...")
```

## 📄 许可证

MIT License

## 📚️ 学习交流

**欢迎关注我的公众号，获取更多关于大模型应用的学习资源和技术分享。**

![微信公众号二维码](images/wechat.jpg)