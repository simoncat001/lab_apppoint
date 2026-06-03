import pymysql
from app.core.db_utils import get_mysql_connection_kwargs

connection = pymysql.connect(**get_mysql_connection_kwargs())

cursor = connection.cursor()

# 1. 创建 configuration 表
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuration (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            tool_id INT NOT NULL,
            configurable_item_name VARCHAR(200),
            advance_notice_limit INT NOT NULL DEFAULT 0,
            display_order INT NOT NULL DEFAULT 0,
            prompt TEXT,
            current_settings TEXT,
            available_settings TEXT,
            calendar_colors TEXT,
            absence_string VARCHAR(50),
            qualified_users_are_maintainers BOOLEAN DEFAULT FALSE,
            exclude_from_configuration_agenda BOOLEAN DEFAULT FALSE,
            enabled BOOLEAN DEFAULT TRUE,
            CONSTRAINT fk_config_tool FOREIGN KEY (tool_id) REFERENCES tool(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')
    print('✓ 创建 configuration 表成功')
except Exception as e:
    print(f'✗ 创建 configuration 表失败: {e}')

# 2. 创建 configuration_maintainers 表
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuration_maintainers (
            configuration_id INT NOT NULL,
            user_id INT NOT NULL,
            PRIMARY KEY (configuration_id, user_id),
            CONSTRAINT fk_cm_config FOREIGN KEY (configuration_id) REFERENCES configuration(id) ON DELETE CASCADE,
            CONSTRAINT fk_cm_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')
    print('✓ 创建 configuration_maintainers 表成功')
except Exception as e:
    print(f'✗ 创建 configuration_maintainers 表失败: {e}')

# 3. 创建 configuration_option 表
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuration_option (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            configuration_id INT,
            reservation_id INT NOT NULL,
            current_setting VARCHAR(200),
            available_settings TEXT,
            calendar_colors TEXT,
            absence_string VARCHAR(50),
            CONSTRAINT fk_co_config FOREIGN KEY (configuration_id) REFERENCES configuration(id) ON DELETE SET NULL,
            CONSTRAINT fk_co_reservation FOREIGN KEY (reservation_id) REFERENCES reservation(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')
    print('✓ 创建 configuration_option 表成功')
except Exception as e:
    print(f'✗ 创建 configuration_option 表失败: {e}')

# 4. 创建 configuration_history 表
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuration_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            configuration_id INT NOT NULL,
            user_id INT NOT NULL,
            modification_time DATETIME NOT NULL,
            item_name VARCHAR(200),
            slot INT NOT NULL,
            setting TEXT NOT NULL,
            CONSTRAINT fk_ch_config FOREIGN KEY (configuration_id) REFERENCES configuration(id) ON DELETE CASCADE,
            CONSTRAINT fk_ch_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')
    print('✓ 创建 configuration_history 表成功')
except Exception as e:
    print(f'✗ 创建 configuration_history 表失败: {e}')

connection.commit()
cursor.close()
connection.close()
