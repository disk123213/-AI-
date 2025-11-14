import os
import configparser
from Common.logger import Logger

class Config:
    _instance = None
    _config = None

    # 配置项默认值
    DEFAULT_CONFIG = {
        # 数据库配置
        'DB': {
            'server': 'localhost',
            'name': 'GobangAI',
            'user': 'sa',
            'password': 'YourStrongPassword123!'
        },
        # 服务器配置
        'SERVER': {
            'host': '0.0.0.0',
            'port': 8888,
            'max_clients': 50,
            'timeout': 30
        },
        # 游戏配置
        'GAME': {
            'board_size': 15,
            'cell_size': 40,
            'win_condition': 5,
            'max_time_per_move': 60,  # 每步最大时间（秒）
            'default_mode': 'pve'
        },
        # AI配置
        'AI': {
            'minimax_depth': 6,
            'mcts_iterations': 1000,
            'nn_input_size': 225,  # 15x15
            'nn_hidden_layers': '[1024, 512, 256]',
            'nn_output_size': 225,
            'learning_rate': 0.001,
            'batch_size': 32,
            'max_epochs': 500
        },
        # 可视化配置
        'VISUAL': {
            'show_thinking': True,
            'thinking_speed': 50,  # 思考过程刷新速度（毫秒）
            'show_score': True,
            'color_black': '#000000',
            'color_white': '#FFFFFF',
            'color_win_line': '#FF0000',
            'color_thinking': '#FFD700'
        },
        # 路径配置
        'PATH': {
            'models': './models',
            'logs': './logs',
            'training_data': './training_data',
            'screenshots': './screenshots'
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
            cls._instance._init_dirs()
        return cls._instance

    def _load_config(self):
        """加载配置文件"""
        self._config = configparser.ConfigParser()
        config_path = os.path.join(os.getcwd(), 'config.ini')
        
        # 如果配置文件不存在，创建默认配置
        if not os.path.exists(config_path):
            self._create_default_config(config_path)
            Logger.get_instance().info("配置文件不存在，已创建默认配置")
        else:
            # 读取配置文件
            self._config.read(config_path, encoding='utf-8')
            Logger.get_instance().info("配置文件加载成功")

    def _create_default_config(self, config_path):
        """创建默认配置文件"""
        for section, options in self.DEFAULT_CONFIG.items():
            self._config.add_section(section)
            for key, value in options.items():
                self._config.set(section, key, str(value))
        # 写入文件
        with open(config_path, 'w', encoding='utf-8') as f:
            self._config.write(f)

    def _init_dirs(self):
        """初始化所需目录"""
        path_config = self.get_section('PATH')
        for dir_name, dir_path in path_config.items():
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                Logger.get_instance().info(f"创建目录: {dir_path}")

    def get(self, section, key):
        """获取配置项"""
        try:
            return self._config.get(section, key)
        except configparser.NoSectionError:
            Logger.get_instance().warning(f"配置段不存在: {section}")
            return self.DEFAULT_CONFIG.get(section, {}).get(key)
        except configparser.NoOptionError:
            Logger.get_instance().warning(f"配置项不存在: {section}.{key}")
            return self.DEFAULT_CONFIG.get(section, {}).get(key)

    def get_int(self, section, key):
        """获取整数类型配置项"""
        value = self.get(section, key)
        try:
            return int(value)
        except:
            return int(self.DEFAULT_CONFIG.get(section, {}).get(key))

    def get_float(self, section, key):
        """获取浮点数类型配置项"""
        value = self.get(section, key)
        try:
            return float(value)
        except:
            return float(self.DEFAULT_CONFIG.get(section, {}).get(key))

    def get_bool(self, section, key):
        """获取布尔类型配置项"""
        value = self.get(section, key)
        if isinstance(value, str):
            return value.lower() in ['true', '1', 'yes']
        return bool(value)

    def get_list(self, section, key):
        """获取列表类型配置项"""
        value = self.get(section, key)
        try:
            return eval(value)
        except:
            return self.DEFAULT_CONFIG.get(section, {}).get(key)

    def get_section(self, section):
        """获取整个配置段"""
        try:
            return dict(self._config.items(section))
        except configparser.NoSectionError:
            Logger.get_instance().warning(f"配置段不存在: {section}")
            return self.DEFAULT_CONFIG.get(section, {})

    def set(self, section, key, value):
        """设置配置项"""
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, key, str(value))
        # 保存到文件
        config_path = os.path.join(os.getcwd(), 'config.ini')
        with open(config_path, 'w', encoding='utf-8') as f:
            self._config.write(f)

    @property
    def db_server(self):
        return self.get('DB', 'server')

    @property
    def db_name(self):
        return self.get('DB', 'name')

    @property
    def db_user(self):
        return self.get('DB', 'user')

    @property
    def db_password(self):
        return self.get('DB', 'password')

    @property
    def server_host(self):
        return self.get('SERVER', 'host')

    @property
    def server_port(self):
        return self.get_int('SERVER', 'port')

    @property
    def board_size(self):
        return self.get_int('GAME', 'board_size')

    @property
    def cell_size(self):
        return self.get_int('GAME', 'cell_size')

    @property
    def ai_minimax_depth(self):
        return self.get_int('AI', 'minimax_depth')

    @property
    def ai_mcts_iterations(self):
        return self.get_int('AI', 'mcts_iterations')

    @property
    def ai_learning_rate(self):
        return self.get_float('AI', 'learning_rate')

    @property
    def ai_batch_size(self):
        return self.get_int('AI', 'batch_size')

    @property
    def ai_max_epochs(self):
        return self.get_int('AI', 'max_epochs')

    @property
    def show_thinking_visual(self):
        return self.get_bool('VISUAL', 'show_thinking')

    @staticmethod
    def get_instance():
        """获取单例实例"""
        if Config._instance is None:
            Config._instance = Config()
        return Config._instance