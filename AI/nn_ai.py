import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import List, Tuple, Dict, Optional, Callable
from Common.constants import PIECE_COLORS, AI_LEVELS, EVAL_WEIGHTS
from Common.config import Config
from Common.logger import Logger
from Common.data_utils import DataUtils
from AI.base_ai import BaseAI
from AI.evaluator import BoardEvaluator

class GobangNN(nn.Module):
    """五子棋神经网络（用于落子预测）"""
    def __init__(self, input_size: int = 225, hidden_layers: List[int] = [1024, 512, 256], output_size: int = 225):
        super().__init__()
        self.input_size = input_size
        self.output_size = output_size
        
        # 构建网络层
        layers = []
        prev_size = input_size
        for hidden_size in hidden_layers:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.3))  # 防止过拟合
            prev_size = hidden_size
        layers.append(nn.Linear(prev_size, output_size))
        layers.append(nn.Softmax(dim=1))  # 输出落子概率
        
        self.model = nn.Sequential(*layers)
        
        # 初始化权重
        self._init_weights()
    
    def _init_weights(self):
        """初始化网络权重"""
        for m in self.model.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        return self.model(x)

class NNAI(BaseAI):
    """神经网络AI（基于PyTorch+CUDA）"""
    def __init__(self, color: int, level: str = AI_LEVELS['HARD'], model_path: Optional[str] = None):
        super().__init__(color, level)
        self.evaluator = BoardEvaluator(self.board_size)  # 棋盘评估器
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')  # 自动选择设备
        self.config = Config.get_instance()
        
        # 初始化神经网络
        self.input_size = self.board_size * self.board_size
        self.hidden_layers = self.config.get_list('AI', 'nn_hidden_layers')
        self.output_size = self.board_size * self.board_size
        self.model = GobangNN(self.input_size, self.hidden_layers, self.output_size).to(self.device)
        
        # 加载预训练模型
        if model_path and self._load_model(model_path):
            self.logger.info(f"成功加载预训练模型: {model_path}")
        else:
            self.logger.warning("未加载预训练模型，使用随机初始化权重")
        
        # 训练相关参数
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.config.ai_learning_rate)
        self.batch_size = self.config.ai_batch_size
        self.max_epochs = self.config.ai_max_epochs
        
        # 温度参数（控制探索程度）
        self.temperature = self._get_temperature_by_level()
    
    def _get_temperature_by_level(self) -> float:
        """根据难度获取温度参数（温度越低，越倾向于选择最佳落子）"""
        temp_map = {
            AI_LEVELS['EASY']: 1.5,
            AI_LEVELS['MEDIUM']: 1.0,
            AI_LEVELS['HARD']: 0.5,
            AI_LEVELS['EXPERT']: 0.1
        }
        return temp_map.get(self.level, 0.5)
    
    def _load_model(self, model_path: str) -> bool:
        """加载模型权重"""
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()  # 设置为评估模式
            return True
        except Exception as e:
            self.logger.error(f"加载模型失败: {str(e)}")
            return False
    
    def _save_model(self, model_path: str, metadata: Optional[Dict] = None) -> bool:
        """保存模型权重"""
        try:
            checkpoint = {
                'model_state_dict': self.model.state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict(),
                'metadata': metadata or {}
            }
            torch.save(checkpoint, model_path)
            return True
        except Exception as e:
            self.logger.error(f"保存模型失败: {str(e)}")
            return False
    
    def _preprocess_board(self, board: List[List[int]]) -> torch.Tensor:
        """预处理棋盘数据（转换为模型输入）"""
        # 转换为numpy数组
        board_np = np.array(board, dtype=np.float32)
        
        # 标准化：自己的棋子为1，对手为-1，空为0
        board_np[board_np == self.color] = 1.0
        board_np[board_np == self.opponent_color] = -1.0
        board_np[board_np == PIECE_COLORS['EMPTY']] = 0.0
        
        # 展平为一维向量并转换为Tensor
        board_flat = board_np.flatten()
        return torch.tensor(board_flat, dtype=torch.float32).unsqueeze(0).to(self.device)
    
    def _postprocess_output(self, output: torch.Tensor, board: List[List[int]]) -> Tuple[np.ndarray, List[Tuple[int, int, float]]]:
        """后处理模型输出（转换为落子概率）"""
        # 应用温度参数
        output = output / self.temperature
        probabilities = torch.softmax(output, dim=1).detach().cpu().numpy()[0]
        
        # 过滤掉已落子的位置（概率设为0）
        board_np = np.array(board)
        mask = (board_np == PIECE_COLORS['EMPTY']).flatten()
        probabilities[~mask] = 0.0
        
        # 归一化概率
        if probabilities.sum() > 0:
            probabilities /= probabilities.sum()
        
        # 转换为落子概率列表
        move_probs = []
        for i in range(self.board_size):
            for j in range(self.board_size):
                idx = DataUtils.move_to_index(i, j, self.board_size)
                move_probs.append((i, j, probabilities[idx]))
        
        return probabilities.reshape((self.board_size, self.board_size)), move_probs
    
    def move(self, board: List[List[int]], thinking_callback: Optional[Callable[[Dict], None]] = None) -> Tuple[int, int]:
        """计算最佳落子（神经网络预测）"""
        self.set_thinking_callback(thinking_callback)
        self.model.eval()  # 设置为评估模式
        
        # 检查是否有必胜落子
        winning_move = self._check_winning_move(board)
        if winning_move:
            self._notify_thinking({
                'scores': np.zeros((self.board_size, self.board_size)),
                'best_move': winning_move,
                'considering_moves': [],
                'depth': 0,
                'iteration': 1
            })
            return winning_move
        
        # 预处理棋盘
        input_tensor = self._preprocess_board(board)
        
        # 模型预测
        with torch.no_grad():
            output = self.model(input_tensor)
        
        # 后处理输出
        prob_matrix, move_probs = self._postprocess_output(output, board)
        
        # 排序并获取最佳落子
        move_probs.sort(key=lambda x: x[2], reverse=True)
        best_move = move_probs[0][:2]
        top_moves = [move[:2] for move in move_probs[:5]]
        
        # 通知思考结果（概率矩阵归一化到0-255用于可视化）
        vis_matrix = prob_matrix * 255
        self._notify_thinking({
            'scores': vis_matrix,
            'best_move': best_move,
            'considering_moves': top_moves,
            'depth': 1,
            'iteration': 1
        })
        
        self.logger.info(f"NN AI 落子: {best_move}，概率: {move_probs[0][2]:.4f}")
        return best_move
    
    def _check_winning_move(self, board: List[List[int]]) -> Optional[Tuple[int, int]]:
        """检查是否有必胜落子"""
        empty_positions = self._get_empty_positions(board)
        for (x, y) in empty_positions:
            temp_board = self._copy_board(board)
            temp_board[x][y] = self.color
            if self._is_win(temp_board, self.color)[0]:
                return (x, y)
        return None
    
    def train_model(self, train_data: List[Tuple[List[List[int]], Tuple[int, int]]], epochs: int = None, batch_size: int = None) -> Tuple[List[float], List[float]]:
        """训练模型
        Args:
            train_data: 训练数据列表，每个元素为(棋盘状态, 最佳落子)
            epochs: 训练轮数（默认使用配置值）
            batch_size: 批次大小（默认使用配置值）
        Returns:
            (loss_history, accuracy_history): 损失和准确率历史
        """
        if not train_data:
            raise AIError("没有训练数据", 4301)
        
        self.model.train()  # 设置为训练模式
        epochs = epochs or self.max_epochs
        batch_size = batch_size or self.batch_size
        
        loss_history = []
        accuracy_history = []
        
        # 准备训练数据
        inputs = []
        labels = []
        for board, move in train_data:
            # 预处理输入
            input_tensor = self._preprocess_board(board)
            inputs.append(input_tensor)
            
            # 转换标签（落子位置索引）
            label_idx = DataUtils.move_to_index(move[0], move[1], self.board_size)
            labels.append(torch.tensor(label_idx, dtype=torch.long).to(self.device))
        
        # 组合数据并分批
        dataset = torch.utils.data.TensorDataset(torch.cat(inputs), torch.stack(labels))
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # 开始训练
        for epoch in range(epochs):
            total_loss = 0.0
            correct = 0
            total = 0
            
            for batch_inputs, batch_labels in dataloader:
                # 前向传播
                outputs = self.model(batch_inputs)
                loss = self.criterion(outputs, batch_labels)
                
                # 反向传播和优化
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                
                # 计算损失和准确率
                total_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += batch_labels.size(0)
                correct += (predicted == batch_labels).sum().item()
            
            # 记录历史
            avg_loss = total_loss / len(dataloader)
            accuracy = correct / total
            loss_history.append(avg_loss)
            accuracy_history.append(accuracy)
            
            self.logger.info(f"训练轮次 {epoch+1}/{epochs} - 损失: {avg_loss:.4f} - 准确率: {accuracy:.4f}")
        
        return loss_history, accuracy_history
    
    def merge_models(self, model_paths: List[str], weights: Optional[List[float]] = None) -> bool:
        """合并多个模型权重
        Args:
            model_paths: 要合并的模型路径列表
            weights: 模型权重（默认等权重）
        Returns:
            是否合并成功
        """
        if len(model_paths) < 2:
            self.logger.error("至少需要两个模型才能合并")
            return False
        
        # 初始化合并权重
        merged_state_dict = None
        weights = weights or [1.0 / len(model_paths)] * len(model_paths)
        
        # 加载并合并每个模型的权重
        for i, path in enumerate(model_paths):
            try:
                checkpoint = torch.load(path, map_location=self.device)
                model_state = checkpoint['model_state_dict']
                
                if merged_state_dict is None:
                    # 初始化合并权重
                    merged_state_dict = {k: v * weights[i] for k, v in model_state.items()}
                else:
                    # 累加权重
                    for k, v in model_state.items():
                        merged_state_dict[k] += v * weights[i]
            except Exception as e:
                self.logger.error(f"加载模型 {path} 失败: {str(e)}")
                return False
        
        # 应用合并后的权重
        self.model.load_state_dict(merged_state_dict)
        self.logger.info(f"成功合并 {len(model_paths)} 个模型")
        return True
    
    def evaluate(self, board: List[List[int]]) -> float:
        """评估棋盘得分（使用模型输出概率）"""
        self.model.eval()
        input_tensor = self._preprocess_board(board)
        
        with torch.no_grad():
            output = self.model(input_tensor)
        
        # 后处理输出
        prob_matrix, _ = self._postprocess_output(output, board)
        
        # 计算得分（最佳落子概率 * 评估得分）
        best_move_prob = prob_matrix.max()
        eval_score = self.evaluator.evaluate_board(board, self.color)
        return eval_score * best_move_prob
    
    def set_level(self, level: str):
        """重写设置难度方法（调整温度参数）"""
        super().set_level(level)
        self.temperature = self._get_temperature_by_level()
        self.logger.info(f"NN AI 温度参数已设置为: {self.temperature}")
    
    def save_model(self, path: str, metadata: Optional[Dict] = None) -> bool:
        """对外暴露的保存模型方法"""
        return self._save_model(path, metadata)