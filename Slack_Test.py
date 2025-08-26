import os
import logging
import json
import requests
from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s")

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
if not SLACK_BOT_TOKEN:
    raise ValueError("Slack Bot Token이 설정되지 않았습니다. 환경변수 확인 필요")

SLACK_API_URL = "https://slack.com/api"
TARGET_CHANNEL = "C09C4S28412" # #업무생성채널  # 메시지 보낼 채널을 변경

app = Flask(__name__)

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
            logger.error("멤버 조회 실패: %s", str(e))
            break
        data = response.json()
        if not data.get("ok", False):
            logger.error("Slack API 오류: %s", data.get("error"))
            break
        all_members.extend(data.get("members", []))
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    logger.info("전체 멤버 수: %d", len(all_members))
    return all_members

def open_create_new_work_modal(trigger_id):
    modal_view = {
        "type": "modal",
        "callback_id": "work_create_modal",
        "title": {"type": "plain_text", "text": "새 업무 등록"},
        "submit": {"type": "plain_text", "text": "등록"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {"type": "input", "block_id": "title", "element": {"type": "plain_text_input", "action_id": "title_input"}, "label": {"type": "plain_text", "text": "제목"}},
            {"type": "input", "block_id": "content", "element": {"type": "plain_text_input", "action_id": "content_input", "multiline": True}, "label": {"type": "plain_text", "text": "내용"}},
            {"type": "input", "block_id": "period", "element": {"type": "plain_text_input", "action_id": "period_input"}, "label": {"type": "plain_text", "text": "기간"}},
            {"type": "input", "block_id": "plan_url", "optional": True, "element": {"type": "plain_text_input", "action_id": "plan_url_input"}, "label": {"type": "plain_text", "text": "기획서 (URL)"}},
            {"type": "input", "block_id": "assignee", "element": {"type": "plain_text_input", "action_id": "assignee_input"}, "label": {"type": "plain_text", "text": "담당자 (실명)"}}
        ]
    }
    payload = {"trigger_id": trigger_id, "view": modal_view}
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json; charset=utf-8"}
    response = requests.post(f"{SLACK_API_URL}/views.open", headers=headers, json=payload)
    logger.info("Modal open response: %s", response.text)
    return response.json()


@app.before_request
def log_request_info():
    logger.info(f"Received request: {request.method} {request.path} from {request.remote_addr}")

@app.errorhandler(404)
def page_not_found(e):
    logger.warning(f"404 Not Found: {request.method} {request.path} from {request.remote_addr}")
    return "요청한 URL이 존재하지 않습니다.", 404


@app.route("/slack/command", methods=["POST"])
def slash_command_router():
    data = request.form.to_dict()
    command_text = data.get("command")
    user_name = data.get("user_name", "Guest")
    trigger_id = data.get("trigger_id")
    logger.info(f"Slash Command 요청: {data}")

    if command_text == "/hi":
        members = get_all_members()
        mentions = [f"<@{m.get('id')}> HI" for m in members if not m.get("deleted") and not m.get("is_bot")]
        MAX_CHARS = 3000
        mentions_text = "\n".join(mentions)
        if len(mentions_text) > MAX_CHARS:
            mentions_text = mentions_text[:MAX_CHARS] + "\n... (이하 생략)"
        response_text = f"hi {user_name}! 전체 멤버에게 인사합니다:\n{mentions_text}"
        logger.info(f"응답 메시지 길이: {len(response_text)}")
        return jsonify({"response_type": "in_channel", "text": response_text})

    elif command_text == "/create_new_work":
        logger.info(f"/create_new_work")
        if trigger_id:
            logger.info(f"/create_new_work1")
            modal_resp = open_create_new_work_modal(trigger_id)
            logger.info(f"/create_new_work2")
            if not modal_resp.get("ok"):
                logger.error(f"Modal open 실패: {modal_resp.get('error')}")
                return jsonify({"response_type": "ephemeral", "text": f"모달을 띄우는 데 실패했습니다: {modal_resp.get('error')}"})
            return "", 200
        return jsonify({"response_type": "ephemeral", "text": "trigger_id가 없습니다. Slack 인터랙티브 명령에서만 동작합니다."})

    return jsonify({"response_type": "ephemeral", "text": f"알 수 없는 커맨드({command_text})입니다."})

@app.route("/slack/interactions", methods=["POST"])
def interactions():
    logger.info(f"interactions")
    payload_str = request.form.get("payload")
    logger.info(f"interactions1")
    if not payload_str:
        return "", 400
    data = json.loads(payload_str)
    logger.info(f"interactions2")
    if data.get("type") == "view_submission" and data.get("view", {}).get("callback_id") == "work_create_modal":
        state_values = data["view"]["state"]["values"]
        title = state_values["title"]["title_input"]["value"]
        content = state_values["content"]["content_input"]["value"]
        period = state_values["period"]["period_input"]["value"]
        plan_url = state_values["plan_url"]["plan_url_input"].get("value", "")
        assignee = state_values["assignee"]["assignee_input"]["value"]

        message = (
            f"*새 업무 등록*\n"
            f"• 제목: {title}\n"
            f"• 내용: {content}\n"
            f"• 기간: {period}\n"
            f"• 기획서: {plan_url}\n"
            f"• 담당자: {assignee}"
        )

        headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-type": "application/json"}
        payload = {"channel": TARGET_CHANNEL, "text": message}
        resp = requests.post(f"{SLACK_API_URL}/chat.postMessage", headers=headers, json=payload)
        logger.info(f"chat.postMessage status: {resp.status_code}, response:{resp.text}")

        # modal 닫힘 위해 빈 json 응답
        return jsonify({})

    return "", 200

if __name__ == "__main__":
    logging.info("🚀 Flask Slack Command Server Started on port 5000")
    app.run(host="0.0.0.0", port=5000)
