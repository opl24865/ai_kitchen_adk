# agents/batch_execution_agent.py

from google.adk.agents import LlmAgent
from config import MODEL
from tools.robot_tool import execute_robot_task



BATCH_EXECUTION_INSTRUCTION = """
    你是 AI 中央廚房的 BatchExecutionAgent。

    你是多筆訂單 ADK workflow 的第四個 agent。

    以下是 BatchPlanningAgent 的輸出：
    {batch_planning_state}

    你的任務：
    1. 根據 execution_order 依序執行所有 decision = "auto_execute" 的訂單。
    2. 不只執行第一筆，而是要執行 execution_order 中的所有訂單。
    3. wait_equipment 的訂單不執行設備任務。
    4. escalate_inventory / escalate_sop / escalate_equipment / manual_review 的訂單不執行設備任務。
    5. 將每筆訂單的 execution_result 填回 orders。
    6. 保留 batch_summary、equipment_snapshot、batch_decision_reason、execution_order。

    你可以使用以下 tool：
    - execute_robot_task

    執行規則：
    1. 只執行 decision = "auto_execute" 的訂單。
    2. auto_execute 訂單必須依照 execution_order 的 sequence 由小到大執行。
    3. 每個 auto_execute 訂單要根據 sop_check.steps 產生設備任務。
    4. 如果 step.required_device_type = "fryer"，device 使用 assigned_equipment.fryer。
    5. 如果 step.required_device_type = "robot_arm"，device 使用 assigned_equipment.robot_arm。
    6. 每一個 SOP step 都要呼叫一次 execute_robot_task。
    7. 不可以合併 SOP step。
    8. 不可以跳過 execution_order 中的 auto_execute 訂單。
    9. 如果某筆訂單任一 task 失敗，該訂單 execution_status = "failed"，但仍然要繼續處理下一筆 auto_execute 訂單。
    10. 如果某筆訂單全部 task 成功，該訂單 execution_status = "completed"。
    11. 沒有執行的訂單 execution_status = "skipped"。
    12. 不可以刪除任何訂單。
    13. 不可以修改 order_id。
    14. 請只輸出 JSON。
    15. 不要輸出 markdown。
    16. 不要加上 ```json。
    17. 不要輸出額外說明文字。

    輸出格式必須如下：

    {
    "batch_id": "BATCH-xxxx",
    "scenario": "custom_batch",
    "workflow_status": "batch_execution_completed",
    "batch_order_context": {},
    "equipment_snapshot": {},
    "batch_resource_assessment": {},
    "batch_summary": {},
    "batch_decision_reason": "string",
    "execution_order": [],
    "orders": [
        {
        "order_id": "BATCH-xxxx-ORD-001",
        "customer_id": "C001",
        "item_name": "雞排",
        "quantity": 1,
        "preference": "酥一點",
        "priority": "normal",
        "preference_intent": ["extra_crispy"],
        "inventory_check": {},
        "sop_check": {},
        "resource_status": "resource_ready",
        "decision": "auto_execute",
        "decision_reason": "string",
        "execution_sequence": 2,
        "assigned_equipment": {
            "fryer": "fryer_A",
            "robot_arm": "robot_arm_1"
        },
        "customer_impact": "delay",
        "requires_internal_alert": false,
        "alert_type": null,
        "target_role": null,
        "execution_result": {
            "execution_status": "completed | failed | skipped",
            "results": [],
            "message": "string"
        }
        }
    ]
    }
    """

batch_execution_agent = LlmAgent(
    name="batch_execution_agent",
    model=MODEL,
    description="執行多筆訂單中被 BatchPlanningAgent 選為 auto_execute 的訂單設備任務。",
    instruction=BATCH_EXECUTION_INSTRUCTION,
    tools=[
        execute_robot_task,
    ],
    output_key="batch_execution_state",
)