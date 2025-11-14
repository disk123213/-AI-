import socket
import threading
import time
from typing import List, Dict, Optional
from Common.config import Config
from Common.logger import Logger
from Common.constants import MSG_TYPES, ROOM_STATUSES
from Common.error_handler import ServerError
from Server.tcp_server import TCPServer
from Server.client_handler import ClientHandler
from Server.room_manager import RoomManager
from DB.user_dao import UserDAO

class Server:
    """联机对战主服务器"""
    def __init__(self, host: str = '0.0.0.0', port: int = 8888):
        self.config = Config.get_instance()
        self.logger = Logger.get_instance()
        self.user_dao = UserDAO()
        
        # 服务器配置
        self.host = host or self.config.server_host
        self.port = port or self.config.server_port
        self.max_clients = self.config.get_int('SERVER', 'max_clients')
        self.timeout = self.config.get_int('SERVER', 'timeout')
        
        # 核心组件
        self.tcp_server = TCPServer(self.host, self.port)
        self.room_manager = RoomManager()
        self.client_handlers: List[ClientHandler] = []  # 客户端处理器列表
        self.client_map: Dict[str, ClientHandler] = {}  # 用户ID -> 客户端处理器映射
        
        # 状态变量
        self.running = False
        self.lock = threading.Lock()  # 线程安全锁
        
        # 心跳检测线程
        self.heartbeat_thread = None
    
    def start(self):
        """启动服务器"""
        try:
            self.running = True
            # 启动TCP服务器
            self.tcp_server.start(self._on_client_connected)
            self.logger.info(f"主服务器启动成功，监听 {self.host}:{self.port}")
            
            # 启动心跳检测线程
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_check, daemon=True)
            self.heartbeat_thread.start()
            
            # 等待服务器停止
            while self.running:
                time.sleep(1)
        except Exception as e:
            self.logger.error(f"服务器启动失败: {str(e)}")
            raise ServerError(f"服务器启动失败: {str(e)}", 3001)
    
    def stop(self):
        """停止服务器"""
        self.running = False
        # 停止TCP服务器
        self.tcp_server.stop()
        # 关闭所有客户端连接
        with self.lock:
            for handler in self.client_handlers:
                handler.stop()
            self.client_handlers.clear()
            self.client_map.clear()
        self.logger.info("服务器已停止")
    
    def _on_client_connected(self, client_socket: socket.socket, client_addr: tuple):
        """客户端连接回调"""
        with self.lock:
            # 检查最大连接数
            if len(self.client_handlers) >= self.max_clients:
                self.logger.warning(f"客户端 {client_addr} 连接被拒绝：已达到最大连接数 {self.max_clients}")
                client_socket.sendall(self._pack_message(MSG_TYPES['ERROR'], {'message': '服务器繁忙，请稍后再试'}))
                client_socket.close()
                return
            
            # 创建客户端处理器
            handler = ClientHandler(
                client_socket,
                client_addr,
                self,
                self.room_manager,
                self.user_dao,
                self.timeout
            )
            self.client_handlers.append(handler)
            self.logger.info(f"客户端 {client_addr} 连接成功，当前连接数：{len(self.client_handlers)}")
            
            # 启动客户端处理线程
            handler.start()
    
    def _heartbeat_check(self):
        """心跳检测（定期清理超时客户端）"""
        while self.running:
            time.sleep(10)  # 每10秒检测一次
            with self.lock:
                current_time = time.time()
                to_remove = []
                
                for handler in self.client_handlers:
                    # 检查超时（超过timeout秒无心跳）
                    if current_time - handler.last_heartbeat > self.timeout:
                        self.logger.warning(f"客户端 {handler.client_addr} 心跳超时，断开连接")
                        to_remove.append(handler)
                        handler.stop()
                
                # 移除超时客户端
                for handler in to_remove:
                    if handler.user_id in self.client_map:
                        del self.client_map[handler.user_id]
                    self.client_handlers.remove(handler)
                
                # 清理空房间
                self.room_manager.clean_empty_rooms()
    
    def register_client(self, user_id: str, handler: ClientHandler):
        """注册客户端（用户登录后）"""
        with self.lock:
            # 踢掉已登录的同名用户
            if user_id in self.client_map:
                old_handler = self.client_map[user_id]
                self.logger.warning(f"用户 {user_id} 在新客户端 {handler.client_addr} 登录，踢掉旧客户端 {old_handler.client_addr}")
                old_handler.send_error("你的账号在其他设备登录，已被强制下线")
                old_handler.stop()
                self.client_handlers.remove(old_handler)
            
            self.client_map[user_id] = handler
            self.logger.info(f"用户 {user_id} 注册到客户端 {handler.client_addr}")
    
    def unregister_client(self, user_id: str, handler: ClientHandler):
        """注销客户端（用户退出或断开连接）"""
        with self.lock:
            if user_id in self.client_map and self.client_map[user_id] == handler:
                del self.client_map[user_id]
                self.logger.info(f"用户 {user_id} 从客户端 {handler.client_addr} 注销")
            
            # 从客户端列表移除
            if handler in self.client_handlers:
                self.client_handlers.remove(handler)
    
    def get_client_by_user_id(self, user_id: str) -> Optional[ClientHandler]:
        """根据用户ID获取客户端处理器"""
        with self.lock:
            return self.client_map.get(user_id)
    
    @staticmethod
    def _pack_message(msg_type: str, data: Dict) -> bytes:
        """打包消息（JSON序列化+长度前缀）"""
        import json
        message = {
            'type': msg_type,
            'data': data,
            'timestamp': time.time()
        }
        json_str = json.dumps(message, ensure_ascii=False) + '\n'  # 换行符作为消息结束标志
        return json_str.encode('utf-8')
    
    @staticmethod
    def _unpack_message(data: bytes) -> Tuple[Optional[str], Optional[Dict]]:
        """解包消息（JSON反序列化）"""
        try:
            json_str = data.decode('utf-8').strip()
            if not json_str:
                return None, None
            message = json.loads(json_str)
            return message.get('type'), message.get('data', {})
        except Exception as e:
            Logger.get_instance().error(f"消息解包失败: {str(e)}")
            return None, None