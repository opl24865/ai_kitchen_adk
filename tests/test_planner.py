# test_planner.py

import asyncio
import json
from dotenv import load_dotenv

from agents.planner_agent import planner_agent
from agents.adk_runner import run_agent, safe_json_loads


load_dotenv()


async def main():
    planner_input = {
        "order_id": "ORD-TEST001",
        "order": {
            "customer_id": "C001",
            "item_name": "雞排",
            "quantity": 1,
            "preference": "酥一點"
        },
        "inventory_check": {
            "success": True,
            "item_name": "雞排",
            "required_qty": 1,
            "stock_qty": 10,
            "message": "雞排庫存足夠"
        },
        "equipment_check": {
            "success": True,
            "available_equipment": ["fryer_A", "robot_arm_1"],
            "message": "設備狀態正常"
        },
        "sop_check": {
            "success": True,
            "sop_id": "fried_chicken_standard",
            "item_name": "雞排",
            "preference_note": "依照顧客偏好，炸製時間增加 30 秒",
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
                    "duration_sec": 210
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
    }

    raw_result = await run_agent(planner_agent, planner_input)

    print("\n=== Raw Planner Output ===")
    print(raw_result)

    print("\n=== Parsed JSON ===")
    parsed = safe_json_loads(raw_result)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())