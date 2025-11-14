import pygame
import math
from typing import Tuple, Optional
from Common.constants import COLORS, PIECE_COLORS
from Common.error_handler import UIError

class Piece:
    """棋子组件（单个棋子）"""
    def __init__(
        self,
        x: int,
        y: int,
        color: int,
        cell_size: int,
        is_ai: bool = False,
        is_winner: bool = False
    ):
        self.x = x  # 棋盘X坐标
        self.y = y  # 棋盘Y坐标
        self.color = color  # 棋子颜色
        self.cell_size = cell_size  # 单元格大小
        self.is_ai = is_ai  # 是否是AI落子
        self.is_winner = is_winner  # 是否是获胜棋子
        
        # 屏幕坐标（动态计算）
        self.screen_x = 0
        self.screen_y = 0
        
        # 棋子半径
        self.radius = self.cell_size // 2 - 2
        self.border_radius = self.radius + 2
        
        # 动画属性
        self.animation_progress = 0  # 动画进度（0-100）
        self.animation_type = None  # 动画类型：None, 'place', 'remove', 'highlight'
        self.animation_speed = 5  # 动画速度
        
        # 高亮属性
        self.highlighted = False
        self.highlight_intensity = 0  # 高亮强度（0-255）
    
    def set_screen_position(self, base_x: int, base_y: int):
        """设置屏幕坐标（基于棋盘位置）"""
        self.screen_x = base_x + self.y * self.cell_size
        self.screen_y = base_y + self.x * self.cell_size
    
    def start_animation(self, animation_type: str):
        """开始动画"""
        self.animation_type = animation_type
        self.animation_progress = 0
        if animation_type == 'highlight':
            self.highlighted = True
    
    def stop_animation(self):
        """停止动画"""
        self.animation_type = None
        self.animation_progress = 0
        if self.highlighted:
            self.highlighted = False
            self.highlight_intensity = 0
    
    def update(self):
        """更新棋子状态（动画、高亮等）"""
        # 处理动画
        if self.animation_type == 'place':
            self.animation_progress += self.animation_speed
            if self.animation_progress >= 100:
                self.animation_progress = 100
                self.animation_type = None
        elif self.animation_type == 'remove':
            self.animation_progress += self.animation_speed
            if self.animation_progress >= 100:
                self.animation_progress = 100
                self.animation_type = None
        elif self.animation_type == 'highlight':
            self.animation_progress += self.animation_speed
            if self.animation_progress >= 100:
                self.animation_progress = 100
                self.animation_type = None
        
        # 处理高亮
        if self.highlighted:
            if self.highlight_intensity < 200:
                self.highlight_intensity += 5
        else:
            if self.highlight_intensity > 0:
                self.highlight_intensity -= 5
    
    def _get_current_radius(self) -> int:
        """获取当前动画状态下的半径"""
        if self.animation_type == 'place':
            return int(self.radius * (self.animation_progress / 100))
        elif self.animation_type == 'remove':
            return int(self.radius * ((100 - self.animation_progress) / 100))
        return self.radius
    
    def _get_current_alpha(self) -> int:
        """获取当前动画状态下的透明度"""
        if self.animation_type == 'place':
            return int(255 * (self.animation_progress / 100))
        elif self.animation_type == 'remove':
            return int(255 * ((100 - self.animation_progress) / 100))
        return 255
    
    def draw(self, surface: pygame.Surface):
        """绘制棋子"""
        current_radius = self._get_current_radius()
        current_alpha = self._get_current_alpha()
        
        if current_radius <= 0:
            return
        
        # 绘制获胜棋子边框
        if self.is_winner:
            winner_surface = pygame.Surface((self.border_radius * 2, self.border_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                winner_surface,
                (*COLORS['WIN_LINE'], current_alpha),
                (self.border_radius, self.border_radius),
                self.border_radius
            )
            surface.blit(
                winner_surface,
                (self.screen_x - self.border_radius, self.screen_y - self.border_radius)
            )
        
        # 绘制棋子主体
        piece_surface = pygame.Surface((current_radius * 2, current_radius * 2), pygame.SRCALPHA)
        
        if self.color == PIECE_COLORS['BLACK']:
            # 黑色棋子（带高光和阴影）
            # 阴影
            shadow_color = (30, 30, 30, current_alpha)
            pygame.draw.circle(
                piece_surface,
                shadow_color,
                (current_radius + 2, current_radius + 2),
                current_radius
            )
            # 主体
            pygame.draw.circle(
                piece_surface,
                (*COLORS['BLACK'], current_alpha),
                (current_radius, current_radius),
                current_radius
            )
            # 高光
            highlight_color = (80, 80, 80, current_alpha // 2)
            pygame.draw.circle(
                piece_surface,
                highlight_color,
                (current_radius - 4, current_radius - 4),
                current_radius // 2
            )
        else:
            # 白色棋子（带高光和阴影）
            # 阴影
            shadow_color = (180, 180, 180, current_alpha)
            pygame.draw.circle(
                piece_surface,
                shadow_color,
                (current_radius + 2, current_radius + 2),
                current_radius
            )
            # 主体
            pygame.draw.circle(
                piece_surface,
                (*COLORS['WHITE'], current_alpha),
                (current_radius, current_radius),
                current_radius
            )
            # 高光
            highlight_color = (255, 255, 255, current_alpha // 2)
            pygame.draw.circle(
                piece_surface,
                highlight_color,
                (current_radius - 4, current_radius - 4),
                current_radius // 2
            )
        
        # 绘制AI标记（小图标）
        if self.is_ai and current_radius >= 8:
            ai_icon_radius = current_radius // 4
            ai_color = (255, 215, 0, current_alpha)
            pygame.draw.circle(
                piece_surface,
                ai_color,
                (current_radius + current_radius // 2, current_radius - current_radius // 2),
                ai_icon_radius
            )
        
        # 绘制高亮效果
        if self.highlight_intensity > 0:
            highlight_surface = pygame.Surface((current_radius * 2, current_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                highlight_surface,
                (0, 255, 0, self.highlight_intensity),
                (current_radius, current_radius),
                current_radius
            )
            piece_surface.blit(highlight_surface, (0, 0), special_flags=pygame.BLEND_ADD)
        
        # 绘制到屏幕
        surface.blit(
            piece_surface,
            (self.screen_x - current_radius, self.screen_y - current_radius)
        )
    
    def is_hovered(self, mouse_pos: Tuple[int, int]) -> bool:
        """判断鼠标是否悬停在棋子上"""
        distance = math.hypot(mouse_pos[0] - self.screen_x, mouse_pos[1] - self.screen_y)
        return distance <= self.radius
    
    def toggle_highlight(self):
        """切换高亮状态"""
        self.highlighted = not self.highlighted
        if self.highlighted:
            self.start_animation('highlight')
        else:
            self.stop_animation()

class PieceManager:
    """棋子管理器（管理多个棋子）"""
    def __init__(self, cell_size: int):
        self.cell_size = cell_size
        self.pieces = []  # 棋子列表
        self.piece_map = {}  # 棋子映射：(x,y) -> Piece
    
    def add_piece(self, x: int, y: int, color: int, is_ai: bool = False) -> Piece:
        """添加棋子"""
        if (x, y) in self.piece_map:
            raise UIError(f"位置({x},{y})已存在棋子", 6002)
        
        piece = Piece(x, y, color, self.cell_size, is_ai)
        self.pieces.append(piece)
        self.piece_map[(x, y)] = piece
        piece.start_animation('place')
        return piece
    
    def remove_piece(self, x: int, y: int) -> Optional[Piece]:
        """移除棋子"""
        if (x, y) not in self.piece_map:
            return None
        
        piece = self.piece_map[(x, y)]
        piece.start_animation('remove')
        # 动画结束后从列表和映射中移除
        # 实际项目中可通过定时器或帧更新检测
        self.pieces.remove(piece)
        del self.piece_map[(x, y)]
        return piece
    
    def get_piece(self, x: int, y: int) -> Optional[Piece]:
        """获取指定位置的棋子"""
        return self.piece_map.get((x, y), None)
    
    def update_pieces(self, base_x: int, base_y: int):
        """更新所有棋子的状态"""
        for piece in self.pieces:
            piece.set_screen_position(base_x, base_y)
            piece.update()
    
    def draw_pieces(self, surface: pygame.Surface):
        """绘制所有棋子"""
        for piece in self.pieces:
            piece.draw(surface)
    
    def mark_winner_pieces(self, win_line: List[Tuple[int, int]]):
        """标记获胜棋子"""
        for (x, y) in win_line:
            piece = self.get_piece(x, y)
            if piece:
                piece.is_winner = True
    
    def reset(self):
        """重置棋子管理器"""
        self.pieces = []
        self.piece_map = {}
    
    def get_piece_at_mouse(self, mouse_pos: Tuple[int, int]) -> Optional[Piece]:
        """获取鼠标位置的棋子"""
        for piece in self.pieces:
            if piece.is_hovered(mouse_pos):
                return piece
        return None