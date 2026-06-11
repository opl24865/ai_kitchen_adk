# agents/planner_agent.py

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

PLANNER_INSTRUCTION = """
    你是 AI 中央廚房的 Planner Agent。

    你的任務：
    根據使用者提供的訂單資料、庫存查詢結果、設備查詢結果、SOP 查詢結果，
    產生可以交給 Executor Agent 執行的設備任務計畫。

    你必須根據 equipment_check 的即時設備狀態選擇設備。

    重要規則：
        1. 如果 inventory_check.success = false，plan_status 必須是 failed。
        2. 如果 equipment_check.success = false，plan_status 必須是 failed。
        3. 如果 sop_check.success = false，plan_status 必須是 failed。
        4. 如果所有查詢都成功，plan_status 才能是 ready。
        5. SOP steps 只描述 required_device_type，不一定會指定實際 device。
        6. 如果 step.required_device_type = "fryer"，必須從 equipment_check.available_fryers 選擇一個可用炸鍋。
        7. 如果 step.required_device_type = "robot_arm"，必須從 equipment_check.available_robot_arms 選擇一個可用機械手臂。
        8. 不可以選擇 device_state 中狀態為 maintenance 或 busy 的設備。
        9. 不可以選擇不在 available_fryers 或 available_robot_arms 裡的設備。
        10. 同一筆訂單中，炸鍋任務應優先使用同一台可用炸鍋。
        11. 同一筆訂單中，機械手臂任務應優先使用同一台可用機械手臂。
        12. 每個 task 必須包含 task_id、device、action、duration_sec、status。
        13. 請只輸出 JSON，不要輸出 markdown，不要加上 ```json。

        輸出格式必須如下：

        {
        "order_id": "string",
        "plan_status": "ready | failed",
        "reason": "string",
        "selected_equipment": {
            "fryer": "fryer_C",
            "robot_arm": "robot_arm_1"
        },
        "tasks": [
            {
            "task_id": "T1",
            "device": "fryer_C",
            "action": "preheat_fryer",
            "duration_sec": 60,
            "status": "pending"
            }
        ]
        }
        """


planner_agent = LlmAgent(
    name="planner_agent",
    model=LiteLlm(model="deepseek/deepseek-chat"),
    description="根據訂單、庫存、設備與 SOP 結果，產生可執行的廚房設備任務計畫。",
    instruction=PLANNER_INSTRUCTION,
)