import time
from typing import List, Dict, Optional, Tuple
from Common.logger import Logger
from Common.constants import ROOM_STATUSES, PIECE_COLORS, GAME_MODES
from Common.data_utils import DataUtils
from Common.config import Config
from Server.room import Room

class RoomManager:
    """房间管理器（管理所有联机房间）"""
    def __init__(self):
        self.config = Config.get_instance()
        self.logger = Logger.get_instance()
        self.rooms: Dict[str, Room] = {}  # 房间ID -> 房间实例映射
        self.room_counter = 1000  # 房间ID计数器（从1000开始）
        self.lock = threading.Lock()  # 线程安全锁
    
    def create_room(self, host_id: str, host_nickname: str, room_name: str = "默认房间") -> Optional[str]:
        """创建房间
        Args:
            host_id: 主机用户ID
            host_nickname: 主机昵称
            room_name: 房间名称
        Returns:
            房间ID/None
        """
        with self.lock:
            # 生成房间ID
            room_id = str(self.room_counter)
            self.room_counter += 1
            
            # 初始化棋盘状态
            board_size = self.config.board_size
            board = [[PIECE_COLORS['EMPTY'] for _ in range(board_size)] for _ in range(board_size)]
            board_state = DataUtils.board_to_str(board)
            
            # 创建房间实例
            room = Room(
                room_id=room_id,
                host_id=host_id,
                host_nickname=host_nickname,
                room_name=room_name,
                board_state=board_state,
                board_size=board_size
            )
            
            # 添加到房间列表
            self.rooms[room_id] = room
            self.logger.info(f"创建房间成功：ID={room_id}，名称={room_name}，主机={host_id}")
            return room_id
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """根据房间ID获取房间实例"""
        with self.lock:
            return self.rooms.get(room_id)
    
    def join_room(self, room_id: str, user_id: str, user_nickname: str) -> Tuple[bool, Optional[str]]:
        """加入房间
        Args:
            room_id: 房间ID
            user_id: 加入用户ID
            user_nickname: 加入用户昵称
        Returns:
            (是否成功, 消息/None)
        """
        with self.lock:
            # 检查房间是否存在
            room = self.rooms.get(room_id)
            if not room:
                return False, "房间不存在"
            
            # 检查房间是否已满
            if room.guest_id is not None:
                return False, "房间已满，无法加入"
            
            # 检查是否是主机自己加入
            if user_id == room.host_id:
                return False, "不能加入自己创建的房间"
            
            # 加入房间
            room.guest_id = user_id
            room.guest_nickname = user_nickname
            room.room_status = ROOM_STATUSES['PLAYING']  # 房间状态改为游戏中
            room.current_player = room.host_id  # 主机先落子（黑方）
            room.update_time = time.time()
            
            self.logger.info(f"用户 {user_id} 加入房间 {room_id}，房间状态变为游戏中")
            return True, None
    
    def leave_room(self, room_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
        """离开房间
        Args:
            room_id: 房间ID
            user_id: 离开用户ID
        Returns:
            (是否成功, 消息/None)
        """
        with self.lock:
            # 检查房间是否存在
            room = self.rooms.get(room_id)
            if not room:
                return False, "房间不存在"
            
            # 检查用户是否在房间中
            if user_id not in [room.host_id, room.guest_id]:
                return False, "你不在这个房间中"
            
            # 处理离开逻辑
            if user_id == room.host_id:
                # 主机离开，房间解散
                del self.rooms[room_id]
                self.logger.info(f"主机 {user_id} 离开房间 {room_id}，房间已解散")
            else:
                # 访客离开，房间状态改为等待
                room.guest_id = None
                room.guest_nickname = None
                room.room_status = ROOM_STATUSES['WAITING']
                room.current_player = room.host_id
                room.update_time = time.time()
                self.logger.info(f"访客 {user_id} 离开房间 {room_id}，房间状态变为等待")
            
            return True, None
    
    def clean_empty_rooms(self):
        """清理空房间（无访客且超过5分钟未活动）"""
        with self.lock:
            current_time = time.time()
            to_remove = []
            
            for room_id, room in self.rooms.items():
                # 空房间（无访客）且超过5分钟未更新
                if room.guest_id is None and current_time - room.update_time > 300:
                    to_remove.append(room_id)
            
            # 移除空房间
            for room_id in to_remove:
                del self.rooms[room_id]
                self.logger.info(f"清理空房间：{room_id}")
    
    def get_room_list(self) -> List[Dict]:
        """获取房间列表（供客户端查询）"""
        with self.lock:
            room_list = []
            for room in self.rooms.values():
                room_list.append({
                    'room_id': room.room_id,
                    'room_name': room.room_name,
                    'host_nickname': room.host_nickname,
                    'guest_nickname': room.guest_nickname or '无',
                    'status': room.room_status,
                    'player_count': 2 if room.guest_id else 1,
                    'update_time': room.update_time
                })
            # 按更新时间排序（最新的在前）
            room_list.sort(key=lambda x: x['update_time'], reverse=True)
            return room_list