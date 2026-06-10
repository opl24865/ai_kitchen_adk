# tools/robot_tool.py

from database import execute_query


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

    if not device or not action:
        result = {
            "success": False,
            "device": device,
            "action": action,
            "duration_sec": duration_sec,
            "message": "任務缺少 device 或 action，無法執行"
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

    # 這裡目前只是模擬呼叫外部設備 API 成功
    result = {
        "success": True,
        "device": device,
        "action": action,
        "duration_sec": duration_sec,
        "message": f"{device} 已完成 {action}，耗時 {duration_sec} 秒"
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