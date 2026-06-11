import os
from dotenv import load_dotenv

load_dotenv()

DEVICE_STATUS_URL = os.getenv(
    "DEVICE_STATUS_URL",
    "http://127.0.0.1:9000/device/status"
)

ROBOT_SERVER_URL = os.getenv(
    "ROBOT_SERVER_URL",
    "http://127.0.0.1:9000"
)