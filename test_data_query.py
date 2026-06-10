# test_data_query.py

import asyncio
import json
from dotenv import load_dotenv

from init_db import init_database
from agents.data_query_agent import data_query_agent
from agents.adk_runner import run_agent, safe_json_loads


load_dotenv()


async def main():
    # 每次測試前重建 DB，避免資料狀態混亂
    init_database()

    order_input = {
        "order_id": "ORD-TEST-DQ001",
        "customer_id": "C001",
        "item_name": "雞排",
        "quantity": 1,
        "preference": "酥一點"
    }

    raw_result = await run_agent(data_query_agent, order_input)

    print("\n=== Raw DataQueryAgent Output ===")
    print(raw_result)

    print("\n=== Parsed JSON ===")
    parsed = safe_json_loads(raw_result)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())