import sys
import os
import pygame
from Common.config import Config
from Common.logger import Logger
from Common.error_handler import ErrorHandler, BaseError
from DB.db_conn import DatabaseConnection, DBInitializer
from UI.main_window import MainWindow
from Server.main_server import Server
import threading

def init_environment():
    """初始化运行环境"""
    # 1. 初始化配置
    config = Config.get_instance()
    # 2. 初始化日志
    logger = Logger.get_instance()
    # 3. 初始化数据库
    try:
        DBInitializer.init_db()
    except Exception as e:
        logger.error(f"数据库初始化失败，但程序继续运行（离线模式）: {str(e)}")
    # 4. 初始化Pygame
    pygame.init()
    pygame.font.init()
    pygame.display.set_caption(config.get('WINDOW', 'TITLE') or '五子棋AI对战平台')
    # 5. 检查CUDA
    check_cuda()

def check_cuda():
    """检查CUDA是否可用"""
    logger = Logger.get_instance()
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"CUDA可用，设备: {torch.cuda.get_device_name(0)}")
            logger.info(f"CUDA版本: {torch.version.cuda}")
            # 验证CUDA 12.2
            if '12.2' not in torch.version.cuda:
                logger.warning(f"检测到CUDA版本: {torch.version.cuda}，推荐使用12.2版本")
        else:
            logger.warning("CUDA不可用，将使用CPU运行（AI速度会变慢）")
    except Exception as e:
        logger.error(f"CUDA检查失败: {str(e)}")

def start_server():
    """启动服务器（独立线程）"""
    logger = Logger.get_instance()
    try:
        config = Config.get_instance()
        server = Server(config.server_host, config.server_port)
        logger.info(f"服务器启动成功，监听 {config.server_host}:{config.server_port}")
        server.start()
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}")

def main():
    """程序主函数"""
    # 初始化环境
    init_environment()
    logger = Logger.get_instance()
    logger.info("程序启动成功，进入主界面")

    # 启动服务器（后台线程）
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # 启动主界面
    try:
        main_window = MainWindow()
        main_window.run()
    except BaseError as e:
        ErrorHandler.handle_error(e)
    except Exception as e:
        ErrorHandler.handle_error(e)
    finally:
        # 清理资源
        pygame.quit()
        logger.info("程序正常退出")
        sys.exit(0)

if __name__ == "__main__":
    # 设置当前工作目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()