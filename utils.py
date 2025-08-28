import logging
import requests
from config import SLACK_BOT_TOKEN, SLACK_API_URL

logger = logging.getLogger(__name__)

def get_all_members():
    logger.info("Slack 전체 멤버 조회 시작")
    base_url = f"{SLACK_API_URL}/users.list"
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    all_members = []
    cursor = None
    while True:
        params = {"limit": 1000}
        if cursor:
            params["cursor"] = cursor
        try:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"멤버 조회 실패: {e}")
            break
        data = response.json()
        if not data.get("ok", False):
            logger.error(f"Slack API 오류: {data.get('error')}")
            break
        all_members.extend(data.get("members", []))
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    logger.info(f"전체 멤버 수: {len(all_members)}")
    return all_members
