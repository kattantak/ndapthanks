# app.py
import os
from flask import Flask, request, jsonify
app = Flask(__name__)


def is_request_valid(request):
    is_token_valid = request.form['token'] == os.environ['6mPhVZmqSZ57QFfMioqhl1Ra']
    is_team_id_valid = request.form['team_id'] == os.environ['T70DXRVH6']

    return is_token_valid and is_team_id_valid


@app.route('/', methods=['POST'])
def ndap_thanks():
    if not is_request_valid(request):
        return jsonify(
            response_type='in_channel',
            text='Not a valid team!',
            )
    else:
        return jsonify(
            response_type='in_channel',
            text='<https://youtu.be/frszEJb0aOo|General Kenobi!>',
            )


# A welcome message to test our server
@app.route('/', methods=['GET'])
def index():
    return "<h1>Welcome to NDAP Thanks!!</h1>"

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
