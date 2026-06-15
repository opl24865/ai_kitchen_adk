import requests

from config import ROBOT_SERVER_URL
from database import execute_query


def execute_robot_task(order_id: str, task: dict) -> dict:
    """
    將設備任務送往 Robot Server。

    Args:
        order_id: 訂單 ID。
        task: 任務資料，包含：
            task_id
            device
            action
            duration_sec
            planned_start_time

    Returns:
        Robot Server 的排程或失敗結果。
    """

    task_id = task.get("task_id")
    device = task.get("device")
    action = task.get("action")
    planned_start_time = task.get("planned_start_time")

    try:
        duration_sec = int(task.get("duration_sec", 0))
    except (TypeError, ValueError):
        duration_sec = 0

    validation_error = validate_task(
        device=device,
        action=action,
        duration_sec=duration_sec,
    )

    if validation_error:
        result = build_failure_result(
            task_id=task_id,
            device=device,
            action=action,
            duration_sec=duration_sec,
            planned_start_time=planned_start_time,
            message=validation_error,
        )

        write_robot_log(order_id, result)
        return result

    equipment_check = get_device_status(device)

    if not equipment_check["success"]:
        result = build_failure_result(
            task_id=task_id,
            device=device,
            action=action,
            duration_sec=duration_sec,
            planned_start_time=planned_start_time,
            message=equipment_check["message"],
        )

        write_robot_log(order_id, result)
        return result

    device_detail = equipment_check["device_detail"]

    if device_detail.get("status") == "maintenance":
        result = build_failure_result(
            task_id=task_id,
            device=device,
            action=action,
            duration_sec=duration_sec,
            planned_start_time=planned_start_time,
            message=f"{device} is under maintenance",
        )

        write_robot_log(order_id, result)
        return result

    request_payload = {
        "order_id": order_id,
        "task_id": task_id,
        "device": device,
        "action": action,
        "duration_sec": duration_sec,
        "planned_start_time": planned_start_time,
    }

    try:
        response = requests.post(
            f"{ROBOT_SERVER_URL}/device/execute",
            json=request_payload,
            timeout=5,
        )

        response.raise_for_status()
        server_result = response.json()

        result = {
            "success": bool(
                server_result.get("success", False)
            ),
            "order_id": order_id,
            "task_id": task_id,
            "device": device,
            "action": action,
            "duration_sec": duration_sec,
            "execution_status": server_result.get(
                "execution_status",
                (
                    "scheduled"
                    if server_result.get("success")
                    else "rejected"
                ),
            ),
            "planned_start_time": planned_start_time,
            "actual_start_time": server_result.get(
                "actual_start_time"
            ),
            "expected_end_time": server_result.get(
                "expected_end_time"
            ),
            "message": server_result.get(
                "message",
                "",
            ),
            "robot_server_time": server_result.get(
                "server_time"
            ),
            "device_status_before_execution": (
                device_detail.get("status")
            ),
            "device_next_available_at_before_execution": (
                device_detail.get("next_available_at")
            ),
        }

    except requests.Timeout:
        result = build_failure_result(
            task_id=task_id,
            device=device,
            action=action,
            duration_sec=duration_sec,
            planned_start_time=planned_start_time,
            message="Robot Server request timed out",
        )

    except requests.RequestException as error:
        result = build_failure_result(
            task_id=task_id,
            device=device,
            action=action,
            duration_sec=duration_sec,
            planned_start_time=planned_start_time,
            message=f"Robot Server request failed: {error}",
        )

    except ValueError as error:
        result = build_failure_result(
            task_id=task_id,
            device=device,
            action=action,
            duration_sec=duration_sec,
            planned_start_time=planned_start_time,
            message=(
                "Robot Server returned invalid JSON: "
                f"{error}"
            ),
        )

    write_robot_log(order_id, result)
    return result


def validate_task(
    device: str | None,
    action: str | None,
    duration_sec: int,
) -> str | None:
    if not device:
        return "Task is missing device"

    if not action:
        return "Task is missing action"

    if duration_sec < 0:
        return "duration_sec cannot be negative"

    return None


def get_device_status(device_id: str) -> dict:
    """
    執行任務前取得指定設備的最新狀態。

    忙碌設備不會被拒絕，Robot Server 會將新任務排在
    該設備既有預約之後。
    """

    try:
        response = requests.get(
            f"{ROBOT_SERVER_URL}/device/status",
            timeout=5,
        )

        response.raise_for_status()
        server_result = response.json()

    except requests.Timeout:
        return {
            "success": False,
            "device_detail": {},
            "message": (
                "Robot Server status request timed out"
            ),
        }

    except requests.RequestException as error:
        return {
            "success": False,
            "device_detail": {},
            "message": (
                "Unable to query Robot Server status: "
                f"{error}"
            ),
        }

    except ValueError as error:
        return {
            "success": False,
            "device_detail": {},
            "message": (
                "Robot Server status returned invalid JSON: "
                f"{error}"
            ),
        }

    devices = server_result.get("devices", {})

    if device_id in devices:
        return {
            "success": True,
            "device_detail": devices[device_id],
            "message": "Device status retrieved",
        }

    # 相容舊版 Robot Server。
    device_state = server_result.get("device_state", {})

    if device_id in device_state:
        return {
            "success": True,
            "device_detail": {
                "device_id": device_id,
                "device_type": detect_device_type(
                    device_id
                ),
                "status": device_state[device_id],
                "current_order_id": None,
                "current_task_id": None,
                "current_action": None,
                "busy_until": None,
                "remaining_sec": 0,
                "next_available_at": None,
                "reservation_count": 0,
            },
            "message": "Device status retrieved",
        }

    return {
        "success": False,
        "device_detail": {},
        "message": f"Unknown device: {device_id}",
    }


def detect_device_type(device_id: str) -> str:
    if device_id.startswith("fryer_"):
        return "fryer"

    if device_id.startswith("robot_arm_"):
        return "robot_arm"

    return "unknown"


def build_failure_result(
    task_id: str | None,
    device: str | None,
    action: str | None,
    duration_sec: int,
    planned_start_time: str | None,
    message: str,
) -> dict:
    return {
        "success": False,
        "task_id": task_id,
        "device": device,
        "action": action,
        "duration_sec": duration_sec,
        "execution_status": "failed",
        "planned_start_time": planned_start_time,
        "actual_start_time": None,
        "expected_end_time": None,
        "message": message,
        "robot_server_time": None,
    }


def write_robot_log(
    order_id: str,
    result: dict,
) -> None:
    status = (
        "success"
        if result.get("success") is True
        else "failed"
    )

    action = result.get("action") or "unknown_action"
    message = result.get("message") or ""

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
            "BatchExecutionAgent",
            action,
            status,
            message,
        ),
    )