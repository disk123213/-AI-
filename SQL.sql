-- 用户表
CREATE TABLE `user` (
  `user_id` int PRIMARY KEY AUTO_INCREMENT,
  `username` varchar(50) UNIQUE NOT NULL,
  `password` varchar(100) NOT NULL,
  `nickname` varchar(50) NOT NULL,
  `win_count` int DEFAULT 0,
  `lose_count` int DEFAULT 0,
  `draw_count` int DEFAULT 0,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP
);

-- 模型表
CREATE TABLE `model` (
  `model_id` int PRIMARY KEY AUTO_INCREMENT,
  `model_name` varchar(100) NOT NULL,
  `user_id` int NOT NULL,
  `model_type` varchar(20) NOT NULL,
  `model_path` varchar(255) NOT NULL,
  `accuracy` float DEFAULT 0.0,
  `train_count` int DEFAULT 0,
  `is_default` tinyint DEFAULT 0,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`)
);

-- 训练数据表
CREATE TABLE `training_data` (
  `data_id` int PRIMARY KEY AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `input_data` text NOT NULL,
  `output_data` varchar(10) NOT NULL,
  `score` float DEFAULT 0.0,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`)
);

-- 游戏记录表
CREATE TABLE `game_record` (
  `record_id` int PRIMARY KEY AUTO_INCREMENT,
  `user1_id` int NOT NULL,
  `user2_id` int DEFAULT NULL,
  `mode` varchar(20) NOT NULL,
  `result` varchar(10) NOT NULL,
  `move_count` int NOT NULL,
  `start_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `end_time` datetime DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user1_id`) REFERENCES `user`(`user_id`),
  FOREIGN KEY (`user2_id`) REFERENCES `user`(`user_id`)
);