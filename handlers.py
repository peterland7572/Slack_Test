from flask import request, jsonify
import json
from slack_api import (
    open_create_new_work_modal,
    open_create_jira_issue_create_modal,
    open_meeting_request_modal,
    post_message,
)
from utils import get_all_members
from config import CHANNEL_MAP, TARGET_CHANNEL, PREFIX_MAP, DEFAULT_CC_USER_IDS
import logging

logger = logging.getLogger(__name__)

def handle_slash_command():
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
        if not trigger_id:
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": "trigger_id가 없습니다. Slack 인터랙티브 명령에서만 동작합니다.",
                }
            )
        modal_resp = open_create_new_work_modal(trigger_id)
        if not modal_resp.get("ok"):
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": f"모달을 띄우는데 실패했습니다: {modal_resp.get('error')}",
                }
            )
        return "", 200

    elif command_text == "/jira_issue_create":
        if not trigger_id:
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": "trigger_id가 필요합니다. Slack 인터랙티브 명령에서만 동작합니다.",
                }
            )
        modal_resp = open_create_jira_issue_create_modal(trigger_id)
        if not modal_resp.get("ok"):
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": f"모달을 띄우는데 실패했습니다: {modal_resp.get('error')}",
                }
            )
        return "", 200

    elif command_text == "/모임요청":
        if not trigger_id:
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": "trigger_id가 필요합니다.",
                }
            )
        modal_resp = open_meeting_request_modal(trigger_id)
        if not modal_resp.get("ok"):
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": f"모달 열기에 실패했습니다: {modal_resp.get('error')}",
                }
            )
        return "", 200

    else:
        return jsonify(
            {
                "response_type": "ephemeral",
                "text": f"알 수 없는 커맨드({command_text})입니다.",
            }
        )


def handle_interactions():
    payload_str = request.form.get("payload")
    if not payload_str:
        return "", 400
    data = json.loads(payload_str)
    logger.info("인터랙션 이벤트 수신됨")

    if data.get("type") == "view_submission":
        callback_id = data.get("view", {}).get("callback_id")
        state_values = data["view"]["state"]["values"]

        if callback_id == "work_create_modal":
            work_type = state_values["work_type"]["work_type_select"]["selected_option"]["value"]
            title = state_values["title"]["title_input"]["value"]
            content = state_values["content"]["content_input"]["value"]
            plan_url = state_values.get("plan_url", {}).get("plan_url_input", {}).get("value", "")
            assignee_user_id = state_values["assignee"]["assignee_input"]["selected_user"]
            start_date = state_values.get("start_date", {}).get("start_date_input", {}).get("selected_date", "")
            end_date = state_values.get("end_date", {}).get("end_date_input", {}).get("selected_date", "")
            period = f"{start_date} ~ {end_date}" if start_date and end_date else "기간 미설정"
            prefix = PREFIX_MAP.get(work_type, "")

            blocks = [
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*<{prefix}업무 요청>*"},
                },
                {"type": "section", "fields": [{"type": "mrkdwn", "text": f"- *제목:*\n{title}"}]},
                {"type": "section", "fields": [{"type": "mrkdwn", "text": f"- *내용:*\n{content}"}]},
                {"type": "section", "fields": [{"type": "mrkdwn", "text": f"- *기간:*\n{period}"}]},
                {
                    "type": "section",
                    "fields": [{"type": "mrkdwn", "text": f"- *기획서:*\n{plan_url if plan_url else '없음'}"}],
                },
                {
                    "type": "section",
                    "fields": [{"type": "mrkdwn", "text": f"- *담당자:*\n<@{assignee_user_id}>"}],
                },
                {"type": "divider"},
            ]

            target_channel = CHANNEL_MAP.get(work_type, TARGET_CHANNEL)
            response = post_message(target_channel, blocks=blocks, text=f"{prefix}업무 요청: {title}")
            if response.status_code == 200:
                return jsonify({"response_action": "clear"})
            else:
                return jsonify(
                    {"response_action": "errors", "errors": {"title": "메시지 전송 실패"}}
                )

        elif callback_id == "meeting_review_modal":
            title = state_values["title"]["title_input"]["value"]
            document = state_values.get("document", {}).get("document_input", {}).get("value", "")
            content = state_values.get("content", {}).get("content_input", {}).get("value", "")
            place = state_values.get("place", {}).get("place_input", {}).get("value", "")

            assignees = state_values["assignee"]["assignee_input"].get("selected_users", [])
            assignee_mentions = " ".join(f"<@{uid}>" for uid in assignees) if assignees else "없음"

            cc_mentions = " ".join(f"<@{uid}>" for uid in DEFAULT_CC_USER_IDS)

            lines = [
                "**[기획 리뷰 요청드립니다.]**",
                f"제목: << {title} >>",
                f"기획서: {document if document else '없음'}",
                f"내용: {content if content else '없음'}",
                f"장소: {place if place else '미정'}",
                f"담당자: {assignee_mentions}",
                f"참조: {cc_mentions}",
            ]
            msg_text = "\n".join(lines)

            response = post_message(MEETING_REQUEST_CHANNEL, text=msg_text)
            if response.status_code == 200:
                return jsonify({"response_action": "clear"})
            else:
                return jsonify(
                    {"response_action": "errors", "errors": {"title": "메시지 전송 실패"}}
                )

    return "", 200
