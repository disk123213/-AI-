import pygame
import sys
import os
from typing import Optional, Dict, List
from Common.config import Config
from Common.constants import WINDOW_CONFIG, COLORS, GAME_MODES, AI_LEVELS
from Common.logger import Logger
from Common.error_handler import UIError
from UI.board import Board
from UI.control_panel import ControlPanel
from UI.visualizer import AIVisualizer
from UI.menu import MainMenu, GameMenu
from Game.game_core import GameCore
from Game.game_mode import GameModeManager
from DB.user_dao import UserDAO
from DB.game_dao import GameDAO

class MainWindow:
    """程序主窗口"""
    def __init__(self):
        self.config = Config.get_instance()
        self.logger = Logger.get_instance()
        self.user_dao = UserDAO()
        self.game_dao = GameDAO()
        
        # 初始化窗口尺寸
        self.width = WINDOW_CONFIG['DEFAULT_WIDTH']
        self.height = WINDOW_CONFIG['DEFAULT_HEIGHT']
        self.min_width = WINDOW_CONFIG['MIN_WIDTH']
        self.min_height = WINDOW_CONFIG['MIN_HEIGHT']
        
        # 创建窗口（支持调整大小）
        self.screen = pygame.display.set_mode(
            (self.width, self.height),
            pygame.RESIZABLE | pygame.DOUBLEBUF
        )
        pygame.display.set_caption(WINDOW_CONFIG['TITLE'])
        
        # 初始化时钟（控制帧率）
        self.clock = pygame.time.Clock()
        self.fps = WINDOW_CONFIG['FPS']
        
        # 初始化组件
        self._init_components()
        
        # 初始化游戏核心
        self.game_core = GameCore()
        self.mode_manager = GameModeManager(self.game_core)
        
        # 状态变量
        self.running = True
        self.current_mode = None
        self.current_user = None  # 当前登录用户
        self.show_menu = True  # 是否显示主菜单
        self.show_control_panel = True  # 是否显示控制面板
        self.show_visualizer = self.config.show_thinking_visual  # 是否显示AI思考可视化
        
        # 加载资源
        self._load_resources()
        
    def _init_components(self):
        """初始化UI组件"""
        # 计算布局位置
        self.panel_width = 300
        self.board_x = self.panel_width + 20
        self.board_y = 20
        
        # 控制面板
        self.control_panel = ControlPanel(
            x=10,
            y=20,
            width=self.panel_width,
            height=self.height - 40,
            on_mode_change=self.on_mode_change,
            on_ai_level_change=self.on_ai_level_change,
            on_start_game=self.on_start_game,
            on_stop_game=self.on_stop_game,
            on_save_model=self.on_save_model,
            on_load_model=self.on_load_model,
            on_train_model=self.on_train_model,
            on_analyze_board=self.on_analyze_board
        )
        
        # 棋盘
        self.board = Board(
            x=self.board_x,
            y=self.board_y,
            size=self.config.board_size,
            cell_size=self.config.cell_size,
            on_piece_place=self.on_piece_place
        )
        
        # AI思考可视化组件
        self.ai_visualizer = AIVisualizer(
            x=self.board_x,
            y=self.board_y,
            size=self.config.board_size,
            cell_size=self.config.cell_size
        )
        
        # 菜单
        self.main_menu = MainMenu(
            x=self.width // 2 - 200,
            y=self.height // 2 - 150,
            width=400,
            height=300,
            on_login=self.on_login,
            on_register=self.on_register,
            on_guest_login=self.on_guest_login,
            on_exit=self.on_exit
        )
        
        self.game_menu = GameMenu(
            x=self.width - 150,
            y=10,
            width=140,
            height=200,
            on_new_game=self.on_new_game,
            on_change_mode=self.on_change_mode_menu,
            on_settings=self.on_settings,
            on_back_menu=self.on_back_menu
        )
        
    def _load_resources(self):
        """加载资源（字体、图片等）"""
        # 加载字体
        self.fonts = {
            'title': pygame.font.SysFont('Arial', 24, bold=True),
            'sub_title': pygame.font.SysFont('Arial', 20, bold=True),
            'normal': pygame.font.SysFont('Arial', 16),
            'small': pygame.font.SysFont('Arial', 12)
        }
        
        # 加载图标（可选）
        self.icons = {}
        icon_path = os.path.join(os.getcwd(), 'UI', 'icons')
        if os.path.exists(icon_path):
            try:
                self.icons['black_piece'] = pygame.image.load(os.path.join(icon_path, 'black_piece.png')).convert_alpha()
                self.icons['white_piece'] = pygame.image.load(os.path.join(icon_path, 'white_piece.png')).convert_alpha()
                self.icons['ai_icon'] = pygame.image.load(os.path.join(icon_path, 'ai_icon.png')).convert_alpha()
            except Exception as e:
                self.logger.warning(f"加载图标失败: {str(e)}，将使用默认绘制")
        
        # 加载背景图
        self.background = None
        bg_path = os.path.join(os.getcwd(), 'UI', 'background.jpg')
        if os.path.exists(bg_path):
            try:
                self.background = pygame.image.load(bg_path).convert()
                self.background = pygame.transform.scale(self.background, (self.width, self.height))
            except Exception as e:
                self.logger.warning(f"加载背景图失败: {str(e)}")
        
    def on_login(self, username: str, password: str):
        """登录回调"""
        try:
            user = self.user_dao.login(username, password)
            if user:
                self.current_user = user
                self.show_menu = False
                self.control_panel.update_user_info(user)
                self.logger.info(f"用户登录成功: {username}")
                pygame.display.set_caption(f"{WINDOW_CONFIG['TITLE']} - 登录用户：{user['nickname']}")
            else:
                self.main_menu.show_error("用户名或密码错误")
        except Exception as e:
            self.logger.error(f"登录失败: {str(e)}")
            self.main_menu.show_error(f"登录失败: {str(e)}")
    
    def on_register(self, username: str, password: str, nickname: str):
        """注册回调"""
        try:
            success = self.user_dao.register(username, password, nickname)
            if success:
                self.main_menu.show_message("注册成功，请登录")
                self.logger.info(f"用户注册成功: {username}")
            else:
                self.main_menu.show_error("注册失败，用户名已存在")
        except Exception as e:
            self.logger.error(f"注册失败: {str(e)}")
            self.main_menu.show_error(f"注册失败: {str(e)}")
    
    def on_guest_login(self):
        """游客登录回调"""
        self.current_user = {
            'user_id': -1,
            'username': 'guest',
            'nickname': '游客'
        }
        self.show_menu = False
        self.control_panel.update_user_info(self.current_user)
        self.logger.info("游客登录成功")
        pygame.display.set_caption(f"{WINDOW_CONFIG['TITLE']} - 游客模式")
    
    def on_exit(self):
        """退出回调"""
        self.running = False
    
    def on_mode_change(self, mode: str):
        """模式切换回调（控制面板）"""
        self.current_mode = mode
        self.mode_manager.set_mode(mode)
        self.control_panel.update_mode_info(mode)
        self.board.reset()
        self.ai_visualizer.reset()
        self.logger.info(f"切换游戏模式: {mode}")
    
    def on_ai_level_change(self, level: str):
        """AI难度切换回调"""
        self.game_core.set_ai_level(level)
        self.control_panel.update_ai_level(level)
        self.logger.info(f"切换AI难度: {level}")
    
    def on_start_game(self):
        """开始游戏回调"""
        if not self.current_mode:
            self.control_panel.show_error("请先选择游戏模式")
            return
        
        self.game_core.start_game()
        self.control_panel.update_game_status("游戏中")
        self.board.set_game_active(True)
        self.logger.info("游戏开始")
        
        # 如果是人机对战且AI先手，AI自动落子
        if self.current_mode == GAME_MODES['PVE'] and self.game_core.ai_first:
            self._ai_auto_move()
    
    def on_stop_game(self):
        """停止游戏回调"""
        self.game_core.stop_game()
        self.control_panel.update_game_status("已停止")
        self.board.set_game_active(False)
        self.ai_visualizer.reset()
        self.logger.info("游戏停止")
    
    def on_save_model(self):
        """保存模型回调"""
        if not self.current_user:
            self.control_panel.show_error("请先登录")
            return
        
        try:
            model_name = self.control_panel.get_model_name()
            if not model_name:
                self.control_panel.show_error("请输入模型名称")
                return
            
            # 保存当前AI模型
            success = self.game_core.save_ai_model(
                model_name=model_name,
                user_id=self.current_user['user_id']
            )
            if success:
                self.control_panel.show_message("模型保存成功")
                self.logger.info(f"模型保存成功: {model_name}")
            else:
                self.control_panel.show_error("模型保存失败")
        except Exception as e:
            self.logger.error(f"保存模型失败: {str(e)}")
            self.control_panel.show_error(f"保存失败: {str(e)}")
    
    def on_load_model(self):
        """加载模型回调"""
        if not self.current_user:
            self.control_panel.show_error("请先登录")
            return
        
        try:
            model_id = self.control_panel.get_selected_model()
            if not model_id:
                self.control_panel.show_error("请选择要加载的模型")
                return
            
            # 加载模型
            success = self.game_core.load_ai_model(
                model_id=model_id,
                user_id=self.current_user['user_id']
            )
            if success:
                self.control_panel.show_message("模型加载成功")
                self.logger.info(f"模型加载成功: {model_id}")
            else:
                self.control_panel.show_error("模型加载失败")
        except Exception as e:
            self.logger.error(f"加载模型失败: {str(e)}")
            self.control_panel.show_error(f"加载失败: {str(e)}")
    
    def on_train_model(self):
        """训练模型回调"""
        if not self.current_user:
            self.control_panel.show_error("请先登录")
            return
        
        try:
            epochs = self.control_panel.get_train_epochs()
            batch_size = self.control_panel.get_train_batch_size()
            
            # 开始训练
            self.control_panel.show_message("开始训练模型...")
            self.control_panel.set_train_status("training")
            
            # 训练回调（更新进度）
            def train_callback(epoch: int, loss: float, accuracy: float):
                self.control_panel.update_train_progress(epoch, loss, accuracy)
            
            # 启动训练（异步）
            import threading
            train_thread = threading.Thread(
                target=self.game_core.train_ai_model,
                args=(self.current_user['user_id'], epochs, batch_size, train_callback),
                daemon=True
            )
            train_thread.start()
        except Exception as e:
            self.logger.error(f"训练模型失败: {str(e)}")
            self.control_panel.show_error(f"训练失败: {str(e)}")
            self.control_panel.set_train_status("idle")
    
    def on_analyze_board(self):
        """棋盘分析回调"""
        if not self.game_core.game_active:
            self.control_panel.show_error("请先开始游戏")
            return
        
        try:
            # 生成分析报告
            analysis_report = self.game_core.analyze_board()
            # 显示分析结果
            self.control_panel.show_analysis_report(analysis_report)
            # 在棋盘上标记关键落子
            if analysis_report.get('key_move'):
                x, y = analysis_report['key_move']
                self.board.mark_key_position(x, y)
            self.logger.info("棋盘分析完成")
        except Exception as e:
            self.logger.error(f"棋盘分析失败: {str(e)}")
            self.control_panel.show_error(f"分析失败: {str(e)}")
    
    def on_piece_place(self, x: int, y: int):
        """棋子放置回调（棋盘）"""
        if not self.game_core.game_active:
            return
        
        try:
            # 玩家落子
            result = self.game_core.place_piece(x, y)
            if result == 'success':
                # 更新棋盘显示
                self.board.update_board(self.game_core.board)
                self.control_panel.update_move_count(len(self.game_core.move_history))
                
                # 检查游戏是否结束
                game_result = self.game_core.check_game_end()
                if game_result:
                    self._handle_game_end(game_result)
                    return
                
                # 如果是人机对战，AI落子
                if self.current_mode == GAME_MODES['PVE'] or self.current_mode == GAME_MODES['TRAIN']:
                    self._ai_auto_move()
            elif result == 'invalid_position':
                self.control_panel.show_error("无效的落子位置")
            elif result == 'occupied':
                self.control_panel.show_error("该位置已被占用")
            elif result == 'not_your_turn':
                self.control_panel.show_error("不是你的回合")
        except Exception as e:
            self.logger.error(f"落子失败: {str(e)}")
            self.control_panel.show_error(f"落子失败: {str(e)}")
    
    def _ai_auto_move(self):
        """AI自动落子"""
        if not self.game_core.game_active:
            return
        
        # 显示AI思考中
        self.control_panel.update_game_status("AI思考中...")
        self.board.set_ai_thinking(True)
        
        # AI落子（异步，避免阻塞UI）
        import threading
        ai_thread = threading.Thread(
            target=self._ai_move_thread,
            daemon=True
        )
        ai_thread.start()
    
    def _ai_move_thread(self):
        """AI落子线程"""
        try:
            # 思考过程回调（用于可视化）
            def thinking_callback(thinking_data: Dict):
                if self.show_visualizer:
                    pygame.fastevent.post(pygame.event.Event(
                        pygame.USEREVENT + 1,
                        {'type': 'ai_thinking', 'data': thinking_data}
                    ))
            
            # AI计算最佳落子
            x, y = self.game_core.ai_move(thinking_callback)
            
            # 发送落子事件到主线程
            pygame.fastevent.post(pygame.event.Event(
                pygame.USEREVENT,
                {'type': 'ai_move', 'x': x, 'y': y}
            ))
        except Exception as e:
            self.logger.error(f"AI落子失败: {str(e)}")
            pygame.fastevent.post(pygame.event.Event(
                pygame.USEREVENT + 2,
                {'type': 'ai_error', 'message': str(e)}
            ))
    
    def _handle_ai_move(self, x: int, y: int):
        """处理AI落子结果"""
        if not self.game_core.game_active:
            return
        
        # AI落子
        self.game_core.place_piece(x, y, is_ai=True)
        # 更新棋盘
        self.board.update_board(self.game_core.board)
        self.board.set_ai_thinking(False)
        self.control_panel.update_move_count(len(self.game_core.move_history))
        self.control_panel.update_game_status("游戏中")
        
        # 检查游戏是否结束
        game_result = self.game_core.check_game_end()
        if game_result:
            self._handle_game_end(game_result)
            return
    
    def _handle_game_end(self, game_result: Dict):
        """处理游戏结束"""
        self.board.set_game_active(False)
        winner = game_result.get('winner')
        win_line = game_result.get('win_line', [])
        
        # 标记获胜线
        if win_line:
            self.board.draw_win_line(win_line)
        
        # 更新状态
        if winner == 'draw':
            self.control_panel.update_game_status("平局")
            self.control_panel.show_message("游戏结束，平局！")
            self.logger.info("游戏结束，平局")
        elif winner == 'player1':
            self.control_panel.update_game_status("黑方获胜")
            self.control_panel.show_message("游戏结束，黑方获胜！")
            self.logger.info("游戏结束，黑方获胜")
        elif winner == 'player2':
            self.control_panel.update_game_status("白方获胜")
            self.control_panel.show_message("游戏结束，白方获胜！")
            self.logger.info("游戏结束，白方获胜")
        
        # 保存对局记录（登录用户）
        if self.current_user and self.current_user['user_id'] != -1:
            try:
                self.game_dao.save_game_record(
                    user1_id=self.current_user['user_id'],
                    user2_id=None if self.current_mode == GAME_MODES['PVE'] else -1,
                    game_mode=self.current_mode,
                    ai_level=self.game_core.ai_level,
                    move_history=self.game_core.move_history,
                    winner_id=self.current_user['user_id'] if winner == 'player1' else None
                )
                self.logger.info("对局记录保存成功")
            except Exception as e:
                self.logger.error(f"保存对局记录失败: {str(e)}")
        
        # 训练模式下自动添加训练数据
        if self.current_mode == GAME_MODES['TRAIN'] and self.current_user and self.current_user['user_id'] != -1:
            try:
                self.game_core.add_training_data(self.current_user['user_id'])
                self.logger.info("训练数据添加成功")
            except Exception as e:
                self.logger.error(f"添加训练数据失败: {str(e)}")
    
    def on_new_game(self):
        """新游戏回调（游戏菜单）"""
        self.board.reset()
        self.ai_visualizer.reset()
        self.game_core.reset_game()
        self.control_panel.update_move_count(0)
        self.on_start_game()
    
    def on_change_mode_menu(self):
        """切换模式回调（游戏菜单）"""
        self.control_panel.show_mode_selection()
    
    def on_settings(self):
        """设置回调（游戏菜单）"""
        # 打开设置窗口（后续实现）
        self.control_panel.show_message("设置功能即将打开")
    
    def on_back_menu(self):
        """返回主菜单回调（游戏菜单）"""
        self.show_menu = True
        self.game_core.stop_game()
        self.board.reset()
        self.ai_visualizer.reset()
        self.control_panel.reset()
        pygame.display.set_caption(WINDOW_CONFIG['TITLE'])
    
    def _handle_events(self):
        """处理事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # 窗口大小调整事件
            elif event.type == pygame.VIDEORESIZE:
                self.width = max(event.w, self.min_width)
                self.height = max(event.h, self.min_height)
                self.screen = pygame.display.set_mode(
                    (self.width, self.height),
                    pygame.RESIZABLE | pygame.DOUBLEBUF
                )
                # 更新组件位置和大小
                self._update_component_layout()
            
            # 鼠标事件
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if self.show_menu:
                    self.main_menu.handle_click(mouse_pos)
                else:
                    self.game_menu.handle_click(mouse_pos)
                    self.control_panel.handle_click(mouse_pos)
                    self.board.handle_click(mouse_pos)
            
            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = pygame.mouse.get_pos()
                if not self.show_menu:
                    self.control_panel.handle_hover(mouse_pos)
                    self.game_menu.handle_hover(mouse_pos)
            
            # 键盘事件
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.show_menu:
                        self.running = False
                    else:
                        self.show_menu = True
                elif event.key == pygame.K_F1:
                    self.on_analyze_board()
                elif event.key == pygame.K_F2:
                    self.on_new_game()
            
            # AI落子事件（自定义）
            elif event.type == pygame.USEREVENT and event.type == 'ai_move':
                self._handle_ai_move(event.x, event.y)
            
            # AI思考可视化事件（自定义）
            elif event.type == pygame.USEREVENT + 1 and event.type == 'ai_thinking':
                if self.show_visualizer:
                    self.ai_visualizer.update_thinking_data(event.data)
            
            # AI错误事件（自定义）
            elif event.type == pygame.USEREVENT + 2 and event.type == 'ai_error':
                self.control_panel.show_error(f"AI错误: {event.message}")
                self.board.set_ai_thinking(False)
                self.control_panel.update_game_status("游戏异常")
    
    def _update_component_layout(self):
        """更新组件布局（窗口调整时）"""
        # 控制面板
        self.control_panel.resize(
            x=10,
            y=20,
            width=self.panel_width,
            height=self.height - 40
        )
        
        # 棋盘
        self.board_x = self.panel_width + 20
        self.board_y = 20
        # 调整棋盘大小以适应窗口
        max_board_width = self.width - self.board_x - 20
        max_board_height = self.height - 40
        max_cell_size = min(
            max_board_width // self.config.board_size,
            max_board_height // self.config.board_size
        )
        if max_cell_size != self.board.cell_size and max_cell_size >= 20:
            self.board.resize(
                x=self.board_x,
                y=self.board_y,
                cell_size=max_cell_size
            )
            self.ai_visualizer.resize(
                x=self.board_x,
                y=self.board_y,
                cell_size=max_cell_size
            )
        
        # 游戏菜单
        self.game_menu.move(
            x=self.width - 150,
            y=10
        )
        
        # 背景图
        if self.background:
            self.background = pygame.transform.scale(self.background, (self.width, self.height))
    
    def _draw(self):
        """绘制UI"""
        # 绘制背景
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(COLORS['PANEL_BG'])
        
        if self.show_menu:
            # 绘制主菜单
            self.main_menu.draw(self.screen, self.fonts)
        else:
            # 绘制控制面板
            self.control_panel.draw(self.screen, self.fonts)
            # 绘制棋盘
            self.board.draw(self.screen, self.fonts)
            # 绘制AI思考可视化（如果开启）
            if self.show_visualizer and self.board.ai_thinking:
                self.ai_visualizer.draw(self.screen)
            # 绘制游戏菜单
            self.game_menu.draw(self.screen, self.fonts)
        
        # 更新显示
        pygame.display.flip()
    
    def run(self):
        """运行主循环"""
        while self.running:
            # 处理事件
            self._handle_events()
            # 绘制UI
            self._draw()
            # 控制帧率
            self.clock.tick(self.fps)
        
        # 退出时清理资源
        pygame.quit()
        self.logger.info("主窗口关闭")