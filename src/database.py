"""
旅游规划助手 - 数据库持久化模块
使用aiosqlite实现异步SQLite数据库操作
"""

import aiosqlite
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from node import TravelState

# 数据库文件路径
DB_PATH = Path(__file__).parent.parent / "data" / "travel_planning.db"

class TravelDatabase:
    """旅游规划数据库管理类"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._connection = None
    
    async def init_database(self):
        """初始化数据库表结构"""
        async with aiosqlite.connect(self.db_path) as db:
            # 创建旅游会话表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS travel_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    user_query TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    final_itinerary TEXT,
                    total_cost REAL,
                    is_completed BOOLEAN DEFAULT FALSE
                )
            """)
            
            # 创建旅游状态表 - 存储完整的TravelState
            await db.execute("""
                CREATE TABLE IF NOT EXISTS travel_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    state_data TEXT NOT NULL,  -- JSON格式的完整状态
                    step_number INTEGER NOT NULL,
                    node_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES travel_sessions (session_id)
                )
            """)
            
            # 创建旅游信息表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS travel_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    destination TEXT,
                    days INTEGER,
                    budget REAL,
                    travel_date TEXT,
                    travelers TEXT,
                    requirements TEXT,  -- JSON格式的需求列表
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES travel_sessions (session_id)
                )
            """)
            
            # 创建查询结果缓存表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS query_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE NOT NULL,  -- 基于查询参数生成的唯一键
                    query_type TEXT NOT NULL,  -- flight, hotel, attractions
                    query_params TEXT NOT NULL,  -- JSON格式的查询参数
                    result_data TEXT NOT NULL,  -- JSON格式的查询结果
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,  -- 缓存过期时间
                    hit_count INTEGER DEFAULT 0  -- 缓存命中次数
                )
            """)
            
            # 创建费用分析表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cost_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    total_cost REAL NOT NULL,
                    flight_cost REAL DEFAULT 0,
                    hotel_cost REAL DEFAULT 0,
                    attraction_cost REAL DEFAULT 0,
                    food_cost REAL DEFAULT 0,
                    transport_cost REAL DEFAULT 0,
                    is_over_budget BOOLEAN DEFAULT FALSE,
                    budget_difference REAL DEFAULT 0,
                    optimization_applied BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES travel_sessions (session_id)
                )
            """)
            
            # 创建消息历史表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS message_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,  -- human, ai, system
                    content TEXT NOT NULL,
                    metadata TEXT,  -- JSON格式的额外信息
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES travel_sessions (session_id)
                )
            """)
            
            # 创建索引以提高查询性能
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON travel_sessions(status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_states_session ON travel_states(session_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON query_cache(cache_key)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_cache_type ON query_cache(query_type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON message_history(session_id)")
            
            await db.commit()
            print("✅ 数据库初始化完成")
    
    async def create_session(self, session_id: str, user_query: str) -> bool:
        """创建新的旅游规划会话"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO travel_sessions (session_id, user_query, status)
                    VALUES (?, ?, 'active')
                """, (session_id, user_query))
                await db.commit()
                print(f"✅ 创建会话: {session_id}")
                return True
        except Exception as e:
            print(f"❌ 创建会话失败: {e}")
            return False
    
    async def save_travel_state(self, session_id: str, state: TravelState, step_number: int, node_name: str = None) -> bool:
        """保存旅游状态到数据库"""
        try:
            # 将TravelState转换为可序列化的字典
            state_dict = dict(state)
            
            # 处理消息列表 - 转换为可序列化格式
            if 'messages' in state_dict and state_dict['messages']:
                messages_data = []
                for msg in state_dict['messages']:
                    msg_data = {
                        'type': msg.__class__.__name__,
                        'content': msg.content
                    }
                    if hasattr(msg, 'additional_kwargs'):
                        msg_data['additional_kwargs'] = msg.additional_kwargs
                    messages_data.append(msg_data)
                state_dict['messages'] = messages_data
            
            state_json = json.dumps(state_dict, ensure_ascii=False, default=str)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO travel_states (session_id, state_data, step_number, node_name)
                    VALUES (?, ?, ?, ?)
                """, (session_id, state_json, step_number, node_name))
                await db.commit()
                print(f"💾 保存状态: 步骤{step_number} - {node_name}")
                return True
        except Exception as e:
            print(f"❌ 保存状态失败: {e}")
            return False
    
    async def save_travel_info(self, session_id: str, travel_info: Dict[str, Any]) -> bool:
        """保存旅游基本信息"""
        try:
            requirements_json = json.dumps(travel_info.get('requirements', []), ensure_ascii=False)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 先删除旧记录，再插入新记录
                await db.execute("DELETE FROM travel_info WHERE session_id = ?", (session_id,))
                
                await db.execute("""
                    INSERT INTO travel_info 
                    (session_id, destination, days, budget, travel_date, travelers, requirements)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    travel_info.get('destination'),
                    travel_info.get('days'),
                    travel_info.get('budget'),
                    travel_info.get('travel_date'),
                    travel_info.get('travelers'),
                    requirements_json
                ))
                await db.commit()
                print(f"💾 保存旅游信息: {travel_info.get('destination')}")
                return True
        except Exception as e:
            print(f"❌ 保存旅游信息失败: {e}")
            return False
    
    async def save_query_cache(self, cache_key: str, query_type: str, query_params: Dict, result_data: Dict, expires_hours: int = 24) -> bool:
        """保存查询结果到缓存"""
        try:
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(hours=expires_hours)
            
            params_json = json.dumps(query_params, ensure_ascii=False)
            result_json = json.dumps(result_data, ensure_ascii=False)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO query_cache 
                    (cache_key, query_type, query_params, result_data, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (cache_key, query_type, params_json, result_json, expires_at.isoformat()))
                await db.commit()
                print(f"💾 缓存查询结果: {query_type} - {cache_key}")
                return True
        except Exception as e:
            print(f"❌ 保存缓存失败: {e}")
            return False
    
    async def get_query_cache(self, cache_key: str) -> Optional[Dict]:
        """从缓存获取查询结果"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT result_data, expires_at, hit_count 
                    FROM query_cache 
                    WHERE cache_key = ? AND expires_at > datetime('now')
                """, (cache_key,))
                row = await cursor.fetchone()
                
                if row:
                    result_data, expires_at, hit_count = row
                    
                    # 更新命中次数
                    await db.execute("""
                        UPDATE query_cache SET hit_count = hit_count + 1 
                        WHERE cache_key = ?
                    """, (cache_key,))
                    await db.commit()
                    
                    print(f"🎯 缓存命中: {cache_key} (第{hit_count + 1}次)")
                    return json.loads(result_data)
                
                return None
        except Exception as e:
            print(f"❌ 获取缓存失败: {e}")
            return None
    
    async def save_cost_analysis(self, session_id: str, cost_analysis: Dict[str, Any]) -> bool:
        """保存费用分析"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 先删除旧记录
                await db.execute("DELETE FROM cost_analysis WHERE session_id = ?", (session_id,))
                
                await db.execute("""
                    INSERT INTO cost_analysis 
                    (session_id, total_cost, flight_cost, hotel_cost, attraction_cost, 
                     food_cost, transport_cost, is_over_budget, budget_difference, optimization_applied)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    cost_analysis.get('total_cost', 0),
                    cost_analysis.get('flight_cost', 0),
                    cost_analysis.get('hotel_cost', 0),
                    cost_analysis.get('attraction_cost', 0),
                    cost_analysis.get('food_cost', 0),
                    cost_analysis.get('transport_cost', 0),
                    cost_analysis.get('is_over_budget', False),
                    cost_analysis.get('budget_difference', 0),
                    cost_analysis.get('optimization_applied', False)
                ))
                await db.commit()
                print(f"💾 保存费用分析: 总计{cost_analysis.get('total_cost', 0)}元")
                return True
        except Exception as e:
            print(f"❌ 保存费用分析失败: {e}")
            return False
    
    async def save_message(self, session_id: str, message_type: str, content: str, metadata: Dict = None) -> bool:
        """保存消息到历史记录"""
        try:
            metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO message_history (session_id, message_type, content, metadata)
                    VALUES (?, ?, ?, ?)
                """, (session_id, message_type, content, metadata_json))
                await db.commit()
                return True
        except Exception as e:
            print(f"❌ 保存消息失败: {e}")
            return False
    
    async def update_session_completion(self, session_id: str, final_itinerary: str, total_cost: float) -> bool:
        """更新会话完成状态"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE travel_sessions 
                    SET status = 'completed', is_completed = TRUE, 
                        final_itinerary = ?, total_cost = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                """, (final_itinerary, total_cost, session_id))
                await db.commit()
                print(f"✅ 会话完成: {session_id}")
                return True
        except Exception as e:
            print(f"❌ 更新会话状态失败: {e}")
            return False
    
    async def get_session_history(self, session_id: str) -> Optional[Dict]:
        """获取会话历史记录"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 获取会话基本信息
                cursor = await db.execute("""
                    SELECT user_query, status, final_itinerary, total_cost, created_at, updated_at
                    FROM travel_sessions WHERE session_id = ?
                """, (session_id,))
                session_row = await cursor.fetchone()
                
                if not session_row:
                    return None
                
                # 获取消息历史
                cursor = await db.execute("""
                    SELECT message_type, content, metadata, created_at
                    FROM message_history WHERE session_id = ?
                    ORDER BY created_at
                """, (session_id,))
                messages = await cursor.fetchall()
                
                # 获取旅游信息
                cursor = await db.execute("""
                    SELECT destination, days, budget, travel_date, travelers, requirements
                    FROM travel_info WHERE session_id = ?
                """, (session_id,))
                travel_info_row = await cursor.fetchone()
                
                return {
                    'session': {
                        'user_query': session_row[0],
                        'status': session_row[1],
                        'final_itinerary': session_row[2],
                        'total_cost': session_row[3],
                        'created_at': session_row[4],
                        'updated_at': session_row[5]
                    },
                    'messages': [
                        {
                            'type': msg[0],
                            'content': msg[1],
                            'metadata': json.loads(msg[2]) if msg[2] else {},
                            'created_at': msg[3]
                        } for msg in messages
                    ],
                    'travel_info': {
                        'destination': travel_info_row[0] if travel_info_row else None,
                        'days': travel_info_row[1] if travel_info_row else None,
                        'budget': travel_info_row[2] if travel_info_row else None,
                        'travel_date': travel_info_row[3] if travel_info_row else None,
                        'travelers': travel_info_row[4] if travel_info_row else None,
                        'requirements': json.loads(travel_info_row[5]) if travel_info_row and travel_info_row[5] else []
                    } if travel_info_row else None
                }
        except Exception as e:
            print(f"❌ 获取会话历史失败: {e}")
            return None
    
    async def cleanup_expired_cache(self) -> int:
        """清理过期的缓存记录"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    DELETE FROM query_cache WHERE expires_at < datetime('now')
                """)
                await db.commit()
                deleted_count = cursor.rowcount
                print(f"🧹 清理过期缓存: {deleted_count}条记录")
                return deleted_count
        except Exception as e:
            print(f"❌ 清理缓存失败: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT 
                        COUNT(*) as total_cache,
                        SUM(hit_count) as total_hits,
                        COUNT(CASE WHEN expires_at > datetime('now') THEN 1 END) as active_cache,
                        COUNT(CASE WHEN expires_at <= datetime('now') THEN 1 END) as expired_cache
                    FROM query_cache
                """)
                row = await cursor.fetchone()
                
                return {
                    'total_cache': row[0],
                    'total_hits': row[1] or 0,
                    'active_cache': row[2],
                    'expired_cache': row[3]
                }
        except Exception as e:
            print(f"❌ 获取缓存统计失败: {e}")
            return {}
    
    async def get_latest_state(self, session_id: str) -> Optional[Dict]:
        """获取会话的最新状态 - 用于中断恢复"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT state_data, step_number, node_name, created_at
                    FROM travel_states 
                    WHERE session_id = ?
                    ORDER BY step_number DESC, created_at DESC
                    LIMIT 1
                """, (session_id,))
                row = await cursor.fetchone()
                
                if row:
                    import json
                    from langchain_core.messages import HumanMessage, AIMessage
                    
                    state_data = json.loads(row[0])
                    
                    # 恢复消息对象
                    if 'messages' in state_data and state_data['messages']:
                        restored_messages = []
                        for msg_data in state_data['messages']:
                            if msg_data['type'] == 'HumanMessage':
                                restored_messages.append(HumanMessage(content=msg_data['content']))
                            elif msg_data['type'] == 'AIMessage':
                                additional_kwargs = msg_data.get('additional_kwargs', {})
                                restored_messages.append(AIMessage(
                                    content=msg_data['content'],
                                    additional_kwargs=additional_kwargs
                                ))
                        state_data['messages'] = restored_messages
                    
                    return {
                        'state_data': state_data,
                        'step_number': row[1],
                        'node_name': row[2],
                        'created_at': row[3]
                    }
                return None
        except Exception as e:
            print(f"❌ 获取最新状态失败: {e}")
            return None
    
    async def list_active_sessions(self) -> List[Dict]:
        """列出所有活跃的会话 - 用于选择恢复会话"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT session_id, user_query, created_at, updated_at, 
                           is_completed, final_itinerary
                    FROM travel_sessions 
                    WHERE status = 'active'
                    ORDER BY updated_at DESC
                """)
                rows = await cursor.fetchall()
                
                sessions = []
                for row in rows:
                    # 获取最新步骤信息
                    step_cursor = await db.execute("""
                        SELECT MAX(step_number), node_name
                        FROM travel_states 
                        WHERE session_id = ?
                    """, (row[0],))
                    step_row = await step_cursor.fetchone()
                    
                    sessions.append({
                        'session_id': row[0],
                        'user_query': row[1],
                        'created_at': row[2],
                        'updated_at': row[3],
                        'is_completed': bool(row[4]),
                        'final_itinerary': row[5],
                        'latest_step': step_row[0] if step_row[0] else 0,
                        'latest_node': step_row[1] if step_row[1] else 'unknown'
                    })
                
                return sessions
        except Exception as e:
            print(f"❌ 获取活跃会话失败: {e}")
            return []

# 全局数据库实例
travel_db = TravelDatabase()

# 工具函数
def generate_cache_key(query_type: str, params: Dict) -> str:
    """生成缓存键"""
    import hashlib
    params_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
    hash_obj = hashlib.md5(f"{query_type}:{params_str}".encode('utf-8'))
    return hash_obj.hexdigest()

async def init_database():
    """初始化数据库（外部调用接口）"""
    await travel_db.init_database()

if __name__ == "__main__":
    # 测试数据库初始化
    asyncio.run(init_database())