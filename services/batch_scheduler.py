# services/batch_scheduler.py

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any


def schedule_batch(
    orders: list[dict],
    equipment_snapshot: dict,
    base_time: datetime | None = None,
) -> dict[str, Any]:
    """
    為所有 resource_ready 訂單安排炸鍋、機械手臂及執行時間。
    """

    current_time = base_time or datetime.now(timezone.utc)

    # 只有設備和庫存皆有資源，才可進行排序
    ready_orders = [
        order
        for order in orders
        if order.get("resource_status") == "resource_ready"
    ]

    blocked_orders = [
        deepcopy(order)
        for order in orders
        if order.get("resource_status") != "resource_ready"
    ]

    # 先將訂單進行優先排序，排序流程: 
    # 1. 有 deadline 的排前面
    # 2. deadline 越早，排越前面
    # 3. priority_weight 越高，排越前面
    # 4. input_sequence 越小，排越前面
    ready_orders.sort(
        key=lambda order: (
            parse_datetime(order.get("deadline")) is None,
            parse_datetime(order.get("deadline"))
            or datetime.max.replace(tzinfo=timezone.utc),
            -normalize_priority_weight(order),
            order.get("input_sequence", 0),
        )
    )

    # 將設備快照轉成 scheduler 用的格式
    device_timeline = build_device_timeline(
        equipment_snapshot=equipment_snapshot,
        base_time=current_time,
    )

    # 獲得可以使用的設備
    fryer_ids = get_schedulable_devices(
        device_timeline,
        device_type="fryer",
    )

    robot_arm_ids = get_schedulable_devices(
        device_timeline,
        device_type="robot_arm",
    )

    scheduled_orders = []
    unscheduled_orders = []

    for order in ready_orders:
        best_candidate = None

        if not fryer_ids:
            unscheduled_order = deepcopy(order)
            unscheduled_order["decision"] = "wait_equipment"
            unscheduled_order["schedule_error"] = (
                "No schedulable fryer"
            )
            unscheduled_orders.append(unscheduled_order)
            continue

        if not robot_arm_ids:
            unscheduled_order = deepcopy(order)
            unscheduled_order["decision"] = "wait_equipment"
            unscheduled_order["schedule_error"] = (
                "No schedulable robot arm"
            )
            unscheduled_orders.append(unscheduled_order)
            continue

        if not get_sop_steps(order):
            unscheduled_order = deepcopy(order)
            unscheduled_order["decision"] = "manual_review"
            unscheduled_order["schedule_error"] = (
                "No SOP steps"
            )
            unscheduled_orders.append(unscheduled_order)
            continue

        for fryer_id in fryer_ids:
            for robot_arm_id in robot_arm_ids:
                candidate = simulate_order_schedule(
                    order=order,
                    fryer_id=fryer_id,
                    robot_arm_id=robot_arm_id,
                    device_timeline=device_timeline,
                    base_time=current_time,
                )

                candidate_key = (
                    candidate["score"],
                    candidate["expected_completion_time"],
                    candidate["fryer_id"],
                    candidate["robot_arm_id"],
                )

                if best_candidate is None:
                    best_candidate = candidate
                    continue

                best_candidate_key = (
                    best_candidate["score"],
                    best_candidate[
                        "expected_completion_time"
                    ],
                    best_candidate["fryer_id"],
                    best_candidate["robot_arm_id"],
                )

                if candidate_key < best_candidate_key:
                    best_candidate = candidate

        if best_candidate is None:
            unscheduled_order = deepcopy(order)
            unscheduled_order["decision"] = "wait_equipment"
            unscheduled_order["schedule_error"] = (
                "No valid schedule candidate"
            )
            unscheduled_orders.append(unscheduled_order)
            continue

        scheduled_order = apply_candidate(
            order=order,
            candidate=best_candidate,
        )

      
        scheduled_orders.append(scheduled_order)

        reserve_candidate(
            device_timeline=device_timeline,
            candidate=best_candidate,
        )

    scheduled_orders.sort(
        key=lambda order: (
            order.get("planned_start_time") or "",
            order.get("expected_completion_time") or "",
            -normalize_priority_weight(order),
            order.get("input_sequence", 0),
        )
    )

    execution_order = []

    for sequence, order in enumerate(
        scheduled_orders,
        start=1,
    ):
        order["execution_sequence"] = sequence

        execution_order.append({
            "sequence": sequence,
            "order_id": order["order_id"],
            "planned_start_time": order[
                "planned_start_time"
            ],
            "expected_completion_time": order[
                "expected_completion_time"
            ],
        })

    return {
        "success": bool(scheduled_orders),
        "execution_order": execution_order,
        "orders": scheduled_orders + unscheduled_orders + blocked_orders,
        "device_timeline": serialize_device_timeline(
            device_timeline
        ),
    }


def build_device_timeline(
    equipment_snapshot: dict,
    base_time: datetime,
) -> dict[str, dict]:
    """
    將 Robot Server 的 devices 資料轉換成排程器使用的時間軸。
    """

    timeline = {}
    devices = equipment_snapshot.get("devices", {})

    for device_id, detail in devices.items():
        status = detail.get("status", "unknown")

        if status == "maintenance":
            continue

        next_available_at = parse_datetime(
            detail.get("next_available_at")
        )

        timeline[device_id] = {
            "device_id": device_id,
            "device_type": detail.get("device_type"),
            "available_at": max(
                base_time,
                next_available_at or base_time,
            ),
            "reservations": [],
        }

    return timeline


def get_schedulable_devices(
    device_timeline: dict[str, dict],
    device_type: str,
) -> list[str]:
    return sorted(
        device_id
        for device_id, detail in device_timeline.items()
        if detail.get("device_type") == device_type
    )


def simulate_order_schedule(
    order: dict,
    fryer_id: str,
    robot_arm_id: str,
    device_timeline: dict[str, dict],
    base_time: datetime,
) -> dict:
    """
    模擬一筆訂單在指定設備組合上的完整 SOP 時間。
    不得修改正式的 device_timeline。
    """

    simulated_available_at = {
        device_id: detail["available_at"]
        for device_id, detail in device_timeline.items()
    }

    scheduled_tasks = []

    previous_step_end = base_time

    for step in get_sop_steps(order):
        device_id = select_step_device(
            step=step,
            fryer_id=fryer_id,
            robot_arm_id=robot_arm_id,
        )

        # 必須同時滿足:
        # 1. 前一個 SOP step 已經完成
        # 2. 這台設備已經空出來 
        step_start = max(
            previous_step_end,
            simulated_available_at[device_id],
        )

        duration_sec = normalize_duration(
            step.get("duration_sec")
        )

        step_end = step_start + timedelta(
            seconds=duration_sec
        )

        scheduled_tasks.append({
            "task_id": build_task_id(
                order_id=order["order_id"],
                step_id=step["step_id"],
            ),
            "step_id": step["step_id"],
            "device": device_id,
            "action": step["action"],
            "duration_sec": duration_sec,
            "planned_start_time": to_iso(step_start),
            "planned_end_time": to_iso(step_end),
        })

        simulated_available_at[device_id] = step_end

        previous_step_end = step_end

    expected_completion = previous_step_end

    score_details = calculate_schedule_score(
        order=order,
        expected_completion=expected_completion,
        base_time=base_time,
    )

    return {
        "fryer_id": fryer_id,
        "robot_arm_id": robot_arm_id,
        "planned_start_time": (
            scheduled_tasks[0]["planned_start_time"]
            if scheduled_tasks
            else None
        ),
        "expected_completion_time": to_iso(
            expected_completion
        ),
        "estimated_duration_sec": int(
            (
                expected_completion - base_time
            ).total_seconds()
        ),
        "scheduled_tasks": scheduled_tasks,
        **score_details,
    }


def calculate_schedule_score(
    order: dict,
    expected_completion: datetime,
    base_time: datetime,
) -> dict:
    deadline = parse_datetime(order.get("deadline"))
    priority_weight = normalize_priority_weight(order)

    lateness_sec = 0

    if deadline is not None:
        lateness_sec = max(
            0,
            int(
                (
                    expected_completion - deadline
                ).total_seconds()
            ),
        )

    flow_time_sec = max(
        0,
        int(
            (
                expected_completion - base_time
            ).total_seconds()
        ),
    )

    score = (
        lateness_sec * priority_weight
        + flow_time_sec
    )

    return {
        "score": score,
        "lateness_sec": lateness_sec,
        "priority_weight": priority_weight,
    }


def reserve_candidate(
    device_timeline: dict[str, dict],
    candidate: dict,
) -> None:
    for task in candidate.get("scheduled_tasks", []):
        device_id = task["device"]

        task_start = parse_datetime(
            task.get("planned_start_time")
        )

        task_end = parse_datetime(
            task.get("planned_end_time")
        )

        if task_start is None or task_end is None:
            continue

        reservation = deepcopy(task)
        device_timeline[device_id][
            "reservations"
        ].append(reservation)

        device_timeline[device_id]["available_at"] = max(
            device_timeline[device_id]["available_at"],
            task_end,
        )


def apply_candidate(
    order: dict,
    candidate: dict,
) -> dict:
    result = deepcopy(order)

    result["decision"] = "auto_execute"

    result["assigned_equipment"] = {
        "fryer": candidate["fryer_id"],
        "robot_arm": candidate["robot_arm_id"],
    }

    result["planned_start_time"] = candidate[
        "planned_start_time"
    ]

    result["expected_completion_time"] = candidate[
        "expected_completion_time"
    ]

    result["estimated_duration_sec"] = candidate[
        "estimated_duration_sec"
    ]

    result["schedule_score"] = candidate["score"]

    result["lateness_sec"] = candidate[
        "lateness_sec"
    ]

    result["priority_weight"] = candidate[
        "priority_weight"
    ]

    result["scheduled_tasks"] = deepcopy(
        candidate["scheduled_tasks"]
    )

    return result


def get_sop_steps(order: dict) -> list[dict]:
    return (
        order.get("sop_check", {})
        .get("steps", [])
    )


def select_step_device(
    step: dict,
    fryer_id: str,
    robot_arm_id: str,
) -> str:
    device_type = step.get("required_device_type")

    if device_type == "fryer":
        return fryer_id

    if device_type == "robot_arm":
        return robot_arm_id

    raise ValueError(
        f"Unsupported device type: {device_type}"
    )


def normalize_priority_weight(order: dict) -> int:
    explicit_weight = order.get("priority_weight")

    if explicit_weight is not None:
        try:
            return max(1, int(explicit_weight))
        except (TypeError, ValueError):
            pass

    return (
        3
        if order.get("priority") == "high"
        else 1
    )


def normalize_duration(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def build_task_id(
    order_id: str,
    step_id: str,
) -> str:
    return f"{order_id}-{step_id}"


def parse_datetime(
    value: str | None,
) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (TypeError, ValueError):
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(timezone.utc)


def to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None

    return value.astimezone(timezone.utc).isoformat(
        timespec="seconds"
    )


def serialize_device_timeline(
    device_timeline: dict[str, dict],
) -> dict[str, dict]:
    result = {}

    for device_id, detail in device_timeline.items():
        result[device_id] = {
            "device_id": detail["device_id"],
            "device_type": detail["device_type"],
            "available_at": to_iso(
                detail["available_at"]
            ),
            "reservations": deepcopy(
                detail["reservations"]
            ),
        }

    return result
