"""游戏常量定义"""

# 游戏模式
GAME_MODES = {
    'PVP': 'pvp',          # 人人对战
    'PVE': 'pve',          # 人机对战
    'ONLINE': 'online',    # 联机对战
    'TRAIN': 'train'       # 训练模式
}

# AI难度
AI_LEVELS = {
    'EASY': 'easy',                # 简单（Minimax深度3）
    'MEDIUM': 'medium',            # 中等（Minimax深度4）
    'HARD': 'hard',                # 困难（Minimax深度5+MCTS500迭代）
    'EXPERT': 'expert'             # 专家（NN+MCTS1000迭代+Minimax深度6）
}

# AI类型
AI_TYPES = {
    'MINIMAX': 'minimax',
    'MCTS': 'mcts',
    'NN': 'nn',
    'MINIMAX_MCTS': 'minimax+mcts',
    'NN_MCTS': 'nn+mcts'
}

# 玩家类型
PLAYER_TYPES = {
    'HUMAN': 'human',
    'AI': 'ai'
}

# 棋子颜色
PIECE_COLORS = {
    'BLACK': 1,
    'WHITE': 2,
    'EMPTY': 0
}

# 颜色值（RGB）
COLORS = {
    'BLACK': (0, 0, 0),
    'WHITE': (255, 255, 255),
    'BOARD_BG': (210, 180, 140),
    'BOARD_LINE': (139, 69, 19),
    'WIN_LINE': (255, 0, 0),
    'THINKING': (255, 215, 0),
    'HINT': (0, 255, 0, 100),  # 带透明度
    'TEXT': (0, 0, 0),
    'TEXT_LIGHT': (255, 255, 255),
    'BUTTON': (50, 150, 255),
    'BUTTON_HOVER': (80, 180, 255),
    'BUTTON_CLICK': (30, 120, 220),
    'PANEL_BG': (245, 245, 245),
    'PANEL_BORDER': (200, 200, 200)
}

# 游戏状态
GAME_STATUSES = {
    'READY': 'ready',        # 准备就绪
    'PLAYING': 'playing',    # 游戏中
    'PAUSED': 'paused',      # 暂停
    'ENDED': 'ended',        # 结束
    'DRAW': 'draw'           # 平局
}

# 联机房间状态
ROOM_STATUSES = {
    'WAITING': 'waiting',    # 等待玩家
    'PLAYING': 'playing',    # 游戏中
    'ENDED': 'ended'         # 结束
}

# 落子结果
MOVE_RESULTS = {
    'SUCCESS': 'success',            # 落子成功
    'INVALID_POS': 'invalid_position',# 位置无效
    'OCCUPIED': 'occupied',          # 位置已被占用
    'NOT_YOUR_TURN': 'not_your_turn',# 不是你的回合
    'GAME_ENDED': 'game_ended',      # 游戏已结束
    'TIMEOUT': 'timeout'             # 超时
}

# 模型训练状态
TRAIN_STATUSES = {
    'IDLE': 'idle',          # 空闲
    'TRAINING': 'training',  # 训练中
    'FINISHED': 'finished',  # 完成
    'FAILED': 'failed'       # 失败
}

# 棋盘评估权重（用于AI评分）
EVAL_WEIGHTS = {
    'FIVE': 1000000,         # 五连
    'FOUR': 100000,          # 活四
    'BLOCKED_FOUR': 10000,   # 冲四
    'THREE': 10000,          # 活三
    'BLOCKED_THREE': 1000,   # 冲三
    'TWO': 100,              # 活二
    'BLOCKED_TWO': 10,       # 冲二
    'ONE': 1                 # 活一
}

# 网络消息类型
MSG_TYPES = {
    'LOGIN': 'login',
    'LOGOUT': 'logout',
    'CREATE_ROOM': 'create_room',
    'JOIN_ROOM': 'join_room',
    'LEAVE_ROOM': 'leave_room',
    'MOVE': 'move',
    'GAME_STATUS': 'game_status',
    'CHAT': 'chat',
    'HEARTBEAT': 'heartbeat',
    'SYNC_DATA': 'sync_data',
    'ERROR': 'error'
}

# 窗口配置
WINDOW_CONFIG = {
    'TITLE': '五子棋AI对战平台',
    'MIN_WIDTH': 800,
    'MIN_HEIGHT': 600,
    'DEFAULT_WIDTH': 1200,
    'DEFAULT_HEIGHT': 800,
    'FPS': 60
}

# 字体配置
FONT_CONFIG = {
    'DEFAULT': 'Arial',
    'TITLE_SIZE': 24,
    'SUB_TITLE_SIZE': 20,
    'NORMAL_SIZE': 16,
    'SMALL_SIZE': 12
}

# 路径常量
PATH_CONSTANTS = {
    'MODELS': 'models',
    'LOGS': 'logs',
    'TRAINING_DATA': 'training_data',
    'SCREENSHOTS': 'screenshots',
    'CONFIG': 'config.ini',
    'DB_SQL': 'DB/sql'
}