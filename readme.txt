slack_app/
│
├── app.py                 # Flask 앱과 Slack Bolt 앱 초기화 및 실행
├── config.py              # 환경변수, 상수(채널, 업무타입 등) 정의
├── slack_api.py           # Slack API 호출 함수 (모달 열기, 메시지 전송 등)
├── handlers.py            # Flask 라우팅과 Slack 이벤트/인터랙션 핸들러
├── utils.py               # 공통 유틸 함수 (예: 멤버 조회 함수)
└── requirements.txt       # 패키지 목록
