# test_batch_scheduler.py

import json
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.batch_scheduler_tool import schedule_batch_orders


BASE_TIME = "2026-06-16T05:00:00+00:00"


def build_sop_steps(item_name: str, fry_duration_sec: int) -> list[dict]:
    return [
        {
            "step_id": "S1",
            "action": f"preheat_fryer_for_{item_name}",
            "required_device_type": "fryer",
            "duration_sec": 60,
        },
        {
            "step_id": "S2",
            "action": f"place_{item_name}_into_fryer",
            "required_device_type": "robot_arm",
            "duration_sec": 20,
        },
        {
            "step_id": "S3",
            "action": f"fry_{item_name}",
            "required_device_type": "fryer",
            "duration_sec": fry_duration_sec,
        },
        {
            "step_id": "S4",
            "action": f"remove_{item_name}_from_fryer",
            "required_device_type": "robot_arm",
            "duration_sec": 20,
        },
    ]


def build_order(
    order_id: str,
    input_sequence: int,
    item_name: str,
    priority: str,
    priority_weight: int,
    deadline: str,
    fry_duration_sec: int,
) -> dict:
    return {
        "order_id": order_id,
        "input_sequence": input_sequence,
        "customer_id": f"C{input_sequence:03d}",
        "item_name": item_name,
        "quantity": 1,
        "preference": "標準",
        "priority": priority,
        "priority_weight": priority_weight,
        "deadline": deadline,
        "requested_finish_sec": None,
        "preference_intent": "standard",
        "order_goal": "complete_order",
        "inventory_check": {"success": True},
        "sop_check": {
            "success": True,
            "item_name": item_name,
            "steps": build_sop_steps(item_name, fry_duration_sec),
        },
        "resource_status": "resource_ready",
        "resource_reason": "Inventory and SOP are ready",
    }


def build_equipment_snapshot() -> dict:
    return {
        "success": True,
        "server_time": BASE_TIME,
        "devices": {
            "fryer_A": {
                "device_type": "fryer",
                "status": "idle",
                "next_available_at": BASE_TIME,
            },
            "fryer_B": {
                "device_type": "fryer",
                "status": "idle",
                "next_available_at": BASE_TIME,
            },
            "robot_arm_1": {
                "device_type": "robot_arm",
                "status": "idle",
                "next_available_at": BASE_TIME,
            },
            "robot_arm_2": {
                "device_type": "robot_arm",
                "status": "idle",
                "next_available_at": BASE_TIME,
            },
        },
    }


def seconds_between(start_iso: str, end_iso: str) -> int:
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    return int((end - start).total_seconds())


def main() -> None:
    orders = [
        build_order(
            "ORD-BATCH-001",
            1,
            "chicken_cutlet",
            "high",
            3,
            "2026-06-16T05:07:00+00:00",
            210,
        ),
        build_order(
            "ORD-BATCH-002",
            2,
            "french_fries",
            "normal",
            1,
            "2026-06-16T05:08:00+00:00",
            180,
        ),
        build_order(
            "ORD-BATCH-003",
            3,
            "tempura",
            "high",
            4,
            "2026-06-16T05:06:00+00:00",
            150,
        ),
        build_order(
            "ORD-BATCH-004",
            4,
            "fried_squid",
            "normal",
            2,
            "2026-06-16T05:09:00+00:00",
            240,
        ),
    ]

    started_at = perf_counter()
    result = schedule_batch_orders(
        orders=orders,
        equipment_snapshot=build_equipment_snapshot(),
        base_time=BASE_TIME,
    )
    elapsed_ms = (perf_counter() - started_at) * 1000

    scheduled_orders = [
        order
        for order in result.get("orders", [])
        if order.get("decision") == "auto_execute"
    ]

    assert result["success"] is True, result
    assert len(result["execution_order"]) == 4, result["execution_order"]
    assert len(scheduled_orders) == 4, scheduled_orders

    order_timings = []
    for order in sorted(
        scheduled_orders,
        key=lambda item: item["execution_sequence"],
    ):
        active_duration_sec = sum(
            task["duration_sec"]
            for task in order.get("scheduled_tasks", [])
        )
        finish_from_batch_start_sec = seconds_between(
            BASE_TIME,
            order["expected_completion_time"],
        )
        order_timings.append({
            "order_id": order["order_id"],
            "execution_sequence": order["execution_sequence"],
            "assigned_equipment": order["assigned_equipment"],
            "planned_start_time": order["planned_start_time"],
            "expected_completion_time": order[
                "expected_completion_time"
            ],
            "active_duration_sec": active_duration_sec,
            "finish_from_batch_start_sec": finish_from_batch_start_sec,
            "lateness_sec": order["lateness_sec"],
        })

    batch_completion_sec = max(
        item["finish_from_batch_start_sec"]
        for item in order_timings
    )

    report = {
        "scheduler_success": result["success"],
        "message": result["message"],
        "scheduler_runtime_ms": round(elapsed_ms, 3),
        "order_count": len(orders),
        "scheduled_count": len(scheduled_orders),
        "batch_completion_sec": batch_completion_sec,
        "order_timings": order_timings,
        "execution_order": result["execution_order"],
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
