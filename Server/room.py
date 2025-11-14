import time
from typing import Dict, List, Tuple, Optional
from Common.constants import ROOM_STATUSES, PIECE_COLORS, EVAL_WEIGHTS
from Common.data_utils import DataUtils
from Common.logger import Logger
from Server.client_handler import ClientHandler

class Room:
    """联机对战房间"""
    def __init__(
        self,
        room_id: str,
        host_id: str,
        host_nickname: str,
        room_name: str,
        board_state: str,
        board_size: int = 15
    ):
        self.room_id = room_id  # 房间ID
        self.host_id = host_id  # 主机用户ID
        self.host_nickname = host_nickname  # 主机昵称
        self.guest_id = None  # 访客用户ID（None表示空）
        self.guest_nickname = None  # 访客昵称
        self.room_name = room_name  # 房间名称
        self.room_status = ROOM_STATUSES['WAITING']  # 房间状态
        
        # 游戏相关
        self.board_state = board_state  # 棋盘状态（字符串格式）
        self.board_size = board_size  # 棋盘尺寸
        self.move_history = []  # 落子历史（[(x,y,user_id,timestamp), ...]）
        self.current_player = host_id  # 当前回合玩家ID
        self.winner_id = None  # 获胜者ID（None表示未结束）
        
        # 时间相关
        self.create_time = time.time()  # 创建时间
        self.update_time = time.time()  # 最后更新时间
        
        # 日志
        self.logger = Logger.get_instance()
    
    def make_move(self, user_id: str, x: int, y: int) -> Tuple[bool, Dict]:
        """执行落子
        Args:
            user_id: 落子用户ID
            x: 落子X坐标
            y: 落子Y坐标
        Returns:
            (是否成功, 结果字典)
        """
        # 转换棋盘状态
        board = DataUtils.str_to_board(self.board_state)
        
        # 检查落子位置
        if board[x][y] != PIECE_COLORS['EMPTY']:
            return False, {'success': False, 'message': '该位置已被占用'}
        
        # 确定落子颜色（主机黑，访客白）
        color = PIECE_COLORS['BLACK'] if user_id == self.host_id else PIECE_COLORS['WHITE']
        
        # 执行落子
        board[x][y] = color
        
        # 更新棋盘状态和落子历史
        self.board_state = DataUtils.board_to_str(board)
        self.move_history.append({
            'x': x,
            'y': y,
            'user_id': user_id,
            'nickname': self.host_nickname if user_id == self.host_id else self.guest_nickname,
            'color': color,
            'timestamp': time.time()
        })
        self.update_time = time.time()
        
        # 检查游戏是否结束
        win, win_line = self._check_win(board, color)
        game_result = None
        if win:
            self.winner_id = user_id
            self.room_status = ROOM_STATUSES['ENDED']
            game_result = {
                'result': 'win',
                'winner_id': user_id,
                'winner_nickname': self.host_nickname if user_id == self.host_id else self.guest_nickname,
                'win_line': win_line
            }
        elif self._is_board_full(board):
            self.room_status = ROOM_STATUSES['ENDED']
            game_result = {'result': 'draw', 'winner_id': None}
        
        # 切换当前玩家
        if not game_result:
            self.current_player = self.guest_id if user_id == self.host_id else self.host_id
        
        return True, {
            'success': True,
            'game_result': game_result,
            'win_line': win_line
        }
    
    def _check_win(self, board: List[List[int]], color: int) -> Tuple[bool, List[Tuple[int, int]]]:
        """检查是否获胜"""
        # 横向
        for i in range(self.board_size):
            for j in range(self.board_size - 4):
                if all(board[i][j + k] == color for k in range(5)):
                    return True, [(i, j + k) for k in range(5)]
        
        # 纵向
        for j in range(self.board_size):
            for i in range(self.board_size - 4):
                if all(board[i + k][j] == color for k in range(5)):
                    return True, [(i + k, j) for k in range(5)]
        
        # 正对角线
        for i in range(self.board_size - 4):
            for j in range(self.board_size - 4):
                if all(board[i + k][j + k] == color for k in range(5)):
                    return True, [(i + k, j + k) for k in range(5)]
        
        # 反对角线
        for i in range(self.board_size - 4):
            for j in range(4, self.board_size):
                if all(board[i + k][j - k] == color for k in range(5)):
                    return True, [(i + k, j - k) for k in range(5)]
        
        return False, []
    
    def _is_board_full(self, board: List[List[int]]) -> bool:
        """检查棋盘是否下满"""
        for i in range(self.board_size):
            for j in range(self.board_size):
                if board[i][j] == PIECE_COLORS['EMPTY']:
                    return False
        return True
    
    def broadcast_message(self, sender_id: str, msg_type: str, data: Dict):
        """广播消息给房间内所有成员"""
        from Server.main_server import Server
        server = Server.get_instance()  # 假设Server是单例
        
        # 发送给主机
        host_handler = server.get_client_by_user_id(self.host_id)
        if host_handler and host_handler.user_id != sender_id:
            host_handler.send_message(msg_type, data)
        
        # 发送给访客
        if self.guest_id:
            guest_handler = server.get_client_by_user_id(self.guest_id)
            if guest_handler and guest_handler.user_id != sender_id:
                guest_handler.send_message(msg_type, data)
    
    def reset_game(self) -> bool:
        """重置游戏（重新开始）"""
        if self.room_status != ROOM_STATUSES['ENDED']:
            self.logger.error(f"房间 {self.room_id} 未结束，无法重置游戏")
            return False
        
        # 初始化棋盘
        board = [[PIECE_COLORS['EMPTY'] for _ in range(self.board_size)] for _ in range(self.board_size)]
        self.board_state = DataUtils.board_to_str(board)
        
        # 重置游戏状态
        self.move_history = []
        self.current_player = self.host_id
        self.winner_id = None
        self.room_status = ROOM_STATUSES['PLAYING']
        self.update_time = time.time()
        
        self.logger.info(f"房间 {self.room_id} 游戏重置成功")
        return True