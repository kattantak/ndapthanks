# app.py
# import os
import logging
from flask import Flask, request, jsonify
app = Flask(__name__)

#logging.basicConfig(filename='example.log')
logging.basicConfig(level=logging.INFO)

def is_request_valid(request):
    is_token_valid = request.form.get('token', None) == '6mPhVZmqSZ57QFfMioqhl1Ra'
    is_team_valid = request.form.get('team_id', None) == 'T70DXRVH6'
    return is_token_valid and is_team_valid

@app.route('/', methods=['POST'])
def ndap_thanks():
    # Parse the parameters you need
    command = request.form.get('command', None)
    user_name = request.form.get('user_name', None)
    text = request.form.get('text', None)
    logging.info(user_name)
    logging.info(text)

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
