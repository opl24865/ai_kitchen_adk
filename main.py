import json
import requests

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.batch_root_agent import batch_root_agent
from agents.root_agent import root_agent
from config import ROBOT_SERVER_URL
from database import execute_query, fetch_all
from services.adk_runner import safe_json_loads, run_agent_with_state
from utils.debug_recorder import save_workflow_debug_files


app = FastAPI(title="AI kitchen ADK MVP")

app.mount("/static", StaticFiles(directory="static"), name="static")


class OrderRequest(BaseModel):
    customer_id: str
    item_name: str
    quantity: int = 1
    preference: str = ""


class BatchOrderItem(BaseModel):
    customer_id: str
    item_name: str
    quantity: int = 1
    preference: str = ""
    deadline: str | None = None
    priority_weight: int | None = None


class BatchOrderRequest(BaseModel):
    scenario: str = "custom_batch"
    orders: list[BatchOrderItem]


def normalize_quantity(value) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


async def run_batch_order_decision(batch_input: dict) -> dict:
    """
    Run ADK batch workflow:

    BatchOrderIntakeAgent
        ->
    BatchResourceAssessmentAgent
        ->
    BatchPlanningAgent
        ->
    BatchExecutionAgent
        ->
    BatchNotificationAgent
    """

    batch_id = batch_input.get("batch_id") or f"BATCH-{uuid4().hex[:8]}"
    batch_input["batch_id"] = batch_id

    normalized_orders = []

    for index, order in enumerate(batch_input.get("orders", []), start=1):
        order_id = order.get("order_id") or f"{batch_id}-ORD-{index:03d}"

        normalized_orders.append({
            "order_id": order_id,
            "customer_id": order.get("customer_id", f"C{index:03d}"),
            "item_name": order.get("item_name", ""),
            "quantity": normalize_quantity(order.get("quantity", 1)),
            "preference": order.get("preference", ""),
            "deadline": order.get("deadline"),
            "priority_weight": order.get("priority_weight"),
        })

    batch_input["orders"] = normalized_orders

    agent_run_result = await run_agent_with_state(
        batch_root_agent,
        batch_input,
    )

    raw_result = agent_run_result["final_text"]
    session_state = agent_run_result["session_state"]

    batch_result = safe_json_loads(raw_result)

    batch_result.setdefault("success", False)
    batch_result.setdefault("batch_id", batch_id)
    batch_result.setdefault(
        "scenario",
        batch_input.get("scenario", "custom_batch"),
    )
    batch_result.setdefault("message", "")
    batch_result.setdefault("batch_summary", {})
    batch_result.setdefault("equipment_snapshot", {})
    batch_result.setdefault("orders", [])
    batch_result.setdefault("batch_decision_reason", "")

    batch_result["debug"] = {
        "adk_workflow": "batch_root_agent",
        "session_state_keys": list(session_state.keys()),
        "has_batch_order_intake_state": (
            "batch_order_intake_state" in session_state
        ),
        "has_batch_resource_assessment_state": (
            "batch_resource_assessment_state" in session_state
        ),
        "has_batch_planning_state": (
            "batch_planning_state" in session_state
        ),
        "has_batch_execution_state": (
            "batch_execution_state" in session_state
        ),
        "has_batch_final_state": (
            "batch_final_state" in session_state
        ),
    }

    return batch_result


def reset_inventory_items():
    inventory_items = [
        ("雞排", 10, "份"),
        ("薯條", 20, "份"),
        ("雞塊", 15, "份"),
        ("甜不辣", 12, "份"),
        ("花枝丸", 12, "份"),
    ]

    for item_name, stock_qty, unit in inventory_items:
        execute_query(
            """
            INSERT OR REPLACE INTO inventory (
                item_name,
                stock_qty,
                unit
            )
            VALUES (?, ?, ?)
            """,
            (item_name, stock_qty, unit),
        )


def reset_equipment_items():
    equipment_items = [
        ("fryer_A", "炸鍋 A", "available"),
        ("fryer_B", "炸鍋 B", "available"),
        ("fryer_C", "炸鍋 C", "available"),
        ("robot_arm_1", "機械手臂 1", "available"),
        ("robot_arm_2", "機械手臂 2", "available"),
    ]

    for equipment_id, equipment_name, status in equipment_items:
        execute_query(
            """
            INSERT OR REPLACE INTO equipment (
                equipment_id,
                equipment_name,
                status
            )
            VALUES (?, ?, ?)
            """,
            (equipment_id, equipment_name, status),
        )


def call_robot_server_reset() -> dict:
    try:
        response = requests.post(
            f"{ROBOT_SERVER_URL}/device/reset",
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as error:
        return {
            "success": False,
            "message": f"Robot Server reset failed: {error}",
        }


def call_robot_server_set_maintenance(device_id: str) -> dict:
    try:
        response = requests.post(
            f"{ROBOT_SERVER_URL}/device/set-maintenance/{device_id}",
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as error:
        return {
            "success": False,
            "message": f"Robot Server set-maintenance failed: {error}",
        }


@app.get("/")
def dashboard():
    return FileResponse("static/index.html")


@app.post("/order")
async def create_order(order: OrderRequest):
    order_id = f"ORD-{uuid4().hex[:8]}"

    execute_query(
        """
        INSERT INTO orders (
            order_id,
            customer_id,
            item_name,
            preference,
            status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            order.customer_id,
            order.item_name,
            order.preference,
            "created",
        ),
    )

    workflow_input = {
        "order_id": order_id,
        "customer_id": order.customer_id,
        "item_name": order.item_name,
        "quantity": normalize_quantity(order.quantity),
        "preference": order.preference,
    }

    try:
        agent_run_result = await run_agent_with_state(
            root_agent,
            workflow_input,
        )

        raw_result = agent_run_result["final_text"]
        session_state = agent_run_result["session_state"]

        workflow_result = safe_json_loads(raw_result)

        debug_result = save_workflow_debug_files(
            order_id=order_id,
            workflow_input=workflow_input,
            session_state=session_state,
            final_raw_output=raw_result,
            final_parsed_output=workflow_result,
        )

        workflow_result["debug"] = debug_result

    except Exception as error:
        execute_query(
            "UPDATE orders SET status = ? WHERE order_id = ?",
            ("failed", order_id),
        )

        return {
            "success": False,
            "order_id": order_id,
            "stage": "root_agent",
            "reason": f"ADK root_agent failed: {error}",
            "message": f"ADK root_agent failed: {error}",
            "data_query_result": {},
            "resource_assessment": {},
            "production_decision": {},
            "plan": {},
            "execution_result": {},
            "notify_result": {},
        }

    final_status = (
        "completed"
        if workflow_result.get("success") is True
        else "failed"
    )

    execute_query(
        "UPDATE orders SET status = ? WHERE order_id = ?",
        (final_status, order_id),
    )

    workflow_result.setdefault("success", False)
    workflow_result.setdefault("order_id", order_id)
    workflow_result.setdefault("message", "")
    workflow_result.setdefault("order_context", {})
    workflow_result.setdefault("data_query_result", {})
    workflow_result.setdefault("resource_assessment", {})
    workflow_result.setdefault("production_decision", {})
    workflow_result.setdefault("plan", {})
    workflow_result.setdefault("execution_result", {})
    workflow_result.setdefault("notify_result", {})

    return workflow_result


@app.post("/batch-orders")
async def create_batch_orders(request: BatchOrderRequest):
    """
    Run batch order workflow with ADK batch_root_agent.

    BatchOrderIntakeAgent
        ->
    BatchResourceAssessmentAgent
        ->
    BatchPlanningAgent
        ->
    BatchExecutionAgent
        ->
    BatchNotificationAgent
    """

    batch_id = f"BATCH-{uuid4().hex[:8]}"

    batch_input = {
        "batch_id": batch_id,
        "scenario": request.scenario,
        "orders": [
            {
                "order_id": f"{batch_id}-ORD-{index + 1:03d}",
                "customer_id": order.customer_id,
                "item_name": order.item_name,
                "quantity": normalize_quantity(order.quantity),
                "preference": order.preference,
                "deadline": order.deadline,
                "priority_weight": order.priority_weight,
            }
            for index, order in enumerate(request.orders)
        ],
    }

    try:
        return await run_batch_order_decision(batch_input)

    except Exception as error:
        return build_batch_error_response(
            batch_id=batch_id,
            scenario=request.scenario,
            total_orders=len(request.orders),
            error=error,
        )


def build_batch_error_response(
    batch_id: str,
    scenario: str,
    total_orders: int,
    error: Exception,
) -> dict:
    return {
        "success": False,
        "batch_id": batch_id,
        "scenario": scenario,
        "message": f"ADK batch_root_agent failed: {error}",
        "batch_summary": {
            "total_orders": total_orders,
            "auto_execute_count": 0,
            "wait_count": 0,
            "escalation_count": 0,
            "selected_order_for_execution": None,
            "summary": f"Batch workflow failed: {error}",
        },
        "equipment_snapshot": {},
        "batch_decision_reason": (
            f"Batch workflow failed before final decision: {error}"
        ),
        "orders": [],
        "debug": {
            "adk_workflow": "batch_root_agent",
            "error": str(error),
        },
    }


@app.get("/orders/{order_id}/logs")
def get_order_logs(order_id: str):
    logs = fetch_all(
        """
        SELECT *
        FROM task_logs
        WHERE order_id = ?
        ORDER BY created_at ASC
        """,
        (order_id,),
    )

    return {
        "success": True,
        "order_id": order_id,
        "logs": logs,
    }


@app.get("/orders/{order_id}/alerts")
def get_order_alerts(order_id: str):
    alerts = fetch_all(
        """
        SELECT *
        FROM alert_logs
        WHERE order_id = ?
        ORDER BY created_at ASC
        """,
        (order_id,),
    )

    return {
        "success": True,
        "order_id": order_id,
        "alerts": alerts,
    }


@app.post("/demo/reset")
def demo_reset():
    reset_inventory_items()
    reset_equipment_items()
    robot_server_result = call_robot_server_reset()

    return {
        "success": True,
        "scenario": "normal",
        "message": "Demo inventory, equipment, and Robot Server reset.",
        "robot_server_result": robot_server_result,
    }


@app.post("/demo/set-inventory-low")
def demo_set_inventory_low():
    execute_query(
        "UPDATE inventory SET stock_qty = ? WHERE item_name = ?",
        (0, "雞排"),
    )

    return {
        "success": True,
        "scenario": "inventory_low",
        "message": "雞排 inventory has been set to 0.",
    }


@app.post("/demo/set-equipment-down")
def demo_set_equipment_down():
    execute_query(
        "UPDATE inventory SET stock_qty = ? WHERE item_name = ?",
        (10, "雞排"),
    )

    robot_server_result = call_robot_server_set_maintenance("fryer_A")

    return {
        "success": True,
        "scenario": "equipment_down",
        "message": "fryer_A has been set to maintenance.",
        "robot_server_result": robot_server_result,
    }


@app.get("/demo/status")
def demo_status():
    inventory = fetch_all(
        """
        SELECT item_name, stock_qty, unit
        FROM inventory
        ORDER BY item_name
        """
    )

    sqlite_equipment = fetch_all(
        """
        SELECT equipment_id, equipment_name, status
        FROM equipment
        ORDER BY equipment_id
        """
    )

    robot_server = {
        "success": False,
        "device_state": {},
        "message": "Robot Server has not been queried.",
    }

    try:
        response = requests.get(
            f"{ROBOT_SERVER_URL}/device/status",
            timeout=5,
        )
        response.raise_for_status()
        robot_server = response.json()

    except requests.RequestException as error:
        robot_server = {
            "success": False,
            "device_state": {},
            "message": f"Robot Server status failed: {error}",
        }

    return {
        "success": True,
        "robot_server_url": ROBOT_SERVER_URL,
        "inventory": inventory,
        "sqlite_equipment": sqlite_equipment,
        "robot_server": robot_server,
    }


@app.post("/demo/lunch-peak")
async def demo_lunch_peak():
    """
    Lunch peak demo.

    注意：
    這裡只使用 data/sop_templates.json 內存在的品項：
    雞排、薯條、雞塊、甜不辣。
    init_db.py 裡的花枝丸目前沒有 SOP，因此不放入此 demo。
    """

    batch_id = f"BATCH-{uuid4().hex[:8]}"

    batch_input = {
        "batch_id": batch_id,
        "scenario": "lunch_peak",
        "orders": [
            {
                "order_id": f"{batch_id}-ORD-001",
                "customer_id": "C001",
                "item_name": "雞排",
                "quantity": 1,
                "preference": "酥一點",
                "deadline": None,
                "priority_weight": 1,
            },
            {
                "order_id": f"{batch_id}-ORD-002",
                "customer_id": "C002",
                "item_name": "薯條",
                "quantity": 2,
                "preference": "趕時間",
                "deadline": None,
                "priority_weight": 3,
            },
            {
                "order_id": f"{batch_id}-ORD-003",
                "customer_id": "C003",
                "item_name": "甜不辣",
                "quantity": 1,
                "preference": "少油",
                "deadline": None,
                "priority_weight": 1,
            },
            {
                "order_id": f"{batch_id}-ORD-004",
                "customer_id": "C004",
                "item_name": "雞塊",
                "quantity": 1,
                "preference": "",
                "deadline": None,
                "priority_weight": 1,
            },
        ],
    }

    try:
        return await run_batch_order_decision(batch_input)

    except Exception as error:
        return build_batch_error_response(
            batch_id=batch_id,
            scenario="lunch_peak",
            total_orders=len(batch_input["orders"]),
            error=error,
        )


@app.get("/orders/{order_id}/debug")
def get_order_debug(order_id: str):
    debug_index_path = (
        Path("debug_runs")
        / order_id
        / "debug_index.json"
    )

    if not debug_index_path.exists():
        return {
            "success": False,
            "order_id": order_id,
            "message": "Debug file not found.",
        }

    with debug_index_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return {
        "success": True,
        "order_id": order_id,
        "debug": data,
    }


@app.get("/orders/{order_id}/debug/{file_name}")
def get_order_debug_file(order_id: str, file_name: str):
    allowed_files = {
        "00_workflow_input.json",
        "01_data_query_agent.json",
        "02_planner_agent.json",
        "03_executor_agent.json",
        "04_notify_agent.json",
        "01_order_intake_agent.json",
        "02_resource_assessment_agent.json",
        "03_production_planning_agent.json",
        "04_equipment_execution_agent.json",
        "05_notification_escalation_agent.json",
        "99_final_result.json",
        "debug_index.json",
    }

    if file_name not in allowed_files:
        return {
            "success": False,
            "message": "Invalid debug file name.",
        }

    file_path = Path("debug_runs") / order_id / file_name

    if not file_path.exists():
        return {
            "success": False,
            "order_id": order_id,
            "file_name": file_name,
            "message": "Debug file not found.",
        }

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return {
        "success": True,
        "order_id": order_id,
        "file_name": file_name,
        "data": data,
    }