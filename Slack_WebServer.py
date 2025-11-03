import os
import logging
import json
import requests
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_API_URL = "https://slack.com/api"
conversations_client = WebClient(token=SLACK_BOT_TOKEN)


JIRA_URL = os.environ.get("JIRA_URL")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")


# 업무 유형 → 슬랙 채널 ID 매핑 (예시, 실제 채널 ID로 변경 필요)
CHANNEL_MAP = {
    "client_task": "C09QEGZ4W92",
    "planning_task": "C09PVGS3U31",
    "qa_task": "C09Q4JY193M",
    "character_task": "C09Q7H0QB0D",
    "background_task": "C09Q4J03Y1Z",
    "concept_task": "C09Q4JJ1AM9",
    "animation_task": "C09QB1AJBCJ",
    "effect_task": "C09QPTJ3KMX",
#   "art_task": "C09C4S28412", # 주석처리
    "server_task": "C09QB1H753L",
    "ta_task": "C09Q7H3QA1K",
    "test_task": "C09PWF7SGKH",
    "ui_task": "C09QPTE5BSM"
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
#   "art_task": "아트", # 주석처리
    "server_task": "서버",
    "ta_task": "TA",
    "test_task": "테스트",
    "ui_task": "UI"
}

PREFIX_MAP = {k: f"{v}-" for k, v in WORK_TYPE_OPTIONS.items()}

# 기획리뷰 채널
MEETING_REQUEST_CHANNEL = "C09QF1TKQQ4"

DEFAULT_CC_USER_IDS = ["U09Q5HLF3R6","U09Q13V4E75","U09Q7GTU0BU"]# 예: 홍석기,노승한,김주현 PM님들

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

def open_create_new_work_modal(trigger_id, user_id):
    modal_view = {
        "type": "modal",
        "callback_id": "work_create_modal",
        "title": {"type": "plain_text", "text": "새 업무 요청"},
        "submit": {"type": "plain_text", "text": "등록"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "work_type",
                "label": {"type": "plain_text", "text": "담당 부서"},
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
                "block_id": "start_date",
                "optional": True,
                "element": {
                    "type": "datepicker",
                    "action_id": "start_date_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "시작일 선택"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "시작일"
                }
            },
            {
                "type": "input",
                "block_id": "end_date",
                "optional": True,
                "element": {
                    "type": "datepicker",
                    "action_id": "end_date_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "종료일 선택"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "종료일"
                }
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
                    "initial_user": user_id,  # 작성자를 기본 선택
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

def open_create_jira_issue_create_modal(trigger_id):
    modal_view = {
        "type": "modal",
        "callback_id": "jira_issue_create_modal",
        "title": {"type": "plain_text", "text": "Jira 이슈 생성"},
        "submit": {"type": "plain_text", "text": "생성"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "summary",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "summary_input",
                    "placeholder": {"type": "plain_text", "text": "이슈 제목 입력"}
                },
                "label": {"type": "plain_text", "text": "제목"},
                "optional": False
            },
            {
                "type": "input",
                "block_id": "description",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "이슈 상세 설명"}
                },
                "label": {"type": "plain_text", "text": "설명"},
                "optional": True
            },
            {
                "type": "input",
                "block_id": "project",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "project_input",
                    "placeholder": {"type": "plain_text", "text": "프로젝트 키 입력 (예: PROJ)"}
                },
                "label": {"type": "plain_text", "text": "프로젝트 키"},
                "optional": False
            },
            {
                "type": "input",
                "block_id": "issuetype",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "issuetype_input",
                    "placeholder": {"type": "plain_text", "text": "이슈 타입 입력 (예: Task)"}
                },
                "label": {"type": "plain_text", "text": "이슈 타입"},
                "optional": False
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "trigger_id": trigger_id,
        "view": modal_view
    }
    response = requests.post(f"{SLACK_API_URL}/views.open", headers=headers, json=payload)
    logger.info(f"Jira 이슈 생성 모달 열기 응답: {response.text}")
    return response.json()

def open_meeting_request_modal(trigger_id):
    modal_view = {
        "type": "modal",
        "callback_id": "meeting_review_modal",
        "title": {"type": "plain_text", "text": "모임요청"},
        "submit": {"type": "plain_text", "text": "보내기"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "title",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "title_input",
                },
                "label": {"type": "plain_text", "text": "제목"},
                "optional": False,
            },
            {
                "type": "input",
                "block_id": "assignee",
                "element": {
                    "type": "multi_users_select",
                    "action_id": "assignee_input",
                    "placeholder": {"type": "plain_text", "text": "담당자를 선택하세요"},
                },
                "label": {"type": "plain_text", "text": "담당자"},
                "optional": False,
            },
            {
                "type": "input",
                "block_id": "document",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "document_input",
                },
                "label": {"type": "plain_text", "text": "기획서 링크"},
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "content",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "content_input",
                    "multiline": True,
                },
                "label": {"type": "plain_text", "text": "내용"},
                "optional": True,
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {"trigger_id": trigger_id, "view": modal_view}
    response = requests.post(f"{SLACK_API_URL}/views.open", headers=headers, json=payload)
    logger.info(f"모임요청 모달 열기 응답: {response.text}")
    return response.json()

# 필요 권한: conversations:read
def dm_channel_to_user_id(conversations_client, channel_id):
    # conversations.info로 IM 채널 정보 조회하면 'user' 필드에 상대방 user id가 있습니다.
    resp = conversations_client.conversations_info(channel=channel_id)
    if not resp.get("ok"):
        raise RuntimeError(f"conversations.info 실패: {resp.get('error')}")
    channel = resp.get("channel", {})
    # IM(D...) 채널이면 'user' 키에 상대 사용자(U...)가 들어있음
    return channel.get("user")

# 예: DEFAULT_CC_IDS 안에 D... 가 섞여 있을 때 정규화
def normalize_cc_user_ids(conversations_client: WebClient, user_ids: list[str]) -> list[str]:
    """유저 ID 목록을 받아 DM 채널을 열어 멘션 가능한 ID 리스트를 리턴한다"""
    normalized_ids = []

    for user_id in user_ids:
        try:
            # DM 채널 열기 (기존 conversations.info → conversations.open 으로 변경)
            resp = conversations_client.conversations_open(users=[user_id])
            if resp["ok"]:
                normalized_ids.append(user_id)  # <@user_id> 형태로 Slack에서 렌더링됨
            else:
                logger.warning(f"DM open 실패 {user_id}: {resp}")
        except SlackApiError as e:
            logger.warning(
                f"DM open 실패 {user_id}: {e.response['error'] if e.response else e}"
            )

    return normalized_ids

def get_dm_channel_id(user_id: str):
    try:
        response = client.conversations_open(users=[user_id])
        if response["ok"]:
            return response["channel"]["id"]
    except SlackApiError as e:
        logger.warning(f"DM open 실패 {user_id}: {e.response['error']}")
    return None
    

@app.route("/slack/command", methods=["POST"])
def slash_command_router():
    data = request.form.to_dict()
    command_text = data.get("command")
    user_name = data.get("user_name", "Guest")
    user_id = data.get("user_id")  # 슬랙 사용자 ID 추출
    trigger_id = data.get("trigger_id")
    logger.info(f"Slash Command 요청: {data}")

        #  Heartbeat 커맨드 추가
    if command == "/heartbeat":
        logger.info("💓 Heartbeat 요청 수신됨")
        return jsonify({"status": "alive"}), 200
        

    elif command_text == "/create_new_work":
        logger.info(f"/create_new_work 호출 by {user_id}")
        if trigger_id:
            modal_resp = open_create_new_work_modal(trigger_id, user_id) # trigger_id , user_id 전달
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
    elif command_text == "/jira_issue_create":
        logger.info(f"/jira_issue_create")
        if not trigger_id:
            return jsonify({
                "response_type": "ephemeral",
                "text": "trigger_id가 필요합니다. Slack 인터랙티브 명령에서만 동작합니다."
            })

        modal_resp = open_create_jira_issue_create_modal(trigger_id)
        if not modal_resp.get("ok"):
            return jsonify({
                "response_type": "ephemeral",
                "text": f"모달을 띄우는 데 실패했습니다: {modal_resp.get('error')}"
            })
        return "", 200

    elif command_text == "/모임요청":

        if not trigger_id:
            return jsonify({
                "response_type": "ephemeral",
                "text": "trigger_id가 필요합니다."
            }), 200

        modal_resp = open_meeting_request_modal(trigger_id)

        if not modal_resp.get("ok"):
            return jsonify({

                "response_type": "ephemeral",

                "text": f"모달 열기에 실패했습니다: {modal_resp.get('error')}"

            }), 200

        return "", 200

    return jsonify(
        {"response_type": "ephemeral", "text": f"알 수 없는 커맨드({command_text})입니다."}
    )


@app.route("/slack/interactions", methods=["POST"])
def interactions():
    logger.info("interactions1")
    payload_str = request.form.get("payload")
    if not payload_str:
        return "", 400
    data = json.loads(payload_str)
    logger.info("interactions2")

    if data.get("type") == "view_submission":
        callback_id = data.get("view", {}).get("callback_id")
        state_values = data["view"]["state"]["values"]

        # 1) 기존 업무 생성 모달 처리
        if callback_id == "work_create_modal":
            work_type = state_values["work_type"]["work_type_select"]["selected_option"]["value"]
            title = state_values["title"]["title_input"]["value"]
            content = state_values["content"]["content_input"]["value"]
            plan_url = state_values["plan_url"]["plan_url_input"].get("value", "")
            assignee_user_id = state_values["assignee"]["assignee_input"]["selected_user"]

            start_date = state_values.get("start_date", {}).get("start_date_input", {}).get("selected_date", "")
            end_date = state_values.get("end_date", {}).get("end_date_input", {}).get("selected_date", "")
            period = f"{start_date} ~ {end_date}" if start_date and end_date else "기간 미설정"

            prefix = PREFIX_MAP.get(work_type, "")
            
            # conversations_client는 slack_sdk WebClient 예: WebClient(token=SLACK_BOT_TOKEN)
            normalized = normalize_cc_user_ids(conversations_client, DEFAULT_CC_USER_IDS)
            cc_mentions = " ".join([f"<@{uid}>" for uid in normalized])
            blocks = [
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"{cc_mentions}\n*지라 일감 요청드립니다!*"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*<{prefix}업무 요청>*\n"
                            f"*제목:* {prefix}{title}\n"
                            f"*내용:* {content}\n"
                            f"*기간:* {period}\n"
                            f"*기획서:* {plan_url if plan_url else '없음'}\n"
                            f"*담당자:* <@{assignee_user_id}>"
                        ),
                    },
                },
                {"type": "divider"},
            ]

            headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json"}
            target_channel = CHANNEL_MAP.get(work_type, TARGET_CHANNEL)
            payload = {"channel": target_channel, "blocks": blocks, "text": f"{prefix}업무 요청: {title}"}
            response = requests.post(f"{SLACK_API_URL}/chat.postMessage", headers=headers, json=payload)
            if response.status_code == 200:
                logger.info("신규 잡 메시지 전송 성공")
                return jsonify({"response_action": "clear"})
            else:
                logger.error(f"Slack 메시지 전송 실패: {response.text}")
                return jsonify({"response_action": "errors", "errors": {"title": "메시지 전송 실패"}})

        # 2) 모임요청 모달 처리
        elif callback_id == "meeting_review_modal":
            # 필드 추출: block_id / action_id는 모달을 만든 블록 정의와 정확히 일치해야 함
            title = state_values["title"]["title_input"]["value"]
            document = state_values.get("document", {}).get("document_input", {}).get("value", "")
            content = state_values.get("content", {}).get("content_input", {}).get("value", "")
            # 장소 블록을 모달에 추가했다면 다음과 같이 읽음(없다면 빈 문자열 처리)
            place = state_values.get("place", {}).get("place_input", {}).get("value", "")

            # 담당자: multi_users_select
            assignees = state_values["assignee"]["assignee_input"].get("selected_users", [])
            assignee_mentions = " ".join([f"<@{uid}>" for uid in assignees]) if assignees else "없음"

            # 참조: 기본 3명(환경설정 권장)
            default_refs = DEFAULT_CC_USER_IDS  # 예: ["UAAAAAAA1","UBBBBBBB2","UCCCCCCC3"]
            cc_mentions = " ".join([f"<@{uid}>" for uid in default_refs])

            # 메시지 텍스트(요청하신 형식)
            # 굵게/각괄호/화살괄호 등은 mrkdwn에서 그대로 표시 가능
            lines = [
                "**[기획 리뷰 요청드립니다.]**",
                f"제목: << {title} >>",
                f"기획서: {document if document else '없음'}",
                f"내용: {content if content else '없음'}",
                f"담당자: {assignee_mentions}",
                f"참조: {cc_mentions}",
            ]
            msg_text = "\n".join(lines)

            headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json"}
            target_channel = MEETING_REQUEST_CHANNEL  # 모임요청을 보낼 채널
            payload = {"channel": target_channel, "text": msg_text}
            response = requests.post(f"{SLACK_API_URL}/chat.postMessage", headers=headers, json=payload)
            if response.status_code == 200:
                logger.info("모임요청 메시지 전송 성공")
                return jsonify({"response_action": "clear"})
            else:
                logger.error(f"슬랙 모임요청 메시지 전송 실패: {response.text}")
                return jsonify({"response_action": "errors", "errors": {"title": "메시지 전송 실패"}})

    return "", 200




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
