"""
测试数据库初始化脚本

创建测试用的 SQLite 数据库和示例数据。
"""

import sqlite3
from pathlib import Path


# 数据库路径
DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "test.db"


def init_database():
    """初始化数据库"""

    # 确保目录存在
    DB_DIR.mkdir(parents=True, exist_ok=True)

    # 如果数据库已存在，先删除
    if DB_PATH.exists():
        DB_PATH.unlink()

    # 创建连接
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 创建人员表
    cursor.execute("""
        CREATE TABLE persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT,
            position TEXT,
            email TEXT,
            phone TEXT,
            hire_date TEXT
        )
    """)

    # 插入测试数据
    test_data = [
        ("张三", "技术部", "高级工程师", "zhangsan@example.com", "13800138001", "2022-03-15"),
        ("李四", "技术部", "工程师", "lisi@example.com", "13800138002", "2023-01-10"),
        ("王五", "产品部", "产品经理", "wangwu@example.com", "13800138003", "2021-06-20"),
        ("赵六", "市场部", "市场专员", "zhaoliu@example.com", "13800138004", "2023-05-08"),
        ("李明", "技术部", "技术总监", "liming@example.com", "13800138005", "2020-01-15"),
        ("陈晓", "人事部", "HR经理", "chenxiao@example.com", "13800138006", "2021-09-01"),
        ("刘洋", "技术部", "前端工程师", "liuyang@example.com", "13800138007", "2022-08-15"),
        ("周芳", "财务部", "财务主管", "zhoufang@example.com", "13800138008", "2019-11-20"),
        ("吴强", "技术部", "后端工程师", "wuqiang@example.com", "13800138009", "2023-02-28"),
        ("郑丽", "产品部", "UI设计师", "zhengli@example.com", "13800138010", "2022-12-01"),
    ]

    cursor.executemany("""
        INSERT INTO persons (name, department, position, email, phone, hire_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, test_data)

    conn.commit()
    conn.close()

    print(f"数据库已创建: {DB_PATH}")
    print(f"已插入 {len(test_data)} 条测试数据")


def verify_database():
    """验证数据库"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 查询所有数据
    cursor.execute("SELECT COUNT(*) FROM persons")
    count = cursor.fetchone()[0]

    print(f"\n数据库验证:")
    print(f"  - 人员总数: {count}")

    # 按部门统计
    cursor.execute("SELECT department, COUNT(*) FROM persons GROUP BY department")
    for row in cursor.fetchall():
        print(f"  - {row[0]}: {row[1]} 人")

    conn.close()


if __name__ == "__main__":
    init_database()
    verify_database()
