import numpy as np
import random
from typing import List, Tuple, Dict, Optional, Callable
from Common.constants import PIECE_COLORS, AI_LEVELS, EVAL_WEIGHTS
from Common.config import Config
from Common.logger import Logger
from AI.base_ai import BaseAI
from AI.evaluator import BoardEvaluator

class MCTSNode:
    """MCTS节点类（蒙特卡洛树搜索节点）"""
    def __init__(self, board: List[List[int]], parent: Optional['MCTSNode'] = None, move: Optional[Tuple[int, int]] = None):
        self.board = board  # 当前节点的棋盘状态
        self.parent = parent  # 父节点
        self.move = move  # 到达当前节点的落子
        self.children = []  # 子节点列表
        self.visits = 0  # 访问次数
        self.wins = 0  # 获胜次数
        self.untried_moves = self._get_empty_positions(board)  # 未尝试的落子
        self.value = 0.0  # 节点价值（结合评估得分）
    
    def _get_empty_positions(self, board: List[List[int]]) -> List[Tuple[int, int]]:
        """获取棋盘上的空位置"""
        empty_pos = []
        board_size = len(board)
        for i in range(board_size):
            for j in range(board_size):
                if board[i][j] == PIECE_COLORS['EMPTY']:
                    empty_pos.append((i, j))
        return empty_pos
    
    def is_terminal(self, board_size: int) -> Tuple[bool, int]:
        """判断节点是否为终端节点（游戏结束）
        Returns:
            (是否终端节点, 获胜方颜色/0表示平局)
        """
        # 检查横向
        for i in range(board_size):
            for j in range(board_size - 4):
                color = self.board[i][j]
                if color != PIECE_COLORS['EMPTY'] and all(self.board[i][j + k] == color for k in range(5)):
                    return True, color
        
        # 检查纵向
        for j in range(board_size):
            for i in range(board_size - 4):
                color = self.board[i][j]
                if color != PIECE_COLORS['EMPTY'] and all(self.board[i + k][j] == color for k in range(5)):
                    return True, color
        
        # 检查正对角线
        for i in range(board_size - 4):
            for j in range(board_size - 4):
                color = self.board[i][j]
                if color != PIECE_COLORS['EMPTY'] and all(self.board[i + k][j + k] == color for k in range(5)):
                    return True, color
        
        # 检查反对角线
        for i in range(board_size - 4):
            for j in range(4, board_size):
                color = self.board[i][j]
                if color != PIECE_COLORS['EMPTY'] and all(self.board[i + k][j - k] == color for k in range(5)):
                    return True, color
        
        # 检查棋盘是否下满（平局）
        if not self.untried_moves:
            return True, 0
        
        return False, 0
    
    def uct_select_child(self, exploration_constant: float = 1.414) -> 'MCTSNode':
        """使用UCT算法选择子节点（平衡探索与利用）"""
        # 计算所有子节点的UCT值
        uct_values = []
        for child in self.children:
            if child.visits == 0:
                uct_value = float('inf')  # 未访问过的节点优先选择
            else:
                # UCT公式：胜率 + 探索常数 * sqrt(ln(父节点访问次数)/子节点访问次数)
                win_rate = child.wins / child.visits
                exploration_term = exploration_constant * np.sqrt(np.log(self.visits) / child.visits)
                uct_value = win_rate + exploration_term
            uct_values.append(uct_value)
        
        # 选择UCT值最大的子节点
        max_index = np.argmax(uct_values)
        return self.children[max_index]
    
    def expand(self, color: int) -> 'MCTSNode':
        """扩展节点（选择一个未尝试的落子创建子节点）"""
        if not self.untried_moves:
            raise AIError("没有可扩展的落子", 4201)
        
        # 选择一个未尝试的落子
        move = self.untried_moves.pop(random.randint(0, len(self.untried_moves) - 1))
        x, y = move
        
        # 模拟落子，创建新棋盘
        new_board = [row.copy() for row in self.board]
        new_board[x][y] = color
        
        # 创建子节点
        child_node = MCTSNode(new_board, self, move)
        self.children.append(child_node)
        return child_node
    
    def backpropagate(self, result: int, ai_color: int):
        """回溯更新节点的访问次数和获胜次数"""
        self.visits += 1
        
        # 判断结果对AI是否有利
        if result == ai_color:
            self.wins += 1
            self.value += EVAL_WEIGHTS['FIVE']  # 获胜价值
        elif result == 0:
            self.value += EVAL_WEIGHTS['THREE'] / 2  # 平局价值
        else:
            self.value -= EVAL_WEIGHTS['FIVE']  # 失败价值
        
        # 递归更新父节点
        if self.parent:
            self.parent.backpropagate(result, ai_color)

class MCTSAI(BaseAI):
    """MCTS（蒙特卡洛树搜索）AI"""
    def __init__(self, color: int, level: str = AI_LEVELS['HARD']):
        super().__init__(color, level)
        self.evaluator = BoardEvaluator(self.board_size)  # 棋盘评估器
        self.iterations = self._get_iterations_by_level()  # 搜索迭代次数
        self.exploration_constant = 1.414  # UCT探索常数
        self.simulation_depth = 5  # 模拟最大深度
        self.root = None  # MCTS根节点
    
    def _get_iterations_by_level(self) -> int:
        """根据难度获取迭代次数"""
        iterations_map = {
            AI_LEVELS['EASY']: 200,
            AI_LEVELS['MEDIUM']: 500,
            AI_LEVELS['HARD']: 1000,
            AI_LEVELS['EXPERT']: 2000
        }
        return iterations_map.get(self.level, 1000)
    
    def move(self, board: List[List[int]], thinking_callback: Optional[Callable[[Dict], None]] = None) -> Tuple[int, int]:
        """计算最佳落子（MCTS算法）"""
        self.set_thinking_callback(thinking_callback)
        
        # 初始化根节点
        self.root = MCTSNode(board)
        
        # 检查是否有必胜落子（优先处理）
        winning_move = self._check_winning_move(board)
        if winning_move:
            self.logger.info(f"MCTS AI 发现必胜落子: {winning_move}")
            self._notify_thinking({
                'scores': self._get_node_scores(),
                'best_move': winning_move,
                'considering_moves': [],
                'depth': 0,
                'iteration': self.iterations
            })
            return winning_move
        
        # 开始MCTS搜索
        for i in range(self.iterations):
            # 1. 选择（Selection）
            selected_node = self._select_node(self.root)
            
            # 2. 扩展（Expansion）
            if not selected_node.is_terminal(self.board_size)[0] and selected_node.untried_moves:
                selected_node = selected_node.expand(self.color if selected_node.parent else self.opponent_color)
            
            # 3. 模拟（Simulation）
            result = self._simulate(selected_node)
            
            # 4. 回溯（Backpropagation）
            selected_node.backpropagate(result, self.color)
            
            # 每100次迭代通知一次思考进度
            if (i + 1) % 100 == 0 or i == self.iterations - 1:
                self._notify_thinking({
                    'scores': self._get_node_scores(),
                    'best_move': self._get_best_move(),
                    'considering_moves': self._get_top_moves(5),
                    'depth': self._get_tree_depth(self.root),
                    'iteration': i + 1,
                    'total_iterations': self.iterations
                })
        
        # 获取最佳落子（访问次数最多的子节点）
        best_move = self._get_best_move()
        self.logger.info(f"MCTS AI 落子: {best_move}，迭代次数: {self.iterations}，根节点访问次数: {self.root.visits}")
        return best_move
    
    def _select_node(self, node: MCTSNode) -> MCTSNode:
        """选择节点（UCT算法）"""
        current_node = node
        while current_node.children and not current_node.is_terminal(self.board_size)[0]:
            current_node = current_node.uct_select_child(self.exploration_constant)
        return current_node
    
    def _simulate(self, node: MCTSNode) -> int:
        """模拟游戏直到结束，返回结果（获胜方颜色/0平局）"""
        current_board = [row.copy() for row in node.board]
        current_color = self.color if node.parent else self.opponent_color  # 交替落子
        depth = 0
        
        while depth < self.simulation_depth:
            # 检查游戏是否结束
            is_terminal, winner = node.is_terminal(self.board_size)
            if is_terminal:
                return winner
            
            # 获取所有空位置并评估
            empty_positions = self._get_empty_positions(current_board)
            if not empty_positions:
                return 0  # 平局
            
            # 基于评估得分选择落子（启发式模拟）
            scored_moves = []
            for (x, y) in empty_positions:
                score = self.evaluator.evaluate_position(current_board, x, y, current_color)
                scored_moves.append((x, y, score))
            
            # 选择得分最高的落子
            scored_moves.sort(key=lambda x: x[2], reverse=True)
            best_move = scored_moves[0][:2]
            x, y = best_move
            
            # 模拟落子
            current_board[x][y] = current_color
            current_color = self.opponent_color if current_color == self.color else self.color
            depth += 1
        
        # 达到最大模拟深度，使用评估得分判断结果
        ai_score = self.evaluator.evaluate_board(current_board, self.color)
        if ai_score > EVAL_WEIGHTS['THREE']:
            return self.color
        elif ai_score < -EVAL_WEIGHTS['THREE']:
            return self.opponent_color
        else:
            return 0  # 平局
    
    def _get_best_move(self) -> Tuple[int, int]:
        """获取最佳落子（访问次数最多的子节点）"""
        if not self.root.children:
            return self._get_empty_positions(self.root.board)[0]
        
        # 选择访问次数最多的子节点
        best_child = max(self.root.children, key=lambda c: c.visits)
        return best_child.move
    
    def _get_node_scores(self) -> np.ndarray:
        """获取节点得分（用于可视化）"""
        scores = np.zeros((self.board_size, self.board_size))
        if not self.root.children:
            return scores
        
        # 子节点得分 = 胜率（wins/visits） + 价值权重
        for child in self.root.children:
            if child.visits == 0:
                score = 0.0
            else:
                win_rate = child.wins / child.visits
                value_weight = child.value / EVAL_WEIGHTS['FIVE']
                score = (win_rate + value_weight) * 127  # 归一化到0-255
            x, y = child.move
            scores[x][y] = score
        
        return scores
    
    def _get_top_moves(self, top_k: int) -> List[Tuple[int, int]]:
        """获取得分最高的top_k个落子"""
        if not self.root.children:
            return []
        
        # 按访问次数排序
        sorted_children = sorted(self.root.children, key=lambda c: c.visits, reverse=True)
        return [child.move for child in sorted_children[:top_k]]
    
    def _get_tree_depth(self, node: MCTSNode) -> int:
        """获取树的深度"""
        if not node.children:
            return 0
        return 1 + max(self._get_tree_depth(child) for child in node.children)
    
    def _check_winning_move(self, board: List[List[int]]) -> Optional[Tuple[int, int]]:
        """检查是否有必胜落子"""
        empty_positions = self._get_empty_positions(board)
        for (x, y) in empty_positions:
            temp_board = self._copy_board(board)
            temp_board[x][y] = self.color
            if self._is_win(temp_board, self.color)[0]:
                return (x, y)
        return None
    
    def evaluate(self, board: List[List[int]]) -> float:
        """评估棋盘得分（使用MCTS节点价值）"""
        if not self.root:
            return self.evaluator.evaluate_board(board, self.color)
        
        # 找到对应棋盘状态的节点
        node = self._find_node_by_board(self.root, board)
        if node:
            return node.value / node.visits if node.visits > 0 else 0.0
        return self.evaluator.evaluate_board(board, self.color)
    
    def _find_node_by_board(self, node: MCTSNode, target_board: List[List[int]]) -> Optional[MCTSNode]:
        """根据棋盘状态查找节点"""
        if node.board == target_board:
            return node
        for child in node.children:
            found = self._find_node_by_board(child, target_board)
            if found:
                return found
        return None
    
    def set_level(self, level: str):
        """重写设置难度方法（调整迭代次数）"""
        super().set_level(level)
        self.iterations = self._get_iterations_by_level()
        # 调整模拟深度
        depth_map = {
            AI_LEVELS['EASY']: 3,
            AI_LEVELS['MEDIUM']: 4,
            AI_LEVELS['HARD']: 5,
            AI_LEVELS['EXPERT']: 6
        }
        self.simulation_depth = depth_map.get(level, 5)
        self.logger.info(f"MCTS AI 难度已设置为: {level}，迭代次数: {self.iterations}，模拟深度: {self.simulation_depth}")