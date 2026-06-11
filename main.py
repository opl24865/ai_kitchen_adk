# main.py
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from uuid import uuid4

from database import execute_query, fetch_all

from agents.adk_runner import run_agent, safe_json_loads
from agents.data_query_agent import data_query_agent
from agents.planner_agent import planner_agent
from agents.executor_agent import executor_agent
from agents.notify_agent import notify_agent
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from config import ROBOT_SERVER_URL


app = FastAPI(title="AI Kitchen ADK MVP")
app.mount("/static", StaticFiles(directory="static"), name="static")

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

    # 1. 建立訂單
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

    # 2. DataQueryAgent：使用 ADK 呼叫 tools 查詢庫存、設備、SOP
    data_query_input = {
        "order_id": order_id,
        "customer_id": order.customer_id,
        "item_name": order.item_name,
        "quantity": order.quantity,
        "preference": order.preference,
    }

    raw_data_query_result = await run_agent(data_query_agent, data_query_input)
    data_query_result = safe_json_loads(raw_data_query_result)

    inventory_result = data_query_result["inventory_check"]
    equipment_result = data_query_result["equipment_check"]
    sop_result = data_query_result["sop_check"]

    if not inventory_result["success"]:
        execute_query(
            "UPDATE orders SET status = ? WHERE order_id = ?",
            ("failed", order_id)
        )
        return {
            "success": False,
            "order_id": order_id,
            "stage": "inventory_check",
            "reason": inventory_result["message"],
            "data_query_result": data_query_result,
        }

    if not equipment_result["success"]:
        execute_query(
            "UPDATE orders SET status = ? WHERE order_id = ?",
            ("failed", order_id)
        )
        return {
            "success": False,
            "order_id": order_id,
            "stage": "equipment_check",
            "reason": equipment_result["message"],
            "data_query_result": data_query_result,
        }

    if not sop_result["success"]:
        execute_query(
            "UPDATE orders SET status = ? WHERE order_id = ?",
            ("failed", order_id)
        )
        return {
            "success": False,
            "order_id": order_id,
            "stage": "sop_check",
            "reason": sop_result["message"],
            "data_query_result": data_query_result,
        }

    # 3. PlannerAgent：使用 ADK 產生任務計畫
    planner_input = {
        "order_id": order_id,
        "order": {
            "customer_id": order.customer_id,
            "item_name": order.item_name,
            "quantity": order.quantity,
            "preference": order.preference,
        },
        "inventory_check": inventory_result,
        "equipment_check": equipment_result,
        "sop_check": sop_result,
    }

    raw_plan = await run_agent(planner_agent, planner_input)
    plan = safe_json_loads(raw_plan)

    if plan.get("plan_status") != "ready":
        execute_query(
            "UPDATE orders SET status = ? WHERE order_id = ?",
            ("failed", order_id)
        )
        return {
            "success": False,
            "order_id": order_id,
            "stage": "planning",
            "reason": plan.get("reason", "Planner Agent 無法產生可執行計畫"),
            "raw_plan": raw_plan,
        }

    execute_query(
        """
        INSERT INTO task_logs (order_id, agent_name, action, status, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            "PlannerAgent",
            "create_task_plan",
            "success",
            f"ADK Planner 已產生 {len(plan['tasks'])} 個任務"
        )
    )

    # 4. ExecutorAgent：使用 ADK 呼叫 Robot Tool 執行任務
    executor_input = {
        "order_id": order_id,
        "plan_status": plan["plan_status"],
        "tasks": plan["tasks"],
    }

    raw_execution_result = await run_agent(executor_agent, executor_input)
    execution_result = safe_json_loads(raw_execution_result)

    if execution_result.get("execution_status") != "completed":
        execute_query(
            "UPDATE orders SET status = ? WHERE order_id = ?",
            ("failed", order_id)
        )
        return {
            "success": False,
            "order_id": order_id,
            "stage": "execution",
            "reason": execution_result.get("message", "Executor Agent 執行失敗"),
            "execution_result": execution_result,
        }

    # 5. NotifyAgent：使用 ADK 呼叫 Notify Tool 通知顧客
    notify_input = {
        "order_id": order_id,
        "customer_id": order.customer_id,
        "item_name": order.item_name,
        "execution_status": execution_result.get("execution_status"),
        "execution_message": execution_result.get("message", ""),
    }

    raw_notify_result = await run_agent(notify_agent, notify_input)
    notify_result = safe_json_loads(raw_notify_result)

    if notify_result.get("notify_status") != "sent":
        execute_query(
            "UPDATE orders SET status = ? WHERE order_id = ?",
            ("completed_but_notify_failed", order_id)
        )
        return {
            "success": False,
            "order_id": order_id,
            "stage": "notify",
            "reason": notify_result.get("message", "通知失敗"),
            "notify_result": notify_result,
        }

    # 6. 更新訂單狀態
    execute_query(
        "UPDATE orders SET status = ? WHERE order_id = ?",
        ("completed", order_id)
    )

    return {
        "success": True,
        "order_id": order_id,
        "message": f"{order.item_name} 製作完成，已通知顧客取餐",
        "data_query_result": data_query_result,
        "plan": plan,
        "execution_result": execution_result,
        "notify_result": notify_result
    }


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
    - 雞排庫存恢復 10
    - 薯條庫存恢復 20
    - 炸鍋與機械手臂恢復 available
    """

    execute_query(
        "UPDATE inventory SET stock_qty = ? WHERE item_name = ?",
        (10, "雞排")
    )

    execute_query(
        "UPDATE inventory SET stock_qty = ? WHERE item_name = ?",
        (20, "薯條")
    )

    execute_query(
        "UPDATE equipment SET status = ? WHERE equipment_id = ?",
        ("available", "fryer_A")
    )

    execute_query(
        "UPDATE equipment SET status = ? WHERE equipment_id = ?",
        ("available", "robot_arm_1")
    )

    return {
        "success": True,
        "scenario": "normal",
        "message": "已恢復正常情境：庫存足夠，設備可用"
    }


@app.post("/demo/set-inventory-low")
def demo_set_inventory_low():
    """
    設定庫存不足情境：
    - 雞排庫存設為 0
    - 設備維持 available
    """

    execute_query(
        "UPDATE inventory SET stock_qty = ? WHERE item_name = ?",
        (0, "雞排")
    )

    execute_query(
        "UPDATE equipment SET status = ? WHERE equipment_id = ?",
        ("available", "fryer_A")
    )

    execute_query(
        "UPDATE equipment SET status = ? WHERE equipment_id = ?",
        ("available", "robot_arm_1")
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
    - 炸鍋設為 maintenance
    - 機械手臂維持 available
    """

    execute_query(
        "UPDATE inventory SET stock_qty = ? WHERE item_name = ?",
        (10, "雞排")
    )

    execute_query(
        "UPDATE equipment SET status = ? WHERE equipment_id = ?",
        ("maintenance", "fryer_A")
    )

    execute_query(
        "UPDATE equipment SET status = ? WHERE equipment_id = ?",
        ("available", "robot_arm_1")
    )

    return {
        "success": True,
        "scenario": "equipment_down",
        "message": "已切換成設備維修情境：炸鍋 A 目前維修中"
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