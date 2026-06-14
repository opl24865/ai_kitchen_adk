# tools/sop_tool.py

import json
from pathlib import Path

from database import execute_query


SOP_TEMPLATE_PATH = Path("data/sop_templates.json")


def get_sop(order_id: str, item_name: str, preference: str = "") -> dict:
    """
    根據品項與顧客偏好取得對應 SOP。
    SOP 內容從 data/sop_templates.json 讀取，不再寫死在 Python 程式碼中。

    Args:
        order_id: 訂單 ID。
        item_name: 品項名稱，例如「雞排」、「薯條」、「雞塊」。
        preference: 顧客偏好，例如「酥一點」、「少油」。

    Returns:
        dict: SOP 查詢結果，包含 success、sop_id、item_name、preference_note、steps、message。
    """

    templates = load_sop_templates()

    if item_name not in templates:
        result = {
            "success": False,
            "sop_id": None,
            "item_name": item_name,
            "preference_note": "",
            "steps": [],
            "message": f"目前沒有 {item_name} 的 SOP"
        }

        write_sop_log(order_id, result)
        return result

    template = templates[item_name]

    fry_time, preference_note = apply_preference_rule(
        base_fry_time=template["base_fry_time"],
        preference=preference,
        preference_rules=template.get("preference_rules", {})
    )

    steps = build_frying_steps(
        preheat_time=template.get("preheat_time", 60),
        place_time=template.get("place_time", 20),
        fry_time=fry_time,
        remove_time=template.get("remove_time", 20)
    )

    result = {
        "success": True,
        "sop_id": template["sop_id"],
        "item_name": item_name,
        "preference_note": preference_note,
        "steps": steps,
        "message": f"成功取得 {item_name} SOP"
    }

    write_sop_log(order_id, result)
    return result


def load_sop_templates() -> dict:
    """
    讀取 SOP template JSON。
    """

    if not SOP_TEMPLATE_PATH.exists():
        return {}

    with SOP_TEMPLATE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def apply_preference_rule(
    base_fry_time: int,
    preference: str,
    preference_rules: dict
) -> tuple[int, str]:
    """
    根據顧客偏好調整炸製時間。
    目前使用簡單 keyword matching：
    - preference 裡包含「酥」→ 增加炸製時間
    - preference 裡包含「少油」→ 減少炸製時間
    """

    fry_time = base_fry_time
    matched_notes = []

    for keyword, rule in preference_rules.items():
        if keyword in preference:
            fry_time += int(rule.get("fry_time_delta", 0))
            matched_notes.append(rule.get("note", f"套用偏好規則：{keyword}"))

    if matched_notes:
        preference_note = "；".join(matched_notes)
    else:
        preference_note = "使用標準炸製時間"

    # 避免炸製時間被偏好規則調到不合理
    fry_time = max(fry_time, 30)

    return fry_time, preference_note


def build_frying_steps(
    preheat_time: int,
    place_time: int,
    fry_time: int,
    remove_time: int
) -> list[dict]:
    """
    建立標準油炸流程。
    SOP 只描述需要的設備類型，不指定實際設備 ID。
    實際使用 fryer_C 或 robot_arm_1 由 PlannerAgent 決定。
    """

    return [
        {
            "step_id": "S1",
            "action": "preheat_fryer",
            "required_device_type": "fryer",
            "duration_sec": preheat_time
        },
        {
            "step_id": "S2",
            "action": "place_food_into_fryer",
            "required_device_type": "robot_arm",
            "duration_sec": place_time
        },
        {
            "step_id": "S3",
            "action": "fry",
            "required_device_type": "fryer",
            "duration_sec": fry_time
        },
        {
            "step_id": "S4",
            "action": "remove_food_from_fryer",
            "required_device_type": "robot_arm",
            "duration_sec": remove_time
        }
    ]


def write_sop_log(order_id: str, result: dict):
    """
    寫入 task_logs。
    """

    execute_query(
        """
        INSERT INTO task_logs (order_id, agent_name, action, status, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            "DataQueryAgent",
            "get_sop",
            "success" if result["success"] else "failed",
            result["message"]
        )
    )