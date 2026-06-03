import pymysql
from app.core.db_utils import get_mysql_connection_kwargs

connection = pymysql.connect(**get_mysql_connection_kwargs())

cursor = connection.cursor()

# 1. 创建 bill 表
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bill (
            id INT AUTO_INCREMENT PRIMARY KEY,
            account_id INT NOT NULL,
            reference_number VARCHAR(100) NOT NULL UNIQUE,
            period_start DATETIME NOT NULL,
            period_end DATETIME NOT NULL,
            issued_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            due_date DATETIME,
            total_amount DECIMAL(10, 2) DEFAULT 0.00,
            status VARCHAR(20) DEFAULT 'DRAFT' COMMENT 'DRAFT, ISSUED, PAID, CANCELLED',
            CONSTRAINT fk_bill_account FOREIGN KEY (account_id) REFERENCES account(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')
    print('✓ 创建 bill 表成功')
except Exception as e:
    print(f'✗ 创建 bill 表失败: {e}')

# 2. 修改 usage_event 表 (添加 bill_id)
try:
    cursor.execute('''
        ALTER TABLE usage_event
        ADD COLUMN bill_id INT NULL,
        ADD CONSTRAINT fk_usage_event_bill FOREIGN KEY (bill_id) REFERENCES bill(id) ON DELETE SET NULL
    ''')
    print('✓ usage_event 添加 bill_id 成功')
except Exception as e:
    if 'Duplicate column' in str(e):
        print('✓ usage_event 已存在 bill_id')
    else:
        print(f'✗ usage_event 添加 bill_id 失败: {e}')

# 3. 修改 staff_charge 表 (添加 bill_id 和 amount)
try:
    cursor.execute('''
        ALTER TABLE staff_charge
        ADD COLUMN bill_id INT NULL,
        ADD COLUMN amount DECIMAL(10, 2) DEFAULT 0.00,
        ADD CONSTRAINT fk_staff_charge_bill FOREIGN KEY (bill_id) REFERENCES bill(id) ON DELETE SET NULL
    ''')
    print('✓ staff_charge 添加 bill_id 和 amount 成功')
except Exception as e:
    if 'Duplicate column' in str(e):
        print('✓ staff_charge 已存在新字段')
    else:
        print(f'✗ staff_charge 添加字段失败: {e}')

connection.commit()
cursor.close()
connection.close()
