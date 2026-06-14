# tools/alert_tool.py

from database import execute_query


def send_internal_alert(
    order_id: str,
    alert_type: str,
    target_role: str,
    message: str
) -> dict:
    """
    模擬通知內部人員處理異常狀況。

    Args:
        order_id: 訂單 ID。
        alert_type: 異常類型，例如 inventory_shortage、equipment_unavailable、robot_server_offline、execution_failed。
        target_role: 通知對象，例如 kitchen_staff、maintenance_staff、operation_staff、tech_staff。
        message: 要通知內部人員的訊息。

    Returns:
        dict: 內部通知結果。
    """

    if not order_id or not alert_type or not target_role or not message:
        result = {
            "success": False,
            "order_id": order_id,
            "alert_type": alert_type,
            "target_role": target_role,
            "message": "內部通知失敗：缺少 order_id、alert_type、target_role 或 message"
        }

        _write_alert_logs(order_id or "unknown_order", result)
        return result

    result = {
        "success": True,
        "order_id": order_id,
        "alert_type": alert_type,
        "target_role": target_role,
        "message": f"[Internal Alert] 已通知 {target_role}：{message}"
    }

    _write_alert_logs(order_id, result)
    return result


def _write_alert_logs(order_id: str, result: dict):
    """
    同時寫入 alert_logs 與 task_logs。
    alert_logs 用於異常通知紀錄。
    task_logs 用於 Dashboard 的 workflow 執行紀錄。
    """

    execute_query(
        """
        INSERT INTO alert_logs (order_id, alert_type, target_role, status, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            result.get("alert_type", "unknown"),
            result.get("target_role", "unknown"),
            "success" if result.get("success") else "failed",
            result.get("message", "")
        )
    )

    execute_query(
        """
        INSERT INTO task_logs (order_id, agent_name, action, status, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            "NotifyAgent",
            "send_internal_alert",
            "success" if result.get("success") else "failed",
            result.get("message", "")
        )
    )