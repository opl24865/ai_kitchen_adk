# test_executor.py

import asyncio
import json
from dotenv import load_dotenv

from init_db import init_database
from agents.executor_agent import executor_agent
from agents.adk_runner import run_agent, safe_json_loads


load_dotenv()


async def main():
    init_database()

    executor_input = {
        "order_id": "ORD-TEST-EXE001",
        "plan_status": "ready",
        "tasks": [
            {
                "task_id": "T1",
                "device": "fryer_A",
                "action": "preheat_fryer",
                "duration_sec": 60,
                "status": "pending"
            },
            {
                "task_id": "T2",
                "device": "robot_arm_1",
                "action": "place_food_into_fryer",
                "duration_sec": 20,
                "status": "pending"
            },
            {
                "task_id": "T3",
                "device": "fryer_A",
                "action": "fry",
                "duration_sec": 210,
                "status": "pending"
            },
            {
                "task_id": "T4",
                "device": "robot_arm_1",
                "action": "remove_food_from_fryer",
                "duration_sec": 20,
                "status": "pending"
            }
        ]
    }

    raw_result = await run_agent(executor_agent, executor_input)

    print("\n=== Raw ExecutorAgent Output ===")
    print(raw_result)

    print("\n=== Parsed JSON ===")
    parsed = safe_json_loads(raw_result)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())