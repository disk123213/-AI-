import pyodbc
import json
import os
from Common.config import Config
from Common.logger import Logger
from Common.error_handler import DatabaseError

class DatabaseConnection:
    _instance = None
    _conn = None
    _cursor = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_conn()
        return cls._instance

    def _init_conn(self):
        """初始化数据库连接"""
        try:
            config = Config.get_instance()
            self._conn = pyodbc.connect(
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={config.db_server};"
                f"DATABASE={config.db_name};"
                f"UID={config.db_user};"
                f"PWD={config.db_password};"
                f"Encrypt=yes;"
                f"TrustServerCertificate=yes;"
                f"Connection Timeout=30;"
            )
            self._cursor = self._conn.cursor()
            Logger.get_instance().info("数据库连接成功")
        except Exception as e:
            Logger.get_instance().error(f"数据库连接失败: {str(e)}")
            raise DatabaseError(f"数据库连接失败: {str(e)}")

    def execute_query(self, sql, params=None):
        """执行查询语句"""
        try:
            if params:
                self._cursor.execute(sql, params)
            else:
                self._cursor.execute(sql)
            columns = [column[0] for column in self._cursor.description]
            results = []
            for row in self._cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            Logger.get_instance().error(f"查询执行失败: {str(e)} | SQL: {sql} | Params: {params}")
            raise DatabaseError(f"查询执行失败: {str(e)}")

    def execute_non_query(self, sql, params=None):
        """执行非查询语句（INSERT/UPDATE/DELETE）"""
        try:
            if params:
                self._cursor.execute(sql, params)
            else:
                self._cursor.execute(sql)
            self._conn.commit()
            return self._cursor.rowcount
        except Exception as e:
            self._conn.rollback()
            Logger.get_instance().error(f"非查询执行失败: {str(e)} | SQL: {sql} | Params: {params}")
            raise DatabaseError(f"非查询执行失败: {str(e)}")

    def execute_batch(self, sql, params_list):
        """批量执行语句"""
        try:
            self._cursor.executemany(sql, params_list)
            self._conn.commit()
            return self._cursor.rowcount
        except Exception as e:
            self._conn.rollback()
            Logger.get_instance().error(f"批量执行失败: {str(e)} | SQL: {sql}")
            raise DatabaseError(f"批量执行失败: {str(e)}")

    def close(self):
        """关闭连接"""
        if self._cursor:
            self._cursor.close()
        if self._conn:
            self._conn.close()
            Logger.get_instance().info("数据库连接已关闭")

    def __del__(self):
        """析构函数：自动关闭连接"""
        self.close()

# 数据转换工具：将Python对象转换为SQL可用格式
class DataConverter:
    @staticmethod
    def obj_to_json(obj):
        """将对象转换为JSON字符串"""
        return json.dumps(obj, ensure_ascii=False)

    @staticmethod
    def json_to_obj(json_str):
        """将JSON字符串转换为对象"""
        if not json_str or json_str == 'NULL':
            return None
        return json.loads(json_str)

    @staticmethod
    def board_to_str(board):
        """将棋盘状态（二维列表）转换为字符串"""
        return ';'.join(['|'.join(map(str, row)) for row in board])

    @staticmethod
    def str_to_board(board_str):
        """将字符串转换为棋盘状态（二维列表）"""
        if not board_str or board_str == 'NULL':
            return None
        return [[int(cell) for cell in row.split('|')] for row in board_str.split(';')]

# 数据库初始化工具
class DBInitializer:
    @staticmethod
    def init_db():
        """初始化数据库（执行建表脚本）"""
        try:
            db_conn = DatabaseConnection()
            sql_path = os.path.join(os.path.dirname(__file__), 'sql', 'create_tables.sql')
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            # 执行建表脚本（按GO分割）
            sql_commands = sql_script.split('GO')
            for cmd in sql_commands:
                cmd = cmd.strip()
                if cmd:
                    db_conn.execute_non_query(cmd)
            Logger.get_instance().info("数据库初始化成功")
            # 插入默认模型
            DBInitializer._insert_default_models()
        except Exception as e:
            Logger.get_instance().error(f"数据库初始化失败: {str(e)}")
            raise DatabaseError(f"数据库初始化失败: {str(e)}")

    @staticmethod
    def _insert_default_models():
        """插入默认AI模型"""
        db_conn = DatabaseConnection()
        # 检查默认模型是否已存在
        existing = db_conn.execute_query("SELECT COUNT(*) AS count FROM [dbo].[AI_Models] WHERE [is_default] = 1")
        if existing[0]['count'] > 0:
            return
        # 默认模型数据
        default_models = [
            (
                '默认简单模型',
                1,  # 管理员用户（假设user_id=1）
                'minimax',
                0.7500,
                1000,
                os.path.join(os.getcwd(), 'models', 'default_easy.pth'),
                0
            ),
            (
                '默认中等模型',
                1,
                'minimax',
                0.8500,
                3000,
                os.path.join(os.getcwd(), 'models', 'default_medium.pth'),
                0
            ),
            (
                '默认困难模型',
                1,
                'minimax+mcts',
                0.9200,
                5000,
                os.path.join(os.getcwd(), 'models', 'default_hard.pth'),
                0
            ),
            (
                '默认专家模型',
                1,
                'nn+mcts',
                0.9800,
                10000,
                os.path.join(os.getcwd(), 'models', 'default_expert.pth'),
                1  # 设为默认模型
            )
        ]
        # 插入默认模型
        sql = """
            INSERT INTO [dbo].[AI_Models] 
            ([model_name], [user_id], [model_type], [accuracy], [train_count], [model_path], [is_default])
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        db_conn.execute_batch(sql, default_models)
        Logger.get_instance().info("默认AI模型插入成功")