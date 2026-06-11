# robot_server.py

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from typing import Literal


app = FastAPI(title="Robot Arm Simulator Server")


class DeviceTaskRequest(BaseModel):
    order_id: str
    task_id: str | None = None
    device: str
    action: str
    duration_sec: int = 0


# class DeviceState:
#     fryer_A: Literal["available", "busy", "maintenance"] = "available"
#     fryer_B: Literal["available", "busy", "maintenance"] = "available"
#     fryer_C: Literal["available", "busy", "maintenance"] = "available"
#     robot_arm_1: Literal["available", "busy", "maintenance"] = "available"
#     robot_arm_2: Literal["available", "busy", "maintenance"] = "available"


device_state = {
    "fryer_A": "maintenance",
    "fryer_B": "busy",
    "fryer_C": "available",
    "robot_arm_1": "available",
    "robot_arm_2": "busy"
}


execution_history = []


@app.get("/")
def health_check():
    return {
        "success": True,
        "message": "Robot simulator server is running",
        "device_state": device_state,
    }


@app.get("/device/status")
def get_device_status():
    return {
        "success": True,
        "device_state": device_state,
        "history_count": len(execution_history),
    }


@app.post("/device/execute")
def execute_device_task(task: DeviceTaskRequest):
    if task.device not in device_state:
        result = {
            "success": False,
            "order_id": task.order_id,
            "task_id": task.task_id,
            "device": task.device,
            "action": task.action,
            "duration_sec": task.duration_sec,
            "message": f"未知設備：{task.device}",
            "server_time": datetime.now().isoformat(timespec="seconds"),
        }

        execution_history.append(result)
        return result

    if device_state[task.device] == "maintenance":
        result = {
            "success": False,
            "order_id": task.order_id,
            "task_id": task.task_id,
            "device": task.device,
            "action": task.action,
            "duration_sec": task.duration_sec,
            "message": f"{task.device} 目前維修中，無法執行 {task.action}",
            "server_time": datetime.now().isoformat(timespec="seconds"),
        }

        execution_history.append(result)
        return result

    # 模擬設備執行：這裡不真的 sleep，避免 demo 太慢
    result = {
        "success": True,
        "order_id": task.order_id,
        "task_id": task.task_id,
        "device": task.device,
        "action": task.action,
        "duration_sec": task.duration_sec,
        "message": f"[Robot Server] {task.device} 已完成 {task.action}",
        "server_time": datetime.now().isoformat(timespec="seconds"),
    }

    execution_history.append(result)
    return result


@app.post("/device/set-maintenance/{device_id}")
def set_device_maintenance(device_id: str):
    if device_id not in device_state:
        return {
            "success": False,
            "message": f"未知設備：{device_id}",
        }

    device_state[device_id] = "maintenance"

    return {
        "success": True,
        "message": f"{device_id} 已切換為 maintenance",
        "device_state": device_state,
    }


@app.post("/device/set-available/{device_id}")
def set_device_available(device_id: str):
    if device_id not in device_state:
        return {
            "success": False,
            "message": f"未知設備：{device_id}",
        }

    device_state[device_id] = "available"

    return {
        "success": True,
        "message": f"{device_id} 已切換為 available",
        "device_state": device_state,
    }


@app.post("/device/reset")
def reset_device_state():
    device_state["fryer_A"] = "available"
    device_state["fryer_B"] = "available"
    device_state["fryer_C"] = "available"
    device_state["robot_arm_1"] = "available"
    device_state["robot_arm_2"] = "available"
    execution_history.clear()

    return {
        "success": True,
        "message": "Robot simulator 已恢復正常狀態",
        "device_state": device_state,
    }


@app.get("/device/history")
def get_execution_history():
    return {
        "success": True,
        "history": execution_history,
    }