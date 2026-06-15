# tools/batch_scheduler_tool.py

from datetime import datetime

from services.batch_scheduler import (
    parse_datetime,
    schedule_batch,
)


def schedule_batch_orders(
    orders: list[dict],
    equipment_snapshot: dict,
    base_time: str | None = None,
) -> dict:
    """
    根據訂單、SOP 與設備狀態建立批次生產排程。

    Args:
        orders:
            Resource Assessment Agent 處理後的訂單。
            每筆訂單應包含 resource_status 與 sop_check.steps。

        equipment_snapshot:
            check_equipment 回傳的設備狀態。
            必須包含 devices。

        base_time:
            排程基準時間，使用 ISO 8601 格式。
            未提供時使用目前 UTC 時間。

    Returns:
        包含 execution_order、orders 與 device_timeline
        的排程結果。
    """

    validation_error = validate_scheduler_input(
        orders=orders,
        equipment_snapshot=equipment_snapshot,
    )

    if validation_error:
        return {
            "success": False,
            "message": validation_error,
            "execution_order": [],
            "orders": orders if isinstance(orders, list) else [],
            "device_timeline": {},
        }

    parsed_base_time = parse_base_time(base_time)

    try:
        result = schedule_batch(
            orders=orders,
            equipment_snapshot=equipment_snapshot,
            base_time=parsed_base_time,
        )

    except (KeyError, TypeError, ValueError) as error:
        return {
            "success": False,
            "message": f"Batch scheduling failed: {error}",
            "execution_order": [],
            "orders": orders,
            "device_timeline": {},
        }

    result.setdefault("success", False)
    result.setdefault("execution_order", [])
    result.setdefault("orders", [])
    result.setdefault("device_timeline", {})

    if result["success"]:
        result["message"] = (
            f"Scheduled {len(result['execution_order'])} orders"
        )
    else:
        result["message"] = (
            "No orders could be scheduled"
        )

    return result


def validate_scheduler_input(
    orders: list[dict],
    equipment_snapshot: dict,
) -> str | None:
    if not isinstance(orders, list):
        return "orders must be a list"

    if not orders:
        return "orders cannot be empty"

    if not isinstance(equipment_snapshot, dict):
        return "equipment_snapshot must be an object"

    devices = equipment_snapshot.get("devices")

    if not isinstance(devices, dict):
        return (
            "equipment_snapshot.devices must be an object"
        )

    if not devices:
        return "equipment_snapshot.devices cannot be empty"

    for index, order in enumerate(orders):
        if not isinstance(order, dict):
            return f"orders[{index}] must be an object"

        if not order.get("order_id"):
            return (
                f"orders[{index}] is missing order_id"
            )

    return None


def parse_base_time(
    base_time: str | None,
) -> datetime | None:
    if not base_time:
        return None

    return parse_datetime(base_time)