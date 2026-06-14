import os
from dotenv import load_dotenv
from google.adk.models.lite_llm import LiteLlm
load_dotenv()

DEVICE_STATUS_URL = os.getenv(
    "DEVICE_STATUS_URL",
    "http://127.0.0.1:9000/device/status"
)

ROBOT_SERVER_URL = os.getenv(
    "ROBOT_SERVER_URL",
    "http://127.0.0.1:9000"
)

USE_ADK_WEB_SAFE_MODEL = False

if USE_ADK_WEB_SAFE_MODEL:
    ㄊ = "gemini-2.5-flash"
else:
    MODEL = LiteLlm(
        model="deepseek/deepseek-chat",
    )