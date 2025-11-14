-- 用户表：存储用户信息
CREATE TABLE [dbo].[Users](
    [user_id] INT IDENTITY(1,1) PRIMARY KEY,
    [username] NVARCHAR(50) NOT NULL UNIQUE,
    [password] NVARCHAR(100) NOT NULL,
    [nickname] NVARCHAR(50) NOT NULL,
    [win_count] INT DEFAULT 0,
    [lose_count] INT DEFAULT 0,
    [draw_count] INT DEFAULT 0,
    [create_time] DATETIME DEFAULT GETDATE(),
    [last_login_time] DATETIME NULL
);

-- 对局表：存储对战记录
CREATE TABLE [dbo].[Games](
    [game_id] INT IDENTITY(1,1) PRIMARY KEY,
    [user1_id] INT NOT NULL,
    [user2_id] INT NULL, -- 人机对战时为NULL
    [game_mode] NVARCHAR(20) NOT NULL, -- 'pvp', 'pve', 'online', 'train'
    [ai_level] NVARCHAR(20) NULL, -- AI难度（pve/train模式）
    [start_time] DATETIME DEFAULT GETDATE(),
    [end_time] DATETIME NULL,
    [winner_id] INT NULL, -- 获胜者ID（平局为NULL）
    [move_history] NVARCHAR(MAX) NOT NULL, -- 落子历史（JSON格式）
    [analysis_report] NVARCHAR(MAX) NULL, -- 分析报告（JSON格式）
    FOREIGN KEY ([user1_id]) REFERENCES [dbo].[Users]([user_id]),
    FOREIGN KEY ([user2_id]) REFERENCES [dbo].[Users]([user_id]),
    FOREIGN KEY ([winner_id]) REFERENCES [dbo].[Users]([user_id])
);

-- 模型表：存储AI模型信息
CREATE TABLE [dbo].[AI_Models](
    [model_id] INT IDENTITY(1,1) PRIMARY KEY,
    [model_name] NVARCHAR(100) NOT NULL UNIQUE,
    [user_id] INT NOT NULL, -- 模型所有者
    [model_type] NVARCHAR(20) NOT NULL, -- 'nn', 'minimax', 'mcts'
    [accuracy] DECIMAL(5,4) DEFAULT 0.0, -- 准确率
    [train_count] INT DEFAULT 0, -- 训练次数
    [create_time] DATETIME DEFAULT GETDATE(),
    [update_time] DATETIME DEFAULT GETDATE(),
    [model_path] NVARCHAR(255) NOT NULL, -- 本地存储路径
    [is_default] BIT DEFAULT 0, -- 是否为默认模型
    FOREIGN KEY ([user_id]) REFERENCES [dbo].[Users]([user_id])
);

-- 训练数据表：存储训练数据
CREATE TABLE [dbo].[Training_Data](
    [data_id] INT IDENTITY(1,1) PRIMARY KEY,
    [user_id] INT NOT NULL,
    [model_id] INT NULL, -- 关联模型（可为NULL）
    [input_data] NVARCHAR(MAX) NOT NULL, -- 输入数据（棋盘状态）
    [output_data] NVARCHAR(MAX) NOT NULL, -- 输出数据（最佳落子）
    [score] DECIMAL(5,4) DEFAULT 0.0, -- 数据评分
    [create_time] DATETIME DEFAULT GETDATE(),
    FOREIGN KEY ([user_id]) REFERENCES [dbo].[Users]([user_id]),
    FOREIGN KEY ([model_id]) REFERENCES [dbo].[AI_Models]([model_id])
);

-- 联机房间表：存储联机对战房间
CREATE TABLE [dbo].[Online_Rooms](
    [room_id] INT IDENTITY(1,1) PRIMARY KEY,
    [host_id] INT NOT NULL,
    [guest_id] INT NULL,
    [room_status] NVARCHAR(20) DEFAULT 'waiting', -- 'waiting', 'playing', 'ended'
    [create_time] DATETIME DEFAULT GETDATE(),
    [update_time] DATETIME DEFAULT GETDATE(),
    [board_state] NVARCHAR(MAX) NOT NULL, -- 当前棋盘状态
    [current_player] INT DEFAULT 1, -- 当前回合玩家（1:黑，2:白）
    [move_history] NVARCHAR(MAX) DEFAULT '[]', -- 落子历史
    FOREIGN KEY ([host_id]) REFERENCES [dbo].[Users]([user_id]),
    FOREIGN KEY ([guest_id]) REFERENCES [dbo].[Users]([user_id])
);

-- 索引优化
CREATE INDEX [IX_Games_User1Id] ON [dbo].[Games]([user1_id]);
CREATE INDEX [IX_Games_GameMode] ON [dbo].[Games]([game_mode]);
CREATE INDEX [IX_AI_Models_UserId] ON [dbo].[AI_Models]([user_id]);
CREATE INDEX [IX_Online_Rooms_Status] ON [dbo].[Online_Rooms]([room_status]);