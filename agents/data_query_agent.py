# agents/data_query_agent.py

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from tools.inventory_tool import check_inventory
from tools.equipment_tool import check_equipment
from tools.sop_tool import get_sop


DATA_QUERY_INSTRUCTION = """
    你是 AI 中央廚房的 Data Query Agent。

    你的任務：
    根據使用者提供的訂單資料，呼叫工具查詢：
    1. 庫存是否足夠
    2. 設備是否可用
    3. SOP 是否存在

    你必須呼叫以下工具：
    - check_inventory
    - check_equipment
    - get_sop

    請注意：
    1. 你必須真的呼叫工具，不可以自行編造查詢結果。
    2. 即使庫存不足，也仍然可以查詢設備與 SOP，方便回傳完整資訊。
    3. 請把三個工具的結果整理成固定 JSON。
    4. check_equipment 的結果必須完整保留 available_equipment、available_fryers、available_robot_arms、device_state。
    5. 不可以改欄位名稱。
    6. 請只輸出 JSON，不要輸出 markdown，不要加上 ```json。
    7. 不要輸出額外說明文字。

    輸入格式大致如下：

    {
    "order_id": "ORD-xxxx",
    "customer_id": "C001",
    "item_name": "雞排",
    "quantity": 1,
    "preference": "酥一點"
    }

    輸出格式必須如下：

    {
    "order_id": "string",
    "query_status": "success | failed",
    "inventory_check": {
        "success": true,
        "item_name": "string",
        "required_qty": 1,
        "stock_qty": 10,
        "message": "string"
    },
    "equipment_check": {
        "success": true,
        "available_equipment": ["fryer_A", "robot_arm_1"],
        "message": "string"
    },
    "sop_check": {
        "success": true,
        "sop_id": "string",
        "item_name": "string",
        "preference_note": "string",
        "steps": [],
        "message": "string"
    },
    "message": "string"
    }
    """


data_query_agent = LlmAgent(
    name="data_query_agent",
    model=LiteLlm(model="deepseek/deepseek-chat"),
    description="查詢訂單所需的庫存、設備與 SOP 資訊。",
    instruction=DATA_QUERY_INSTRUCTION,
    tools=[
        check_inventory,
        check_equipment,
        get_sop,
    ],
)