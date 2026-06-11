import requests

from uuid import uuid4

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database import execute_query, fetch_all
from config import ROBOT_SERVER_URL

from agents.root_agent import root_agent
from services.adk_runner import run_agent, safe_json_loads


app = FastAPI(title = "AI kitchen ADK MVP")

app.mount("/static", StaticFiles(directory = "static"), name = "static")

class OrderRequest(BaseModel):
    customer_id: str
    item_name: str
    quantity: int = 1
    preference: str = ""


@app.get("/")
def dashboard():
    return FileResponse("static/index.html")

@app.post("/order")
async def create_order(order: OrderRequest):
    order_id = f"ORD-{uuid4().hex[:8]}"

    execute_query(
        """
        INSERT INTO orders (order_id, customer_id, item_name, preference, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            order.customer_id,
            order.item_name,
            order.preference,
            "created"
        )
    )

    workflow_input = {
    "order_id": order_id,
    "customer_id": order.customer_id,
    "item_name": order.item_name,
    "quantity": order.quantity,
    "preference": order.preference
    }

    try:
        raw_result = await run_agent(root_agent, workflow_input)
        workflow_result = safe_json_loads(raw_result)
    
    except Exception as e:
        execute_query(
            "UPDATE orders SET status = ? WHERE order_id = ?",
            ("faild", order_id)
        )

        return {
            "success": False,
            "order_id": order_id,
            "stage": "root_agent",
            "reason": f"ADK root_agent 執行或解析失敗：{str(e)}",
            "data_query_result": {},
            "plan": {},
            "execution_result": {},
            "notify_result": {}
        }
    
    if workflow_result.get("success") is True:
        final_status = "completed"
    else:
        final_status = "failed"
    
    execute_query(
        "UPDATE orders SET status = ? WHERE order_id = ?",
        (final_status, order_id)
    )

    # 5. 確保前端需要的欄位存在
    workflow_result.setdefault("success", False)
    workflow_result.setdefault("order_id", order_id)
    workflow_result.setdefault("message", "")
    workflow_result.setdefault("data_query_result", {})
    workflow_result.setdefault("plan", {})
    workflow_result.setdefault("execution_result", {})
    workflow_result.setdefault("notify_result", {})

    return workflow_result


@app.get("/orders/{order_id}/logs")
def get_order_logs(order_id: str):
    logs = fetch_all(
        "SELECT * FROM task_logs WHERE order_id = ? ORDER BY created_at ASC",
        (order_id,)
    )

    return {
        "success": True,
        "order_id": order_id,
        "logs": logs
    }


@app.post("/demo/reset")
def demo_reset():
    """
    恢復正常 demo 狀態：
    - SQLite 庫存恢復
    - SQLite 設備恢復
    - Robot Server 設備恢復
    """

    # SQLite inventory
    execute_query(
        "UPDATE inventory SET stock_qty = ? WHERE item_name = ?",
        (10, "雞排")
    )

    execute_query(
        "UPDATE inventory SET stock_qty = ? WHERE item_name = ?",
        (20, "薯條")
    )

    # SQLite equipment，只保留基本狀態同步
    execute_query(
        "UPDATE equipment SET status = ? WHERE equipment_id = ?",
        ("available", "fryer_A")
    )

    execute_query(
        "UPDATE equipment SET status = ? WHERE equipment_id = ?",
        ("available", "robot_arm_1")
    )

    # Robot Server reset
    robot_server_result = call_robot_server_reset()

    return {
        "success": True,
        "scenario": "normal",
        "message": "已恢復正常情境：庫存足夠，設備可用",
        "robot_server_result": robot_server_result,
    }


@app.post("/demo/set-inventory-low")
def demo_set_inventory_low():
    """
    設定庫存不足情境：
    - 雞排庫存設為 0
    - Robot Server 維持目前設備狀態
    """

    execute_query(
        "UPDATE inventory SET stock_qty = ? WHERE item_name = ?",
        (0, "雞排")
    )

    return {
        "success": True,
        "scenario": "inventory_low",
        "message": "已切換成庫存不足情境：雞排庫存為 0"
    }


@app.post("/demo/set-equipment-down")
def demo_set_equipment_down():
    """
    設定設備維修情境：
    - 雞排庫存恢復 10
    - Robot Server 將 fryer_A 設為 maintenance
    - 若你要測所有 fryer 不可用，後續可以再新增 set-all-fryers-down
    """

    execute_query(
        "UPDATE inventory SET stock_qty = ? WHERE item_name = ?",
        (10, "雞排")
    )

    robot_server_result = call_robot_server_set_maintenance("fryer_A")

    return {
        "success": True,
        "scenario": "equipment_down",
        "message": "已切換成設備維修情境：fryer_A 設為 maintenance",
        "robot_server_result": robot_server_result,
    }


@app.get("/demo/status")
def demo_status():
    inventory = fetch_all(
        "SELECT item_name, stock_qty, unit FROM inventory ORDER BY item_name"
    )

    sqlite_equipment = fetch_all(
        "SELECT equipment_id, equipment_name, status FROM equipment ORDER BY equipment_id"
    )

    robot_server = {
        "success": False,
        "device_state": {},
        "message": "尚未取得 Robot Server 狀態"
    }

    try:
        response = requests.get(
            f"{ROBOT_SERVER_URL}/device/status",
            timeout=5
        )
        response.raise_for_status()
        robot_server = response.json()

    except requests.RequestException as e:
        robot_server = {
            "success": False,
            "device_state": {},
            "message": f"Robot Server 連線失敗：{str(e)}"
        }

    return {
        "success": True,
        "robot_server_url": ROBOT_SERVER_URL,
        "inventory": inventory,
        "sqlite_equipment": sqlite_equipment,
        "robot_server": robot_server
    }


def call_robot_server_reset() -> dict:
    """
    呼叫 Robot Server reset。
    若 Robot Server 沒開，不讓 main.py crash，只回傳失敗結果。
    """

    try:
        response = requests.post(
            f"{ROBOT_SERVER_URL}/device/reset",
            timeout=5
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        return {
            "success": False,
            "message": f"Robot Server reset 失敗：{str(e)}"
        }


def call_robot_server_set_maintenance(device_id: str) -> dict:
    """
    呼叫 Robot Server 將指定設備設為 maintenance。
    """

    try:
        response = requests.post(
            f"{ROBOT_SERVER_URL}/device/set-maintenance/{device_id}",
            timeout=5
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        return {
            "success": False,
            "message": f"Robot Server set-maintenance 失敗：{str(e)}"
        }