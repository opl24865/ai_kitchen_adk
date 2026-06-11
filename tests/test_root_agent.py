# test_root_agent.py

import asyncio
import json
from dotenv import load_dotenv

from init_db import init_database
from agents.root_agent import root_agent
from agents.adk_runner import run_agent, safe_json_loads


load_dotenv()


async def main():
    # 每次測試前初始化 SQLite
    init_database()

    workflow_input = {
        "order_id": "ORD-ROOT-TEST001",
        "customer_id": "C001",
        "item_name": "雞排",
        "quantity": 1,
        "preference": "酥一點"
    }

    raw_result = await run_agent(root_agent, workflow_input)

    print("\n=== Raw RootAgent Output ===")
    print(raw_result)

    print("\n=== Parsed JSON ===")
    parsed = safe_json_loads(raw_result)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))

    print("\n=== Summary ===")
    print("success:", parsed.get("success"))
    print("order_id:", parsed.get("order_id"))
    print("message:", parsed.get("message"))

    plan = parsed.get("plan", {})
    selected_equipment = plan.get("selected_equipment", {})

    print("selected fryer:", selected_equipment.get("fryer"))
    print("selected robot_arm:", selected_equipment.get("robot_arm"))

    execution_result = parsed.get("execution_result", {})
    print("execution_status:", execution_result.get("execution_status"))

    notify_result = parsed.get("notify_result", {})
    print("notify_status:", notify_result.get("notify_status"))


if __name__ == "__main__":
    asyncio.run(main())