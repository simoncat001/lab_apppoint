#!/usr/bin/env python
"""测试 MySQL 连接"""
import pymysql
from app.core.db_utils import get_mysql_connection_kwargs

try:
    connection = pymysql.connect(**get_mysql_connection_kwargs())
    
    cursor = connection.cursor()
    cursor.execute("SELECT DATABASE()")
    db = cursor.fetchone()
    
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    print("✓ MySQL 连接成功！")
    print(f"当前数据库: {db[0]}")
    print(f"表数量: {len(tables)}")
    print("\n表列表:")
    for table in tables:
        print(f"  - {table[0]}")
    
    cursor.close()
    connection.close()
    
except Exception as e:
    print(f"✗ 连接失败: {e}")
