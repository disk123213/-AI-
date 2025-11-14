import socket
import threading
from typing import Callable, Optional
from Common.logger import Logger
from Common.error_handler import ServerError

class TCPServer:
    """TCP协议服务器（负责底层网络通信）"""
    def __init__(self, host: str = '0.0.0.0', port: int = 8888):
        self.host = host
        self.port = port
        self.logger = Logger.get_instance()
        
        # 服务器Socket
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.client_connected_callback: Optional[Callable] = None  # 客户端连接回调
    
    def start(self, client_connected_callback: Callable):
        """启动TCP服务器"""
        self.client_connected_callback = client_connected_callback
        try:
            # 创建TCP Socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置端口复用
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # 绑定地址和端口
            self.server_socket.bind((self.host, self.port))
            # 开始监听
            self.server_socket.listen(5)
            self.running = True
            self.logger.info(f"TCP服务器启动成功，监听 {self.host}:{self.port}")
            
            # 启动接受连接的线程
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
        except Exception as e:
            self.logger.error(f"TCP服务器启动失败: {str(e)}")
            raise ServerError(f"TCP服务器启动失败: {str(e)}", 3101)
    
    def stop(self):
        """停止TCP服务器"""
        self.running = False
        if self.server_socket:
            # 关闭服务器Socket（会中断accept调用）
            self.server_socket.close()
            self.server_socket = None
        self.logger.info("TCP服务器已停止")
    
    def _accept_connections(self):
        """接受客户端连接（循环运行）"""
        while self.running:
            try:
                # 等待客户端连接（超时时间1秒，便于退出循环）
                self.server_socket.settimeout(1.0)
                client_socket, client_addr = self.server_socket.accept()
                self.server_socket.settimeout(None)  # 重置超时
                
                # 设置客户端Socket超时
                client_socket.settimeout(30.0)
                # 禁用Nagle算法（减少延迟）
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                # 调用连接回调
                if self.client_connected_callback:
                    self.client_connected_callback(client_socket, client_addr)
            except socket.timeout:
                continue  # 超时，继续循环检查是否停止
            except Exception as e:
                if self.running:
                    self.logger.error(f"接受客户端连接失败: {str(e)}")
                else:
                    break  # 服务器已停止，退出循环