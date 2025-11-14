import time
from typing import List, Tuple, Dict, Optional, Callable
from Common.constants import PIECE_COLORS, GAME_MODES, AI_LEVELS, EVAL_WEIGHTS
from Common.config import Config
from Common.logger import Logger
from Common.data_utils import DataUtils
from Common.error_handler import GameError
from AI.base_ai import BaseAI, AIFactory
from AI.model_manager import ModelManager
from AI.evaluator import BoardEvaluator
from DB.game_dao import GameDAO
from DB.training_data_dao import TrainingDataDAO
from Server.main_server import Server

class GameCore:
    """游戏核心管理器（统筹所有游戏逻辑）"""
    def __init__(self):
        self.config = Config.get_instance()
        self.logger = Logger.get_instance()
        
        # 核心组件
        self.model_manager = ModelManager()
        self.evaluator = BoardEvaluator(self.config.board_size)
        self.game_dao = GameDAO()
        self.training_data_dao = TrainingDataDAO()
        
        # 游戏状态
        self.board_size = self.config.board_size
        self.board = [[PIECE_COLORS['EMPTY'] for _ in range(self.board_size)] for _ in range(self.board_size)]
        self.move_history = []  # 落子历史：[(x,y,color,is_ai,timestamp), ...]
        self.game_active = False  # 游戏是否激活
        self.current_player = PIECE_COLORS['BLACK']  # 当前回合玩家（黑先）
        
        # 模式配置
        self.current_mode = None
        self.ai_level = AI_LEVELS['HARD']
        self.ai_type = 'nn+mcts'  # 默认高级AI（神经网络+MCTS）
        self.ai_first = False  # AI是否先手
        self.current_ai: Optional[BaseAI] = None  # 当前AI实例
        
        # 联机相关
        self.is_online = False
        self.server: Optional[Server] = None
        self.current_room_id = None
        self.online_callback: Optional[Callable[[Dict], None]] = None  # 联机回调
        
        # 训练相关
        self.is_training = False
        self.train_user_id = None
    
    def set_mode(self, mode: str):
        """设置游戏模式"""
        self.current_mode = mode
        self.is_online = (mode == GAME_MODES['ONLINE'])
        
        # 初始化对应模式的配置
        if mode == GAME_MODES['PVE'] or mode == GAME_MODES['TRAIN']:
            # 人机/训练模式：初始化AI
            self._init_ai()
        elif mode == GAME_MODES['PVP']:
            # 人人模式：清空AI
            self.current_ai = None
        elif mode == GAME_MODES['ONLINE']:
            # 联机模式：初始化服务器连接
            self._init_online()
        
        # 重置游戏状态
        self.reset_game()
        self.logger.info(f"游戏模式已设置为: {mode}")
    
    def _init_ai(self):
        """初始化AI实例"""
        # 根据模式选择AI类型（训练模式默认神经网络AI）
        if self.current_mode == GAME_MODES['TRAIN']:
            self.ai_type = 'nn'
        
        # 创建AI实例
        ai_color = PIECE_COLORS['WHITE'] if self.ai_first else PIECE_COLORS['BLACK']
        self.current_ai = AIFactory.create_ai(self.ai_type, ai_color, self.ai_level)
        
        # 如果是训练模式，加载用户的自定义模型（如果有）
        if self.current_mode == GAME_MODES['TRAIN'] and self.train_user_id:
            user_models = self.model_manager.get_user_models(self.train_user_id)
            if user_models:
                # 加载最新的模型
                latest_model = max(user_models, key=lambda m: m['create_time'])
                self.load_ai_model(latest_model['model_id'], self.train_user_id)
    
    def _init_online(self):
        """初始化联机模式（客户端）"""
        try:
            # 连接服务器
            self.server = Server(self.config.server_host, self.config.server_port)
            self.logger.info(f"已初始化联机模式，将连接服务器: {self.config.server_host}:{self.config.server_port}")
        except Exception as e:
            self.logger.error(f"初始化联机模式失败: {str(e)}")
            raise GameError(f"联机模式初始化失败: {str(e)}", 2001)
    
    def set_ai_level(self, level: str):
        """设置AI难度"""
        self.ai_level = level
        if self.current_ai:
            self.current_ai.set_level(level)
        self.logger.info(f"AI难度已设置为: {level}")
    
    def set_ai_first(self, ai_first: bool):
        """设置AI是否先手"""
        self.ai_first = ai_first
        # 重新初始化AI（切换颜色）
        if self.current_mode in [GAME_MODES['PVE'], GAME_MODES['TRAIN']]:
            self._init_ai()
        self.logger.info(f"AI先手设置为: {ai_first}")
    
    def start_game(self):
        """开始游戏"""
        if self.current_mode is None:
            raise GameError("请先选择游戏模式", 2002)
        
        self.game_active = True
        self.current_player = PIECE_COLORS['BLACK'] if not self.ai_first else PIECE_COLORS['WHITE']
        self.logger.info("游戏开始")
        
        # 联机模式下通知服务器
        if self.is_online and self.current_room_id:
            self._send_online_message('start_game', {'room_id': self.current_room_id})
    
    def stop_game(self):
        """停止游戏"""
        self.game_active = False
        self.logger.info("游戏停止")
        
        # 联机模式下通知服务器
        if self.is_online and self.current_room_id:
            self._send_online_message('stop_game', {'room_id': self.current_room_id})
    
    def reset_game(self):
        """重置游戏"""
        self.board = [[PIECE_COLORS['EMPTY'] for _ in range(self.board_size)] for _ in range(self.board_size)]
        self.move_history = []
        self.game_active = False
        self.current_player = PIECE_COLORS['BLACK'] if not self.ai_first else PIECE_COLORS['WHITE']
        self.logger.info("游戏已重置")
        
        # 联机模式下通知服务器
        if self.is_online and self.current_room_id:
            self._send_online_message('reset_game', {'room_id': self.current_room_id})
    
    def place_piece(self, x: int, y: int, is_ai: bool = False) -> str:
        """落子（返回结果状态）"""
        if not self.game_active:
            return 'game_not_active'
        
        # 检查坐标有效性
        if x < 0 or x >= self.board_size or y < 0 or y >= self.board_size:
            return 'invalid_position'
        
        # 检查位置是否为空
        if self.board[x][y] != PIECE_COLORS['EMPTY']:
            return 'occupied'
        
        # 检查当前回合
        if not is_ai and self.current_player != PIECE_COLORS['BLACK']:
            return 'not_your_turn'
        
        # 执行落子
        color = self.current_player
        self.board[x][y] = color
        
        # 记录落子历史
        self.move_history.append({
            'x': x,
            'y': y,
            'color': color,
            'is_ai': is_ai,
            'timestamp': time.time()
        })
        
        # 联机模式下同步落子
        if self.is_online and self.current_room_id:
            self._send_online_message('move', {
                'room_id': self.current_room_id,
                'x': x,
                'y': y
            })
        
        # 切换回合
        self.current_player = PIECE_COLORS['WHITE'] if color == PIECE_COLORS['BLACK'] else PIECE_COLORS['BLACK']
        
        return 'success'
    
    def ai_move(self, thinking_callback: Optional[Callable[[Dict], None]] = None) -> Tuple[int, int]:
        """AI落子"""
        if not self.game_active or not self.current_ai:
            raise GameError("无法执行AI落子：游戏未激活或未初始化AI", 2003)
        
        # 检查是否是AI的回合
        ai_color = self.current_ai.color
        if self.current_player != ai_color:
            raise GameError("当前不是AI的回合", 2004)
        
        # 调用AI计算落子
        x, y = self.current_ai.move(self.board, thinking_callback)
        
        # 执行落子
        self.place_piece(x, y, is_ai=True)
        
        return x, y
    
    def check_game_end(self) -> Optional[Dict]:
        """检查游戏是否结束（返回结果字典）"""
        if not self.game_active:
            return None
        
        # 检查黑方获胜
        black_win, black_win_line = self.evaluator._is_win(self.board, PIECE_COLORS['BLACK'])
        if black_win:
            self.game_active = False
            return {
                'winner': 'player1',
                'win_line': black_win_line,
                'color': PIECE_COLORS['BLACK']
            }
        
        # 检查白方获胜
        white_win, white_win_line = self.evaluator._is_win(self.board, PIECE_COLORS['WHITE'])
        if white_win:
            self.game_active = False
            return {
                'winner': 'player2',
                'win_line': white_win_line,
                'color': PIECE_COLORS['WHITE']
            }
        
        # 检查平局
        if self.evaluator._is_board_full(self.board):
            self.game_active = False
            return {'winner': 'draw', 'win_line': []}
        
        return None
    
    def analyze_board(self) -> Dict:
        """分析棋盘（生成分析报告）"""
        if not self.game_active:
            raise GameError("请先开始游戏", 2005)
        
        # 确定AI颜色（用于分析）
        ai_color = self.current_ai.color if self.current_ai else PIECE_COLORS['WHITE']
        return self.evaluator.analyze_board(self.board, ai_color)
    
    def save_ai_model(self, model_name: str, user_id: int) -> bool:
        """保存当前AI模型"""
        if not self.current_ai or not isinstance(self.current_ai, NNAI):
            self.logger.error("只有神经网络AI可以保存")
            return False
        
        try:
            # 调用模型管理器保存
            success, model_id = self.model_manager.train_model(
                user_id=user_id,
                ai_type=self.ai_type,
                ai_level=self.ai_level,
                model_name=model_name
            )
            return success
        except Exception as e:
            self.logger.error(f"保存AI模型失败: {str(e)}")
            return False
    
    def load_ai_model(self, model_id: int, user_id: int) -> bool:
        """加载AI模型"""
        try:
            # 调用模型管理器加载
            ai_instance = self.model_manager.get_model_by_id(model_id, user_id)
            if ai_instance:
                self.current_ai = ai_instance
                self.ai_type = ai_instance.__class__.__name__.lower().replace('ai', '')
                self.ai_level = ai_instance.level
                self.logger.info(f"成功加载模型 ID: {model_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"加载AI模型失败: {str(e)}")
            return False
    
    def train_ai_model(
        self,
        user_id: int,
        epochs: int,
        batch_size: int,
        train_callback: Optional[Callable[[int, float, float], None]] = None
    ):
        """训练AI模型"""
        if not self.current_ai or not isinstance(self.current_ai, NNAI):
            raise GameError("只有神经网络AI可以训练", 2006)
        
        if self.current_mode != GAME_MODES['TRAIN']:
            raise GameError("请切换到训练模式进行训练", 2007)
        
        try:
            # 获取训练数据
            training_data = self.training_data_dao.get_training_data_by_user(user_id)
            if not training_data:
                raise GameError("没有可用的训练数据", 2008)
            
            # 转换训练数据格式
            train_data = []
            for data in training_data:
                board = DataUtils.str_to_board(data['input_data'])
                move_idx = int(data['output_data'])
                move = DataUtils.index_to_move(move_idx, self.board_size)
                train_data.append((board, move))
            
            # 开始训练
            self.is_training = True
            loss_history, accuracy_history = self.current_ai.train_model(
                train_data,
                epochs=epochs,
                batch_size=batch_size
            )
            
            # 调用训练回调更新进度
            for epoch in range(epochs):
                if train_callback:
                    train_callback(
                        epoch + 1,
                        loss_history[epoch] if epoch < len(loss_history) else 0.0,
                        accuracy_history[epoch] if epoch < len(accuracy_history) else 0.0
                    )
            
            # 保存训练后的模型
            self.save_ai_model(f"训练模型_{int(time.time())}", user_id)
            
            self.is_training = False
            self.logger.info(f"模型训练完成，总轮数: {epochs}")
        except Exception as e:
            self.is_training = False
            self.logger.error(f"训练AI模型失败: {str(e)}")
            raise GameError(f"训练失败: {str(e)}", 2009)
    
    def add_training_data(self, user_id: int) -> bool:
        """添加训练数据（从当前游戏历史）"""
        if self.current_mode != GAME_MODES['TRAIN'] or not self.move_history:
            self.logger.error("无法添加训练数据：非训练模式或无落子历史")
            return False
        
        try:
            # 取最后一步落子作为最佳落子
            last_move = self.move_history[-1]
            x, y = last_move['x'], last_move['y']
            score = self.evaluator.evaluate_position(self.board, x, y, last_move['color'])
            
            # 转换棋盘状态为字符串
            board_str = DataUtils.board_to_str(self.board)
            # 转换落子位置为索引
            move_idx = DataUtils.move_to_index(x, y, self.board_size)
            
            # 添加到训练数据
            return self.training_data_dao.add_training_data({
                'user_id': user_id,
                'input_data': board_str,
                'output_data': str(move_idx),
                'score': score
            })
        except Exception as e:
            self.logger.error(f"添加训练数据失败: {str(e)}")
            return False
    
    def _send_online_message(self, msg_type: str, data: Dict):
        """发送联机消息"""
        if not self.is_online or not self.server:
            return
        
        try:
            # 调用服务器发送消息
            self.server.send_message(msg_type, {
                **data,
                'user_id': self.train_user_id,
                'room_id': self.current_room_id
            })
        except Exception as e:
            self.logger.error(f"发送联机消息失败: {str(e)}")
    
    def set_online_callback(self, callback: Callable[[Dict], None]):
        """设置联机消息回调（用于UI更新）"""
        self.online_callback = callback
    
    def handle_online_message(self, msg: Dict):
        """处理联机消息（从服务器接收）"""
        if self.online_callback:
            self.online_callback(msg)
        
        # 根据消息类型更新游戏状态
        msg_type = msg.get('type')
        data = msg.get('data', {})
        
        if msg_type == 'move':
            # 处理对手落子
            x = data.get('x')
            y = data.get('y')
            if x is not None and y is not None:
                self.place_piece(x, y, is_ai=False)
        elif msg_type == 'game_end':
            # 处理游戏结束
            self.game_active = False
        elif msg_type == 'reset_game':
            # 处理重置游戏
            self.reset_game()

#### 二、游戏模式管理（Game/game_mode.py）
```python
from typing import Dict, Optional, Callable
from Common.constants import GAME_MODES, ROOM_STATUSES
from Common.logger import Logger
from Common.error_handler import GameError
from Game.game_core import GameCore

class GameModeManager:
    """游戏模式管理器（统一管理不同模式的逻辑切换）"""
    def __init__(self, game_core: GameCore):
        self.game_core = game_core
        self.logger = Logger.get_instance()
        self.current_mode = None
        
        # 模式配置（不同模式的初始化参数）
        self.mode_configs = {
            GAME_MODES['PVE']: {
                'ai_type': 'nn+mcts',
                'ai_first': False,
                'desc': '人机对战模式'
            },
            GAME_MODES['PVP']: {
                'desc': '人人对战模式'
            },
            GAME_MODES['ONLINE']: {
                'desc': '联机对战模式'
            },
            GAME_MODES['TRAIN']: {
                'ai_type': 'nn',
                'ai_first': False,
                'desc': '模型训练模式'
            }
        }
    
    def set_mode(self, mode: str, user_id: Optional[int] = None):
        """设置游戏模式"""
        if mode not in self.mode_configs:
            raise GameError(f"不支持的游戏模式: {mode}", 2101)
        
        self.current_mode = mode
        self.logger.info(f"切换到{self.mode_configs[mode]['desc']}")
        
        # 模式初始化
        if mode == GAME_MODES['PVE']:
            self._init_pve_mode()
        elif mode == GAME_MODES['PVP']:
            self._init_pvp_mode()
        elif mode == GAME_MODES['ONLINE']:
            self._init_online_mode(user_id)
        elif mode == GAME_MODES['TRAIN']:
            self._init_train_mode(user_id)
        
        # 通知游戏核心切换模式
        self.game_core.set_mode(mode)
    
    def _init_pve_mode(self):
        """初始化人机对战模式"""
        # 应用模式配置
        config = self.mode_configs[GAME_MODES['PVE']]
        self.game_core.ai_type = config['ai_type']
        self.game_core.ai_first = config['ai_first']
        self.game_core.is_training = False
    
    def _init_pvp_mode(self):
        """初始化人人对战模式"""
        # 清空AI配置
        self.game_core.current_ai = None
        self.game_core.is_training = False
    
    def _init_online_mode(self, user_id: Optional[int]):
        """初始化联机对战模式"""
        if not user_id:
            raise GameError("联机模式需要先登录", 2102)
        
        self.game_core.train_user_id = user_id
        self.game_core.is_training = False
        # 初始化服务器连接
        self.game_core._init_online()
    
    def _init_train_mode(self, user_id: Optional[int]):
        """初始化模型训练模式"""
        if not user_id:
            raise GameError("训练模式需要先登录", 2103)
        
        # 应用模式配置
        config = self.mode_configs[GAME_MODES['TRAIN']]
        self.game_core.ai_type = config['ai_type']
        self.game_core.ai_first = config['ai_first']
        self.game_core.train_user_id = user_id
        self.game_core.is_training = True
        
        # 加载用户的训练数据统计
        from DB.training_data_dao import TrainingDataDAO
        training_dao = TrainingDataDAO()
        data_count = training_dao.get_training_data_count(user_id)
        self.logger.info(f"当前用户训练数据总量: {data_count}")
    
    def create_online_room(self, room_name: str = "默认房间") -> str:
        """创建联机房间"""
        if self.current_mode != GAME_MODES['ONLINE']:
            raise GameError("请先切换到联机模式", 2104)
        
        try:
            # 调用服务器创建房间
            room_id = self.game_core.server.create_room(
                host_id=self.game_core.train_user_id,
                host_nickname=self._get_user_nickname(),
                room_name=room_name
            )
            self.game_core.current_room_id = room_id
            self.logger.info(f"创建联机房间成功，ID: {room_id}，名称: {room_name}")
            return room_id
        except Exception as e:
            self.logger.error(f"创建联机房间失败: {str(e)}")
            raise GameError(f"创建房间失败: {str(e)}", 2105)
    
    def join_online_room(self, room_id: str) -> bool:
        """加入联机房间"""
        if self.current_mode != GAME_MODES['ONLINE']:
            raise GameError("请先切换到联机模式", 2106)
        
        try:
            # 调用服务器加入房间
            success = self.game_core.server.join_room(
                room_id=room_id,
                user_id=self.game_core.train_user_id,
                user_nickname=self._get_user_nickname()
            )
            if success:
                self.game_core.current_room_id = room_id
                self.logger.info(f"加入联机房间成功，ID: {room_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"加入联机房间失败: {str(e)}")
            raise GameError(f"加入房间失败: {str(e)}", 2107)
    
    def leave_online_room(self) -> bool:
        """离开联机房间"""
        if self.current_mode != GAME_MODES['ONLINE'] or not self.game_core.current_room_id:
            raise GameError("你不在任何联机房间中", 2108)
        
        try:
            # 调用服务器离开房间
            success = self.game_core.server.leave_room(
                room_id=self.game_core.current_room_id,
                user_id=self.game_core.train_user_id
            )
            if success:
                self.game_core.current_room_id = None
                self.logger.info(f"离开联机房间成功")
                return True
            return False
        except Exception as e:
            self.logger.error(f"离开联机房间失败: {str(e)}")
            raise GameError(f"离开房间失败: {str(e)}", 2109)
    
    def get_online_room_list(self) -> list:
        """获取联机房间列表"""
        if self.current_mode != GAME_MODES['ONLINE']:
            raise GameError("请先切换到联机模式", 2110)
        
        try:
            # 调用服务器获取房间列表
            return self.game_core.server.get_room_list()
        except Exception as e:
            self.logger.error(f"获取房间列表失败: {str(e)}")
            raise GameError(f"获取房间列表失败: {str(e)}", 2111)
    
    def _get_user_nickname(self) -> str:
        """获取当前用户昵称"""
        from DB.user_dao import UserDAO
        user_dao = UserDAO()
        user = user_dao.get_user_by_id(self.game_core.train_user_id)
        return user['nickname'] if user else f"用户{self.game_core.train_user_id}"

#### 三、棋盘分析器（Game/board_analyzer.py）
```python
import numpy as np
from typing import List, Tuple, Dict, Optional
from Common.constants import PIECE_COLORS, EVAL_WEIGHTS
from Common.logger import Logger
from Common.data_utils import DataUtils
from AI.evaluator import BoardEvaluator

class AdvancedBoardAnalyzer:
    """高级棋盘分析器（扩展评估器功能，支持深度分析）"""
    def __init__(self, board_size: int = 15):
        self.board_size = board_size
        self.evaluator = BoardEvaluator(board_size)
        self.logger = Logger.get_instance()
    
    def analyze_move_quality(self, board: List[List[int]], x: int, y: int, color: int) -> Dict:
        """分析落子质量"""
        # 模拟落子前的局势
        before_score = self.evaluator.evaluate_board(board, color)
        
        # 模拟落子
        temp_board = [row.copy() for row in board]
        temp_board[x][y] = color
        
        # 模拟落子后的局势
        after_score = self.evaluator.evaluate_board(temp_board, color)
        score_change = after_score - before_score
        
        # 判断落子类型
        move_type = self._classify_move_type(temp_board, x, y, color)
        
        # 评估落子风险（对手可能的反击）
        opponent_color = PIECE_COLORS['WHITE'] if color == PIECE_COLORS['BLACK'] else PIECE_COLORS['BLACK']
        opponent_key_moves = self.evaluator.get_key_moves(temp_board, opponent_color, top_k=3)
        max_opponent_score = max([score for _, _, score in opponent_key_moves], default=0.0)
        risk_level = "高" if max_opponent_score >= EVAL_WEIGHTS['FOUR'] else "中" if max_opponent_score >= EVAL_WEIGHTS['THREE'] else "低"
        
        return {
            'move_type': move_type,
            'score_change': score_change,
            'before_score': before_score,
            'after_score': after_score,
            'risk_level': risk_level,
            'opponent_threats': [{'x': x, 'y': y, 'score': s} for x, y, s in opponent_key_moves if s >= EVAL_WEIGHTS['THREE']]
        }
    
    def _classify_move_type(self, board: List[List[int]], x: int, y: int, color: int) -> str:
        """分类落子类型"""
        # 检查是否是必胜落子
        if self.evaluator._is_win(board, color)[0]:
            return "必胜落子"
        
        # 检查是否是防守落子
        opponent_color = PIECE_COLORS['WHITE'] if color == PIECE_COLORS['BLACK'] else PIECE_COLORS['BLACK']
        temp_board = [row.copy() for row in board]
        temp_board[x][y] = PIECE_COLORS['EMPTY']  # 撤销落子
        if self.evaluator._is_win(temp_board, opponent_color)[0]:
            return "防守落子"
        
        # 检查棋型
        segments = self.evaluator._get_line_segments(board, x, y)
        for segment in segments:
            pattern, _ = self.evaluator._match_pattern(segment, color)
            if pattern == 'live_four':
                return "活四进攻"
            elif pattern == 'blocked_four':
                return "冲四进攻"
            elif pattern == 'live_three':
                return "活三进攻"
            elif pattern == 'blocked_three':
                return "冲三进攻"
        
        # 普通落子
        return "普通落子"
    
    def generate_game_report(self, move_history: List[Dict]) -> Dict:
        """生成游戏报告"""
        if not move_history:
            return {'error': '无落子历史'}
        
        # 统计信息
        black_moves = [m for m in move_history if m['color'] == PIECE_COLORS['BLACK']]
        white_moves = [m for m in move_history if m['color'] == PIECE_COLORS['WHITE']]
        total_moves = len(move_history)
        
        # 分析关键落子
        key_moves = []
        board = [[PIECE_COLORS['EMPTY'] for _ in range(self.board_size)] for _ in range(self.board_size)]
        
        for i, move in enumerate(move_history):
            x, y, color = move['x'], move['y'], move['color']
            # 分析落子质量
            quality = self.analyze_move_quality(board, x, y, color)
            # 记录关键落子（进攻、防守、必胜）
            if quality['move_type'] in ["必胜落子", "活四进攻", "冲四进攻", "活三进攻", "防守落子"]:
                key_moves.append({
                    'move_index': i + 1,
                    'x': x,
                    'y': y,
                    'color': color,
                    'move_type': quality['move_type'],
                    'score_change': quality['score_change'],
                    'risk_level': quality['risk_level']
                })
            # 执行落子
            board[x][y] = color
        
        # 最终局势分析
        final_score_black = self.evaluator.evaluate_board(board, PIECE_COLORS['BLACK'])
        final_score_white = self.evaluator.evaluate_board(board, PIECE_COLORS['WHITE'])
        situation = "黑方优势" if final_score_black - final_score_white > EVAL_WEIGHTS['THREE'] else \
                    "白方优势" if final_score_white - final_score_black > EVAL_WEIGHTS['THREE'] else \
                    "局势均衡"
        
        return {
            'total_moves': total_moves,
            'black_moves_count': len(black_moves),
            'white_moves_count': len(white_moves),
            'key_moves': key_moves,
            'final_situation': situation,
            'final_score_black': final_score_black,
            'final_score_white': final_score_white,
            'analysis_time': DataUtils.get_current_time_str()
        }
    
    def predict_best_moves(self, board: List[List[int]], color: int, top_k: int = 3) -> List[Dict]:
        """预测最佳落子（基于深度分析）"""
        # 获取初始关键落子
        key_moves = self.evaluator.get_key_moves(board, color, top_k=10)
        if not key_moves:
            return []
        
        # 对每个候选落子进行深度分析
        move_analysis = []
        for x, y, score in key_moves:
            # 模拟落子
            temp_board = [row.copy() for row in board]
            temp_board[x][y] = color
            
            # 分析落子质量
            quality = self.analyze_move_quality(board, x, y, color)
            
            # 预测对手的反击
            opponent_color = PIECE_COLORS['WHITE'] if color == PIECE_COLORS['BLACK'] else PIECE_COLORS['BLACK']
            opponent_moves = self.evaluator.get_key_moves(temp_board, opponent_color, top_k=2)
            
            move_analysis.append({
                'x': x,
                'y': y,
                'initial_score': score,
                'move_type': quality['move_type'],
                'score_change': quality['score_change'],
                'risk_level': quality['risk_level'],
                'opponent_counter': [{'x': ox, 'y': oy, 'score': os} for ox, oy, os in opponent_moves]
            })
        
        # 按综合得分排序（初始得分*0.6 + 得分变化*0.4 - 风险惩罚）
        move_analysis.sort(
            key=lambda m: m['initial_score'] * 0.6 + m['score_change'] * 0.4 - (1 if m['risk_level'] == '高' else 0.5 if m['risk_level'] == '中' else 0),
            reverse=True
        )
        
        return move_analysis[:top_k]