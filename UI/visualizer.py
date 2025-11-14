import pygame
import numpy as np
from typing import List, Tuple, Dict, Optional
from Common.constants import COLORS, PIECE_COLORS
from Common.config import Config
from Common.logger import Logger

class AIVisualizer:
    """AI思考可视化组件（展示AI思维过程）"""
    def __init__(
        self,
        x: int,
        y: int,
        size: int = 15,
        cell_size: int = 40
    ):
        self.x = x  # 可视化区域X坐标
        self.y = y  # 可视化区域Y坐标
        self.size = size  # 棋盘尺寸
        self.cell_size = cell_size  # 单元格大小
        
        # 配置和日志
        self.config = Config.get_instance()
        self.logger = Logger.get_instance()
        
        # 可视化数据
        self.thinking_data = {
            'scores': np.zeros((self.size, self.size), dtype=np.float32),  # 每个位置的评分
            'best_move': None,  # 最佳落子
            'considering_moves': [],  # 正在考虑的落子
            'iteration': 0,  # MCTS迭代次数
            'depth': 0  # Minimax搜索深度
        }
        
        # 颜色映射（用于评分可视化）
        self.color_map = self._init_color_map()
        
        # 透明度控制
        self.alpha = 180  # 整体透明度
        
        # 动画状态
        self.animation_frame = 0
        self.animation_speed = 5
    
    def resize(self, x: int, y: int, cell_size: int):
        """调整可视化区域大小和位置"""
        self.x = x
        self.y = y
        self.cell_size = cell_size
        # 重新初始化评分矩阵
        self.thinking_data['scores'] = np.zeros((self.size, self.size), dtype=np.float32)
    
    def reset(self):
        """重置可视化数据"""
        self.thinking_data = {
            'scores': np.zeros((self.size, self.size), dtype=np.float32),
            'best_move': None,
            'considering_moves': [],
            'iteration': 0,
            'depth': 0
        }
        self.animation_frame = 0
    
    def update_thinking_data(self, data: Dict):
        """更新AI思考数据"""
        if 'scores' in data:
            self.thinking_data['scores'] = self._normalize_scores(data['scores'])
        if 'best_move' in data:
            self.thinking_data['best_move'] = data['best_move']
        if 'considering_moves' in data:
            self.thinking_data['considering_moves'] = data['considering_moves']
        if 'iteration' in data:
            self.thinking_data['iteration'] = data['iteration']
        if 'depth' in data:
            self.thinking_data['depth'] = data['depth']
        
        # 更新动画帧
        self.animation_frame = (self.animation_frame + 1) % self.animation_speed
    
    def _init_color_map(self) -> List[Tuple[int, int, int]]:
        """初始化颜色映射（从蓝色到红色，代表评分从低到高）"""
        color_map = []
        # 蓝色到青色（低评分）
        for i in range(0, 64):
            color_map.append((0, i * 4, 255))
        # 青色到绿色（中低评分）
        for i in range(0, 64):
            color_map.append((0, 255, 255 - i * 4))
        # 绿色到黄色（中高评分）
        for i in range(0, 64):
            color_map.append((i * 4, 255, 0))
        # 黄色到红色（高评分）
        for i in range(0, 64):
            color_map.append((255, 255 - i * 4, 0))
        return color_map
    
    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        """归一化评分（0-255）"""
        if scores.max() == scores.min():
            return np.zeros_like(scores)
        # 归一化到0-255
        normalized = (scores - scores.min()) / (scores.max() - scores.min()) * 255
        return normalized.astype(np.float32)
    
    def _get_screen_position(self, x: int, y: int) -> Tuple[int, int]:
        """将棋盘坐标转换为屏幕坐标"""
        screen_x = self.x + y * self.cell_size
        screen_y = self.y + x * self.cell_size
        return (screen_x, screen_y)
    
    def _draw_score_heatmap(self, surface: pygame.Surface):
        """绘制评分热力图"""
        cell_half = self.cell_size // 2
        
        for i in range(self.size):
            for j in range(self.size):
                score = self.thinking_data['scores'][i][j]
                if score <= 0:
                    continue
                
                # 根据评分获取颜色
                color_idx = int(min(score, 255))
                color = self.color_map[color_idx]
                
                # 创建半透明表面
                heat_surface = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
                # 绘制圆形热力图
                screen_x, screen_y = self._get_screen_position(i, j)
                center_x = self.cell_size // 2
                center_y = self.cell_size // 2
                radius = int(cell_half * (score / 255))  # 评分越高，半径越大
                
                if radius > 0:
                    pygame.draw.circle(
                        heat_surface,
                        (*color, self.alpha),
                        (center_x, center_y),
                        radius
                    )
                    surface.blit(heat_surface, (screen_x - cell_half, screen_y - cell_half))
    
    def _draw_considering_moves(self, surface: pygame.Surface):
        """绘制AI正在考虑的落子"""
        if not self.thinking_data['considering_moves']:
            return
        
        cell_half = self.cell_size // 2
        # 只绘制当前动画帧对应的落子
        move_idx = self.animation_frame % len(self.thinking_data['considering_moves'])
        x, y = self.thinking_data['considering_moves'][move_idx]
        
        screen_x, screen_y = self._get_screen_position(x, y)
        # 创建闪烁效果
        alpha = 150 + 50 * np.sin(pygame.time.get_ticks() / 200)
        
        # 绘制考虑中的落子标记
        consider_surface = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
        pygame.draw.circle(
            consider_surface,
            (*COLORS['THINKING'], int(alpha)),
            (cell_half, cell_half),
            cell_half - 2
        )
        surface.blit(consider_surface, (screen_x - cell_half, screen_y - cell_half))
    
    def _draw_best_move(self, surface: pygame.Surface):
        """绘制最佳落子"""
        best_move = self.thinking_data['best_move']
        if not best_move:
            return
        
        x, y = best_move
        screen_x, screen_y = self._get_screen_position(x, y)
        cell_half = self.cell_size // 2
        
        # 绘制最佳落子标记（红色边框+闪烁效果）
        best_surface = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
        # 外框
        pygame.draw.circle(
            best_surface,
            (*COLORS['WIN_LINE'], self.alpha),
            (cell_half, cell_half),
            cell_half - 2,
            3
        )
        # 内圈闪烁
        alpha = 100 + 100 * np.sin(pygame.time.get_ticks() / 150)
        pygame.draw.circle(
            best_surface,
            (*COLORS['WIN_LINE'], int(alpha)),
            (cell_half, cell_half),
            cell_half - 8
        )
        surface.blit(best_surface, (screen_x - cell_half, screen_y - cell_half))
    
    def _draw_thinking_info(self, surface: pygame.Surface):
        """绘制思考信息（迭代次数、搜索深度）"""
        # 创建半透明背景
        info_surface = pygame.Surface((200, 80), pygame.SRCALPHA)
        info_surface.fill((0, 0, 0, 150))
        surface.blit(info_surface, (self.x + self.size * self.cell_size + 10, self.y + 10))
        
        # 绘制文本
        font = pygame.font.SysFont('Arial', 12)
        iteration_text = font.render(f"MCTS迭代: {self.thinking_data['iteration']}", True, COLORS['TEXT_LIGHT'])
        depth_text = font.render(f"搜索深度: {self.thinking_data['depth']}", True, COLORS['TEXT_LIGHT'])
        surface.blit(iteration_text, (self.x + self.size * self.cell_size + 20, self.y + 20))
        surface.blit(depth_text, (self.x + self.size * self.cell_size + 20, self.y + 40))
        
        # 评分范围提示
        min_score = self.thinking_data['scores'].min()
        max_score = self.thinking_data['scores'].max()
        score_text = font.render(f"评分范围: {min_score:.2f}~{max_score:.2f}", True, COLORS['TEXT_LIGHT'])
        surface.blit(score_text, (self.x + self.size * self.cell_size + 20, self.y + 60))
    
    def draw(self, surface: pygame.Surface):
        """绘制AI思考可视化"""
        # 绘制评分热力图
        self._draw_score_heatmap(surface)
        
        # 绘制考虑中的落子
        self._draw_considering_moves(surface)
        
        # 绘制最佳落子
        self._draw_best_move(surface)
        
        # 绘制思考信息
        self._draw_thinking_info(surface)