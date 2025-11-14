import socket
import threading
import time
from typing import Dict, Optional, Tuple
from Common.logger import Logger
from Common.constants import MSG_TYPES, ROOM_STATUSES, PIECE_COLORS
from Common.error_handler import ServerError
from Common.data_utils import DataUtils
from DB.user_dao import UserDAO
from Server.room_manager import RoomManager
from Server.room import Room

class ClientHandler:
    """客户端处理器（单个客户端的消息处理）"""
    def __init__(
        self,
        client_socket: socket.socket,
        client_addr: tuple,
        server: 'Server',
        room_manager: RoomManager,
        user_dao: UserDAO,
        timeout: int = 30
    ):
        self.client_socket = client_socket
        self.client_addr = client_addr
        self.server = server
        self.room_manager = room_manager
        self.user_dao = user_dao
        self.timeout = timeout
        
        # 状态变量
        self.running = False
        self.user_id = None  # 登录后的用户ID
        self.username = None  # 用户名
        self.nickname = None  # 昵称
        self.current_room_id = None  # 当前所在房间ID
        self.last_heartbeat = time.time()  # 最后心跳时间
        
        # 线程
        self.recv_thread: Optional[threading.Thread] = None
        
        # 日志
        self.logger = Logger.get_instance()
    
    def start(self):
        """启动客户端处理器"""
        self.running = True
        # 启动接收消息线程
        self.recv_thread = threading.Thread(target=self._recv_messages, daemon=True)
        self.recv_thread.start()
        self.logger.info(f"客户端处理器启动，处理 {self.client_addr} 的消息")
    
    def stop(self):
        """停止客户端处理器"""
        self.running = False
        # 退出当前房间
        if self.current_room_id:
            self.room_manager.leave_room(self.current_room_id, self.user_id)
            self.current_room_id = None
        # 注销客户端
        if self.user_id:
            self.server.unregister_client(self.user_id, self)
        # 关闭Socket
        try:
            self.client_socket.close()
        except:
            pass
        self.logger.info(f"客户端处理器已停止，客户端 {self.client_addr} 断开连接")
    
    def _recv_messages(self):
        """接收并处理客户端消息（循环运行）"""
        buffer = b''
        while self.running:
            try:
                # 接收数据（每次最多4096字节）
                data = self.client_socket.recv(4096)
                if not data:
                    self.logger.warning(f"客户端 {self.client_addr} 主动断开连接")
                    break
                
                # 拼接缓冲区
                buffer += data
                # 按换行符分割消息（处理粘包）
                while b'\n' in buffer:
                    msg_bytes, buffer = buffer.split(b'\n', 1)
                    if msg_bytes:
                        self._handle_message(msg_bytes)
            
            except socket.timeout:
                self.logger.warning(f"客户端 {self.client_addr} 接收消息超时")
                break
            except Exception as e:
                self.logger.error(f"接收客户端 {self.client_addr} 消息失败: {str(e)}")
                break
        
        # 停止处理器
        self.stop()
    
    def _handle_message(self, msg_bytes: bytes):
        """处理单个消息"""
        # 解包消息
        msg_type, data = self.server._unpack_message(msg_bytes)
        if not msg_type or not data:
            self.send_error("无效的消息格式")
            return
        
        self.logger.info(f"收到客户端 {self.client_addr} 的消息：{msg_type}，数据：{data}")
        
        # 更新心跳时间
        self.last_heartbeat = time.time()
        
        # 根据消息类型处理
        try:
            if msg_type == MSG_TYPES['LOGIN']:
                self._handle_login(data)
            elif msg_type == MSG_TYPES['LOGOUT']:
                self._handle_logout(data)
            elif msg_type == MSG_TYPES['CREATE_ROOM']:
                self._handle_create_room(data)
            elif msg_type == MSG_TYPES['JOIN_ROOM']:
                self._handle_join_room(data)
            elif msg_type == MSG_TYPES['LEAVE_ROOM']:
                self._handle_leave_room(data)
            elif msg_type == MSG_TYPES['MOVE']:
                self._handle_move(data)
            elif msg_type == MSG_TYPES['CHAT']:
                self._handle_chat(data)
            elif msg_type == MSG_TYPES['HEARTBEAT']:
                self._handle_heartbeat(data)
            else:
                self.send_error(f"不支持的消息类型：{msg_type}")
        except Exception as e:
            self.logger.error(f"处理消息 {msg_type} 失败: {str(e)}")
            self.send_error(f"处理请求失败：{str(e)}")
    
    def _handle_login(self, data: Dict):
        """处理登录请求"""
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            self.send_error("用户名和密码不能为空")
            return
        
        # 验证用户
        user = self.user_dao.login(username, password)
        if not user:
            self.send_error("用户名或密码错误")
            return
        
        # 注册客户端
        self.user_id = str(user['user_id'])
        self.username = username
        self.nickname = user['nickname']
        self.server.register_client(self.user_id, self)
        
        # 发送登录成功响应
        self.send_message(MSG_TYPES['LOGIN'], {
            'success': True,
            'user_info': {
                'user_id': self.user_id,
                'username': self.username,
                'nickname': self.nickname,
                'win_count': user['win_count'],
                'lose_count': user['lose_count'],
                'draw_count': user['draw_count']
            }
        })
        self.logger.info(f"用户 {self.username}（ID：{self.user_id}）登录成功")
    
    def _handle_logout(self, data: Dict):
        """处理退出登录请求"""
        self.send_message(MSG_TYPES['LOGOUT'], {'success': True, 'message': '退出成功'})
        self.logger.info(f"用户 {self.username}（ID：{self.user_id}）退出登录")
        self.stop()
    
    def _handle_create_room(self, data: Dict):
        """处理创建房间请求"""
        if not self.user_id:
            self.send_error("请先登录")
            return
        
        room_name = data.get('room_name', f"{self.nickname}的房间")
        # 创建房间（主机为当前用户）
        room_id = self.room_manager.create_room(
            host_id=self.user_id,
            host_nickname=self.nickname,
            room_name=room_name
        )
        
        if room_id:
            # 加入创建的房间
            self.current_room_id = room_id
            self.send_message(MSG_TYPES['CREATE_ROOM'], {
                'success': True,
                'room_id': room_id,
                'room_name': room_name,
                'message': '房间创建成功'
            })
            self.logger.info(f"用户 {self.user_id} 创建房间 {room_id}：{room_name}")
        else:
            self.send_error("创建房间失败")
    
    def _handle_join_room(self, data: Dict):
        """处理加入房间请求"""
        if not self.user_id:
            self.send_error("请先登录")
            return
        
        room_id = data.get('room_id')
        if not room_id:
            self.send_error("房间ID不能为空")
            return
        
        # 加入房间
        success, message = self.room_manager.join_room(room_id, self.user_id, self.nickname)
        if success:
            self.current_room_id = room_id
            # 获取房间信息
            room = self.room_manager.get_room(room_id)
            if room:
                # 通知房间内所有成员
                room.broadcast_message(
                    sender_id=self.user_id,
                    msg_type=MSG_TYPES['JOIN_ROOM'],
                    data={
                        'user_id': self.user_id,
                        'nickname': self.nickname,
                        'message': f"{self.nickname}加入了房间"
                    }
                )
                # 发送加入成功响应（包含房间信息）
                self.send_message(MSG_TYPES['JOIN_ROOM'], {
                    'success': True,
                    'room_id': room_id,
                    'room_name': room.room_name,
                    'host_id': room.host_id,
                    'host_nickname': room.host_nickname,
                    'guest_id': room.guest_id,
                    'guest_nickname': room.guest_nickname,
                    'board_state': room.board_state,
                    'current_player': room.current_player
                })
                self.logger.info(f"用户 {self.user_id} 加入房间 {room_id}")
        else:
            self.send_error(message or "加入房间失败")
    
    def _handle_leave_room(self, data: Dict):
        """处理离开房间请求"""
        if not self.user_id or not self.current_room_id:
            self.send_error("你不在任何房间中")
            return
        
        # 离开房间
        success, message = self.room_manager.leave_room(self.current_room_id, self.user_id)
        if success:
            # 通知房间内其他成员
            room = self.room_manager.get_room(self.current_room_id)
            if room:
                room.broadcast_message(
                    sender_id=self.user_id,
                    msg_type=MSG_TYPES['LEAVE_ROOM'],
                    data={
                        'user_id': self.user_id,
                        'nickname': self.nickname,
                        'message': f"{self.nickname}离开了房间"
                    }
                )
            # 发送离开成功响应
            self.send_message(MSG_TYPES['LEAVE_ROOM'], {
                'success': True,
                'message': '离开房间成功'
            })
            self.current_room_id = None
            self.logger.info(f"用户 {self.user_id} 离开房间 {self.current_room_id}")
        else:
            self.send_error(message or "离开房间失败")
    
    def _handle_move(self, data: Dict):
        """处理落子请求"""
        if not self.user_id or not self.current_room_id:
            self.send_error("你不在任何房间中，无法落子")
            return
        
        # 获取落子数据
        x = data.get('x')
        y = data.get('y')
        if x is None or y is None:
            self.send_error("落子坐标不能为空")
            return
        
        # 转换为整数
        try:
            x = int(x)
            y = int(y)
        except:
            self.send_error("落子坐标必须是整数")
            return
        
        # 获取房间
        room = self.room_manager.get_room(self.current_room_id)
        if not room:
            self.send_error("房间不存在")
            return
        
        # 检查房间状态
        if room.room_status != ROOM_STATUSES['PLAYING']:
            self.send_error("房间未处于游戏中，无法落子")
            return
        
        # 检查是否是当前玩家的回合
        if room.current_player not in [self.user_id, 'ai']:
            self.send_error("不是你的回合，无法落子")
            return
        
        # 检查落子位置是否有效
        board = DataUtils.str_to_board(room.board_state)
        board_size = len(board)
        if x < 0 or x >= board_size or y < 0 or y >= board_size:
            self.send_error("落子位置超出棋盘范围")
            return
        if board[x][y] != PIECE_COLORS['EMPTY']:
            self.send_error("该位置已被占用，无法落子")
            return
        
        # 执行落子
        success, result = room.make_move(self.user_id, x, y)
        if success:
            # 广播落子信息
            room.broadcast_message(
                sender_id=self.user_id,
                msg_type=MSG_TYPES['MOVE'],
                data={
                    'user_id': self.user_id,
                    'nickname': self.nickname,
                    'x': x,
                    'y': y,
                    'board_state': room.board_state,
                    'move_history': room.move_history,
                    'current_player': room.current_player,
                    'game_result': result.get('game_result'),
                    'win_line': result.get('win_line', [])
                }
            )
            self.logger.info(f"用户 {self.user_id} 在房间 {self.current_room_id} 落子：({x},{y})")
        else:
            self.send_error(result.get('message', "落子失败"))
    
    def _handle_chat(self, data: Dict):
        """处理聊天消息"""
        if not self.user_id or not self.current_room_id:
            self.send_error("你不在任何房间中，无法发送消息")
            return
        
        content = data.get('content', '').strip()
        if not content:
            self.send_error("聊天内容不能为空")
            return
        
        # 获取房间
        room = self.room_manager.get_room(self.current_room_id)
        if not room:
            self.send_error("房间不存在")
            return
        
        # 广播聊天消息
        room.broadcast_message(
            sender_id=self.user_id,
            msg_type=MSG_TYPES['CHAT'],
            data={
                'user_id': self.user_id,
                'nickname': self.nickname,
                'content': content,
                'timestamp': time.time()
            }
        )
        self.logger.info(f"用户 {self.user_id} 在房间 {self.current_room_id} 发送消息：{content}")
    
    def _handle_heartbeat(self, data: Dict):
        """处理心跳包"""
        # 发送心跳响应
        self.send_message(MSG_TYPES['HEARTBEAT'], {'status': 'alive'})
        self.logger.debug(f"收到客户端 {self.client_addr} 的心跳包，已响应")
    
    def send_message(self, msg_type: str, data: Dict):
        """发送消息给客户端"""
        try:
            message = self.server._pack_message(msg_type, data)
            self.client_socket.sendall(message)
        except Exception as e:
            self.logger.error(f"发送消息给客户端 {self.client_addr} 失败: {str(e)}")
    
    def send_error(self, message: str):
        """发送错误消息给客户端"""
        self.send_message(MSG_TYPES['ERROR'], {'message': message})