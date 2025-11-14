import pygame
import os
from typing import Optional, List, Dict, Callable
from Common.constants import COLORS, GAME_MODES, AI_LEVELS, TRAIN_STATUSES
from Common.config import Config
from Common.logger import Logger
from Common.error_handler import UIError
from DB.model_dao import ModelDAO

class ControlPanel:
    """控制面板组件（用户操作核心）"""
    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        on_mode_change: Optional[Callable[[str], None]] = None,
        on_ai_level_change: Optional[Callable[[str], None]] = None,
        on_start_game: Optional[Callable[[], None]] = None,
        on_stop_game: Optional[Callable[[], None]] = None,
        on_save_model: Optional[Callable[[], None]] = None,
        on_load_model: Optional[Callable[[], None]] = None,
        on_train_model: Optional[Callable[[], None]] = None,
        on_analyze_board: Optional[Callable[[], None]] = None
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        # 回调函数
        self.on_mode_change = on_mode_change
        self.on_ai_level_change = on_ai_level_change
        self.on_start_game = on_start_game
        self.on_stop_game = on_stop_game
        self.on_save_model = on_save_model
        self.on_load_model = on_load_model
        self.on_train_model = on_train_model
        self.on_analyze_board = on_analyze_board
        
        # 配置和日志
        self.config = Config.get_instance()
        self.logger = Logger.get_instance()
        self.model_dao = ModelDAO()
        
        # 状态变量
        self.current_mode = None
        self.current_ai_level = AI_LEVELS['HARD']
        self.current_game_status = "未开始"
        self.current_user = None
        self.move_count = 0
        self.train_status = TRAIN_STATUSES['IDLE']
        self.train_progress = 0
        self.train_loss = 0.0
        self.train_accuracy = 0.0
        
        # 组件状态
        self.show_mode_selection = True
        self.show_ai_level_selection = False
        self.show_train_settings = False
        self.show_model_selection = False
        
        # 输入框状态
        self.input_fields = {
            'model_name': {
                'text': '',
                'active': False,
                'x': self.x + 20,
                'y': self.y + 400,
                'width': 220,
                'height': 30
            },
            'train_epochs': {
                'text': str(self.config.ai_max_epochs),
                'active': False,
                'x': self.x + 20,
                'y': self.y + 450,
                'width': 100,
                'height': 30
            },
            'train_batch': {
                'text': str(self.config.ai_batch_size),
                'active': False,
                'x': self.x + 140,
                'y': self.y + 450,
                'width': 100,
                'height': 30
            }
        }
        
        # 按钮位置和尺寸
        self.buttons = self._init_buttons()
        
        # 加载模型列表
        self.model_list = []
        self.selected_model_id = None
        self.load_model_list()
        
    def _init_buttons(self) -> Dict[str, Dict]:
        """初始化按钮配置"""
        button_width = 120
        button_height = 35
        gap = 15
        
        return {
            # 模式选择按钮
            'pve_mode': {
                'text': '人机对战',
                'x': self.x + 20,
                'y': self.y + 60,
                'width': button_width,
                'height': button_height,
                'action': lambda: self._select_mode(GAME_MODES['PVE'])
            },
            'pvp_mode': {
                'text': '人人对战',
                'x': self.x + 155,
                'y': self.y + 60,
                'width': button_width,
                'height': button_height,
                'action': lambda: self._select_mode(GAME_MODES['PVP'])
            },
            'online_mode': {
                'text': '联机对战',
                'x': self.x + 20,
                'y': self.y + 110,
                'width': button_width,
                'height': button_height,
                'action': lambda: self._select_mode(GAME_MODES['ONLINE'])
            },
            'train_mode': {
                'text': '训练模式',
                'x': self.x + 155,
                'y': self.y + 110,
                'width': button_width,
                'height': button_height,
                'action': lambda: self._select_mode(GAME_MODES['TRAIN'])
            },
            
            # AI难度选择按钮
            'easy_ai': {
                'text': '简单',
                'x': self.x + 20,
                'y': self.y + 60,
                'width': button_width,
                'height': button_height,
                'action': lambda: self._select_ai_level(AI_LEVELS['EASY'])
            },
            'medium_ai': {
                'text': '中等',
                'x': self.x + 155,
                'y': self.y + 60,
                'width': button_width,
                'height': button_height,
                'action': lambda: self._select_ai_level(AI_LEVELS['MEDIUM'])
            },
            'hard_ai': {
                'text': '困难',
                'x': self.x + 20,
                'y': self.y + 110,
                'width': button_width,
                'height': button_height,
                'action': lambda: self._select_ai_level(AI_LEVELS['HARD'])
            },
            'expert_ai': {
                'text': '专家',
                'x': self.x + 155,
                'y': self.y + 110,
                'width': button_width,
                'height': button_height,
                'action': lambda: self._select_ai_level(AI_LEVELS['EXPERT'])
            },
            
            # 游戏控制按钮
            'start_game': {
                'text': '开始游戏',
                'x': self.x + 20,
                'y': self.y + 160,
                'width': button_width,
                'height': button_height,
                'action': self.on_start_game
            },
            'stop_game': {
                'text': '停止游戏',
                'x': self.x + 155,
                'y': self.y + 160,
                'width': button_width,
                'height': button_height,
                'action': self.on_stop_game
            },
            'analyze_board': {
                'text': '分析棋盘',
                'x': self.x + 20,
                'y': self.y + 210,
                'width': 255,
                'height': button_height,
                'action': self.on_analyze_board
            },
            
            # 模型管理按钮
            'save_model': {
                'text': '保存模型',
                'x': self.x + 20,
                'y': self.y + 350,
                'width': 120,
                'height': button_height,
                'action': self.on_save_model
            },
            'load_model': {
                'text': '加载模型',
                'x': self.x + 155,
                'y': self.y + 350,
                'width': 120,
                'height': button_height,
                'action': self._show_model_selection
            },
            'train_model': {
                'text': '训练模型',
                'x': self.x + 20,
                'y': self.y + 500,
                'width': 255,
                'height': button_height,
                'action': self.on_train_model
            },
            'back': {
                'text': '返回',
                'x': self.x + 20,
                'y': self.y + 550,
                'width': 255,
                'height': button_height,
                'action': self._back_to_main
            }
        }
    
    def resize(self, x: int, y: int, width: int, height: int):
        """调整控制面板大小和位置"""
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        # 更新输入框位置
        self.input_fields['model_name']['x'] = self.x + 20
        self.input_fields['model_name']['y'] = self.y + 400
        self.input_fields['train_epochs']['x'] = self.x + 20
        self.input_fields['train_epochs']['y'] = self.y + 450
        self.input_fields['train_batch']['x'] = self.x + 140
        self.input_fields['train_batch']['y'] = self.y + 450
        
        # 更新按钮位置
        self.buttons = self._init_buttons()
    
    def reset(self):
        """重置控制面板状态"""
        self.current_mode = None
        self.current_ai_level = AI_LEVELS['HARD']
        self.current_game_status = "未开始"
        self.move_count = 0
        self.train_status = TRAIN_STATUSES['IDLE']
        self.train_progress = 0
        self.train_loss = 0.0
        self.train_accuracy = 0.0
        self.show_mode_selection = True
        self.show_ai_level_selection = False
        self.show_train_settings = False
        self.show_model_selection = False
        
        # 清空输入框
        for field in self.input_fields.values():
            field['text'] = ''
        self.input_fields['train_epochs']['text'] = str(self.config.ai_max_epochs)
        self.input_fields['train_batch']['text'] = str(self.config.ai_batch_size)
    
    def update_user_info(self, user: Dict):
        """更新用户信息"""
        self.current_user = user
        # 重新加载用户的模型列表
        if user and user['user_id'] != -1:
            self.load_model_list(user['user_id'])
    
    def update_mode_info(self, mode: str):
        """更新模式信息"""
        self.current_mode = mode
        self.show_mode_selection = False
        
        # 人机对战和训练模式显示AI难度选择
        if mode in [GAME_MODES['PVE'], GAME_MODES['TRAIN']]:
            self.show_ai_level_selection = True
        else:
            self.show_ai_level_selection = False
            self.show_train_settings = (mode == GAME_MODES['TRAIN'])
    
    def update_ai_level(self, level: str):
        """更新AI难度"""
        self.current_ai_level = level
        self.show_ai_level_selection = False
        self.show_train_settings = (self.current_mode == GAME_MODES['TRAIN'])
    
    def update_game_status(self, status: str):
        """更新游戏状态"""
        self.current_game_status = status
    
    def update_move_count(self, count: int):
        """更新落子计数"""
        self.move_count = count
    
    def update_train_status(self, status: str):
        """更新训练状态"""
        self.train_status = status
        if status == TRAIN_STATUSES['IDLE']:
            self.train_progress = 0
    
    def update_train_progress(self, epoch: int, loss: float, accuracy: float):
        """更新训练进度"""
        self.train_progress = int((epoch / int(self.input_fields['train_epochs']['text'])) * 100)
        self.train_loss = loss
        self.train_accuracy = accuracy
    
    def show_mode_selection(self):
        """显示模式选择"""
        self.show_mode_selection = True
        self.show_ai_level_selection = False
        self.show_train_settings = False
        self.show_model_selection = False
    
    def show_error(self, message: str):
        """显示错误消息"""
        self.error_message = message
        # 3秒后自动清除错误消息
        import threading
        threading.Timer(3, self.clear_error).start()
    
    def show_message(self, message: str):
        """显示普通消息"""
        self.message = message
        # 3秒后自动清除消息
        import threading
        threading.Timer(3, self.clear_message).start()
    
    def clear_error(self):
        """清除错误消息"""
        self.error_message = None
    
    def clear_message(self):
        """清除普通消息"""
        self.message = None
    
    def load_model_list(self, user_id: Optional[int] = None):
        """加载模型列表"""
        try:
            if user_id:
                self.model_list = self.model_dao.get_models_by_user(user_id)
            else:
                self.model_list = self.model_dao.get_default_models()
            self.logger.info(f"加载模型列表成功，共{len(self.model_list)}个模型")
        except Exception as e:
            self.logger.error(f"加载模型列表失败: {str(e)}")
            self.model_list = []
    
    def _show_model_selection(self):
        """显示模型选择列表"""
        self.show_model_selection = True
        self.show_mode_selection = False
        self.show_ai_level_selection = False
        self.show_train_settings = False
        # 重新加载模型列表
        if self.current_user and self.current_user['user_id'] != -1:
            self.load_model_list(self.current_user['user_id'])
    
    def _select_mode(self, mode: str):
        """选择游戏模式"""
        if self.on_mode_change:
            self.on_mode_change(mode)
    
    def _select_ai_level(self, level: str):
        """选择AI难度"""
        if self.on_ai_level_change:
            self.on_ai_level_change(level)
    
    def _select_model(self, model_id: int):
        """选择模型"""
        self.selected_model_id = model_id
        self.show_model_selection = False
        # 找到选中的模型
        selected_model = next((m for m in self.model_list if m['model_id'] == model_id), None)
        if selected_model:
            self.show_message(f"已选择模型: {selected_model['model_name']}")
    
    def _back_to_main(self):
        """返回主界面"""
        if self.show_model_selection:
            self.show_model_selection = False
            self.show_train_settings = (self.current_mode == GAME_MODES['TRAIN'])
        elif self.show_train_settings:
            self.show_train_settings = False
            self.show_ai_level_selection = (self.current_mode in [GAME_MODES['PVE'], GAME_MODES['TRAIN']])
        elif self.show_ai_level_selection:
            self.show_ai_level_selection = False
            self.show_mode_selection = True
        elif self.show_mode_selection:
            pass
    
    def get_model_name(self) -> str:
        """获取输入的模型名称"""
        return self.input_fields['model_name']['text'].strip()
    
    def get_train_epochs(self) -> int:
        """获取训练轮数"""
        try:
            return int(self.input_fields['train_epochs']['text'].strip())
        except:
            return self.config.ai_max_epochs
    
    def get_train_batch_size(self) -> int:
        """获取批次大小"""
        try:
            return int(self.input_fields['train_batch']['text'].strip())
        except:
            return self.config.ai_batch_size
    
    def get_selected_model(self) -> Optional[int]:
        """获取选中的模型ID"""
        return self.selected_model_id
    
    def show_analysis_report(self, report: Dict):
        """显示棋盘分析报告"""
        self.analysis_report = report
    
    def _draw_panel_bg(self, surface: pygame.Surface):
        """绘制控制面板背景"""
        # 面板背景
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, COLORS['PANEL_BG'], panel_rect)
        pygame.draw.rect(surface, COLORS['PANEL_BORDER'], panel_rect, 2)
        
        # 标题背景
        title_rect = pygame.Rect(self.x, self.y, self.width, 40)
        pygame.draw.rect(surface, COLORS['BUTTON'], title_rect)
    
    def _draw_title(self, surface: pygame.Surface, fonts: Dict):
        """绘制标题"""
        # 面板标题
        title_text = fonts['sub_title'].render('控制面板', True, COLORS['TEXT_LIGHT'])
        title_rect = title_text.get_rect(center=(self.x + self.width//2, self.y + 20))
        surface.blit(title_text, title_rect)
        
        # 用户信息
        if self.current_user:
            user_text = fonts['small'].render(f"当前用户: {self.current_user['nickname']}", True, COLORS['TEXT'])
            surface.blit(user_text, (self.x + 10, self.y + self.height - 30))
    
    def _draw_mode_selection(self, surface: pygame.Surface, fonts: Dict):
        """绘制模式选择界面"""
        # 标题
        title = fonts['normal'].render('选择游戏模式', True, COLORS['TEXT'])
        surface.blit(title, (self.x + 20, self.y + 20))
        
        # 绘制模式按钮
        self._draw_buttons(surface, fonts, ['pve_mode', 'pvp_mode', 'online_mode', 'train_mode'])
    
    def _draw_ai_level_selection(self, surface: pygame.Surface, fonts: Dict):
        """绘制AI难度选择界面"""
        # 标题
        title = fonts['normal'].render('选择AI难度', True, COLORS['TEXT'])
        surface.blit(title, (self.x + 20, self.y + 20))
        
        # 当前模式
        mode_text = fonts['small'].render(f"当前模式: {self._get_mode_text()}", True, COLORS['TEXT'])
        surface.blit(mode_text, (self.x + 20, self.y + 40))
        
        # 绘制AI难度按钮
        self._draw_buttons(surface, fonts, ['easy_ai', 'medium_ai', 'hard_ai', 'expert_ai'])
        
        # 返回按钮
        self._draw_button(surface, fonts, self.buttons['back'])
    
    def _draw_train_settings(self, surface: pygame.Surface, fonts: Dict):
        """绘制训练设置界面"""
        # 标题
        title = fonts['normal'].render('模型训练设置', True, COLORS['TEXT'])
        surface.blit(title, (self.x + 20, self.y + 20))
        
        # 当前模式和AI难度
        mode_text = fonts['small'].render(f"当前模式: {self._get_mode_text()}", True, COLORS['TEXT'])
        surface.blit(mode_text, (self.x + 20, self.y + 40))
        ai_text = fonts['small'].render(f"AI难度: {self._get_ai_level_text()}", True, COLORS['TEXT'])
        surface.blit(ai_text, (self.x + 20, self.y + 60))
        
        # 游戏状态信息
        status_text = fonts['small'].render(f"游戏状态: {self.current_game_status}", True, COLORS['TEXT'])
        surface.blit(status_text, (self.x + 20, self.y + 100))
        move_text = fonts['small'].render(f"落子计数: {self.move_count}", True, COLORS['TEXT'])
        surface.blit(move_text, (self.x + 20, self.y + 120))
        
        # 游戏控制按钮
        self._draw_buttons(surface, fonts, ['start_game', 'stop_game', 'analyze_board'])
        
        # 模型名称输入
        model_name_label = fonts['small'].render('模型名称:', True, COLORS['TEXT'])
        surface.blit(model_name_label, (self.x + 20, self.y + 380))
        self._draw_input_field(surface, fonts, 'model_name')
        
        # 模型管理按钮
        self._draw_buttons(surface, fonts, ['save_model', 'load_model'])
        
        # 训练参数
        train_param_label = fonts['small'].render('训练参数:', True, COLORS['TEXT'])
        surface.blit(train_param_label, (self.x + 20, self.y + 430))
        
        epochs_label = fonts['small'].render('轮数:', True, COLORS['TEXT'])
        surface.blit(epochs_label, (self.x + 20, self.y + 470))
        self._draw_input_field(surface, fonts, 'train_epochs')
        
        batch_label = fonts['small'].render('批次:', True, COLORS['TEXT'])
        surface.blit(batch_label, (self.x + 140, self.y + 470))
        self._draw_input_field(surface, fonts, 'train_batch')
        
        # 训练按钮
        self._draw_button(surface, fonts, self.buttons['train_model'])
        
        # 训练状态
        if self.train_status != TRAIN_STATUSES['IDLE']:
            train_status_text = fonts['small'].render(f"训练状态: {self.train_status}", True, COLORS['TEXT'])
            surface.blit(train_status_text, (self.x + 20, self.y + 530))
            
            # 训练进度条
            progress_rect = pygame.Rect(self.x + 20, self.y + 550, 255, 10)
            pygame.draw.rect(surface, COLORS['PANEL_BORDER'], progress_rect)
            fill_width = int(255 * (self.train_progress / 100))
            fill_rect = pygame.Rect(self.x + 20, self.y + 550, fill_width, 10)
            pygame.draw.rect(surface, COLORS['BUTTON'], fill_rect)
            
            # 训练指标
            metric_text = fonts['small'].render(
                f"损失: {self.train_loss:.4f} | 准确率: {self.train_accuracy:.4f}",
                True,
                COLORS['TEXT']
            )
            surface.blit(metric_text, (self.x + 20, self.y + 570))
        
        # 返回按钮
        self._draw_button(surface, fonts, self.buttons['back'])
    
    def _draw_model_selection(self, surface: pygame.Surface, fonts: Dict):
        """绘制模型选择界面"""
        # 标题
        title = fonts['normal'].render('选择模型', True, COLORS['TEXT'])
        surface.blit(title, (self.x + 20, self.y + 20))
        
        # 模型列表区域
        list_rect = pygame.Rect(self.x + 20, self.y + 50, 255, 400)
        pygame.draw.rect(surface, COLORS['PANEL_BORDER'], list_rect)
        
        # 绘制模型列表
        y_offset = 0
        for model in self.model_list:
            model_rect = pygame.Rect(self.x + 20, self.y + 50 + y_offset, 255, 30)
            if model['model_id'] == self.selected_model_id:
                pygame.draw.rect(surface, COLORS['BUTTON_HOVER'], model_rect)
            else:
                pygame.draw.rect(surface, COLORS['PANEL_BG'], model_rect)
            
            # 模型名称
            model_name = fonts['small'].render(model['model_name'], True, COLORS['TEXT'])
            surface.blit(model_name, (self.x + 30, self.y + 55 + y_offset))
            
            # 模型准确率
            acc_text = fonts['small'].render(f"准确率: {model['accuracy']:.2%}", True, COLORS['TEXT'])
            surface.blit(acc_text, (self.x + 180, self.y + 55 + y_offset))
            
            y_offset += 30
            if y_offset >= 400:
                break
        
        # 返回按钮
        self._draw_button(surface, fonts, self.buttons['back'])
    
    def _draw_buttons(self, surface: pygame.Surface, fonts: Dict, button_names: List[str]):
        """绘制多个按钮"""
        for name in button_names:
            if name in self.buttons:
                self._draw_button(surface, fonts, self.buttons[name])
    
    def _draw_button(self, surface: pygame.Surface, fonts: Dict, button: Dict):
        """绘制单个按钮"""
        button_rect = pygame.Rect(button['x'], button['y'], button['width'], button['height'])
        
        # 检查鼠标悬停
        mouse_pos = pygame.mouse.get_pos()
        if button_rect.collidepoint(mouse_pos):
            pygame.draw.rect(surface, COLORS['BUTTON_HOVER'], button_rect)
        else:
            pygame.draw.rect(surface, COLORS['BUTTON'], button_rect)
        
        # 按钮边框
        pygame.draw.rect(surface, COLORS['PANEL_BORDER'], button_rect, 2)
        
        # 按钮文字
        text = fonts['small'].render(button['text'], True, COLORS['TEXT_LIGHT'])
        text_rect = text.get_rect(center=(button['x'] + button['width']//2, button['y'] + button['height']//2))
        surface.blit(text, text_rect)
    
    def _draw_input_field(self, surface: pygame.Surface, fonts: Dict, field_name: str):
        """绘制输入框"""
        field = self.input_fields[field_name]
        field_rect = pygame.Rect(field['x'], field['y'], field['width'], field['height'])
        
        # 输入框背景
        if field['active']:
            pygame.draw.rect(surface, COLORS['WHITE'], field_rect)
        else:
            pygame.draw.rect(surface, COLORS['PANEL_BG'], field_rect)
        
        # 输入框边框
        pygame.draw.rect(surface, COLORS['BUTTON'], field_rect, 2)
        
        # 输入框文字
        text = fonts['small'].render(field['text'], True, COLORS['TEXT'])
        surface.blit(text, (field['x'] + 5, field['y'] + 5))
        
        # 光标
        if field['active'] and pygame.time.get_ticks() % 1000 < 500:
            cursor_x = field['x'] + 5 + fonts['small'].size(field['text'])[0]
            pygame.draw.line(surface, COLORS['TEXT'], (cursor_x, field['y'] + 5), (cursor_x, field['y'] + 25), 2)
    
    def _draw_messages(self, surface: pygame.Surface, fonts: Dict):
        """绘制消息提示"""
        # 错误消息
        if hasattr(self, 'error_message') and self.error_message:
            error_surface = pygame.Surface((self.width - 20, 30), pygame.SRCALPHA)
            error_surface.fill((255, 0, 0, 150))
            surface.blit(error_surface, (self.x + 10, self.y + self.height - 70))
            
            error_text = fonts['small'].render(self.error_message, True, COLORS['TEXT_LIGHT'])
            error_rect = error_text.get_rect(center=(self.x + self.width//2, self.y + self.height - 55))
            surface.blit(error_text, error_rect)
        
        # 普通消息
        if hasattr(self, 'message') and self.message:
            msg_surface = pygame.Surface((self.width - 20, 30), pygame.SRCALPHA)
            msg_surface.fill((0, 255, 0, 150))
            surface.blit(msg_surface, (self.x + 10, self.y + self.height - 70))
            
            msg_text = fonts['small'].render(self.message, True, COLORS['TEXT_LIGHT'])
            msg_rect = msg_text.get_rect(center=(self.x + self.width//2, self.y + self.height - 55))
            surface.blit(msg_text, msg_rect)
    
    def _get_mode_text(self) -> str:
        """获取模式显示文本"""
        mode_map = {
            GAME_MODES['PVE']: '人机对战',
            GAME_MODES['PVP']: '人人对战',
            GAME_MODES['ONLINE']: '联机对战',
            GAME_MODES['TRAIN']: '训练模式'
        }
        return mode_map.get(self.current_mode, '未知模式')
    
    def _get_ai_level_text(self) -> str:
        """获取AI难度显示文本"""
        level_map = {
            AI_LEVELS['EASY']: '简单',
            AI_LEVELS['MEDIUM']: '中等',
            AI_LEVELS['HARD']: '困难',
            AI_LEVELS['EXPERT']: '专家'
        }
        return level_map.get(self.current_ai_level, '未知难度')
    
    def draw(self, surface: pygame.Surface, fonts: Dict):
        """绘制控制面板"""
        # 绘制背景和标题
        self._draw_panel_bg(surface)
        self._draw_title(surface, fonts)
        
        # 根据当前状态绘制不同界面
        if self.show_mode_selection:
            self._draw_mode_selection(surface, fonts)
        elif self.show_ai_level_selection:
            self._draw_ai_level_selection(surface, fonts)
        elif self.show_train_settings:
            self._draw_train_settings(surface, fonts)
        elif self.show_model_selection:
            self._draw_model_selection(surface, fonts)
        
        # 绘制消息提示
        self._draw_messages(surface, fonts)
    
    def handle_click(self, mouse_pos: Tuple[int, int]):
        """处理鼠标点击事件"""
        # 检查输入框点击
        for field_name, field in self.input_fields.items():
            field_rect = pygame.Rect(field['x'], field['y'], field['width'], field['height'])
            if field_rect.collidepoint(mouse_pos):
                # 激活当前输入框，取消其他输入框激活状态
                for f in self.input_fields.values():
                    f['active'] = False
                field['active'] = True
                return
        
        # 检查按钮点击
        for button in self.buttons.values():
            button_rect = pygame.Rect(button['x'], button['y'], button['width'], button['height'])
            if button_rect.collidepoint(mouse_pos) and button['action']:
                button['action']()
                return
        
        # 检查模型列表点击
        if self.show_model_selection:
            y_offset = 0
            for model in self.model_list:
                model_rect = pygame.Rect(self.x + 20, self.y + 50 + y_offset, 255, 30)
                if model_rect.collidepoint(mouse_pos):
                    self._select_model(model['model_id'])
                    return
                y_offset += 30
    
    def handle_hover(self, mouse_pos: Tuple[int, int]):
        """处理鼠标悬停事件"""
        pass
    
    def handle_keyboard(self, event: pygame.event.Event):
        """处理键盘事件"""
        # 处理输入框输入
        for field_name, field in self.input_fields.items():
            if field['active']:
                if event.key == pygame.K_BACKSPACE:
                    field['text'] = field['text'][:-1]
                elif event.key == pygame.K_RETURN:
                    field['active'] = False
                else:
                    # 只允许输入数字（训练参数）或任意字符（模型名称）
                    if field_name in ['train_epochs', 'train_batch']:
                        if event.unicode.isdigit():
                            field['text'] += event.unicode
                    else:
                        field['text'] += event.unicode
                return