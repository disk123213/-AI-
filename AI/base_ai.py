import abc
import numpy as np
from typing import List, Tuple, Dict, Optional, Callable
from Common.constants import PIECE_COLORS, AI_LEVELS, EVAL_WEIGHTS
from Common.config import Config
from Common.logger import Logger
from Common.error_handler import AIError

class BaseAI(metaclass=abc.ABCMeta):
    """AI基础抽象类（所有AI的统一接口）"""
    def __init__(self, color: int, level: str = AI_LEVELS['HARD']):
        self.color = color  # AI棋子颜色
        self.opponent_color = PIECE_COLORS['WHITE'] if color == PIECE_COLORS['BLACK'] else PIECE_COLORS['BLACK']
        self.level = level  # AI难度
        self.board_size = Config.get_instance().board_size  # 棋盘尺寸
        self.logger = Logger.get_instance()  # 日志工具
        
        # 思考过程回调（用于可视化）
        self.thinking_callback: Optional[Callable[[Dict], None]] = None
        
        # 性能优化参数
        self.max_depth = self._get_max_depth_by_level()  # 最大搜索深度
        self.prune_threshold = 0.8  # 剪枝阈值（0-1）
        self.cache_enabled = True  # 是否启用缓存
        self.transposition_table = {}  # 置换表（缓存棋盘状态评估结果）
        
    def _get_max_depth_by_level(self) -> int:
        """根据难度获取最大搜索深度"""
        depth_map = {
            AI_LEVELS['EASY']: 3,
            AI_LEVELS['MEDIUM']: 4,
            AI_LEVELS['HARD']: 5,
            AI_LEVELS['EXPERT']: 6
        }
        return depth_map.get(self.level, 5)
    
    @abc.abstractmethod
    def move(self, board: List[List[int]], thinking_callback: Optional[Callable[[Dict], None]] = None) -> Tuple[int, int]:
        """核心方法：计算最佳落子位置
        Args:
            board: 当前棋盘状态
            thinking_callback: 思考过程回调函数（传递可视化数据）
        Returns:
            (x, y): 最佳落子坐标
        """
        pass
    
    def set_thinking_callback(self, callback: Callable[[Dict], None]):
        """设置思考过程回调"""
        self.thinking_callback = callback
    
    def _notify_thinking(self, data: Dict):
        """通知思考过程（调用回调）"""
        if self.thinking_callback:
            self.thinking_callback(data)
    
    def _get_empty_positions(self, board: List[List[int]]) -> List[Tuple[int, int]]:
        """获取所有空位置"""
        empty_pos = []
        for i in range(self.board_size):
            for j in range(self.board_size):
                if board[i][j] == PIECE_COLORS['EMPTY']:
                    empty_pos.append((i, j))
        return empty_pos
    
    def _is_win(self, board: List[List[int]], color: int) -> Tuple[bool, List[Tuple[int, int]]]:
        """判断某颜色是否获胜
        Returns:
            (是否获胜, 获胜线坐标列表)
        """
        # 检查横向
        for i in range(self.board_size):
            for j in range(self.board_size - 4):
                if all(board[i][j + k] == color for k in range(5)):
                    return True, [(i, j + k) for k in range(5)]
        
        # 检查纵向
        for j in range(self.board_size):
            for i in range(self.board_size - 4):
                if all(board[i + k][j] == color for k in range(5)):
                    return True, [(i + k, j) for k in range(5)]
        
        # 检查正对角线
        for i in range(self.board_size - 4):
            for j in range(self.board_size - 4):
                if all(board[i + k][j + k] == color for k in range(5)):
                    return True, [(i + k, j + k) for k in range(5)]
        
        # 检查反对角线
        for i in range(self.board_size - 4):
            for j in range(4, self.board_size):
                if all(board[i + k][j - k] == color for k in range(5)):
                    return True, [(i + k, j - k) for k in range(5)]
        
        return False, []
    
    def _is_board_full(self, board: List[List[int]]) -> bool:
        """判断棋盘是否下满"""
        for i in range(self.board_size):
            for j in range(self.board_size):
                if board[i][j] == PIECE_COLORS['EMPTY']:
                    return False
        return True
    
    def _copy_board(self, board: List[List[int]]) -> List[List[int]]:
        """复制棋盘（避免修改原棋盘）"""
        return [row.copy() for row in board]
    
    def _get_board_key(self, board: List[List[int]]) -> Tuple[tuple, int]:
        """获取棋盘状态的唯一键（用于置换表）"""
        return (tuple(tuple(row) for row in board), self.color)
    
    def _cache_evaluation(self, board: List[List[int]], score: float, depth: int):
        """缓存棋盘评估结果"""
        if not self.cache_enabled:
            return
        key = self._get_board_key(board)
        self.transposition_table[key] = (score, depth)
    
    def _get_cached_evaluation(self, board: List[List[int]], depth: int) -> Optional[float]:
        """获取缓存的棋盘评估结果"""
        if not self.cache_enabled:
            return None
        key = self._get_board_key(board)
        if key in self.transposition_table:
            cached_score, cached_depth = self.transposition_table[key]
            # 只有缓存的深度大于等于当前搜索深度时才使用
            if cached_depth >= depth:
                return cached_score
        return None
    
    def clear_cache(self):
        """清空置换表缓存"""
        self.transposition_table.clear()
    
    def set_level(self, level: str):
        """设置AI难度"""
        self.level = level
        self.max_depth = self._get_max_depth_by_level()
        self.logger.info(f"AI难度已设置为: {level}，最大搜索深度: {self.max_depth}")
    
    @abc.abstractmethod
    def evaluate(self, board: List[List[int]]) -> float:
        """评估棋盘得分（正数对AI有利，负数对对手有利）"""
        pass
    
    def _get_pattern_score(self, pattern: List[int], color: int) -> float:
        """根据棋型获取得分"""
        opponent = PIECE_COLORS['WHITE'] if color == PIECE_COLORS['BLACK'] else PIECE_COLORS['BLACK']
        empty = PIECE_COLORS['EMPTY']
        
        # 五连
        if pattern.count(color) == 5:
            return EVAL_WEIGHTS['FIVE']
        # 活四（两端为空）
        elif pattern.count(color) == 4 and pattern[0] == empty and pattern[-1] == empty:
            return EVAL_WEIGHTS['FOUR']
        # 冲四（一端为空，一端为自己或边界）
        elif pattern.count(color) == 4:
            return EVAL_WEIGHTS['BLOCKED_FOUR']
        # 活三（两端为空，中间三个连续）
        elif pattern.count(color) == 3 and pattern[0] == empty and pattern[-1] == empty:
            return EVAL_WEIGHTS['THREE']
        # 冲三（一端为空）
        elif pattern.count(color) == 3:
            return EVAL_WEIGHTS['BLOCKED_THREE']
        # 活二
        elif pattern.count(color) == 2 and pattern[0] == empty and pattern[-1] == empty:
            return EVAL_WEIGHTS['TWO']
        # 冲二
        elif pattern.count(color) == 2:
            return EVAL_WEIGHTS['BLOCKED_TWO']
        # 活一
        elif pattern.count(color) == 1 and pattern[0] == empty and pattern[-1] == empty:
            return EVAL_WEIGHTS['ONE']
        
        return 0.0

class AIFactory:
    """AI工厂类（创建不同类型的AI实例）"""
    @staticmethod
    def create_ai(ai_type: str, color: int, level: str = AI_LEVELS['HARD']) -> BaseAI:
        """创建AI实例
        Args:
            ai_type: AI类型（minimax, mcts, nn, minimax+mcts, nn+mcts）
            color: AI棋子颜色
            level: AI难度
        Returns:
            BaseAI: AI实例
        """
        try:
            if ai_type == 'minimax':
                from AI.minimax_ai import MinimaxAI
                return MinimaxAI(color, level)
            elif ai_type == 'mcts':
                from AI.mcts_ai import MCTSAI
                return MCTSAI(color, level)
            elif ai_type == 'nn':
                from AI.nn_ai import NNAI
                return NNAI(color, level)
            elif ai_type == 'minimax+mcts':
                from AI.minimax_mcts_ai import MinimaxMCTSAI
                return MinimaxMCTSAI(color, level)
            elif ai_type == 'nn+mcts':
                from AI.nn_mcts_ai import NNMCTSAI
                return NNMCTSAI(color, level)
            else:
                raise AIError(f"不支持的AI类型: {ai_type}", 4001)
        except ImportError as e:
            raise AIError(f"加载AI类型失败: {str(e)}", 4002)
        except Exception as e:
            raise AIError(f"创建AI实例失败: {str(e)}", 4003)