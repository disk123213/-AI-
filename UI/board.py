import pygame
import math
from typing import Optional, List, Tuple, Dict
from Common.constants import COLORS, PIECE_COLORS, GAME_STATUSES
from Common.error_handler import UIError
from Common.logger import Logger

class Board:
    """棋盘组件"""
    def __init__(
        self,
        x: int,
        y: int,
        size: int = 15,
        cell_size: int = 40,
        on_piece_place: Optional[callable] = None
    ):
        self.x = x  # 棋盘左上角X坐标
        self.y = y  # 棋盘左上角Y坐标
        self.size = size  # 棋盘尺寸（15x15）
        self.cell_size = cell_size  # 单元格大小（像素）
        self.on_piece_place = on_piece_place  # 落子回调函数
        
        # 计算棋盘实际大小
        self.board_width = self.cell_size * (self.size - 1)
        self.board_height = self.cell_size * (self.size - 1)
        
        # 状态变量
        self.board = [[PIECE_COLORS['EMPTY'] for _ in range(self.size)] for _ in range(self.size)]  # 棋盘状态
        self.game_active = False  # 游戏是否激活
        self.ai_thinking = False  # AI是否正在思考
        self.key_position = None  # 关键位置标记
        self.win_line = []  # 获胜线
        
        # 动画相关
        self.animation_pieces = []  # 正在动画的棋子
        self.animation_speed = 10  # 动画速度
        
        # 日志
        self.logger = Logger.get_instance()
    
    def resize(self, x: int, y: int, cell_size: int):
        """调整棋盘大小和位置"""
        self.x = x
        self.y = y
        self.cell_size = cell_size
        self.board_width = self.cell_size * (self.size - 1)
        self.board_height = self.cell_size * (self.size - 1)
    
    def reset(self):
        """重置棋盘"""
        self.board = [[PIECE_COLORS['EMPTY'] for _ in range(self.size)] for _ in range(self.size)]
        self.game_active = False
        self.ai_thinking = False
        self.key_position = None
        self.win_line = []
        self.animation_pieces = []
    
    def set_game_active(self, active: bool):
        """设置游戏激活状态"""
        self.game_active = active
    
    def set_ai_thinking(self, thinking: bool):
        """设置AI思考状态"""
        self.ai_thinking = thinking
    
    def update_board(self, new_board: List[List[int]]):
        """更新棋盘状态"""
        if len(new_board) != self.size or len(new_board[0]) != self.size:
            raise UIError("棋盘尺寸不匹配", 6001)
        
        # 找出新落子的位置（用于动画）
        new_piece = None
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] == PIECE_COLORS['EMPTY'] and new_board[i][j] != PIECE_COLORS['EMPTY']:
                    new_piece = (i, j, new_board[i][j])
                    break
            if new_piece:
                break
        
        # 更新棋盘
        self.board = [row.copy() for row in new_board]
        
        # 添加新棋子动画
        if new_piece:
            x, y, color = new_piece
            self.animation_pieces.append({
                'x': x,
                'y': y,
                'color': color,
                'scale': 0.2,  # 初始缩放比例
                'growing': True  # 是否正在放大
            })
    
    def mark_key_position(self, x: int, y: int):
        """标记关键位置"""
        self.key_position = (x, y)
    
    def draw_win_line(self, win_line: List[Tuple[int, int]]):
        """绘制获胜线"""
        self.win_line = win_line
    
    def _get_screen_position(self, x: int, y: int) -> Tuple[int, int]:
        """将棋盘坐标转换为屏幕坐标"""
        screen_x = self.x + y * self.cell_size
        screen_y = self.y + x * self.cell_size
        return (screen_x, screen_y)
    
    def _get_board_position(self, screen_x: int, screen_y: int) -> Tuple[Optional[int], Optional[int]]:
        """将屏幕坐标转换为棋盘坐标"""
        # 计算棋盘坐标
        x = round((screen_y - self.y) / self.cell_size)
        y = round((screen_x - self.x) / self.cell_size)
        
        # 检查是否在棋盘范围内
        if 0 <= x < self.size and 0 <= y < self.size:
            # 检查是否在单元格中心附近（容错范围）
            center_x, center_y = self._get_screen_position(x, y)
            distance = math.hypot(screen_x - center_x, screen_y - center_y)
            if distance <= self.cell_size / 3:
                return (x, y)
        
        return (None, None)
    
    def _draw_board_lines(self, surface: pygame.Surface):
        """绘制棋盘线条"""
        # 绘制边框
        border_rect = pygame.Rect(
            self.x - 5,
            self.y - 5,
            self.board_width + 10,
            self.board_height + 10
        )
        pygame.draw.rect(surface, COLORS['BOARD_LINE'], border_rect, 3)
        
        # 绘制横线和竖线
        for i in range(self.size):
            # 横线
            start_x = self.x
            start_y = self.y + i * self.cell_size
            end_x = self.x + self.board_width
            end_y = start_y
            pygame.draw.line(surface, COLORS['BOARD_LINE'], (start_x, start_y), (end_x, end_y), 1)
            
            # 竖线
            start_x = self.x + i * self.cell_size
            start_y = self.y
            end_x = start_x
            end_y = self.y + self.board_height
            pygame.draw.line(surface, COLORS['BOARD_LINE'], (start_x, start_y), (end_x, end_y), 1)
        
        # 绘制星位点（天元和四星）
        star_positions = [(3, 3), (3, 11), (7, 7), (11, 3), (11, 11)]
        star_radius = 4
        for x, y in star_positions:
            screen_x, screen_y = self._get_screen_position(x, y)
            pygame.draw.circle(surface, COLORS['BOARD_LINE'], (screen_x, screen_y), star_radius)
    
    def _draw_pieces(self, surface: pygame.Surface, fonts: Dict):
        """绘制棋子"""
        piece_radius = self.cell_size // 2 - 2
        
        # 绘制普通棋子
        for i in range(self.size):
            for j in range(self.size):
                color = self.board[i][j]
                if color == PIECE_COLORS['EMPTY']:
                    continue
                
                screen_x, screen_y = self._get_screen_position(i, j)
                
                # 绘制棋子主体
                if color == PIECE_COLORS['BLACK']:
                    pygame.draw.circle(surface, COLORS['BLACK'], (screen_x, screen_y), piece_radius)
                    # 绘制高光（增加立体感）
                    pygame.draw.circle(surface, (50, 50, 50), (screen_x - 5, screen_y - 5), piece_radius // 2)
                else:
                    pygame.draw.circle(surface, COLORS['WHITE'], (screen_x, screen_y), piece_radius)
                    # 绘制阴影（增加立体感）
                    pygame.draw.circle(surface, (200, 200, 200), (screen_x + 3, screen_y + 3), piece_radius // 2)
                    pygame.draw.circle(surface, (255, 255, 255), (screen_x - 3, screen_y - 3), piece_radius // 2)
        
        # 绘制棋子动画
        self._draw_piece_animations(surface)
        
        # 绘制关键位置标记
        if self.key_position:
            x, y = self.key_position
            screen_x, screen_y = self._get_screen_position(x, y)
            pygame.draw.circle(surface, COLORS['HINT'], (screen_x, screen_y), piece_radius + 3, 2)
    
    def _draw_piece_animations(self, surface: pygame.Surface):
        """绘制棋子动画"""
        if not self.animation_pieces:
            return
        
        piece_radius = self.cell_size // 2 - 2
        
        # 更新并绘制每个动画棋子
        new_animations = []
        for anim in self.animation_pieces:
            x, y, color, scale, growing = anim['x'], anim['y'], anim['color'], anim['scale'], anim['growing']
            
            # 更新缩放比例
            if growing:
                scale += 0.1
                if scale >= 1.0:
                    scale = 1.0
                    growing = False
            else:
                scale -= 0.05
                if scale <= 0.9:
                    growing = True
            
            # 计算当前半径
            current_radius = int(piece_radius * scale)
            
            # 绘制动画棋子
            screen_x, screen_y = self._get_screen_position(x, y)
            if color == PIECE_COLORS['BLACK']:
                pygame.draw.circle(surface, COLORS['BLACK'], (screen_x, screen_y), current_radius)
                pygame.draw.circle(surface, (50, 50, 50), (screen_x - int(5 * scale), screen_y - int(5 * scale)), int(current_radius // 2))
            else:
                pygame.draw.circle(surface, COLORS['WHITE'], (screen_x, screen_y), current_radius)
                pygame.draw.circle(surface, (200, 200, 200), (screen_x + int(3 * scale), screen_y + int(3 * scale)), int(current_radius // 2))
            
            # 保留未完成的动画
            if scale > 0.2:
                new_animations.append({
                    'x': x,
                    'y': y,
                    'color': color,
                    'scale': scale,
                    'growing': growing
                })
        
        self.animation_pieces = new_animations
    
    def _draw_win_line(self, surface: pygame.Surface):
        """绘制获胜线"""
        if not self.win_line or len(self.win_line) < 5:
            return
        
        # 转换为屏幕坐标
        screen_points = [self._get_screen_position(x, y) for x, y in self.win_line]
        
        # 绘制获胜线
        pygame.draw.lines(surface, COLORS['WIN_LINE'], False, screen_points, 3)
        
        # 标记获胜棋子
        piece_radius = self.cell_size // 2 + 2
        for point in screen_points:
            pygame.draw.circle(surface, COLORS['WIN_LINE'], point, piece_radius, 2)
    
    def _draw_ai_thinking(self, surface: pygame.Surface):
        """绘制AI思考中提示"""
        if not self.ai_thinking:
            return
        
        # 绘制半透明遮罩
        overlay = pygame.Surface((self.board_width, self.board_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 50))
        surface.blit(overlay, (self.x, self.y))
        
        # 绘制思考文字
        font = pygame.font.SysFont('Arial', 20, bold=True)
        text = font.render('AI思考中...', True, COLORS['THINKING'])
        text_rect = text.get_rect(
            center=(self.x + self.board_width // 2, self.y + self.board_height // 2)
        )
        surface.blit(text, text_rect)
        
        # 绘制加载动画（旋转的圆圈）
        center_x = self.x + self.board_width // 2 + 100
        center_y = self.y + self.board_height // 2
        radius = 15
        angle = pygame.time.get_ticks() % 360
        for i in range(8):
            current_angle = angle + i * 45
            x = center_x + radius * math.cos(math.radians(current_angle))
            y = center_y + radius * math.sin(math.radians(current_angle))
            alpha = 255 - (i * 30)
            pygame.draw.circle(surface, (255, 215, 0, alpha), (int(x), int(y)), 3)
    
    def draw(self, surface: pygame.Surface, fonts: Dict):
        """绘制棋盘"""
        # 绘制棋盘线条
        self._draw_board_lines(surface)
        
        # 绘制棋子
        self._draw_pieces(surface, fonts)
        
        # 绘制获胜线
        self._draw_win_line(surface)
        
        # 绘制AI思考提示
        self._draw_ai_thinking(surface)
    
    def handle_click(self, mouse_pos: Tuple[int, int]):
        """处理鼠标点击事件"""
        if not self.game_active or self.ai_thinking:
            return
        
        x, y = self._get_board_position(*mouse_pos)
        if x is not None and y is not None:
            # 回调落子事件
            if self.on_piece_place:
                self.on_piece_place(x, y)
    
    def handle_hover(self, mouse_pos: Tuple[int, int]):
        """处理鼠标悬停事件（可选）"""
        pass