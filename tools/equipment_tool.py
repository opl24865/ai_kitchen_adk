# tools/equipment_tool.py

import requests
from config import ROBOT_SERVER_URL
from database import execute_query





def check_equipment(order_id: str) -> dict:
    """
    向 Robot Simulator Server 查詢目前設備狀態，
    並找出可用的炸鍋與機械手臂。

    Args:
        order_id: 訂單 ID。

    Returns:
        dict: 設備查詢結果，包含 success、available_equipment、available_fryers、available_robot_arms、device_state、message。
    """

    try:
        response = requests.get(
            f"{ROBOT_SERVER_URL}/device/status",
            timeout=5
        )
        response.raise_for_status()
        server_result = response.json()

        device_state = server_result.get("device_state", {})

    except requests.RequestException as e:
        result = {
            "success": False,
            "available_equipment": [],
            "available_fryers": [],
            "available_robot_arms": [],
            "device_state": {},
            "message": f"無法連線到 Robot Server：{str(e)}"
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
                "failed",
                result["message"]
            )
        )

        return result

    available_fryers = [
        device_id
        for device_id, status in device_state.items()
        if device_id.startswith("fryer_") and status == "available"
    ]

    available_robot_arms = [
        device_id
        for device_id, status in device_state.items()
        if device_id.startswith("robot_arm_") and status == "available"
    ]

    available_equipment = available_fryers + available_robot_arms

    if not available_fryers:
        result = {
            "success": False,
            "available_equipment": available_equipment,
            "available_fryers": available_fryers,
            "available_robot_arms": available_robot_arms,
            "device_state": device_state,
            "message": "目前沒有可用炸鍋"
        }
    elif not available_robot_arms:
        result = {
            "success": False,
            "available_equipment": available_equipment,
            "available_fryers": available_fryers,
            "available_robot_arms": available_robot_arms,
            "device_state": device_state,
            "message": "目前沒有可用機械手臂"
        }
    else:
        result = {
            "success": True,
            "available_equipment": available_equipment,
            "available_fryers": available_fryers,
            "available_robot_arms": available_robot_arms,
            "device_state": device_state,
            "message": f"設備查詢成功：可用炸鍋 {available_fryers}，可用機械手臂 {available_robot_arms}"
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