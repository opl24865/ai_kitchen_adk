# robot_server.py


from fastapi import FastAPI
from pydantic import BaseModel
from threading import RLock
from datetime import datetime, timedelta, timezone

app = FastAPI(title="Robot Arm Simulator Server")

state_lock = RLock()

class DeviceTaskRequest(BaseModel):
    order_id: str
    task_id: str | None = None
    device: str
    action: str
    duration_sec: int = 0
    planned_start_time: str | None = None


device_registry = {
    "fryer_A": {
        "device_type": "fryer",
        "manual_status": "available",
        "reservations": [],
    },
    "fryer_B": {
        "device_type": "fryer",
        "manual_status": "available",
        "reservations": [],
    },
    "fryer_C": {
        "device_type": "fryer",
        "manual_status": "available",
        "reservations": [],
    },
    "robot_arm_1": {
        "device_type": "robot_arm",
        "manual_status": "available",
        "reservations": [],
    },
    "robot_arm_2": {
        "device_type": "robot_arm",
        "manual_status": "available",
        "reservations": [],
    },
}


execution_history: list[dict] = []


def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        
        return parsed.astimezone(timezone.utc)
    
    except ValueError:
        return None

def to_iso(value: datetime | None):
    if value is None:
        return None
    
    return value.isoformat(timespec="seconds")

def remove_expired_reservations(device: dict, current_time: datetime) -> None:
    device["reservation"] = [
        reservation
        for reservation in device["reservations"]
        if reservation["end_time"] > current_time
    ]

def get_device_snapshot(device_id: str, current_time: datetime) -> dict:
    device = device_registry[device_id]

    remove_expired_reservations(device, current_time)

    reservations = sorted(
        device["reservations"],
        key=lambda item: item["start_time"]
    )

    if device["manual_status"] == "maintenance":
        return {
            "device_id": device_id,
            "device_type": device["device_type"],
            "status": "maintenance",
            "current_order_id": None,
            "current_task_id": None,
            "current_action": None,
            "busy_until": None,
            "remaining_sec": 0,
            "next_available_at": None,
            "reservation_count": len(reservations)
        }
    
    active_reservation = next(
        (
            reservation
            for reservation in reservations
            if reservation["start_time"]
            <= current_time
            < reservation["end_time"]
        ),
        None,
    )

    latest_end_time = max(
        (
            reservation["end_time"]
            for reservation in reservations
        ),
        default=current_time,
    )

    if active_reservation:
        remaining_sec = max(
            0,
            int(
                (
                    active_reservation["end_time"] - current_time
                ).total_seconds()
            ),
        )

        status = "busy"
        current_order_id = active_reservation["order_id"]
        current_task_id = active_reservation["task_id"]
        current_action = active_reservation["action"]
        busy_until = active_reservation["end_time"]

    else:
        status = "available"
        remaining_sec = 0
        current_order_id = None
        current_task_id = None
        current_action = None
        busy_until = None

    return {
        "device_id": device_id,
        "device_type": device["device_type"],
        "status": status,
        "current_order_id": current_order_id,
        "current_task_id": current_task_id,
        "current_action": current_action,
        "busy_until": to_iso(busy_until),
        "remaining_sec": remaining_sec,
        "next_available_at": to_iso(latest_end_time),
        "reservation_count": len(reservations),
    }

def get_all_device_snapshots() -> dict[str, dict]:
    current_time = now_utc()

    return {
        device_id: get_device_snapshot(device_id, current_time)
        for device_id in device_registry
    }


@app.get("/")
def health_check():
    with state_lock:
        devices = get_all_device_snapshots()

    return {
        "success": True,
        "message": "Robot simulator server is running",
        "device_state": {
            device_id: detail["status"]
            for device_id, detail in devices.items()
        },
        "devices": devices,
    }


@app.get("/device/status")
def get_device_status():
    with state_lock:
        devices = get_all_device_snapshots()

    available_fryers = [
        device_id
        for device_id, detail in devices.items()
        if detail["device_type"] == "fryer"
        and detail["status"] == "available"
    ]

    available_robot_arms = [
        device_id
        for device_id, detail in devices.items()
        if detail["device_type"] == "robot_arm"
        and detail["status"] == "available"
    ]

    return {
        "success": True,
        "server_time": to_iso(now_utc()),
        "device_state": {
            device_id: detail["status"]
            for device_id, detail in devices.items()
        },
        "devices": devices,
        "available_fryers": available_fryers,
        "available_robot_arms": available_robot_arms,
        "history_count": len(execution_history),
    }


@app.post("/device/execute")
def execute_device_task(task: DeviceTaskRequest):
    current_time = now_utc()

    with state_lock:
        if task.device not in device_registry:
            result = {
                "success": False,
                "order_id": task.order_id,
                "task_id": task.task_id,
                "device": task.device,
                "action": task.action,
                "duration_sec": task.duration_sec,
                "execution_status": "rejected",
                "message": f"Unknown device: {task.device}",
                "server_time": to_iso(current_time),
            }

            execution_history.append(result)
            return result

        device = device_registry[task.device]

        if device["manual_status"] == "maintenance":
            result = {
                "success": False,
                "order_id": task.order_id,
                "task_id": task.task_id,
                "device": task.device,
                "action": task.action,
                "duration_sec": task.duration_sec,
                "execution_status": "rejected",
                "message": f"{task.device} is under maintenance",
                "server_time": to_iso(current_time),
            }

            execution_history.append(result)
            return result

        remove_expired_reservations(device, current_time)

        requested_start = parse_datetime(task.planned_start_time)
        requested_start = requested_start or current_time

        latest_reserved_end = max(
            (
                reservation["end_time"]
                for reservation in device["reservations"]
            ),
            default=current_time,
        )

        actual_start = max(
            current_time,
            requested_start,
            latest_reserved_end,
        )

        duration_sec = max(0, task.duration_sec)
        actual_end = actual_start + timedelta(seconds=duration_sec)

        reservation = {
            "order_id": task.order_id,
            "task_id": task.task_id,
            "action": task.action,
            "duration_sec": duration_sec,
            "start_time": actual_start,
            "end_time": actual_end,
        }

        device["reservations"].append(reservation)

        result = {
            "success": True,
            "order_id": task.order_id,
            "task_id": task.task_id,
            "device": task.device,
            "action": task.action,
            "duration_sec": duration_sec,
            "execution_status": "scheduled",
            "planned_start_time": task.planned_start_time,
            "actual_start_time": to_iso(actual_start),
            "expected_end_time": to_iso(actual_end),
            "message": (
                f"[Robot Server] {task.device} accepted "
                f"{task.action}"
            ),
            "server_time": to_iso(current_time),
        }

        execution_history.append(result)

    return result


@app.post("/device/set-maintenance/{device_id}")
def set_device_maintenance(device_id: str):
    with state_lock:
        if device_id not in device_registry:
            return {
                "success": False,
                "message": f"Unknown device: {device_id}",
            }

        device_registry[device_id]["manual_status"] = "maintenance"
        device_registry[device_id]["reservations"].clear()

    return {
        "success": True,
        "message": f"{device_id} has been set to maintenance",
        "device_state": get_device_status()["device_state"],
    }


@app.post("/device/set-available/{device_id}")
def set_device_available(device_id: str):
    with state_lock:
        if device_id not in device_registry:
            return {
                "success": False,
                "message": f"Unknown device: {device_id}",
            }

        device_registry[device_id]["manual_status"] = "available"
        device_registry[device_id]["reservations"].clear()

    return {
        "success": True,
        "message": f"{device_id} has been set to available",
        "device_state": get_device_status()["device_state"],
    }


@app.post("/device/reset")
def reset_device_state():
    with state_lock:
        for device in device_registry.values():
            device["manual_status"] = "available"
            device["reservations"].clear()

        execution_history.clear()

    return {
        "success": True,
        "message": "Robot simulator has been reset",
        "device_state": get_device_status()["device_state"],
    }


@app.get("/device/history")
def get_execution_history():
    return {
        "success": True,
        "history": execution_history,
    }