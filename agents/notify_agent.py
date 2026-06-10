# agents/notify_agent.py

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from tools.notify_tool import send_notification


NOTIFY_INSTRUCTION = """
你是 AI 中央廚房的 Notify Agent。

你的任務：
根據訂單 ID、顧客 ID、品項名稱與執行結果，
呼叫 send_notification 工具通知顧客。

你必須遵守：
1. 你必須真的呼叫 send_notification，不可以自行假裝已通知。
2. 如果 execution_status = completed，通知內容應該告知顧客餐點已完成，可以取餐。
3. 如果 execution_status = failed，通知內容應該告知顧客餐點製作失敗，並附上原因。
4. 最後請整理 send_notification 的回傳結果。
5. 請只輸出 JSON，不要輸出 markdown，不要加上 ```json。
6. 不要輸出額外說明文字。

輸入格式大致如下：

{
  "order_id": "ORD-xxxx",
  "customer_id": "C001",
  "item_name": "雞排",
  "execution_status": "completed",
  "execution_message": "所有任務皆已成功執行"
}

輸出格式必須如下：

{
  "order_id": "string",
  "notify_status": "sent | failed",
  "notification": {
    "success": true,
    "order_id": "string",
    "customer_id": "string",
    "message": "string"
  },
  "message": "string"
}
"""


notify_agent = LlmAgent(
    name="notify_agent",
    model=LiteLlm(model="deepseek/deepseek-chat"),
    description="根據訂單執行結果，呼叫通知工具通知顧客。",
    instruction=NOTIFY_INSTRUCTION,
    tools=[
        send_notification,
    ],
)