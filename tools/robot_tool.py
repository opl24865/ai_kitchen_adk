# tools/robot_tool.py
import requests
from database import execute_query
from config import ROBOT_SERVER_URL


def execute_robot_task(order_id: str, task: dict) -> dict:
    """
    模擬呼叫機械手臂或設備 API 執行單一任務。

    Args:
        order_id: 訂單 ID。
        task: 任務資料，必須包含 device、action、duration_sec。

    Returns:
        dict: 任務執行結果，包含 success、device、action、duration_sec、message。
    """

    device = task.get("device")
    action = task.get("action")
    duration_sec = task.get("duration_sec", 0)
    task_id = task.get("task_id")

    if not device or not action:
        result = {
            "success": False,
            "task_id": task_id,
            "device": device,
            "action": action,
            "duration_sec": duration_sec,
            "message": "任務缺少 device 或 action，無法呼叫 Robot Server"
        }

        execute_query(
            """
            INSERT INTO task_logs (order_id, agent_name, action, status, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                order_id,
                "ExecutorAgent",
                action or "unknown_action",
                "failed",
                result["message"]
            )
        )

        return result

    try:
        response = requests.post(
            f"{ROBOT_SERVER_URL}/device/execute",
            json={
                "order_id": order_id,
                "task_id": task_id,
                "device": device,
                "action": action,
                "duration_sec": duration_sec,
            },
            timeout=5,
        )

        response.raise_for_status()
        server_result = response.json()

        result = {
            "success": server_result.get("success", False),
            "task_id": task_id,
            "device": device,
            "action": action,
            "duration_sec": duration_sec,
            "message": server_result.get("message", ""),
            "robot_server_time": server_result.get("server_time"),
        }

    except requests.RequestException as e:
        result = {
            "success": False,
            "task_id": task_id,
            "device": device,
            "action": action,
            "duration_sec": duration_sec,
            "message": f"Robot Server 呼叫失敗：{str(e)}",
        }


    execute_query(
        """
        INSERT INTO task_logs (order_id, agent_name, action, status, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            "ExecutorAgent",
            action,
            "success",
            result["message"]
        )
    )

    return result