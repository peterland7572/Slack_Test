from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
import logging
from handlers import handle_slash_command, handle_interactions
from config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
handler = SlackRequestHandler(app)
flask_app = Flask(__name__)

@flask_app.route("/slack/command", methods=["POST"])
def slash_command_router():
    return handle_slash_command()

@flask_app.route("/slack/interactions", methods=["POST"])
def interactions_router():
    return handle_interactions()

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=5000)
