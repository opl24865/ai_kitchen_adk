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

    # equipment：設備基本資料
    # 注意：目前即時設備狀態主要由 Robot Server 管理，
    # 這張表保留作為設備基本資料或 fallback。
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

    # alert_logs：內部異常通知紀錄
    execute_query("""
    CREATE TABLE IF NOT EXISTS alert_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        alert_type TEXT,
        target_role TEXT,
        status TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 清空測試資料，避免重複初始化時資料混亂
    execute_query("DELETE FROM inventory")
    execute_query("DELETE FROM equipment")
    execute_query("DELETE FROM task_logs")
    execute_query("DELETE FROM alert_logs")
    execute_query("DELETE FROM orders")

    # 初始化庫存
    inventory_items = [
        ("雞排", 10, "份"),
        ("薯條", 20, "份"),
        ("雞塊", 15, "份"),
        ("甜不辣", 12, "份"),
        ("花枝丸", 12, "份"),
    ]

    for item_name, stock_qty, unit in inventory_items:
        execute_query(
            "INSERT INTO inventory (item_name, stock_qty, unit) VALUES (?, ?, ?)",
            (item_name, stock_qty, unit)
        )

    # 初始化設備基本資料
    equipment_items = [
        ("fryer_A", "炸鍋 A", "available"),
        ("fryer_B", "炸鍋 B", "available"),
        ("fryer_C", "炸鍋 C", "available"),
        ("robot_arm_1", "機械手臂 1", "available"),
        ("robot_arm_2", "機械手臂 2", "available"),
    ]

    for equipment_id, equipment_name, status in equipment_items:
        execute_query(
            "INSERT INTO equipment (equipment_id, equipment_name, status) VALUES (?, ?, ?)",
            (equipment_id, equipment_name, status)
        )

    print("SQLite database initialized successfully.")


if __name__ == "__main__":
    init_database()