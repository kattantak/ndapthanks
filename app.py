import os

from flask import abort, Flask, jsonify, request


app = Flask(__name__)


def is_request_valid(request):
    is_token_valid = request.form['token'] == os.environ['6mPhVZmqSZ57QFfMioqhl1Ra']
    #is_team_id_valid = request.form['team_id'] == os.environ['SLACK_TEAM_ID']

    return is_token_valid and is_team_id_valid


@app.route('/', methods=['POST'])
def hello_there():
    if not is_request_valid(request):
        abort(400)

    return jsonify(
        response_type='in_channel',
        text='<https://youtu.be/frszEJb0aOo|General Kenobi!>',
    )
