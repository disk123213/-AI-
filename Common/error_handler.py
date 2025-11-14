"""自定义异常类与错误处理工具"""

class BaseError(Exception):
    """基础异常类"""
    def __init__(self, message, code=1000):
        self.message = message
        self.code = code
        super().__init__(self.message)

    def __str__(self):
        return f"[{self.code}] {self.message}"

class DatabaseError(BaseError):
    """数据库异常"""
    def __init__(self, message, code=2000):
        super().__init__(message, code)

class ServerError(BaseError):
    """服务器异常"""
    def __init__(self, message, code=3000):
        super().__init__(message, code)

class AIError(BaseError):
    """AI模块异常"""
    def __init__(self, message, code=4000):
        super().__init__(message, code)

class GameError(BaseError):
    """游戏逻辑异常"""
    def __init__(self, message, code=5000):
        super().__init__(message, code)

class UIError(BaseError):
    """UI界面异常"""
    def __init__(self, message, code=6000):
        super().__init__(message, code)

class ModelError(BaseError):
    """模型管理异常"""
    def __init__(self, message, code=7000):
        super().__init__(message, code)

class ErrorHandler:
    """错误处理工具类"""
    @staticmethod
    def handle_error(e, re_raise=False):
        """统一错误处理"""
        from Common.logger import Logger
        logger = Logger.get_instance()

        # 记录错误日志
        if isinstance(e, BaseError):
            logger.error(f"自定义异常: {e}")
            if isinstance(e, (AIError, ModelError)):
                logger.exception(e.message)
        else:
            logger.exception(f"系统异常: {str(e)}")

        # 返回错误信息
        error_info = {
            'code': e.code if isinstance(e, BaseError) else 9999,
            'message': str(e)
        }

        # 是否重新抛出异常
        if re_raise:
            raise e

        return error_info

    @staticmethod
    def validate_param(param, param_name, required=True, min_val=None, max_val=None, param_type=None):
        """参数验证"""
        # 检查是否必填
        if required and param is None:
            raise GameError(f"参数[{param_name}]不能为空", 5001)
        
        # 检查类型
        if param_type and param is not None:
            if not isinstance(param, param_type):
                raise GameError(f"参数[{param_name}]类型错误，期望{param_type.__name__}，实际{type(param).__name__}", 5002)
        
        # 检查数值范围
        if param is not None and (min_val is not None or max_val is not None):
            if not isinstance(param, (int, float)):
                raise GameError(f"参数[{param_name}]必须是数值类型", 5003)
            if min_val is not None and param < min_val:
                raise GameError(f"参数[{param_name}]不能小于{min_val}", 5004)
            if max_val is not None and param > max_val:
                raise GameError(f"参数[{param_name}]不能大于{max_val}", 5005)

        return True