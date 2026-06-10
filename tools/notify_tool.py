# tools/notify_tool.py

from database import execute_query


def send_notification(order_id: str, customer_id: str, message: str) -> dict:
    """
    模擬通知顧客訂單狀態。

    Args:
        order_id: 訂單 ID。
        customer_id: 顧客 ID。
        message: 要通知顧客的訊息。

    Returns:
        dict: 通知結果，包含 success、order_id、customer_id、message。
    """

    if not order_id or not customer_id or not message:
        result = {
            "success": False,
            "order_id": order_id,
            "customer_id": customer_id,
            "message": "通知失敗：缺少 order_id、customer_id 或 message"
        }

        execute_query(
            """
            INSERT INTO task_logs (order_id, agent_name, action, status, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                order_id or "unknown_order",
                "NotifyAgent",
                "send_notification",
                "failed",
                result["message"]
            )
        )

        return result

    result = {
        "success": True,
        "order_id": order_id,
        "customer_id": customer_id,
        "message": f"已通知顧客：{message}"
    }

    execute_query(
        """
        INSERT INTO task_logs (order_id, agent_name, action, status, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            "NotifyAgent",
            "send_notification",
            "success",
            result["message"]
        )
    )

    return result