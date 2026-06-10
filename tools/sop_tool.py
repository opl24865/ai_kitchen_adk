# tools/sop_tool.py

from database import execute_query


def get_sop(order_id: str, item_name: str, preference: str = "") -> dict:
    """
    根據品項與顧客偏好取得對應 SOP。

    Args:
        order_id: 訂單 ID。
        item_name: 品項名稱，例如「雞排」。
        preference: 顧客偏好，例如「酥一點」。

    Returns:
        dict: SOP 查詢結果，包含 success、sop_id、item_name、preference_note、steps、message。
    """

    if item_name == "雞排":
        base_fry_time = 180

        if "酥" in preference:
            fry_time = base_fry_time + 30
            preference_note = "依照顧客偏好，炸製時間增加 30 秒"
        else:
            fry_time = base_fry_time
            preference_note = "使用標準炸製時間"

        result = {
            "success": True,
            "sop_id": "fried_chicken_standard",
            "item_name": item_name,
            "preference_note": preference_note,
            "steps": [
                {
                    "step_id": "S1",
                    "action": "preheat_fryer",
                    "device": "fryer_A",
                    "duration_sec": 60
                },
                {
                    "step_id": "S2",
                    "action": "place_food_into_fryer",
                    "device": "robot_arm_1",
                    "duration_sec": 20
                },
                {
                    "step_id": "S3",
                    "action": "fry",
                    "device": "fryer_A",
                    "duration_sec": fry_time
                },
                {
                    "step_id": "S4",
                    "action": "remove_food_from_fryer",
                    "device": "robot_arm_1",
                    "duration_sec": 20
                }
            ],
            "message": "成功取得雞排 SOP"
        }
    else:
        result = {
            "success": False,
            "sop_id": None,
            "item_name": item_name,
            "preference_note": "",
            "steps": [],
            "message": f"目前沒有 {item_name} 的 SOP"
        }

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

    return result