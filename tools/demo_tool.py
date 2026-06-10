# tools/demo_tool.py

from database import execute_query, fetch_all


def reset_demo_data() -> dict:
    """
    重置 demo 資料，恢復庫存與設備狀態。
    """

    execute_query("DELETE FROM inventory")
    execute_query("DELETE FROM equipment")
    execute_query("DELETE FROM task_logs")
    execute_query("DELETE FROM orders")

    execute_query(
        "INSERT INTO inventory (item_name, stock_qty, unit) VALUES (?, ?, ?)",
        ("雞排", 10, "份")
    )

    execute_query(
        "INSERT INTO inventory (item_name, stock_qty, unit) VALUES (?, ?, ?)",
        ("薯條", 20, "份")
    )

    execute_query(
        "INSERT INTO equipment (equipment_id, equipment_name, status) VALUES (?, ?, ?)",
        ("fryer_A", "炸鍋 A", "available")
    )

    execute_query(
        "INSERT INTO equipment (equipment_id, equipment_name, status) VALUES (?, ?, ?)",
        ("robot_arm_1", "機械手臂 1", "available")
    )

    return {
        "success": True,
        "message": "Demo 資料已重置：庫存充足，設備可用"
    }


def set_inventory_low(item_name: str = "雞排", stock_qty: int = 0) -> dict:
    """
    將指定品項庫存調低，用來模擬庫存不足。
    """

    execute_query(
        "UPDATE inventory SET stock_qty = ? WHERE item_name = ?",
        (stock_qty, item_name)
    )

    return {
        "success": True,
        "item_name": item_name,
        "stock_qty": stock_qty,
        "message": f"{item_name} 庫存已調整為 {stock_qty}"
    }


def set_equipment_status(equipment_id: str, status: str) -> dict:
    """
    修改設備狀態，用來模擬設備可用或維修中。
    """

    execute_query(
        "UPDATE equipment SET status = ? WHERE equipment_id = ?",
        (status, equipment_id)
    )

    return {
        "success": True,
        "equipment_id": equipment_id,
        "status": status,
        "message": f"{equipment_id} 狀態已改為 {status}"
    }


def get_demo_status() -> dict:
    """
    查詢目前 demo 狀態，包含庫存、設備與最近 task logs。
    """

    inventory = fetch_all(
        "SELECT * FROM inventory ORDER BY item_name ASC"
    )

    equipment = fetch_all(
        "SELECT * FROM equipment ORDER BY equipment_id ASC"
    )

    recent_logs = fetch_all(
        """
        SELECT * FROM task_logs
        ORDER BY created_at DESC
        LIMIT 20
        """
    )

    return {
        "success": True,
        "inventory": inventory,
        "equipment": equipment,
        "recent_logs": recent_logs
    }

@app.post("/demo/reset")
def demo_reset():
    """
    重置 demo 資料。
    """
    return reset_demo_data()


@app.post("/demo/set-inventory-low")
def demo_set_inventory_low():
    """
    模擬庫存不足。
    預設將雞排庫存改為 0。
    """
    return set_inventory_low(item_name="雞排", stock_qty=0)


@app.post("/demo/set-inventory-normal")
def demo_set_inventory_normal():
    """
    恢復雞排庫存。
    """
    return set_inventory_low(item_name="雞排", stock_qty=10)


@app.post("/demo/set-equipment-down")
def demo_set_equipment_down():
    """
    模擬炸鍋維修中。
    """
    return set_equipment_status(
        equipment_id="fryer_A",
        status="maintenance"
    )


@app.post("/demo/set-equipment-available")
def demo_set_equipment_available():
    """
    恢復炸鍋可用。
    """
    return set_equipment_status(
        equipment_id="fryer_A",
        status="available"
    )


@app.get("/demo/status")
def demo_status():
    """
    查詢目前 demo 狀態。
    """
    return get_demo_status()