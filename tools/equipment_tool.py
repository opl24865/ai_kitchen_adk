# tools/equipment_tool.py

from database import fetch_one, execute_query


def check_equipment(order_id: str) -> dict:
    """
    查詢製作炸物所需設備是否可用。

    Args:
        order_id: 訂單 ID。

    Returns:
        dict: 設備查詢結果，包含 success、available_equipment、message。
    """

    fryer = fetch_one(
        "SELECT * FROM equipment WHERE equipment_id = ?",
        ("fryer_A",)
    )

    robot_arm = fetch_one(
        "SELECT * FROM equipment WHERE equipment_id = ?",
        ("robot_arm_1",)
    )

    if fryer is None or robot_arm is None:
        result = {
            "success": False,
            "available_equipment": [],
            "message": "找不到必要設備"
        }
    elif fryer["status"] != "available":
        result = {
            "success": False,
            "available_equipment": [],
            "message": "炸鍋目前不可用"
        }
    elif robot_arm["status"] != "available":
        result = {
            "success": False,
            "available_equipment": [],
            "message": "機械手臂目前不可用"
        }
    else:
        result = {
            "success": True,
            "available_equipment": ["fryer_A", "robot_arm_1"],
            "message": "設備狀態正常"
        }

    execute_query(
        """
        INSERT INTO task_logs (order_id, agent_name, action, status, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            "DataQueryAgent",
            "check_equipment",
            "success" if result["success"] else "failed",
            result["message"]
        )
    )

    return result