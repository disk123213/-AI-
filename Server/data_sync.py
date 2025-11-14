import json
import numpy as np
from typing import List, Dict, Tuple
from Common.constants import PIECE_COLORS
from Common.data_utils import DataUtils
from Common.logger import Logger
from Common.error_handler import ServerError

class DataSync:
    """数据同步工具（确保客户端与服务器数据一致性）"""
    def __init__(self, board_size: int = 15):
        self.board_size = board_size
        self.logger = Logger.get_instance()
    
    def sync_board_state(self, client_board_str: str, server_board_str: str) -> Tuple[bool, str, List[Dict]]:
        """同步棋盘状态
        Args:
            client_board_str: 客户端棋盘状态字符串
            server_board_str: 服务器棋盘状态字符串
        Returns:
            (是否一致, 权威棋盘状态字符串, 差异落子列表)
        """
        try:
            # 转换为棋盘状态
            client_board = DataUtils.str_to_board(client_board_str)
            server_board = DataUtils.str_to_board(server_board_str)
            
            # 检查棋盘尺寸
            if len(client_board) != self.board_size or len(server_board) != self.board_size:
                raise ServerError("棋盘尺寸不一致", 3301)
            
            # 找出差异
            diff_moves = []
            for i in range(self.board_size):
                for j in range(self.board_size):
                    if client_board[i][j] != server_board[i][j]:
                        # 以服务器状态为准
                        color = server_board[i][j]
                        diff_moves.append({
                            'x': i,
                            'y': j,
                            'color': color,
                            'source': 'server'  # 权威来源
                        })
            
            # 判断是否一致
            is_consistent = len(diff_moves) == 0
            return is_consistent, DataUtils.board_to_str(server_board), diff_moves
        except Exception as e:
            self.logger.error(f"同步棋盘状态失败: {str(e)}")
            # 返回服务器状态作为权威
            return False, server_board_str, []
    
    def validate_move_history(self, client_history: List[Dict], server_history: List[Dict]) -> Tuple[bool, List[Dict]]:
        """验证落子历史
        Args:
            client_history: 客户端落子历史
            server_history: 服务器落子历史
        Returns:
            (是否一致, 权威落子历史)
        """
        # 检查长度
        if len(client_history) != len(server_history):
            self.logger.warning(f"落子历史长度不一致：客户端{len(client_history)}步，服务器{len(server_history)}步")
            return False, server_history
        
        # 检查每一步
        for i, (client_move, server_move) in enumerate(zip(client_history, server_history)):
            if (client_move.get('x') != server_move.get('x') or
                client_move.get('y') != server_move.get('y') or
                client_move.get('user_id') != server_move.get('user_id')):
                self.logger.warning(f"第{i+1}步落子不一致：客户端{client_move}，服务器{server_move}")
                return False, server_history
        
        return True, server_history
    
    def generate_sync_package(self, board_str: str, move_history: List[Dict], current_player: str) -> Dict:
        """生成同步数据包"""
        return {
            'board_state': board_str,
            'move_history': move_history,
            'current_player': current_player,
            'timestamp': json.dumps(time.time()),
            'signature': self._generate_signature(board_str, move_history)
        }
    
    def _generate_signature(self, board_str: str, move_history: List[Dict]) -> str:
        """生成数据签名（防止篡改）"""
        import hashlib
        # 拼接数据
        data_str = board_str + json.dumps(move_history, sort_keys=True)
        # 生成MD5签名
        return hashlib.md5(data_str.encode('utf-8')).hexdigest()
    
    def verify_signature(self, sync_package: Dict) -> bool:
        """验证数据签名"""
        try:
            board_str = sync_package.get('board_state', '')
            move_history = sync_package.get('move_history', [])
            signature = sync_package.get('signature', '')
            
            # 重新生成签名
            expected_signature = self._generate_signature(board_str, move_history)
            return signature == expected_signature
        except Exception as e:
            self.logger.error(f"验证签名失败: {str(e)}")
            return False