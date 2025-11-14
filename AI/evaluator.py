import numpy as np
from typing import List, Tuple, Dict
from Common.constants import PIECE_COLORS, EVAL_WEIGHTS
from Common.config import Config
from Common.logger import Logger

class BoardEvaluator:
    """棋盘评估器（独立的评估工具，供所有AI使用）"""
    def __init__(self, board_size: int = 15):
        self.board_size = board_size
        self.logger = Logger.get_instance()
        
        # 棋型模板（用于快速匹配）
        self.pattern_templates = self._init_pattern_templates()
        
        # 位置权重（中心位置权重更高）
        self.position_weights = self._init_position_weights()
    
    def _init_pattern_templates(self) -> Dict[str, List[List[int]]]:
        """初始化棋型模板"""
        empty = PIECE_COLORS['EMPTY']
        return {
            # 五连（已获胜）
            'five': [[1, 1, 1, 1, 1]],
            # 活四（两端为空）
            'live_four': [[0, 1, 1, 1, 1, 0]],
            # 冲四（一端为空）
            'blocked_four': [
                [0, 1, 1, 1, 1, 2],
                [2, 1, 1, 1, 1, 0],
                [0, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 0, 1]
            ],
            # 活三（两端为空）
            'live_three': [[0, 1, 1, 1, 0]],
            # 冲三（一端为空）
            'blocked_three': [
                [0, 1, 1, 1, 2],
                [2, 1, 1, 1, 0],
                [0, 1, 1, 1, 1],
                [1, 1, 1, 0, 1]
            ],
            # 活二（两端为空）
            'live_two': [[0, 1, 1, 0]],
            # 冲二（一端为空）
            'blocked_two': [
                [0, 1, 1, 2],
                [2, 1, 1, 0],
                [0, 1, 1, 1],
                [1, 1, 0, 1]
            ]
        }
    
    def _init_position_weights(self) -> np.ndarray:
        """初始化位置权重矩阵（中心位置权重高）"""
        weights = np.ones((self.board_size, self.board_size), dtype=np.float32)
        center = self.board_size // 2
        max_distance = np.sqrt(2) * center  # 对角线最大距离
        
        for i in range(self.board_size):
            for j in range(self.board_size):
                # 计算到中心的距离
                distance = np.sqrt((i - center)**2 + (j - center)**2)
                # 距离越近，权重越高（0.5-1.5之间）
                weights[i][j] = 1.5 - (distance / max_distance)
        return weights
    
    def _get_line_segments(self, board: List[List[int]], x: int, y: int) -> List[List[int]]:
        """获取以(x,y)为中心的所有线段（横、竖、两个对角线）"""
        segments = []
        board_np = np.array(board)
        
        # 横向线段（长度9，中心为(x,y)）
        if y - 4 >= 0 and y + 4 < self.board_size:
            segments.append(board_np[x, y-4:y+5].tolist())
        # 纵向线段
        if x - 4 >= 0 and x + 4 < self.board_size:
            segments.append(board_np[x-4:x+5, y].tolist())
        # 正对角线线段
        if x - 4 >= 0 and x + 4 < self.board_size and y - 4 >= 0 and y + 4 < self.board_size:
            diagonal = [board_np[x - 4 + k][y - 4 + k] for k in range(9)]
            segments.append(diagonal)
        # 反对角线线段
        if x - 4 >= 0 and x + 4 < self.board_size and y + 4 < self.board_size and y - 4 >= 0:
            diagonal = [board_np[x - 4 + k][y + 4 - k] for k in range(9)]
            segments.append(diagonal)
        
        return segments
    
    def _match_pattern(self, segment: List[int], color: int) -> Tuple[str, float]:
        """匹配棋型并返回得分"""
        opponent = PIECE_COLORS['WHITE'] if color == PIECE_COLORS['BLACK'] else PIECE_COLORS['BLACK']
        # 将线段中的颜色替换为1（自己）、2（对手）、0（空）
        normalized = [1 if c == color else 2 if c == opponent else 0 for c in segment]
        
        # 检查五连
        for i in range(len(normalized) - 4):
            sub = normalized[i:i+5]
            if sub == [1, 1, 1, 1, 1]:
                return 'five', EVAL_WEIGHTS['FIVE']
        
        # 检查活四
        for i in range(len(normalized) - 5):
            sub = normalized[i:i+6]
            if sub == [0, 1, 1, 1, 1, 0]:
                return 'live_four', EVAL_WEIGHTS['FOUR']
        
        # 检查冲四
        blocked_four_patterns = [
            [0, 1, 1, 1, 1, 2],
            [2, 1, 1, 1, 1, 0],
            [0, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 0, 1]
        ]
        for pattern in blocked_four_patterns:
            pattern_len = len(pattern)
            for i in range(len(normalized) - pattern_len + 1):
                if normalized[i:i+pattern_len] == pattern:
                    return 'blocked_four', EVAL_WEIGHTS['BLOCKED_FOUR']
        
        # 检查活三
        for i in range(len(normalized) - 4):
            sub = normalized[i:i+5]
            if sub == [0, 1, 1, 1, 0]:
                return 'live_three', EVAL_WEIGHTS['THREE']
        
        # 检查冲三
        blocked_three_patterns = [
            [0, 1, 1, 1, 2],
            [2, 1, 1, 1, 0],
            [0, 1, 1, 1, 1],
            [1, 1, 1, 0, 1]
        ]
        for pattern in blocked_three_patterns:
            pattern_len = len(pattern)
            for i in range(len(normalized) - pattern_len + 1):
                if normalized[i:i+pattern_len] == pattern:
                    return 'blocked_three', EVAL_WEIGHTS['BLOCKED_THREE']
        
        # 检查活二
        for i in range(len(normalized) - 3):
            sub = normalized[i:i+4]
            if sub == [0, 1, 1, 0]:
                return 'live_two', EVAL_WEIGHTS['TWO']
        
        # 检查冲二
        blocked_two_patterns = [
            [0, 1, 1, 2],
            [2, 1, 1, 0],
            [0, 1, 1, 1],
            [1, 1, 0, 1]
        ]
        for pattern in blocked_two_patterns:
            pattern_len = len(pattern)
            for i in range(len(normalized) - pattern_len + 1):
                if normalized[i:i+pattern_len] == pattern:
                    return 'blocked_two', EVAL_WEIGHTS['BLOCKED_TWO']
        
        # 活一
        for i in range(len(normalized) - 2):
            sub = normalized[i:i+3]
            if sub == [0, 1, 0]:
                return 'live_one', EVAL_WEIGHTS['ONE']
        
        return 'none', 0.0
    
    def evaluate_position(self, board: List[List[int]], x: int, y: int, color: int) -> float:
        """评估单个位置的得分"""
        if board[x][y] != PIECE_COLORS['EMPTY']:
            return 0.0
        
        # 模拟落子
        temp_board = [row.copy() for row in board]
        temp_board[x][y] = color
        
        # 获取所有线段
        segments = self._get_line_segments(temp_board, x, y)
        
        # 匹配棋型并计算得分
        total_score = 0.0
        for segment in segments:
            pattern, score = self._match_pattern(segment, color)
            total_score += score
        
        # 乘以位置权重
        total_score *= self.position_weights[x][y]
        
        return total_score
    
    def evaluate_board(self, board: List[List[int]], ai_color: int) -> float:
        """评估整个棋盘的得分（对AI有利为正，对手有利为负）"""
        opponent_color = PIECE_COLORS['WHITE'] if ai_color == PIECE_COLORS['BLACK'] else PIECE_COLORS['BLACK']
        
        # 检查是否有获胜者
        ai_win, _ = self._is_win(board, ai_color)
        if ai_win:
            return EVAL_WEIGHTS['FIVE'] * 2
        
        opponent_win, _ = self._is_win(board, opponent_color)
        if opponent_win:
            return -EVAL_WEIGHTS['FIVE'] * 2
        
        # 遍历所有空位置，计算得分
        total_score = 0.0
        for i in range(self.board_size):
            for j in range(self.board_size):
                if board[i][j] == PIECE_COLORS['EMPTY']:
                    # 计算AI落子得分
                    ai_score = self.evaluate_position(board, i, j, ai_color)
                    # 计算对手落子得分（取反）
                    opponent_score = -self.evaluate_position(board, i, j, opponent_color)
                    # 总得分
                    total_score += ai_score + opponent_score
        
        return total_score
    
    def _is_win(self, board: List[List[int]], color: int) -> Tuple[bool, List[Tuple[int, int]]]:
        """判断是否获胜（同BaseAI，但这里用于独立评估）"""
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
    
    def get_key_moves(self, board: List[List[int]], ai_color: int, top_k: int = 5) -> List[Tuple[int, int, float]]:
        """获取关键落子（得分最高的top_k个位置）"""
        key_moves = []
        for i in range(self.board_size):
            for j in range(self.board_size):
                if board[i][j] == PIECE_COLORS['EMPTY']:
                    score = self.evaluate_position(board, i, j, ai_color)
                    key_moves.append((i, j, score))
        
        # 按得分降序排序，取前top_k
        key_moves.sort(key=lambda x: x[2], reverse=True)
        return key_moves[:top_k]
    
    def analyze_board(self, board: List[List[int]], ai_color: int) -> Dict:
        """生成棋盘分析报告"""
        opponent_color = PIECE_COLORS['WHITE'] if ai_color == PIECE_COLORS['BLACK'] else PIECE_COLORS['BLACK']
        
        # 获取关键落子
        ai_key_moves = self.get_key_moves(board, ai_color, 3)
        opponent_key_moves = self.get_key_moves(board, opponent_color, 3)
        
        # 评估整体局势
        total_score = self.evaluate_board(board, ai_color)
        situation = ""
        if total_score > EVAL_WEIGHTS['FOUR']:
            situation = "AI优势明显"
        elif total_score > EVAL_WEIGHTS['THREE']:
            situation = "AI略有优势"
        elif total_score < -EVAL_WEIGHTS['FOUR']:
            situation = "对手优势明显"
        elif total_score < -EVAL_WEIGHTS['THREE']:
            situation = "对手略有优势"
        else:
            situation = "局势均衡"
        
        # 检查潜在威胁
        threats = []
        for i, j, score in opponent_key_moves:
            if score >= EVAL_WEIGHTS['FOUR']:
                threats.append(f"对手在({i},{j})位置有冲四威胁")
            elif score >= EVAL_WEIGHTS['THREE']:
                threats.append(f"对手在({i},{j})位置有活三威胁")
        
        return {
            'total_score': total_score,
            'situation': situation,
            'ai_key_moves': [(x, y, round(score, 2)) for x, y, score in ai_key_moves],
            'opponent_key_moves': [(x, y, round(score, 2)) for x, y, score in opponent_key_moves],
            'threats': threats,
            'key_move': ai_key_moves[0][:2] if ai_key_moves else None
        }