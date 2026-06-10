# agents/adk_runner.py
import re
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
                final_text = event.content.parts[0].text

    return final_text


def safe_json_loads(text: str) -> dict[str, Any]:
    if text is None:
        raise ValueError("模型回傳 None，無法解析 JSON")

    cleaned = text.strip()

    if not cleaned:
        raise ValueError("模型回傳空字串，無法解析 JSON")

    # 第一層：如果本來就是合法 JSON，直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 第二層：處理 markdown code block
    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 第三層：最後才嘗試從文字中抓 JSON object
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        cleaned = match.group(0)
        return json.loads(cleaned)

    raise ValueError(f"找不到可解析的 JSON：{repr(text)}")