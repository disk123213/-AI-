import numpy as np
from typing import List, Tuple, Dict, Optional
from Common.constants import PIECE_COLORS, AI_LEVELS, EVAL_WEIGHTS
from Common.config import Config
from Common.logger import Logger
from AI.base_ai import BaseAI
from AI.evaluator import BoardEvaluator

class MinimaxAI(BaseAI):
    """Minimax算法AI（带Alpha-Beta剪枝）"""
    def __init__(self, color: int, level: str = AI_LEVELS['HARD']):
        super().__init__(color, level)
        self.evaluator = BoardEvaluator(self.board_size)  # 棋盘评估器
        self.node_count = 0  # 搜索节点计数（性能统计）
        self.prune_count = 0  # 剪枝计数（性能统计）
        
        # 优化参数
        self.move_ordering_enabled = True  # 启用落子排序（提升剪枝效率）
        self.killer_moves = {}  # 杀手落子（记录每层最有效的落子）
    
    def move(self, board: List[List[int]], thinking_callback: Optional[Callable[[Dict], None]] = None) -> Tuple[int, int]:
        """计算最佳落子（Minimax+Alpha-Beta剪枝）"""
        self.set_thinking_callback(thinking_callback)
        self.clear_cache()  # 清空缓存
        self.node_count = 0
        self.prune_count = 0
        self.killer_moves.clear()
        
        # 获取所有空位置
        empty_positions = self._get_empty_positions(board)
        if not empty_positions:
            raise AIError("棋盘已满，无法落子", 4101)
        
        # 落子排序（提升剪枝效率）
        if self.move_ordering_enabled:
            empty_positions = self._order_moves(board, empty_positions)
        
        # 通知开始思考
        self._notify_thinking({
            'scores': np.zeros((self.board_size, self.board_size)),
            'considering_moves': empty_positions[:5],  # 先显示前5个候选落子
            'depth': 0,
            'iteration': 0
        })
        
        best_score = -float('inf')
        best_move = empty_positions[0]
        
        # 遍历所有候选落子
        for i, (x, y) in enumerate(empty_positions):
            # 模拟落子
            temp_board = self._copy_board(board)
            temp_board[x][y] = self.color
            
            # 递归搜索
            score = self._alpha_beta(
                temp_board,
                depth=self.max_depth - 1,
                alpha=-float('inf'),
                beta=float('inf'),
                is_maximizing=False,
                current_depth=1
            )
            
            # 更新最佳落子
            if score > best_score:
                best_score = score
                best_move = (x, y)
            
            # 实时通知思考进度
            scores = np.zeros((self.board_size, self.board_size))
            for (nx, ny) in empty_positions[:10]:  # 只显示前10个候选落子的得分
                scores[nx][ny] = self.evaluator.evaluate_position(board, nx, ny, self.color)
            
            self._notify_thinking({
                'scores': scores,
                'best_move': best_move,
                'considering_moves': empty_positions[:5],
                'depth': self.max_depth,
                'iteration': i + 1,
                'total_iterations': len(empty_positions)
            })
        
        self.logger.info(f"Minimax AI 落子: {best_move}，得分: {best_score:.2f}，搜索节点: {self.node_count}，剪枝次数: {self.prune_count}")
        return best_move
    
    def _alpha_beta(
        self,
        board: List[List[int]],
        depth: int,
        alpha: float,
        beta: float,
        is_maximizing: bool,
        current_depth: int
    ) -> float:
        """Alpha-Beta剪枝递归函数"""
        self.node_count += 1
        
        # 检查缓存
        cached_score = self._get_cached_evaluation(board, depth)
        if cached_score is not None:
            return cached_score
        
        # 终端节点：到达最大深度或游戏结束
        if depth == 0:
            score = self.evaluate(board)
            self._cache_evaluation(board, score, depth)
            return score
        
        # 检查是否获胜
        if is_maximizing:
            # AI回合（最大化得分）
            win, _ = self._is_win(board, self.color)
            if win:
                score = EVAL_WEIGHTS['FIVE'] + depth  # 深度越大，得分越高（优先结束游戏）
                self._cache_evaluation(board, score, depth)
                return score
        else:
            # 对手回合（最小化得分）
            win, _ = self._is_win(board, self.opponent_color)
            if win:
                score = -EVAL_WEIGHTS['FIVE'] - depth
                self._cache_evaluation(board, score, depth)
                return score
        
        # 检查棋盘是否下满
        if self._is_board_full(board):
            score = 0.0  # 平局
            self._cache_evaluation(board, score, depth)
            return score
        
        # 获取所有空位置并排序
        empty_positions = self._get_empty_positions(board)
        if self.move_ordering_enabled:
            empty_positions = self._order_moves(board, empty_positions, is_maximizing, current_depth)
        
        if is_maximizing:
            # 最大化玩家（AI）
            max_score = -float('inf')
            for (x, y) in empty_positions:
                # 模拟落子
                temp_board = self._copy_board(board)
                temp_board[x][y] = self.color
                
                # 递归搜索
                score = self._alpha_beta(temp_board, depth - 1, alpha, beta, False, current_depth + 1)
                max_score = max(max_score, score)
                
                # Alpha剪枝
                alpha = max(alpha, score)
                if beta <= alpha:
                    self.prune_count += 1
                    # 记录杀手落子
                    self._record_killer_move(current_depth, (x, y))
                    break
            
            self._cache_evaluation(board, max_score, depth)
            return max_score
        else:
            # 最小化玩家（对手）
            min_score = float('inf')
            for (x, y) in empty_positions:
                # 模拟落子
                temp_board = self._copy_board(board)
                temp_board[x][y] = self.opponent_color
                
                # 递归搜索
                score = self._alpha_beta(temp_board, depth - 1, alpha, beta, True, current_depth + 1)
                min_score = min(min_score, score)
                
                # Beta剪枝
                beta = min(beta, score)
                if beta <= alpha:
                    self.prune_count += 1
                    # 记录杀手落子
                    self._record_killer_move(current_depth, (x, y))
                    break
            
            self._cache_evaluation(board, min_score, depth)
            return min_score
    
    def _order_moves(
        self,
        board: List[List[int]],
        moves: List[Tuple[int, int]],
        is_maximizing: bool = True,
        depth: int = 0
    ) -> List[Tuple[int, int]]:
        """落子排序（提升剪枝效率）"""
        if not moves:
            return []
        
        # 1. 优先考虑杀手落子
        killer_move = self.killer_moves.get(depth, None)
        ordered_moves = []
        remaining_moves = []
        
        if killer_move and killer_move in moves:
            ordered_moves.append(killer_move)
        
        # 2. 按评估得分排序
        for move in moves:
            if move not in ordered_moves:
                x, y = move
                if is_maximizing:
                    # AI回合：按AI得分降序
                    score = self.evaluator.evaluate_position(board, x, y, self.color)
                else:
                    # 对手回合：按对手得分升序（对AI最不利的先考虑）
                    score = -self.evaluator.evaluate_position(board, x, y, self.opponent_color)
                remaining_moves.append((move, score))
        
        # 排序并合并
        remaining_moves.sort(key=lambda x: x[1], reverse=True)
        ordered_moves += [move for move, _ in remaining_moves]
        
        return ordered_moves
    
    def _record_killer_move(self, depth: int, move: Tuple[int, int]):
        """记录杀手落子（在当前深度导致剪枝的落子）"""
        # 只记录每个深度的第一个杀手落子
        if depth not in self.killer_moves:
            self.killer_moves[depth] = move
    
    def evaluate(self, board: List[List[int]]) -> float:
        """评估棋盘得分（使用独立评估器）"""
        return self.evaluator.evaluate_board(board, self.color)
    
    def set_level(self, level: str):
        """重写设置难度方法（调整剪枝阈值）"""
        super().set_level(level)
        # 难度越高，剪枝阈值越低（保留更多搜索路径）
        level_threshold = {
            AI_LEVELS['EASY']: 0.9,
            AI_LEVELS['MEDIUM']: 0.85,
            AI_LEVELS['HARD']: 0.8,
            AI_LEVELS['EXPERT']: 0.7
        }
        self.prune_threshold = level_threshold.get(level, 0.8)
        self.logger.info(f"Minimax AI 剪枝阈值已设置为: {self.prune_threshold}")