import json
import pickle
import os
import numpy as np
import torch
from datetime import datetime
from Common.constants import PIECE_COLORS, GAME_MODES, AI_LEVELS
from Common.error_handler import DataError

class DataUtils:
    """数据处理工具类"""

    @staticmethod
    def board_to_tensor(board, player=PIECE_COLORS['BLACK']):
        """将棋盘转换为Tensor（用于AI输入）"""
        board_size = len(board)
        # 创建3通道输入：当前玩家、对手、空位置
        input_tensor = torch.zeros(3, board_size, board_size, dtype=torch.float32)
        for i in range(board_size):
            for j in range(board_size):
                if board[i][j] == player:
                    input_tensor[0][i][j] = 1.0
                elif board[i][j] != PIECE_COLORS['EMPTY']:
                    input_tensor[1][i][j] = 1.0
                else:
                    input_tensor[2][i][j] = 1.0
        return input_tensor.unsqueeze(0)  # 添加batch维度

    @staticmethod
    def tensor_to_board(tensor):
        """将Tensor转换为棋盘"""
        tensor = tensor.squeeze(0)  # 去除batch维度
        board_size = tensor.shape[1]
        board = [[PIECE_COLORS['EMPTY'] for _ in range(board_size)] for _ in range(board_size)]
        for i in range(board_size):
            for j in range(board_size):
                if tensor[0][i][j] == 1.0:
                    board[i][j] = PIECE_COLORS['BLACK']
                elif tensor[1][i][j] == 1.0:
                    board[i][j] = PIECE_COLORS['WHITE']
        return board

    @staticmethod
    def move_to_index(x, y, board_size=15):
        """将落子坐标转换为索引（0-224）"""
        return x * board_size + y

    @staticmethod
    def index_to_move(index, board_size=15):
        """将索引转换为落子坐标"""
        x = index // board_size
        y = index % board_size
        return (x, y)

    @staticmethod
    def save_model(model, path, metadata=None):
        """保存模型（包含权重和元数据）"""
        try:
            save_data = {
                'model_state_dict': model.state_dict(),
                'metadata': metadata or {},
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            torch.save(save_data, path)
            return True
        except Exception as e:
            raise ModelError(f"模型保存失败: {str(e)}", 7001)

    @staticmethod
    def load_model(path, model_class=None):
        """加载模型"""
        try:
            if not os.path.exists(path):
                raise ModelError(f"模型文件不存在: {path}", 7002)
            save_data = torch.load(path, map_location=torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
            if model_class is not None:
                model = model_class()
                model.load_state_dict(save_data['model_state_dict'])
                model.eval()
                return model, save_data.get('metadata', {})
            return save_data
        except Exception as e:
            raise ModelError(f"模型加载失败: {str(e)}", 7003)

    @staticmethod
    def save_training_data(data_list, path):
        """保存训练数据"""
        try:
            # 确保目录存在
            dir_path = os.path.dirname(path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            # 保存为pkl格式（高效）
            with open(path, 'wb') as f:
                pickle.dump(data_list, f)
            return True
        except Exception as e:
            raise DataError(f"训练数据保存失败: {str(e)}", 8001)

    @staticmethod
    def load_training_data(path):
        """加载训练数据"""
        try:
            if not os.path.exists(path):
                raise DataError(f"训练数据文件不存在: {path}", 8002)
            with open(path, 'rb') as f:
                data_list = pickle.load(f)
            return data_list
        except Exception as e:
            raise DataError(f"训练数据加载失败: {str(e)}", 8003)

    @staticmethod
    def save_json(data, path):
        """保存JSON数据"""
        try:
            dir_path = os.path.dirname(path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            raise DataError(f"JSON数据保存失败: {str(e)}", 8004)

    @staticmethod
    def load_json(path):
        """加载JSON数据"""
        try:
            if not os.path.exists(path):
                raise DataError(f"JSON文件不存在: {path}", 8005)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            raise DataError(f"JSON数据加载失败: {str(e)}", 8006)

    @staticmethod
    def normalize_board(board):
        """标准化棋盘数据（0-1）"""
        board_np = np.array(board, dtype=np.float32)
        board_np[board_np == PIECE_COLORS['BLACK']] = 1.0
        board_np[board_np == PIECE_COLORS['WHITE']] = -1.0
        board_np[board_np == PIECE_COLORS['EMPTY']] = 0.0
        return board_np

    @staticmethod
    def generate_move_history_str(move_history):
        """生成落子历史字符串（格式：x1,y1;x2,y2;...）"""
        return ';'.join([f"{x},{y}" for x, y in move_history])

    @staticmethod
    def parse_move_history_str(history_str):
        """解析落子历史字符串"""
        if not history_str or history_str == '[]':
            return []
        moves = history_str.split(';')
        return [(int(x), int(y)) for x, y in [move.split(',') for move in moves if move]]

    @staticmethod
    def calculate_model_accuracy(predictions, labels):
        """计算模型准确率"""
        if len(predictions) != len(labels):
            raise DataError("预测结果与标签长度不匹配", 8007)
        correct = 0
        for pred, label in zip(predictions, labels):
            if torch.argmax(pred) == torch.argmax(label):
                correct += 1
        return correct / len(predictions) if len(predictions) > 0 else 0.0

    @staticmethod
    def generate_unique_id(prefix=''):
        """生成唯一ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        random_str = ''.join([str(np.random.randint(0, 10)) for _ in range(6)])
        return f"{prefix}_{timestamp}_{random_str}"

    @staticmethod
    def format_time(seconds):
        """格式化时间（秒转分:秒）"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def get_current_time_str():
        """获取当前时间字符串（YYYY-MM-DD HH:MM:SS）"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 修正：补充缺失的DataError类定义
class DataError(BaseError):
    """数据处理异常"""
    def __init__(self, message, code=8000):
        super().__init__(message, code)

# 导入基础异常类（避免循环导入）
from Common.error_handler import BaseError, ModelError