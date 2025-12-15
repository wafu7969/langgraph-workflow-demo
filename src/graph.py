"""
旅游规划工作流编排 - LangGraph图构建
"""

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from node import (
    TravelState, 
    node_parse_intent, 
    node_prepare_parallel,
    node_parallel_query,
    node_merge_results,
    node_query_flights,
    node_query_hotels,
    node_query_attractions,
    node_aggregate_parallel_results,
    # node_evaluate_budget,  # 已移除冗余节点
    node_human_intervention,  # 人工干预节点
    node_generate_itinerary,
    node_write_itinerary_file,  # 新增：写入行程文件节点
    # 新增：顺序执行节点
    node_validate_budget,
    node_check_destination,
    node_verify_travel_time,
    node_check_documents,
    # 新增：循环执行节点
    node_budget_optimization,
    node_check_budget_satisfaction,
    node_itinerary_optimization,
    node_check_itinerary_satisfaction
)
from tool import (
    query_flight_prices,
    query_hotel_prices, 
    query_attractions,
    write_itinerary_to_file
)

# 创建统一的工具节点，包含所有工具
all_tools = [write_itinerary_to_file]
tool_node = ToolNode(all_tools)

def create_travel_planning_graph():
    """创建旅游规划Graph"""
    workflow = StateGraph(TravelState)
    
    # 添加核心处理节点
    workflow.add_node("parse_intent", node_parse_intent)              # 解析用户意图，提取旅游需求信息
    
    # 🔄 顺序执行节点链 - 旅行前置验证流程
    workflow.add_node("validate_budget", node_validate_budget)        # 1️⃣ 预算验证
    workflow.add_node("check_destination", node_check_destination)    # 2️⃣ 目的地可行性检查  
    workflow.add_node("verify_travel_time", node_verify_travel_time)  # 3️⃣ 时间可行性检查
    workflow.add_node("check_documents", node_check_documents)        # 4️⃣ 个人信息验证
    
    # 并行执行执行节点
    workflow.add_node("query_flights", node_query_flights)            # 并行查询航班信息
    workflow.add_node("query_hotels", node_query_hotels)              # 并行查询酒店信息  
    workflow.add_node("query_attractions", node_query_attractions)    # 并行查询景点信息
    workflow.add_node("aggregate_results", node_aggregate_parallel_results)  # 汇总并行查询结果
    
    # 🔄 循环执行节点 - 预算优化循环
    workflow.add_node("budget_optimization", node_budget_optimization)               # 预算优化处理
    workflow.add_node("check_budget_satisfaction", node_check_budget_satisfaction)   # 检查预算满意度
    
    
    # 🔄 循环执行节点 - 行程优化循环  
    workflow.add_node("itinerary_optimization", node_itinerary_optimization)       # 行程优化处理
    workflow.add_node("check_itinerary_satisfaction", node_check_itinerary_satisfaction) # 检查行程满意度
    workflow.add_node("human_intervention", node_human_intervention)              # 人工干预处理
    workflow.add_node("generate_itinerary", node_generate_itinerary)  # 生成最终旅游行程
    workflow.add_node("write_itinerary_file", node_write_itinerary_file)  # 写入行程文件节点
    workflow.add_node("tool_node", tool_node)  # ToolNode工具执行节点

    
    # 设置入口点
    workflow.set_entry_point("parse_intent")
    
    # 解析意图后的路由
    def after_parse_router(state: TravelState) -> str:
        control = state.get("_control", {})
        status = state.get("status", "")
        
        print(f"🔍 路由检查: status={status}, control={control}")
        
        if status == "collecting_info":
            return END  # 需要用户输入，暂停流程
        elif status == "planning" and not control.get("validation_completed"):
            return "validate_budget"  # 🔄 开始顺序执行的前置验证流程
        elif status == "planning" and control.get("validation_completed"):
            print("✅ 验证已完成，跳过重复验证")
            return "start_parallel"  # 直接进入并行查询
        elif status == "processing" and not control.get("parsed_attempted"):
            return "parse_intent"  # 首次解析
        elif status == "processing" and control.get("user_confirmed"):
            return "generate_itinerary"  # 用户已确认，生成行程
        elif status == "continuing":
            # 人工干预后继续流程
            if control.get("human_intervention_completed"):
                print("✅ 人工干预完成，继续生成行程")
                return "generate_itinerary"
            else:
                print("⚠️ 人工干预状态异常")
                return END
        else:
            # 避免无限循环，如果状态不明确就结束
            print(f"⚠️ 未知状态，结束流程: status={status}")
            return END
    
    workflow.add_conditional_edges(
        "parse_intent",
        after_parse_router,
        {
            "parse_intent": "parse_intent",
            "validate_budget": "validate_budget",  # 🔄 开始顺序验证流程
            "start_parallel": "start_parallel",    # 🔄 跳过验证，直接并行查询
            "generate_itinerary": "generate_itinerary",
            END: END
        }
    )
    
    # 🔄 顺序执行链 - 旅行前置验证流程
    print("📚 配置顺序执行链：预算验证 → 目的地检查 → 时间验证 → 文件检查")
    workflow.add_edge("validate_budget", "check_destination")      # 1️⃣ → 2️⃣
    workflow.add_edge("check_destination", "verify_travel_time")   # 2️⃣ → 3️⃣  
    workflow.add_edge("verify_travel_time", "check_documents")     # 3️⃣ → 4️⃣
    workflow.add_edge("check_documents", "start_parallel")         # 4️⃣ → 并行查询
    
    # 添加一个虚拟的开始并行节点，用于触发真正的并行执行
    def start_parallel_node(state: TravelState) -> TravelState:
        """开始并行查询的触发节点"""
        print("\n" + "="*60)
        print("🚀 [LangGraph并行] 启动原生并行查询")
        print("⚡ 同时启动3个查询任务...")
        print("="*60)
        return state
    
    workflow.add_node("start_parallel", start_parallel_node)
    
    # 从start_parallel同时启动3个查询节点
    workflow.add_edge("start_parallel", "query_flights")
    workflow.add_edge("start_parallel", "query_hotels") 
    workflow.add_edge("start_parallel", "query_attractions")
    
    # 所有并行查询完成后汇总结果
    workflow.add_edge("query_flights", "aggregate_results")
    workflow.add_edge("query_hotels", "aggregate_results")
    workflow.add_edge("query_attractions", "aggregate_results")
    
    # LangGraph原生并行查询完成后直接进入预算优化循环
    workflow.add_edge("aggregate_results", "budget_optimization")
    
    # 预算优化循环会自动处理预算评估和优化逻辑
    
    # 🔄 预算优化循环逻辑
    def budget_satisfaction_router(state: TravelState) -> str:
        """预算优化循环的条件路由 - 示例：条件分支判断"""
        control = state.get("_control", {})
        budget_attempts = control.get("budget_optimization_attempts", 0)
        budget_satisfied = control.get("budget_satisfied", False)
        needs_human_intervention = control.get("needs_human_intervention", False)
        cost_analysis = state.get("cost_analysis", {})
        is_over_budget = cost_analysis.get("is_over_budget", False)
        
        print(f"💰 [条件分支判断] 预算循环路由决策:")
        print(f"   🔄 尝试次数: {budget_attempts}/3")
        print(f"   ✅ 预算满意: {budget_satisfied}")
        print(f"   ⚠️ 超出预算: {is_over_budget}")
        print(f"   👤 需要人工干预: {needs_human_intervention}")
        
        # 条件分支的优先级判断
        if budget_satisfied:
            print("   ➡️ 路由决策: 预算满意 → 进入行程优化")
            return "itinerary_optimization"  # 预算满意，进入行程优化
        elif needs_human_intervention or (budget_attempts >= 3 and is_over_budget):
            print("   ➡️ 路由决策: 需要人工干预或达到最大尝试次数且仍超预算 → 人工干预")
            return "human_intervention"  # 需要人工干预
        elif budget_attempts >= 3:
            print("   ➡️ 路由决策: 达到最大尝试次数但预算可接受 → 进入行程优化")
            return "itinerary_optimization"  # 强制进入下一阶段
        else:
            print("   ➡️ 路由决策: 继续预算优化")
            return "budget_optimization"  # 继续优化

    workflow.add_edge("budget_optimization", "check_budget_satisfaction")
    workflow.add_conditional_edges(
        "check_budget_satisfaction",
        budget_satisfaction_router,
        {
            "budget_optimization": "budget_optimization",      # 继续优化
            "itinerary_optimization": "itinerary_optimization", # 进入行程优化
            "human_intervention": "human_intervention"          # 人工干预
        }
    )
    
    # 🔄 行程优化循环逻辑  
    def itinerary_satisfaction_router(state: TravelState) -> str:
        """行程优化循环的条件路由 - 示例：复杂条件分支"""
        control = state.get("_control", {})
        itinerary_attempts = control.get("itinerary_optimization_attempts", 0)
        itinerary_satisfied = control.get("itinerary_satisfied", False)
        itinerary_score = control.get("itinerary_score", 0)
        cost_analysis = state.get("cost_analysis", {})
        is_over_budget = cost_analysis.get("is_over_budget", False)
        
        print(f"🗺️ [条件分支判断] 行程循环路由决策:")
        print(f"   🔄 尝试次数: {itinerary_attempts}/3")
        print(f"   ✅ 行程满意: {itinerary_satisfied}")
        print(f"   📊 满意度评分: {itinerary_score:.2f}")
        print(f"   ⚠️ 预算状态: {'超支' if is_over_budget else '正常'}")
        
        # 多条件复合判断
        if itinerary_satisfied:
            print("   ➡️ 路由决策: 行程满意 → 生成最终行程")
            return "generate_itinerary"  # 行程满意，生成最终行程
        elif itinerary_attempts >= 3 and (itinerary_score < 0.7 or is_over_budget):
            print("   ➡️ 路由决策: 达到最大尝试次数且质量不佳 → 人工干预")
            return "human_intervention"  # 需要人工干预
        elif itinerary_attempts >= 3:
            print("   ➡️ 路由决策: 达到最大尝试次数但质量可接受 → 生成行程")
            return "generate_itinerary"  # 强制生成行程
        else:
            print("   ➡️ 路由决策: 继续行程优化")
            return "itinerary_optimization"  # 继续优化
    
    workflow.add_edge("itinerary_optimization", "check_itinerary_satisfaction")
    workflow.add_conditional_edges(
        "check_itinerary_satisfaction", 
        itinerary_satisfaction_router,
        {
            "itinerary_optimization": "itinerary_optimization", # 继续优化
            "generate_itinerary": "generate_itinerary",          # 生成最终行程
            "human_intervention": "human_intervention"          # 人工干预
        }
    )
    
    # 人工干预后的路由
    def human_intervention_router(state: TravelState) -> str:
        """人工干预后的条件路由 - 示例：用户决策分支"""
        status = state.get("status", "")
        control = state.get("_control", {})
        
        print(f"👤 [条件分支判断] 人工干预路由决策:")
        print(f"   📊 当前状态: {status}")
        print(f"   🔄 控制信息: {control}")
        
        # 基于用户决策的条件分支
        if status == "waiting_confirmation":
            print("   ➡️ 路由决策: 等待用户确认 → 暂停流程")
            return END  # 等待用户输入，暂停流程
        elif status == "terminated":
            print("   ➡️ 路由决策: 用户终止规划 → 结束流程")
            return END  # 用户选择终止
        elif control.get("human_intervention_completed"):
            print("   ➡️ 路由决策: 人工干预完成 → 生成最终行程")
            return "generate_itinerary"  # 已处理完成，生成行程
        else:
            print("   ➡️ 路由决策: 继续人工干预处理")
            return "human_intervention"  # 继续处理

    workflow.add_conditional_edges(
        "human_intervention",
        human_intervention_router,
        {
            "human_intervention": "human_intervention",
            "generate_itinerary": "generate_itinerary",
            END: END
        }
    )
    
    # 行程生成后写入文件
    workflow.add_edge("generate_itinerary", "write_itinerary_file")
    
    # 写入文件节点生成工具调用后，交给ToolNode执行
    workflow.add_edge("write_itinerary_file", "tool_node")
    
    # ToolNode执行完成后结束
    workflow.add_edge("tool_node", END)
    
    return workflow