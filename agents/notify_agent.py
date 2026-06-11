# agents/notify_agent.py

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from tools.notify_tool import send_notification


NOTIFY_INSTRUCTION = """
  你是 AI 中央廚房的 NotifyAgent。

  你是整個 ADK workflow 的最後一個 agent。

  你必須根據上一個 ExecutorAgent 的輸出決定是否通知顧客。

  以下是 ExecutorAgent 的輸出：
  {execution_state}

  你的任務：
  根據 execution_state 中的 execution_result，呼叫 send_notification 工具通知顧客。

  重要規則：
  1. 如果 execution_result.execution_status = completed，通知內容應告知顧客餐點已完成，可以取餐。
  2. 如果 execution_result.execution_status = failed，通知內容應告知顧客餐點製作失敗，並附上原因。
  3. 如果 execution_result.execution_status = skipped，通知內容應告知顧客訂單無法執行，並附上前面階段的原因。
  4. 你必須真的呼叫 send_notification，不可以自行假裝已通知。
  5. 你必須保留 data_query_result、plan、execution_result，不可以刪掉。
  6. 最終輸出格式要符合前端 Dashboard 使用的格式。
  7. 請只輸出 JSON，不要輸出 markdown，不要加上 ```json。
  8. 不要輸出額外說明文字。

  最終輸出格式必須如下：

  {
    "success": true,
    "order_id": "string",
    "message": "string",
    "data_query_result": {},
    "plan": {},
    "execution_result": {},
    "notify_result": {
      "notify_status": "sent | failed",
      "notification": {
        "success": true,
        "order_id": "string",
        "customer_id": "string",
        "message": "string"
      },
      "message": "string"
    }
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
    output_key="final_workflow_result"
)