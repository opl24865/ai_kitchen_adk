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
    """

    result = await run_agent_with_state(agent, user_input)
    return result["final_text"]


async def run_agent_with_state(agent, user_input: dict | str) -> dict:
    """
    執行一個 ADK agent，並回傳：
    - final_text
    - session_state

    session_state 會包含每個 agent 透過 output_key 存入的結果，例如：
    - data_query_state
    - planning_state
    - execution_state
    - final_workflow_result
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

    # 讀取 ADK session state
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    session_state = dict(session.state) if session and session.state else {}

    return {
        "final_text": final_text,
        "session_state": session_state,
        "user_id": user_id,
        "session_id": session_id,
    }


def safe_json_loads(text: str) -> dict[str, Any]:
    """
    從模型輸出中找出最大的合法 JSON object。

    可處理：
    - Markdown code fence
    - JSON 前後的說明文字
    - 模型輸出多個 JSON object
    """

    cleaned = text.strip()

    if not cleaned:
        raise ValueError("Agent returned empty output")

    decoder = json.JSONDecoder()
    candidates = []

    for index, character in enumerate(cleaned):
        if character != "{":
            continue

        try:
            value, end_index = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(value, dict):
            candidates.append({
                "value": value,
                "length": end_index,
                "start": index,
            })

    if not candidates:
        raise ValueError(
            f"Agent output does not contain a valid JSON object: "
            f"{cleaned[:300]}"
        )

    # 選擇內容最大的 JSON，避免誤選內層的空物件或前置 {}。
    largest_candidate = max(
        candidates,
        key=lambda candidate: candidate["length"],
    )

    return largest_candidate["value"]