import pymysql
from app.core.db_utils import get_mysql_connection_kwargs

connection = pymysql.connect(**get_mysql_connection_kwargs())

cursor = connection.cursor()

# 创建 staff_charge 表
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_charge (
            id INT AUTO_INCREMENT PRIMARY KEY,
            staff_member_id INT NOT NULL,
            customer_id INT NOT NULL,
            project_id INT NOT NULL,
            validated_by_id INT,
            waived_by_id INT,
            start DATETIME DEFAULT CURRENT_TIMESTAMP,
            end DATETIME,
            waived_on DATETIME,
            validated BOOLEAN DEFAULT FALSE,
            waived BOOLEAN DEFAULT FALSE,
            note TEXT,
            CONSTRAINT fk_staff_charge_staff FOREIGN KEY (staff_member_id) REFERENCES user(id) ON DELETE CASCADE,
            CONSTRAINT fk_staff_charge_customer FOREIGN KEY (customer_id) REFERENCES user(id) ON DELETE CASCADE,
            CONSTRAINT fk_staff_charge_project FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
            CONSTRAINT fk_staff_charge_validated FOREIGN KEY (validated_by_id) REFERENCES user(id) ON DELETE CASCADE,
            CONSTRAINT fk_staff_charge_waived FOREIGN KEY (waived_by_id) REFERENCES user(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')
    print('✓ 创建 staff_charge 表成功')
except Exception as e:
    print(f'✗ 创建 staff_charge 表失败: {e}')

connection.commit()
cursor.close()
connection.close()
