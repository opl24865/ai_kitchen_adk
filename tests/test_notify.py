# test_notify.py

import asyncio
import json
from dotenv import load_dotenv

from init_db import init_database
from agents.notify_agent import notify_agent
from agents.adk_runner import run_agent, safe_json_loads


load_dotenv()


async def main():
    init_database()

    notify_input = {
        "order_id": "ORD-TEST-NOTIFY001",
        "customer_id": "C001",
        "item_name": "雞排",
        "execution_status": "completed",
        "execution_message": "所有任務皆已成功執行"
    }

    raw_result = await run_agent(notify_agent, notify_input)

    print("\n=== Raw NotifyAgent Output ===")
    print(raw_result)

    print("\n=== Parsed JSON ===")
    parsed = safe_json_loads(raw_result)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())