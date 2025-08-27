import os
import logging
import json
import base64
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_API_URL = "https://slack.com/api"


# 업무 유형 → 슬랙 채널 ID 매핑 (예시, 실제 채널 ID로 변경 필요)
CHANNEL_MAP = {
    "client_task": "C1234567890",
    "planning_task": "C2345678901",
    "qa_task": "C3456789012",
    "character_task": "C4567890123",
    "background_task": "C5678901234",
    "concept_task": "C6789012345",
    "animation_task": "C7890123456",
    "effect_task": "C8901234567",
    "art_task": "C9012345678",
    "server_task": "C0123456789",
    "ta_task": "C1123456789",
    "test_task": "C2123456789",
    "ui_task": "C3123456789"
}

# 기본 채널을 client_task 채널로 지정
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
            {
                "type": "input",
                "block_id": "work_type",
                "label": {"type": "plain_text", "text": "업무 유형"},
                "element": {
                    "type": "static_select",
                    "action_id": "work_type_select",
                    "placeholder": {"type": "plain_text", "text": "선택"},
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": v},
                            "value": k,
                        } for k, v in WORK_TYPE_OPTIONS.items()
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "title",
                "element": {"type": "plain_text_input", "action_id": "title_input"},
                "label": {"type": "plain_text", "text": "제목"},
            },
            {
                "type": "input",
                "block_id": "content",
                "element": {
                    "type": "plain_text_input",
                    "multiline": True,
                    "action_id": "content_input",
                },
                "label": {"type": "plain_text", "text": "내용"},
            },
            {
                "type": "input",
                "block_id": "period",
                "element": {"type": "plain_text_input", "action_id": "period_input"},
                "label": {"type": "plain_text", "text": "기간"},
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "plan_url",
                "element": {"type": "plain_text_input", "action_id": "plan_url_input"},
                "label": {"type": "plain_text", "text": "기획서 (URL)"},
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "assignee",
                "element": {
                    "type": "users_select",
                    "action_id": "assignee_input",
                    "placeholder": {"type": "plain_text", "text": "담당자를 선택하세요"},
                },
                "label": {"type": "plain_text", "text": "담당자 (실명)"},
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {"trigger_id": trigger_id, "view": modal_view}
    response = requests.post(f"{SLACK_API_URL}/views.open", headers=headers, json=payload)
    logger.info(f"모달 열기 응답: {response.text}")
    return response.json()


@app.route("/slack/command", methods=["POST"])
def slash_command_router():
    data = request.form.to_dict()
    command_text = data.get("command")
    user_name = data.get("user_name", "Guest")
    trigger_id = data.get("trigger_id")
    logger.info(f"Slash Command 요청: {data}")

    if command_text == "/hi":
        members = get_all_members()
        mentions = [
            f"<@{m.get('id')}> HI"
            for m in members
            if not m.get("deleted") and not m.get("is_bot")
        ]
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
                return jsonify(
                    {
                        "response_type": "ephemeral",
                        "text": f"모달을 띄우는 데 실패했습니다: {modal_resp.get('error')}",
                    }
                )
            return "", 200
        return jsonify(
            {
                "response_type": "ephemeral",
                "text": "trigger_id가 없습니다. Slack 인터랙티브 명령에서만 동작합니다.",
            }
        )

    return jsonify(
        {"response_type": "ephemeral", "text": f"알 수 없는 커맨드({command_text})입니다."}
    )


@app.route("/slack/interactions", methods=["POST"])
def interactions():
    payload_str = request.form.get("payload")
    if not payload_str:
        return "", 400
    data = json.loads(payload_str)

    if data.get("type") == "view_submission" and data.get("view", {}).get("callback_id") == "work_create_modal":
        state_values = data["view"]["state"]["values"]

        work_type = state_values["work_type"]["work_type_select"]["selected_option"]["value"]
        title = state_values["title"]["title_input"]["value"]
        content = state_values["content"]["content_input"]["value"]
        period = state_values["period"]["period_input"]["value"]
        plan_url = state_values["plan_url"]["plan_url_input"].get("value", "")
        assignee_user_id = state_values["assignee"]["assignee_input"]["selected_user"]

        title_with_prefix = f"{PREFIX_MAP.get(work_type, '')}{title}"
        mention_text = f"<@{assignee_user_id}>"
        text_message = (
            f"*업무 요청*\n"
            f"• 유형: {WORK_TYPE_OPTIONS.get(work_type, '')}\n"
            f"• 제목: {title_with_prefix}\n"
            f"• 내용: {content}\n"
            f"• 기간: {period}\n"
            f"• 기획서: {plan_url if plan_url else '없음'}\n"
            f"• 담당자: {mention_text}"
        )

        headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json"}
        target_channel = CHANNEL_MAP.get(work_type, TARGET_CHANNEL)
        payload = {"channel": target_channel, "text": text_message}

        response = requests.post(f"{SLACK_API_URL}/chat.postMessage", headers=headers, json=payload)
        if response.status_code == 200:
            logger.info("Slack 메시지 전송 성공")
            return jsonify({"response_action": "clear"})
        else:
            logger.error(f"Slack 메시지 전송 실패: {response.text}")
            return jsonify({"response_action": "errors", "errors": {"title": "메시지 전송 실패"}})

    return "", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
