# agents/adk_runner.py

import json
import uuid
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


APP_NAME = "ai_kitchen_adk_mvp"


async def run_agent(agent, user_input: dict | str) -> str:
    """
    執行一個 ADK agent，並回傳最後的文字輸出。
    這個 function 可用於 LlmAgent，也可用於 SequentialAgent root_agent。
    """

    session_service = InMemorySessionService()

    user_id = "demo_user"
    session_id = f"session_{uuid.uuid4().hex[:8]}"

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=session_service,
    )

    if isinstance(user_input, dict):
        input_text = json.dumps(user_input, ensure_ascii=False, indent=2)
    else:
        input_text = user_input

    content = types.Content(
        role="user",
        parts=[
            types.Part(text=input_text)
        ]
    )

    final_text = ""

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_text = event.content.parts[0].text or ""

    return final_text


def safe_json_loads(text: str) -> dict[str, Any]:
    """
    防止模型偶爾輸出 ```json 或額外文字。
    這裡會盡量抓出第一個 JSON object。
    """

    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    # 如果模型前後多輸出文字，嘗試擷取第一個 JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    return json.loads(cleaned)