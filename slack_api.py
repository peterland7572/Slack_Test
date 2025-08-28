import logging
import requests
from config import SLACK_BOT_TOKEN, SLACK_API_URL, WORK_TYPE_OPTIONS

logger = logging.getLogger(__name__)

def open_modal(trigger_id, modal_view):
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {"trigger_id": trigger_id, "view": modal_view}
    response = requests.post(f"{SLACK_API_URL}/views.open", headers=headers, json=payload)
    logger.info(f"모달 열기 응답: {response.text}")
    return response.json()

def open_create_new_work_modal(trigger_id):
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
                },
                "label": {"type": "plain_text", "text": "담당자 (실명)"},
            },
        ],
    }
    return open_modal(trigger_id, modal_view)

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
    return open_modal(trigger_id, modal_view)

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
    return open_modal(trigger_id, modal_view)


def post_message(channel, text=None, blocks=None):
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"channel": channel}
    if text:
        payload["text"] = text
    if blocks:
        payload["blocks"] = blocks
    response = requests.post(f"{SLACK_API_URL}/chat.postMessage", headers=headers, json=payload)
    if response.status_code == 200:
        logger.info("메시지 전송 성공")
    else:
        logger.error(f"메시지 전송 실패: {response.text}")
    return response
