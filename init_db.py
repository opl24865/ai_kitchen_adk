# init_db.py

from database import execute_query


def init_database():
    # orders：訂單資料
    execute_query("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        customer_id TEXT,
        item_name TEXT,
        preference TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # inventory：庫存資料
    execute_query("""
    CREATE TABLE IF NOT EXISTS inventory (
        item_name TEXT PRIMARY KEY,
        stock_qty INTEGER,
        unit TEXT
    )
    """)

    # equipment：設備狀態
    execute_query("""
    CREATE TABLE IF NOT EXISTS equipment (
        equipment_id TEXT PRIMARY KEY,
        equipment_name TEXT,
        status TEXT
    )
    """)

    # task_logs：Agent / Tool 執行紀錄
    execute_query("""
    CREATE TABLE IF NOT EXISTS task_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        agent_name TEXT,
        action TEXT,
        status TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 清空測試資料，避免重複初始化時資料混亂
    execute_query("DELETE FROM inventory")
    execute_query("DELETE FROM equipment")
    execute_query("DELETE FROM task_logs")
    execute_query("DELETE FROM orders")

    # 初始化庫存
    execute_query(
        "INSERT INTO inventory (item_name, stock_qty, unit) VALUES (?, ?, ?)",
        ("雞排", 10, "份")
    )

    execute_query(
        "INSERT INTO inventory (item_name, stock_qty, unit) VALUES (?, ?, ?)",
        ("薯條", 20, "份")
    )

    # 初始化設備
    execute_query(
        "INSERT INTO equipment (equipment_id, equipment_name, status) VALUES (?, ?, ?)",
        ("fryer_A", "炸鍋 A", "available")
    )

    execute_query(
        "INSERT INTO equipment (equipment_id, equipment_name, status) VALUES (?, ?, ?)",
        ("robot_arm_1", "機械手臂 1", "available")
    )

    print("SQLite database initialized successfully.")


if __name__ == "__main__":
    init_database()