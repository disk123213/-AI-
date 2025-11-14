import pygame
from typing import Optional, Callable, Tuple
from Common.constants import COLORS, WINDOW_CONFIG
from Common.logger import Logger
from Common.error_handler import UIError

class MainMenu:
    """主菜单（登录、注册、游客登录）"""
    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        on_login: Optional[Callable[[str, str], None]] = None,
        on_register: Optional[Callable[[str, str, str], None]] = None,
        on_guest_login: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        # 回调函数
        self.on_login = on_login
        self.on_register = on_register
        self.on_guest_login = on_guest_login
        self.on_exit = on_exit
        
        # 日志
        self.logger = Logger.get_instance()
        
        # 输入框状态
        self.input_fields = {
            'login_username': {
                'text': '',
                'active': False,
                'x': self.x + 50,
                'y': self.y + 80,
                'width': 300,
                'height': 35,
                'label': '用户名'
            },
            'login_password': {
                'text': '',
                'active': False,
                'x': self.x + 50,
                'y': self.y + 130,
                'width': 300,
                'height': 35,
                'label': '密码',
                'password': True
            },
            'reg_username': {
                'text': '',
                'active': False,
                'x': self.x + 50,
                'y': self.y + 80,
                'width': 300,
                'height': 35,
                'label': '用户名'
            },
            'reg_password': {
                'text': '',
                'active': False,
                'x': self.x + 50,
                'y': self.y + 130,
                'width': 300,
                'height': 35,
                'label': '密码',
                'password': True
            },
            'reg_nickname': {
                'text': '',
                'active': False,
                'x': self.x + 50,
                'y': self.y + 180,
                'width': 300,
                'height': 35,
                'label': '昵称'
            }
        }
        
        # 按钮配置
        self.buttons = {
            'login': {
                'text': '登录',
                'x': self.x + 50,
                'y': self.y + 180,
                'width': 140,
                'height': 40,
                'action': self._handle_login
            },
            'register': {
                'text': '注册',
                'x': self.x + 210,
                'y': self.y + 180,
                'width': 140,
                'height': 40,
                'action': self._switch_to_register
            },
            'guest_login': {
                'text': '游客登录',
                'x': self.x + 50,
                'y': self.y + 230,
                'width': 140,
                'height': 40,
                'action': self.on_guest_login
            },
            'exit': {
                'text': '退出',
                'x': self.x + 210,
                'y': self.y + 230,
                'width': 140,
                'height': 40,
                'action': self.on_exit
            },
            'reg_confirm': {
                'text': '确认注册',
                'x': self.x + 50,
                'y': self.y + 230,
                'width': 140,
                'height': 40,
                'action': self._handle_register
            },
            'reg_back': {
                'text': '返回登录',
                'x': self.x + 210,
                'y': self.y + 230,
                'width': 140,
                'height': 40,
                'action': self._switch_to_login
            }
        }
        
        # 状态变量
        self.is_login_mode = True
        self.error_message = None
        self.message = None
    
    def _switch_to_login(self):
        """切换到登录模式"""
        self.is_login_mode = True
        self.error_message = None
        self.message = None
    
    def _switch_to_register(self):
        """切换到注册模式"""
        self.is_login_mode = False
        self.error_message = None
        self.message = None
    
    def _handle_login(self):
        """处理登录"""
        username = self.input_fields['login_username']['text'].strip()
        password = self.input_fields['login_password']['text'].strip()
        
        if not username or not password:
            self.error_message = "用户名和密码不能为空"
            return
        
        if self.on_login:
            self.on_login(username, password)
    
    def _handle_register(self):
        """处理注册"""
        username = self.input_fields['reg_username']['text'].strip()
        password = self.input_fields['reg_password']['text'].strip()
        nickname = self.input_fields['reg_nickname']['text'].strip()
        
        if not username or not password or not nickname:
            self.error_message = "用户名、密码和昵称不能为空"
            return
        
        if len(password) < 6:
            self.error_message = "密码长度不能少于6位"
            return
        
        if self.on_register:
            self.on_register(username, password, nickname)
    
    def show_error(self, message: str):
        """显示错误消息"""
        self.error_message = message
    
    def show_message(self, message: str):
        """显示普通消息"""
        self.message = message
    
    def _draw_bg(self, surface: pygame.Surface):
        """绘制背景"""
        # 半透明背景
        bg_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 200))
        surface.blit(bg_surface, (self.x, self.y))
        
        # 白色边框
        border_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, COLORS['WHITE'], border_rect, 2)
        
        # 标题背景
        title_rect = pygame.Rect(self.x, self.y, self.width, 50)
        pygame.draw.rect(surface, COLORS['BUTTON'], title_rect)
    
    def _draw_title(self, surface: pygame.Surface, fonts: Dict):
        """绘制标题"""
        title_text = fonts['title'].render(
            '五子棋AI对战平台',
            True,
            COLORS['TEXT_LIGHT']
        )
        title_rect = title_text.get_rect(center=(self.x + self.width//2, self.y + 25))
        surface.blit(title_text, title_rect)
        
        # 子标题
        sub_title = fonts['normal'].render(
            '登录' if self.is_login_mode else '注册',
            True,
            COLORS['TEXT_LIGHT']
        )
        sub_rect = sub_title.get_rect(center=(self.x + self.width//2, self.y + 60))
        surface.blit(sub_title, sub_rect)
    
    def _draw_input_fields(self, surface: pygame.Surface, fonts: Dict):
        """绘制输入框"""
        if self.is_login_mode:
            fields = ['login_username', 'login_password']
        else:
            fields = ['reg_username', 'reg_password', 'reg_nickname']
        
        for field_name in fields:
            field = self.input_fields[field_name]
            # 绘制标签
            label = fonts['small'].render(field['label'], True, COLORS['TEXT_LIGHT'])
            surface.blit(label, (field['x'], field['y'] - 20))
            
            # 绘制输入框
            field_rect = pygame.Rect(field['x'], field['y'], field['width'], field['height'])
            if field['active']:
                pygame.draw.rect(surface, COLORS['WHITE'], field_rect)
            else:
                pygame.draw.rect(surface, (50, 50, 50), field_rect)
            pygame.draw.rect(surface, COLORS['BUTTON'], field_rect, 2)
            
            # 绘制输入文本（密码隐藏）
            display_text = field['text'] if not field.get('password', False) else '*' * len(field['text'])
            text = fonts['normal'].render(display_text, True, COLORS['TEXT'])
            surface.blit(text, (field['x'] + 5, field['y'] + 5))
            
            # 绘制光标
            if field['active'] and pygame.time.get_ticks() % 1000 < 500:
                cursor_x = field['x'] + 5 + fonts['normal'].size(display_text)[0]
                pygame.draw.line(surface, COLORS['TEXT'], (cursor_x, field['y'] + 5), (cursor_x, field['y'] + 30), 2)
    
    def _draw_buttons(self, surface: pygame.Surface, fonts: Dict):
        """绘制按钮"""
        if self.is_login_mode:
            button_names = ['login', 'register', 'guest_login', 'exit']
        else:
            button_names = ['reg_confirm', 'reg_back']
        
        for name in button_names:
            button = self.buttons[name]
            button_rect = pygame.Rect(button['x'], button['y'], button['width'], button['height'])
            
            # 检查鼠标悬停
            mouse_pos = pygame.mouse.get_pos()
            if button_rect.collidepoint(mouse_pos):
                pygame.draw.rect(surface, COLORS['BUTTON_HOVER'], button_rect)
            else:
                pygame.draw.rect(surface, COLORS['BUTTON'], button_rect)
            
            # 按钮边框
            pygame.draw.rect(surface, COLORS['WHITE'], button_rect, 2)
            
            # 按钮文字
            text = fonts['normal'].render(button['text'], True, COLORS['TEXT_LIGHT'])
            text_rect = text.get_rect(center=(button['x'] + button['width']//2, button['y'] + button['height']//2))
            surface.blit(text, text_rect)
    
    def _draw_messages(self, surface: pygame.Surface, fonts: Dict):
        """绘制消息提示"""
        # 错误消息
        if self.error_message:
            error_text = fonts['small'].render(self.error_message, True, (255, 0, 0))
            error_rect = error_text.get_rect(center=(self.x + self.width//2, self.y + 280))
            surface.blit(error_text, error_rect)
        
        # 普通消息
        if self.message:
            msg_text = fonts['small'].render(self.message, True, (0, 255, 0))
            msg_rect = msg_text.get_rect(center=(self.x + self.width//2, self.y + 280))
            surface.blit(msg_text, msg_rect)
    
    def draw(self, surface: pygame.Surface, fonts: Dict):
        """绘制主菜单"""
        self._draw_bg(surface)
        self._draw_title(surface, fonts)
        self._draw_input_fields(surface, fonts)
        self._draw_buttons(surface, fonts)
        self._draw_messages(surface, fonts)
    
    def handle_click(self, mouse_pos: Tuple[int, int]):
        """处理鼠标点击事件"""
        # 检查输入框点击
        for field_name, field in self.input_fields.items():
            # 只处理当前模式的输入框
            if self.is_login_mode and not field_name.startswith('login_'):
                continue
            if not self.is_login_mode and not field_name.startswith('reg_'):
                continue
            
            field_rect = pygame.Rect(field['x'], field['y'], field['width'], field['height'])
            if field_rect.collidepoint(mouse_pos):
                # 激活当前输入框，取消其他输入框激活状态
                for f in self.input_fields.values():
                    f['active'] = False
                field['active'] = True
                self.error_message = None
                self.message = None
                return
        
        # 检查按钮点击
        if self.is_login_mode:
            button_names = ['login', 'register', 'guest_login', 'exit']
        else:
            button_names = ['reg_confirm', 'reg_back']
        
        for name in button_names:
            button = self.buttons[name]
            button_rect = pygame.Rect(button['x'], button['y'], button['width'], button['height'])
            if button_rect.collidepoint(mouse_pos) and button['action']:
                button['action']()
                self.error_message = None
                self.message = None
                return
    
    def handle_keyboard(self, event: pygame.event.Event):
        """处理键盘事件"""
        # 处理输入框输入
        for field_name, field in self.input_fields.items():
            # 只处理当前模式的输入框
            if self.is_login_mode and not field_name.startswith('login_'):
                continue
            if not self.is_login_mode and not field_name.startswith('reg_'):
                continue
            
            if field['active']:
                if event.key == pygame.K_BACKSPACE:
                    field['text'] = field['text'][:-1]
                elif event.key == pygame.K_RETURN:
                    field['active'] = False
                    if self.is_login_mode:
                        self._handle_login()
                    else:
                        self._handle_register()
                else:
                    field['text'] += event.unicode
                return

class GameMenu:
    """游戏菜单（新游戏、切换模式、设置等）"""
    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        on_new_game: Optional[Callable[[], None]] = None,
        on_change_mode: Optional[Callable[[], None]] = None,
        on_settings: Optional[Callable[[], None]] = None,
        on_back_menu: Optional[Callable[[], None]] = None
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        # 回调函数
        self.on_new_game = on_new_game
        self.on_change_mode = on_change_mode
        self.on_settings = on_settings
        self.on_back_menu = on_back_menu
        
        # 按钮配置
        self.buttons = {
            'new_game': {
                'text': '新游戏',
                'x': self.x + 10,
                'y': self.y + 10,
                'width': 120,
                'height': 35,
                'action': self.on_new_game
            },
            'change_mode': {
                'text': '切换模式',
                'x': self.x + 10,
                'y': self.y + 55,
                'width': 120,
                'height': 35,
                'action': self.on_change_mode
            },
            'settings': {
                'text': '设置',
                'x': self.x + 10,
                'y': self.y + 100,
                'width': 120,
                'height': 35,
                'action': self.on_settings
            },
            'back_menu': {
                'text': '返回主菜单',
                'x': self.x + 10,
                'y': self.y + 145,
                'width': 120,
                'height': 35,
                'action': self.on_back_menu
            }
        }
    
    def move(self, x: int, y: int):
        """移动菜单位置"""
        self.x = x
        self.y = y
        
        # 更新按钮位置
        y_offset = 0
        for name in ['new_game', 'change_mode', 'settings', 'back_menu']:
            self.buttons[name]['x'] = self.x + 10
            self.buttons[name]['y'] = self.y + 10 + y_offset
            y_offset += 45
    
    def _draw_bg(self, surface: pygame.Surface):
        """绘制背景"""
        bg_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, COLORS['PANEL_BG'], bg_rect)
        pygame.draw.rect(surface, COLORS['PANEL_BORDER'], bg_rect, 2)
    
    def _draw_buttons(self, surface: pygame.Surface, fonts: Dict):
        """绘制按钮"""
        for button in self.buttons.values():
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
    
    def draw(self, surface: pygame.Surface, fonts: Dict):
        """绘制游戏菜单"""
        self._draw_bg(surface)
        self._draw_buttons(surface, fonts)
    
    def handle_click(self, mouse_pos: Tuple[int, int]):
        """处理鼠标点击事件"""
        for button in self.buttons.values():
            button_rect = pygame.Rect(button['x'], button['y'], button['width'], button['height'])
            if button_rect.collidepoint(mouse_pos) and button['action']:
                button['action']()
                return
    
    def handle_hover(self, mouse_pos: Tuple[int, int]):
        """处理鼠标悬停事件"""
        pass