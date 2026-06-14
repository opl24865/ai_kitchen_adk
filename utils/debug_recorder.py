# utils/debug_recorder.py

import json
from pathlib import Path
from typing import Any


DEBUG_ROOT = Path("debug_runs")


def safe_parse_json(value: Any) -> tuple[bool, Any, str | None]:
    if isinstance(value, dict):
        return True, value, None

    if isinstance(value, list):
        return True, value, None

    if value is None:
        return False, None, "value is None"

    text = str(value).strip()

    if text.startswith("```json"):
        text = text.replace("```json", "", 1).strip()

    if text.startswith("```"):
        text = text.replace("```", "", 1).strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    try:
        return True, json.loads(text), None
    except Exception as e:
        return False, value, str(e)


def check_required_keys(data: Any, required_keys: list[str]) -> dict:
    if not isinstance(data, dict):
        return {
            "passed": False,
            "missing_keys": required_keys,
            "message": "output is not a dict"
        }

    missing_keys = [
        key for key in required_keys
        if key not in data
    ]

    return {
        "passed": len(missing_keys) == 0,
        "missing_keys": missing_keys
    }


def write_json_file(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_agent_debug_record(
    agent_name: str,
    input_data: Any,
    raw_output: Any,
    required_keys: list[str]
) -> dict:
    json_valid, parsed_output, parse_error = safe_parse_json(raw_output)
    key_check = check_required_keys(parsed_output, required_keys)

    return {
        "agent_name": agent_name,
        "input": input_data,
        "raw_output": raw_output,
        "json_valid": json_valid,
        "parse_error": parse_error,
        "output": parsed_output,
        "required_keys_check": key_check
    }


def save_workflow_debug_files(
    order_id: str,
    workflow_input: dict,
    session_state: dict,
    final_raw_output: str,
    final_parsed_output: dict | None = None
) -> dict:
    run_dir = DEBUG_ROOT / order_id
    run_dir.mkdir(parents=True, exist_ok=True)

    order_intake_raw = session_state.get("order_intake_state")
    data_query_raw = session_state.get("data_query_state")
    planning_raw = session_state.get("planning_state")
    execution_raw = session_state.get("execution_state")
    final_state_raw = session_state.get("final_workflow_result")

    _, order_intake_output, _ = safe_parse_json(order_intake_raw)
    _, data_query_output, _ = safe_parse_json(data_query_raw)
    _, planning_output, _ = safe_parse_json(planning_raw)
    _, execution_output, _ = safe_parse_json(execution_raw)

    files = {}

    path = run_dir / "00_workflow_input.json"
    write_json_file(path, {
        "description": "FastAPI 傳給 ADK root_agent 的原始輸入",
        "workflow_input": workflow_input
    })
    files["workflow_input"] = str(path)

    path = run_dir / "01_order_intake_agent.json"
    write_json_file(
        path,
        build_agent_debug_record(
            agent_name="order_intake_agent",
            input_data=workflow_input,
            raw_output=order_intake_raw,
            required_keys=[
                "order_id",
                "customer_id",
                "item_name",
                "quantity",
                "preference",
                "workflow_status",
                "order_context"
            ]
        )
    )
    files["order_intake_agent"] = str(path)

    path = run_dir / "02_resource_assessment_agent.json"
    write_json_file(
        path,
        build_agent_debug_record(
            agent_name="resource_assessment_agent",
            input_data=order_intake_output,
            raw_output=data_query_raw,
            required_keys=[
                "order_id",
                "customer_id",
                "item_name",
                "quantity",
                "preference",
                "workflow_status",
                "order_context",
                "data_query_result",
                "resource_assessment"
            ]
        )
    )
    files["resource_assessment_agent"] = str(path)

    path = run_dir / "03_production_planning_agent.json"
    write_json_file(
        path,
        build_agent_debug_record(
            agent_name="production_planning_agent",
            input_data=data_query_output,
            raw_output=planning_raw,
            required_keys=[
                "order_id",
                "customer_id",
                "item_name",
                "quantity",
                "preference",
                "workflow_status",
                "order_context",
                "data_query_result",
                "resource_assessment",
                "production_decision",
                "plan"
            ]
        )
    )
    files["production_planning_agent"] = str(path)

    path = run_dir / "04_equipment_execution_agent.json"
    write_json_file(
        path,
        build_agent_debug_record(
            agent_name="equipment_execution_agent",
            input_data=planning_output,
            raw_output=execution_raw,
            required_keys=[
                "order_id",
                "customer_id",
                "item_name",
                "quantity",
                "preference",
                "workflow_status",
                "order_context",
                "data_query_result",
                "resource_assessment",
                "production_decision",
                "plan",
                "execution_result"
            ]
        )
    )
    files["equipment_execution_agent"] = str(path)

    path = run_dir / "05_notification_escalation_agent.json"
    write_json_file(
        path,
        build_agent_debug_record(
            agent_name="notification_escalation_agent",
            input_data=execution_output,
            raw_output=final_state_raw,
            required_keys=[
                "success",
                "order_id",
                "message",
                "order_context",
                "data_query_result",
                "resource_assessment",
                "production_decision",
                "plan",
                "execution_result",
                "notify_result"
            ]
        )
    )
    files["notification_escalation_agent"] = str(path)

    path = run_dir / "99_final_result.json"
    write_json_file(path, {
        "description": "root_agent 最終回傳結果",
        "raw_output": final_raw_output,
        "parsed_output": final_parsed_output
    })
    files["final_result"] = str(path)

    path = run_dir / "debug_index.json"
    write_json_file(path, {
        "order_id": order_id,
        "debug_dir": str(run_dir),
        "files": files
    })
    files["debug_index"] = str(path)

    return {
        "success": True,
        "order_id": order_id,
        "debug_dir": str(run_dir),
        "files": files
    }