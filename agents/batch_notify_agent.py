# agents/batch_notify_agent.py

from google.adk.agents import LlmAgent

from tools.alert_tool import send_internal_alert

from config import MODEL

BATCH_NOTIFY_INSTRUCTION = """
    你是 AI 中央廚房的 BatchNotificationAgent。

    你是多筆訂單 ADK workflow 的最後一個 agent。

    以下是 BatchExecutionAgent 的輸出：
    {batch_execution_state}

    你的任務：
    1. 根據每筆訂單的 decision 決定是否需要通知顧客、補貨人員、維護人員、營運人員或技術人員。。
    2. 對需要內部通知的訂單呼叫 send_internal_alert。
    3. 整理最後要回傳給前端的 batch decision JSON。
    4. 保留每筆訂單的 execution_result。
    5. 本階段主要做內部異常分流與結果整理。

    你可以使用以下 tool：
    - send_internal_alert

    內部通知規則：
    1. decision = "escalate_inventory"
    - alert_type = "inventory_shortage"
    - target_role = "kitchen_staff"

    2. decision = "escalate_sop"
    - alert_type = "sop_missing"
    - target_role = "operation_staff"

    3. decision = "escalate_equipment"
    - alert_type = "equipment_unavailable"
    - target_role = "maintenance_staff"

    4. decision = "manual_review"
    - alert_type = "manual_review"
    - target_role = "operation_staff"

    5. execution_result.execution_status = "failed"
    - alert_type = "execution_failed"
    - target_role = "operation_staff"

    6. decision = "auto_execute" 且 execution_result.execution_status = "completed"
    - 不需要呼叫 send_internal_alert
    - internal_alert = {}

    7. decision = "wait_equipment"
    - 不需要呼叫 send_internal_alert
    - internal_alert = {}

    重要規則：
    1. 只有需要內部通知的訂單才呼叫 send_internal_alert。
    2. 不可以刪除任何訂單。
    3. 不可以修改 order_id。
    4. 最終 success 必須是 true，只要 batch workflow 有完成決策與執行階段。
    5. 如果有 escalation 訂單，不代表 success = false，因為 Agent 已經成功完成分流決策。
    6. batch_summary、equipment_snapshot、batch_decision_reason 必須保留。
    7. 每筆訂單都必須保留 decision、decision_reason 與 execution_result。
    8. 每筆訂單都要有 internal_alert 欄位。
    9. 請只輸出 JSON。
    10. 不要輸出 markdown。
    11. 不要加上 ```json。
    12. 不要輸出額外說明文字。

    輸出格式必須如下：

    {
    "success": true,
    "batch_id": "BATCH-xxxx",
    "scenario": "custom_batch",
    "workflow_status": "batch_notification_completed",
    "message": "string",
    "batch_summary": {},
    "equipment_snapshot": {},
    "batch_decision_reason": "string",
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
        "assigned_equipment": {
            "fryer": "fryer_A",
            "robot_arm": "robot_arm_1"
        },
        "customer_impact": "none",
        "execution_result": {
            "execution_status": "completed",
            "results": [],
            "message": "string"
        },
        "internal_alert": {}
        }
    ]
    }
    """


batch_notify_agent = LlmAgent(
    name="batch_notification_agent",
    model=MODEL,
    description="根據批次執行結果通知內部人員，並整理最終批次決策結果。",
    instruction=BATCH_NOTIFY_INSTRUCTION,
    tools=[
        send_internal_alert,
    ],
    output_key="batch_final_state",
)