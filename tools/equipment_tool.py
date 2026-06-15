import requests

from config import ROBOT_SERVER_URL
from database import execute_query


def check_equipment(order_id: str) -> dict:
    """
    查詢 Robot Server 的設備狀態。

    available_* 表示現在立即可用的設備。
    schedulable_* 表示可以納入排程的設備，包含 available 與 busy，
    但不包含 maintenance 設備。
    """

    try:
        response = requests.get(
            f"{ROBOT_SERVER_URL}/device/status",
            timeout=5,
        )
        response.raise_for_status()
        server_result = response.json()

    except (requests.RequestException, ValueError) as error:
        result = {
            "success": False,
            "equipment_status": "server_unavailable",
            "available_equipment": [],
            "available_fryers": [],
            "available_robot_arms": [],
            "schedulable_equipment": [],
            "schedulable_fryers": [],
            "schedulable_robot_arms": [],
            "maintenance_equipment": [],
            "device_state": {},
            "devices": {},
            "server_time": None,
            "message": f"Robot Server connection failed: {error}",
        }

        write_equipment_log(order_id, result)
        return result

    device_state = server_result.get("device_state", {})
    devices = normalize_devices(
        devices=server_result.get("devices", {}),
        device_state=device_state,
    )

    available_fryers = get_devices_by_type_and_status(
        devices=devices,
        device_type="fryer",
        statuses={"available"},
    )

    available_robot_arms = get_devices_by_type_and_status(
        devices=devices,
        device_type="robot_arm",
        statuses={"available"},
    )

    schedulable_fryers = get_devices_by_type_and_status(
        devices=devices,
        device_type="fryer",
        statuses={"available", "busy"},
    )

    schedulable_robot_arms = get_devices_by_type_and_status(
        devices=devices,
        device_type="robot_arm",
        statuses={"available", "busy"},
    )

    maintenance_equipment = sorted(
        device_id
        for device_id, detail in devices.items()
        if detail.get("status") == "maintenance"
    )

    available_equipment = (
        available_fryers + available_robot_arms
    )

    schedulable_equipment = (
        schedulable_fryers + schedulable_robot_arms
    )

    success = bool(
        schedulable_fryers
        and schedulable_robot_arms
    )

    equipment_status = determine_equipment_status(
        success=success,
        available_fryers=available_fryers,
        available_robot_arms=available_robot_arms,
        schedulable_fryers=schedulable_fryers,
        schedulable_robot_arms=schedulable_robot_arms,
    )

    result = {
        "success": success,
        "equipment_status": equipment_status,
        "available_equipment": available_equipment,
        "available_fryers": available_fryers,
        "available_robot_arms": available_robot_arms,
        "schedulable_equipment": schedulable_equipment,
        "schedulable_fryers": schedulable_fryers,
        "schedulable_robot_arms": schedulable_robot_arms,
        "maintenance_equipment": maintenance_equipment,
        "device_state": {
            device_id: detail.get("status", "unknown")
            for device_id, detail in devices.items()
        },
        "devices": devices,
        "server_time": server_result.get("server_time"),
        "message": build_equipment_message(
            equipment_status=equipment_status,
            available_fryers=available_fryers,
            available_robot_arms=available_robot_arms,
            schedulable_fryers=schedulable_fryers,
            schedulable_robot_arms=schedulable_robot_arms,
        ),
    }

    write_equipment_log(order_id, result)
    return result


def normalize_devices(
    devices: dict,
    device_state: dict,
) -> dict:
    """
    統一新舊 Robot Server 的設備資料格式。

    新版本使用 devices 詳細資料。
    舊版本只有 device_state，仍可轉換成基本格式。
    """

    normalized = {}

    if devices:
        for device_id, detail in devices.items():
            status = detail.get(
                "status",
                device_state.get(device_id, "unknown"),
            )

            normalized[device_id] = {
                "device_id": device_id,
                "device_type": detail.get(
                    "device_type",
                    detect_device_type(device_id),
                ),
                "status": status,
                "current_order_id": detail.get(
                    "current_order_id"
                ),
                "current_task_id": detail.get(
                    "current_task_id"
                ),
                "current_action": detail.get(
                    "current_action"
                ),
                "busy_until": detail.get("busy_until"),
                "remaining_sec": int(
                    detail.get("remaining_sec") or 0
                ),
                "next_available_at": detail.get(
                    "next_available_at"
                ),
                "reservation_count": int(
                    detail.get("reservation_count") or 0
                ),
            }

        return normalized

    for device_id, status in device_state.items():
        normalized[device_id] = {
            "device_id": device_id,
            "device_type": detect_device_type(device_id),
            "status": status,
            "current_order_id": None,
            "current_task_id": None,
            "current_action": None,
            "busy_until": None,
            "remaining_sec": 0,
            "next_available_at": None,
            "reservation_count": 0,
        }

    return normalized


def detect_device_type(device_id: str) -> str:
    if device_id.startswith("fryer_"):
        return "fryer"

    if device_id.startswith("robot_arm_"):
        return "robot_arm"

    return "unknown"


def get_devices_by_type_and_status(
    devices: dict,
    device_type: str,
    statuses: set[str],
) -> list[str]:
    return sorted(
        device_id
        for device_id, detail in devices.items()
        if detail.get("device_type") == device_type
        and detail.get("status") in statuses
    )


def determine_equipment_status(
    success: bool,
    available_fryers: list[str],
    available_robot_arms: list[str],
    schedulable_fryers: list[str],
    schedulable_robot_arms: list[str],
) -> str:
    if not success:
        return "equipment_blocked"

    if available_fryers and available_robot_arms:
        all_fryers_available = (
            len(available_fryers)
            == len(schedulable_fryers)
        )

        all_arms_available = (
            len(available_robot_arms)
            == len(schedulable_robot_arms)
        )

        if all_fryers_available and all_arms_available:
            return "all_available"

        return "partially_busy"

    return "all_busy"


def build_equipment_message(
    equipment_status: str,
    available_fryers: list[str],
    available_robot_arms: list[str],
    schedulable_fryers: list[str],
    schedulable_robot_arms: list[str],
) -> str:
    if equipment_status == "equipment_blocked":
        if not schedulable_fryers:
            return "No schedulable fryer is available"

        return "No schedulable robot arm is available"

    if equipment_status == "all_available":
        return (
            "All required equipment is currently available. "
            f"Fryers={available_fryers}, "
            f"robot_arms={available_robot_arms}"
        )

    if equipment_status == "partially_busy":
        return (
            "Some equipment is busy but can be scheduled. "
            f"Available fryers={available_fryers}, "
            f"available robot arms={available_robot_arms}"
        )

    return (
        "All required equipment is currently busy, "
        "but future scheduling is possible. "
        f"Schedulable fryers={schedulable_fryers}, "
        f"schedulable robot arms={schedulable_robot_arms}"
    )


def write_equipment_log(
    order_id: str,
    result: dict,
) -> None:
    execute_query(
        """
        INSERT INTO task_logs (
            order_id,
            agent_name,
            action,
            status,
            message
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            "DataQueryAgent",
            "check_equipment",
            "success" if result["success"] else "failed",
            result["message"],
        ),
    )