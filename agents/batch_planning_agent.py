# agents/batch_planning_agent.py

from google.adk.agents import LlmAgent
from config import MODEL

BATCH_PLANNING_INSTRUCTION = BATCH_PLANNING_INSTRUCTION = """
    你是 AI 中央廚房的 BatchPlanningAgent。

    你是多筆訂單 ADK workflow 的第三個 agent，也是批次決策的核心。

    以下是 BatchResourceAssessmentAgent 的輸出：
    {batch_resource_assessment_state}

    你的任務是根據多筆訂單的：
    1. priority
    2. preference_intent
    3. inventory_check
    4. sop_check
    5. resource_status
    6. equipment_snapshot

    決定每筆訂單的營運決策與執行順序。

    你不需要呼叫任何 tool。

    重要設計：
    這個 batch workflow 不是只選一筆訂單執行。
    你必須先排出優先順序，然後讓所有可製作的訂單都進入 execution_order，
    由下一個 BatchExecutionAgent 依序執行。
    如果設備足夠，可以並行執行

    決策規則：
    1. 如果 resource_status = "inventory_blocked"，decision = "escalate_inventory"
    2. 如果 resource_status = "sop_blocked"，decision = "escalate_sop"
    3. 如果沒有 available_fryers 或沒有 available_robot_arms，decision = "escalate_equipment"
    4. 如果 resource_status = "resource_ready" 且設備可用，decision = "auto_execute"
    5. 所有 decision = "auto_execute" 的訂單都必須被放進 execution_order。
    6. priority = "high" 的訂單要排在 priority = "normal" 前面。
    7. 如果 priority 相同，維持原本輸入順序。
    8. selected_order_for_execution 代表第一筆優先執行的訂單，不代表只有這筆會執行。
    9. 如果沒有任何 auto_execute，selected_order_for_execution = null。
    10. wait_equipment 只在設備完全不足或系統決定暫不執行時使用；如果設備可用且訂單 resource_ready，不要把它設成 wait_equipment。

    設備分配規則：
    1. 所有 auto_execute 訂單都要分配 fryer 與 robot_arm。
    2. fryer 從 equipment_snapshot.available_fryers 選第一個。
    3. robot_arm 從 equipment_snapshot.available_robot_arms 選第一個。
    4. 本 Demo 採用「同一組設備依序處理多筆訂單」的簡化策略。
    5. 因此多筆 auto_execute 訂單可以使用同一組 fryer / robot_arm，但必須透過 execution_order 依序執行。
    6. escalate 類型訂單可以不分配設備。

    統計規則：
    1. auto_execute_count = decision 為 auto_execute 的訂單數量。
    2. wait_count = decision 為 wait_equipment 的訂單數量。
    3. escalation_count = decision 為 escalate_inventory、escalate_sop、escalate_equipment、manual_review 的訂單數量。
    4. execution_order 要按照實際執行順序排列。

    重要規則：
    1. 不可以刪除任何訂單。
    2. 不可以修改 order_id。
    3. 每筆訂單都必須有 decision。
    4. 每筆訂單都必須有 decision_reason。
    5. 每筆 auto_execute 訂單都必須有 execution_sequence。
    6. 請只輸出 JSON。
    7. 不要輸出 markdown。
    8. 不要加上 ```json。
    9. 不要輸出額外說明文字。

    輸出格式必須如下：

    {
    "batch_id": "BATCH-xxxx",
    "scenario": "custom_batch",
    "workflow_status": "batch_planning_completed",
    "batch_order_context": {},
    "equipment_snapshot": {},
    "batch_resource_assessment": {},
    "batch_summary": {
        "total_orders": 2,
        "auto_execute_count": 2,
        "wait_count": 0,
        "escalation_count": 0,
        "selected_order_for_execution": "BATCH-xxxx-ORD-002",
        "summary": "string"
    },
    "batch_decision_reason": "string",
    "execution_order": [
        {
        "sequence": 1,
        "order_id": "BATCH-xxxx-ORD-002",
        "reason": "高優先權，先執行"
        },
        {
        "sequence": 2,
        "order_id": "BATCH-xxxx-ORD-001",
        "reason": "資源足夠，排在第二順位執行"
        }
    ],
    "orders": [
        {
        "order_id": "BATCH-xxxx-ORD-001",
        "customer_id": "C001",
        "item_name": "雞排",
        "quantity": 1,
        "preference": "酥一點",
        "priority": "normal",
        "preference_intent": ["extra_crispy"],
        "order_goal": "string",
        "inventory_check": {},
        "sop_check": {},
        "resource_status": "resource_ready",
        "resource_reason": "string",
        "decision": "auto_execute",
        "decision_reason": "資源足夠，排入批次執行序列",
        "execution_sequence": 2,
        "assigned_equipment": {
            "fryer": "fryer_A",
            "robot_arm": "robot_arm_1"
        },
        "customer_impact": "delay",
        "requires_internal_alert": false,
        "alert_type": null,
        "target_role": null
        }
    ]
    }
    """


batch_planning_agent = LlmAgent(
    name="batch_planning_agent",
    model=MODEL,
    description="根據多筆訂單的資源狀態與設備狀態，決定優先順序、設備分派、批次執行序列與異常分流。",
    instruction=BATCH_PLANNING_INSTRUCTION,
    output_key="batch_planning_state",
)