from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/slack/command", methods=["POST"])
def hi_slash_command():
    # Slack에서 넘어오는 form 데이터
    data = request.form

    # Slack 요청 값들
    user_name = data.get("user_name")  # 명령어 실행한 사용자 이름
    command = data.get("command")      # ex) /hi_slash_command
    text = data.get("text")            # slash 뒤에 입력한 값

    # 응답 메시지 생성
    response_text = f"hi {user_name} !"

    # Slack에 바로 응답
    return jsonify({
        "response_type": "in_channel",   # 채널 전체 공개 (ephemeral = 개인에게만 보임)
        "text": response_text
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
