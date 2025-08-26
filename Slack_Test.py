import os
import logging
import requests


from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s")

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
if not SLACK_BOT_TOKEN:
    raise ValueError("Slack Bot Token이 설정되지 않았습니다. 환경변수 확인 필요")
    

def get_all_members():
    logger.info("Slack 전체 멤버 조회 시작")

    base_url = "https://slack.com/api/users.list"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
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

        members = data.get("members", [])
        logger.info("📦 받은 멤버 수: %d", len(members))
        all_members.extend(members)

        # 다음 페이지 cursor 확인
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    logger.info("전체 멤버 수: %d", len(all_members))
    return all_members




app = Flask(__name__)
'''
@app.route("/slack/command", methods=["POST"])
def hi_slash_command():
    # Slack에서 넘어오는 form 데이터
    data = request.form.to_dict()

    # 요청 데이터 로그 출력
    logging.info(f"📩 Slack Slash Command Received: {data}")

    # Slack 요청 값들
    user_name = data.get("user_name")  # 명령어 실행한 사용자 이름
    command = data.get("command")      # ex) /hi_slash_command
    text = data.get("text")            # slash 뒤에 입력한 값

    # 응답 메시지 생성
    response_text = f"hi {user_name} !"
    logging.info(f"✅ Responding with: {response_text}")

    # Slack에 바로 응답
    return jsonify({
        "response_type": "in_channel",   # 채널 전체 공개 (ephemeral = 개인에게만 보임)
        "text": response_text
    })
'''
@app.route("/slack/command", methods=["POST"])
def hi_slash_command():
    data = request.form.to_dict()
    user_name = data.get("user_name", "Guest")
    command = data.get("command", "")
    text = data.get("text", "")

    logger.info(f"Slash Command 요청: {data}")

    # 전체 멤버 조회
    members = get_all_members()

    # 멤버 이름만 리스트로 생성
    member_names = [m.get("real_name") or m.get("name") for m in members]

    # Slack 메시지는 길이 제한 있음 → 3000자 정도로 제한
    MAX_CHARS = 3000
    members_text = ", ".join(member_names)
    if len(members_text) > MAX_CHARS:
        members_text = members_text[:MAX_CHARS] + " ... (이하 생략)"

    response_text = f"hi {user_name} ! Slack 전체 멤버:\n{members_text}"
    logger.info(f"응답 메시지 길이: {len(response_text)}")

    return jsonify({
        "response_type": "in_channel",  # 전체 채널 공개
        "text": response_text
    })

if __name__ == "__main__":
    logging.info("🚀 Flask Slack Command Server Started on port 5000")
    app.run(host="0.0.0.0", port=5000)
