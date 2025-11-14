import os
import json
import numpy as np
from typing import List, Tuple, Dict, Optional
from Common.constants import AI_TYPES, AI_LEVELS
from Common.config import Config
from Common.logger import Logger
from Common.data_utils import DataUtils
from Common.error_handler import ModelError
from DB.model_dao import ModelDAO
from DB.training_data_dao import TrainingDataDAO
from AI.base_ai import BaseAI, AIFactory
from AI.nn_ai import NNAI

class ModelManager:
    """AI模型管理器（负责模型的训练、保存、加载、合并等）"""
    def __init__(self):
        self.config = Config.get_instance()
        self.logger = Logger.get_instance()
        self.model_dao = ModelDAO()
        self.training_data_dao = TrainingDataDAO()
        
        # 模型存储路径
        self.model_dir = self.config.get('PATH', 'models')
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
        
        # 当前加载的模型
        self.current_models: Dict[str, BaseAI] = {}
        
        # 加载默认模型
        self.load_default_models()
    
    def load_default_models(self):
        """加载默认模型"""
        try:
            default_models = self.model_dao.get_default_models()
            for model in default_models:
                ai_type = model['model_type']
                ai_color = 2  # 默认白色（可动态切换）
                ai_level = model['level'] if 'level' in model else AI_LEVELS['HARD']
                
                # 创建AI实例
                ai_instance = AIFactory.create_ai(ai_type, ai_color, ai_level)
                
                # 加载模型权重（仅神经网络模型）
                if ai_type in ['nn', 'nn+mcts'] and isinstance(ai_instance, NNAI):
                    ai_instance._load_model(model['model_path'])
                
                # 缓存模型
                self.current_models[model['model_id']] = ai_instance
            
            self.logger.info(f"成功加载 {len(self.current_models)} 个默认模型")
        except Exception as e:
            self.logger.error(f"加载默认模型失败: {str(e)}")
    
    def get_model_by_id(self, model_id: int, user_id: int) -> Optional[BaseAI]:
        """根据模型ID获取模型实例"""
        # 先检查缓存
        if str(model_id) in self.current_models:
            return self.current_models[str(model_id)]
        
        # 从数据库获取模型信息
        model_info = self.model_dao.get_model_by_id(model_id, user_id)
        if not model_info:
            self.logger.error(f"模型 {model_id} 不存在或无访问权限")
            return None
        
        try:
            # 创建AI实例
            ai_instance = AIFactory.create_ai(
                model_info['model_type'],
                PIECE_COLORS['WHITE'],  # 默认颜色，可动态切换
                model_info.get('level', AI_LEVELS['HARD'])
            )
            
            # 加载模型权重（仅神经网络模型）
            if model_info['model_type'] in ['nn', 'nn+mcts'] and isinstance(ai_instance, NNAI):
                ai_instance._load_model(model_info['model_path'])
            
            # 缓存模型
            self.current_models[str(model_id)] = ai_instance
            return ai_instance
        except Exception as e:
            self.logger.error(f"加载模型 {model_id} 失败: {str(e)}")
            return None
    
    def train_model(
        self,
        user_id: int,
        ai_type: str,
        ai_level: str,
        epochs: int = None,
        batch_size: int = None,
        model_name: str = "训练模型"
    ) -> Tuple[bool, Optional[int]]:
        """训练模型
        Args:
            user_id: 用户ID
            ai_type: AI类型
            ai_level: AI难度
            epochs: 训练轮数
            batch_size: 批次大小
            model_name: 模型名称
        Returns:
            (是否成功, 新模型ID/None)
        """
        try:
            # 获取训练数据
            training_data = self.training_data_dao.get_training_data_by_user(user_id, limit=10000)
            if not training_data:
                self.logger.error("没有可用的训练数据")
                return False, None
            
            # 转换训练数据格式
            train_data = []
            for data in training_data:
                board = DataUtils.str_to_board(data['input_data'])
                move_idx = int(data['output_data'])
                move = DataUtils.index_to_move(move_idx, self.config.board_size)
                train_data.append((board, move))
            
            # 创建AI实例（仅支持神经网络模型训练）
            if ai_type not in ['nn', 'nn+mcts']:
                self.logger.error(f"不支持 {ai_type} 类型的模型训练")
                return False, None
            
            ai_instance = AIFactory.create_ai(ai_type, PIECE_COLORS['BLACK'], ai_level)
            if not isinstance(ai_instance, NNAI):
                self.logger.error("训练仅支持神经网络模型")
                return False, None
            
            # 开始训练
            self.logger.info(f"开始训练模型: {model_name}，数据量: {len(train_data)}")
            loss_history, accuracy_history = ai_instance.train_model(
                train_data,
                epochs=epochs,
                batch_size=batch_size
            )
            
            # 保存模型文件
            model_filename = f"{model_name}_{user_id}_{DataUtils.generate_unique_id()}.pth"
            model_path = os.path.join(self.model_dir, model_filename)
            metadata = {
                'loss_history': loss_history,
                'accuracy_history': accuracy_history,
                'train_count': len(train_data),
                'level': ai_level,
                'create_time': DataUtils.get_current_time_str()
            }
            if not ai_instance.save_model(model_path, metadata):
                self.logger.error("模型保存失败")
                return False, None
            
            # 保存模型信息到数据库
            model_id = self.model_dao.add_model({
                'model_name': model_name,
                'user_id': user_id,
                'model_type': ai_type,
                'accuracy': accuracy_history[-1] if accuracy_history else 0.0,
                'train_count': len(train_data),
                'model_path': model_path,
                'is_default': 0
            })
            
            # 缓存新模型
            self.current_models[str(model_id)] = ai_instance
            self.logger.info(f"模型训练完成，ID: {model_id}，准确率: {accuracy_history[-1]:.4f}")
            return True, model_id
        except Exception as e:
            self.logger.error(f"模型训练失败: {str(e)}")
            return False, None
    
    def merge_models(
        self,
        user_id: int,
        model_ids: List[int],
        model_name: str = "合并模型",
        weights: Optional[List[float]] = None
    ) -> Tuple[bool, Optional[int]]:
        """合并多个模型
        Args:
            user_id: 用户ID
            model_ids: 要合并的模型ID列表
            model_name: 合并后的模型名称
            weights: 模型权重
        Returns:
            (是否成功, 新模型ID/None)
        """
        try:
            if len(model_ids) < 2:
                self.logger.error("至少需要两个模型才能合并")
                return False, None
            
            # 检查模型是否属于当前用户
            model_paths = []
            model_types = set()
            for model_id in model_ids:
                model_info = self.model_dao.get_model_by_id(model_id, user_id)
                if not model_info:
                    self.logger.error(f"模型 {model_id} 不存在或无访问权限")
                    return False, None
                model_paths.append(model_info['model_path'])
                model_types.add(model_info['model_type'])
            
            # 检查模型类型是否一致（仅支持神经网络模型合并）
            if len(model_types) != 1 or list(model_types)[0] not in ['nn', 'nn+mcts']:
                self.logger.error("只能合并相同类型的神经网络模型")
                return False, None
            
            # 创建基础模型实例
            ai_instance = AIFactory.create_ai(list(model_types)[0], PIECE_COLORS['BLACK'], AI_LEVELS['HARD'])
            if not isinstance(ai_instance, NNAI):
                self.logger.error("合并仅支持神经网络模型")
                return False, None
            
            # 合并模型权重
            if not ai_instance.merge_models(model_paths, weights):
                self.logger.error("模型合并失败")
                return False, None
            
            # 保存合并后的模型
            model_filename = f"{model_name}_{user_id}_{DataUtils.generate_unique_id()}.pth"
            model_path = os.path.join(self.model_dir, model_filename)
            metadata = {
                'merged_model_ids': model_ids,
                'merge_weights': weights or [1.0/len(model_ids)]*len(model_ids),
                'create_time': DataUtils.get_current_time_str()
            }
            if not ai_instance.save_model(model_path, metadata):
                self.logger.error("合并模型保存失败")
                return False, None
            
            # 评估合并后的模型准确率（使用测试数据）
            test_data = self.training_data_dao.get_training_data_by_user(user_id, limit=1000)
            accuracy = 0.0
            if test_data:
                correct = 0
                total = 0
                ai_instance.model.eval()
                
                with torch.no_grad():
                    for data in test_data:
                        board = DataUtils.str_to_board(data['input_data'])
                        move_idx = int(data['output_data'])
                        input_tensor = ai_instance._preprocess_board(board)
                        output = ai_instance.model(input_tensor)
                        _, predicted = torch.max(output.data, 1)
                        if predicted.item() == move_idx:
                            correct += 1
                        total += 1
                
                accuracy = correct / total if total > 0 else 0.0
            
            # 保存模型信息到数据库
            model_id = self.model_dao.add_model({
                'model_name': model_name,
                'user_id': user_id,
                'model_type': list(model_types)[0],
                'accuracy': accuracy,
                'train_count': sum([self.model_dao.get_model_by_id(mid, user_id)['train_count'] for mid in model_ids]),
                'model_path': model_path,
                'is_default': 0
            })
            
            # 缓存新模型
            self.current_models[str(model_id)] = ai_instance
            self.logger.info(f"模型合并完成，ID: {model_id}，准确率: {accuracy:.4f}")
            return True, model_id
        except Exception as e:
            self.logger.error(f"模型合并失败: {str(e)}")
            return False, None
    
    def export_model(self, model_id: int, user_id: int, export_path: str) -> bool:
        """导出模型到本地文件"""
        try:
            # 获取模型信息
            model_info = self.model_dao.get_model_by_id(model_id, user_id)
            if not model_info:
                self.logger.error(f"模型 {model_id} 不存在或无访问权限")
                return False
            
            # 读取模型文件
            if not os.path.exists(model_info['model_path']):
                self.logger.error(f"模型文件不存在: {model_info['model_path']}")
                return False
            
            # 读取模型权重
            with open(model_info['model_path'], 'rb') as f:
                model_data = f.read()
            
            # 写入导出文件
            with open(export_path, 'wb') as f:
                f.write(model_data)
            
            # 生成模型元数据文件
            meta_path = os.path.splitext(export_path)[0] + '.json'
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'model_info': model_info,
                    'export_time': DataUtils.get_current_time_str()
                }, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"模型导出成功: {export_path}")
            return True
        except Exception as e:
            self.logger.error(f"模型导出失败: {str(e)}")
            return False
    
    def import_model(self, user_id: int, import_path: str, model_name: str = "导入模型") -> Tuple[bool, Optional[int]]:
        """从本地文件导入模型"""
        try:
            # 检查文件是否存在
            if not os.path.exists(import_path):
                self.logger.error(f"导入文件不存在: {import_path}")
                return False, None
            
            # 读取元数据（如果存在）
            meta_path = os.path.splitext(import_path)[0] + '.json'
            model_info = {
                'model_name': model_name,
                'user_id': user_id,
                'model_type': 'nn',
                'accuracy': 0.0,
                'train_count': 0,
                'is_default': 0
            }
            
            if os.path.exists(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)
                    if 'model_info' in meta_data:
                        model_info.update({
                            'model_type': meta_data['model_info'].get('model_type', 'nn'),
                            'accuracy': meta_data['model_info'].get('accuracy', 0.0),
                            'train_count': meta_data['model_info'].get('train_count', 0)
                        })
            
            # 复制模型文件到本地存储目录
            model_filename = f"{model_name}_{user_id}_{DataUtils.generate_unique_id()}.pth"
            model_path = os.path.join(self.model_dir, model_filename)
            
            with open(import_path, 'rb') as f_in:
                with open(model_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            # 验证模型文件
            ai_instance = AIFactory.create_ai(model_info['model_type'], PIECE_COLORS['BLACK'], AI_LEVELS['HARD'])
            if isinstance(ai_instance, NNAI) and not ai_instance._load_model(model_path):
                self.logger.error("导入的模型文件无效")
                os.remove(model_path)
                return False, None
            
            # 保存模型信息到数据库
            model_id = self.model_dao.add_model({
                **model_info,
                'model_path': model_path
            })
            
            # 缓存新模型
            self.current_models[str(model_id)] = ai_instance
            self.logger.info(f"模型导入成功，ID: {model_id}")
            return True, model_id
        except Exception as e:
            self.logger.error(f"模型导入失败: {str(e)}")
            return False, None
    
    def delete_model(self, model_id: int, user_id: int) -> bool:
        """删除模型（从数据库和本地文件）"""
        try:
            # 获取模型信息
            model_info = self.model_dao.get_model_by_id(model_id, user_id)
            if not model_info:
                self.logger.error(f"模型 {model_id} 不存在或无访问权限")
                return False
            
            # 删除本地文件
            if os.path.exists(model_info['model_path']):
                os.remove(model_info['model_path'])
                self.logger.info(f"删除模型文件: {model_info['model_path']}")
            
            # 从数据库删除
            if not self.model_dao.delete_model(model_id, user_id):
                self.logger.error("删除数据库中的模型记录失败")
                return False
            
            # 从缓存删除
            if str(model_id) in self.current_models:
                del self.current_models[str(model_id)]
            
            self.logger.info(f"模型 {model_id} 删除成功")
            return True
        except Exception as e:
            self.logger.error(f"删除模型 {model_id} 失败: {str(e)}")
            return False
    
    def get_user_models(self, user_id: int) -> List[Dict]:
        """获取用户的所有模型"""
        return self.model_dao.get_models_by_user(user_id)
    
    def add_training_data(self, user_id: int, board: List[List[int]], best_move: Tuple[int, int], score: float = 0.0) -> bool:
        """添加训练数据"""
        try:
            # 转换数据格式
            input_data = DataUtils.board_to_str(board)
            output_data = str(DataUtils.move_to_index(best_move[0], best_move[1], self.config.board_size))
            
            # 保存到数据库
            return self.training_data_dao.add_training_data({
                'user_id': user_id,
                'input_data': input_data,
                'output_data': output_data,
                'score': score
            })
        except Exception as e:
            self.logger.error(f"添加训练数据失败: {str(e)}")
            return False
    
    def clear_training_data(self, user_id: int) -> bool:
        """清空用户的训练数据"""
        try:
            return self.training_data_dao.clear_training_data(user_id)
        except Exception as e:
            self.logger.error(f"清空训练数据失败: {str(e)}")
            return False