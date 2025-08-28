import os

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN","12345")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET","12345")




SLACK_API_URL = "https://slack.com/api"

JIRA_URL = os.environ.get("JIRA_URL","https://jira.smilegate.net")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN","12345")

PROJECT_KEY = "SGETSQA"
ISSUE_TYPE = "QA 이슈"

# 업무 유형 → 슬랙 채널 ID 매핑 (예시, 실제 채널 ID로 변경 필요)
CHANNEL_MAP = {
    "client_task": "C09C4S28412",
    "planning_task": "C09C4S28412",
    "qa_task": "C09C4S28412",
    "character_task": "C09C4S28412",
    "background_task": "C09C4S28412",
    "concept_task": "C09C4S28412",
    "animation_task": "C09C4S28412",
    "effect_task": "C09C4S28412",
    "art_task": "C09C4S28412",
    "server_task": "C09C4S28412",
    "ta_task": "C09C4S28412",
    "test_task": "C09C4S28412",
    "ui_task": "C09C4S28412"
}

TARGET_CHANNEL = CHANNEL_MAP["client_task"]

WORK_TYPE_OPTIONS = {
    "client_task": "클라",
    "planning_task": "기획",
    "qa_task": "품질",
    "character_task": "캐릭터",
    "background_task": "배경",
    "concept_task": "컨셉",
    "animation_task": "애니",
    "effect_task": "VFX",
    "art_task": "아트",
    "server_task": "서버",
    "ta_task": "TA",
    "test_task": "테스트",
    "ui_task": "UI"
}

PREFIX_MAP = {k: f"{v}-" for k, v in WORK_TYPE_OPTIONS.items()}

MEETING_REQUEST_CHANNEL = "C09BZMY6DEK"

DEFAULT_CC_USER_IDS = ["U08KGSM1KUH","U08KGSM1KUH","U08KGSM1KUH"]
