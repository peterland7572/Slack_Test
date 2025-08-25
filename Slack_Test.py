import logging
from flask import Flask, request, jsonify

# 로깅 설정 (콘솔 + 파일)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),                 # 콘솔 출력
        logging.FileHandler("slack_server.log")  # 파일 저장
    ]
)

app = Flask(__name__)

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

if __name__ == "__main__":
    logging.info("🚀 Flask Slack Command Server Started on port 5000")
    app.run(host="0.0.0.0", port=5000)
