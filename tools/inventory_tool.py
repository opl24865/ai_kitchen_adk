# tools/inventory_tool.py

from database import fetch_one, execute_query


def check_inventory(order_id: str, item_name: str, quantity: int = 1) -> dict:
    """
    查詢指定品項的庫存是否足夠。

    Args:
        order_id: 訂單 ID。
        item_name: 品項名稱，例如「雞排」或「薯條」。
        quantity: 需要的數量。

    Returns:
        dict: 庫存查詢結果，包含 success、item_name、required_qty、stock_qty、message。
    """

    item = fetch_one(
        "SELECT * FROM inventory WHERE item_name = ?",
        (item_name,)
    )

    if item is None:
        result = {
            "success": False,
            "item_name": item_name,
            "required_qty": quantity,
            "stock_qty": 0,
            "message": f"找不到品項：{item_name}"
        }
    elif item["stock_qty"] < quantity:
        result = {
            "success": False,
            "item_name": item_name,
            "required_qty": quantity,
            "stock_qty": item["stock_qty"],
            "message": f"{item_name}庫存不足"
        }
    else:
        result = {
            "success": True,
            "item_name": item_name,
            "required_qty": quantity,
            "stock_qty": item["stock_qty"],
            "message": f"{item_name}庫存足夠"
        }

    execute_query(
        """
        INSERT INTO task_logs (order_id, agent_name, action, status, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            "DataQueryAgent",
            "check_inventory",
            "success" if result["success"] else "failed",
            result["message"]
        )
    )

    return result