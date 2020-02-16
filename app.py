# app.py
import os
import io
import psycopg2
import psycopg2.extras
import logging
import urllib.parse
from flask import Flask, abort, request, jsonify, send_from_directory
import hmac, hashlib, base64, json
from moesifwsgi import MoesifMiddleware
app = Flask(__name__)
#logging.basicConfig(filename='example.log')
logging.basicConfig(level=logging.INFO)
################################################################################
def identifyUser(app, environ):
        content_length = environ.get('CONTENT_LENGTH')
        logging.debug(environ)
        content_length = int(content_length)
        readbytes = environ['wsgi.input'].read(content_length)
        logging.debug('wsgi_input in Bytes: %s', readbytes)
        environ['wsgi.input'] = io.BytesIO(readbytes) # reset request body for the nested app Python3
        raw_body = readbytes.decode('utf-8')
        logging.debug('wsgi_input in String: %s', raw_body)
        if len(raw_body) > 0:
            parsed_body = urllib.parse.parse_qs(raw_body)
            moesif_user_id = parsed_body.get('user_name')[0]
            logging.debug('Parsed body: %s', parsed_body)
            logging.info('Moesif user id: %s', moesif_user_id)
            return moesif_user_id
        else:
            return None

def identifyCompany(app, environ):
    # return the company id here
    return "NDAP"

moesif_settings = {
    'APPLICATION_ID': 'eyJhcHAiOiI2NzY6MjAxIiwidmVyIjoiMi4wIiwib3JnIjoiNDU2OjI2MSIsImlhdCI6MTU3NDQ2NzIwMH0.Bpbhu__hqp_5gsJbe_lDYrFfCo1K6gIe9VU2nS8-lH0',
    'DEBUG': False,
    'CAPTURE_OUTGOING_REQUESTS': False, # Set to True to also capture outgoing calls to 3rd parties.
    'IDENTIFY_USER': identifyUser,
    'IDENTIFY_COMPANY': identifyCompany,
    'LOG_BODY': True,
}

app.wsgi_app = MoesifMiddleware(app.wsgi_app, moesif_settings)
################################################################################
def is_slack_request_valid(request):
    try:
        is_slack_token_valid = request.form.get('token', None) == '6mPhVZmqSZ57QFfMioqhl1Ra'
        is_slack_team_valid = request.form.get('team_id', None) == 'T70DXRVH6'
        return is_slack_token_valid and is_slack_team_valid
    except:
        return False

def is_ms_teams_request_valid (request):
    try:
        # Authenticate
        request_data = request.get_data()
        if request.headers.get('Host') == "ndapthanks.herokuapp.com" :
            security_token = b"0TUoDa/b9pWPDG0F3N/bGdX4OfVhwv3KcLzgWrsqi2g="   #thx webhook -- production  version
        else:
            security_token = b"+EMX4C5xXrrTcv0r6GhuA3ufO1nMiQacUruezK/Kip0="   #test_thx webhook -- test version      
        digest = hmac.new(base64.b64decode(security_token), msg=request_data, digestmod=hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()
        #verify that HMAC header == signature
        is_ms_teams_hmac_valid = request.headers.get('Authorization').split(' ')[1] == signature
        logging.info('HMAC signature: %s',signature)
        return is_ms_teams_hmac_valid
    except:
        return False
################################################################################
@app.route('/', methods=['POST'])
def ndap_thanks():
    client_type = None
    input_data_error = False
    if is_slack_request_valid(request):
        client_type = "slack"
    else:
        if is_ms_teams_request_valid(request) :   #check msteams message validity based on HMAC
            client_type = "msteams"
    if not client_type :
        abort(400)
    else: #fetch the data from request
        response_text_to_client = None
        number_of_mentions = 0
        thx_to_whom = []
        # Parse the parameters from the message what you need
        if client_type == "slack" :
            #command = request.form.get('command', None)
            thx_user_id = request.form.get('user_id', None)
            logging.info('Thx User id: %s',thx_user_id)
            thx_who = request.form.get('user_name', None)
            logging.info('Thx Who: %s',thx_who)
            req_text = request.form.get('text', None)
            data = req_text.split(" ",2)
            try:
                thx_amount = int(data[0])
                logging.info('Thx Amount: %s',thx_amount)
                if thx_amount > 0 and thx_amount <=100 :
                    if data[1][0] == '@' and len(data[1]) > 1 :
                        thx_to_whom.append(data[1][1:])
                        number_of_mentions = 1
                        logging.info('Thx to Whom: %s',thx_to_whom[0])
                        thx_for_what = data[2]
                        logging.info('Thx for What: %s',thx_for_what)
                    else: #if data[1][0] == '@' and len(data[1]) > 1
                        input_data_error = True
                        response_text_to_client = data[1] + " --> This is not a valid '@mention' !"
                        logging.error('Input Error: %s',response_text_to_client)
                else: #if thx_amount > 0
                        input_data_error = True
                        response_text_to_client = data[0] + " --> Only integer numbers beetween 1 and 100 are allowed!"
                        logging.error('Input Error: %s', response_text_to_client)
            except ValueError:
                input_data_error = True
                response_text_to_client = data[0] + "--> This is not an integer number!"
                logging.error('Input Error: %s', response_text_to_client)
        else : #client_type = msteams
            req_whom = []
            json_data = request.get_json()
            #channel = data['channelId']
            #message_type = data['type']
            thx_user_id = json_data['from']['id']
            logging.info('Thx User id: %s',thx_user_id)
            thx_who = json_data['from']['name']
            logging.info('Thx Who: %s',thx_who)
            req_text = json_data['text']
            req_text = req_text.replace("<at>test_thx</at>&nbsp;","")
            logging.info('msteams req text: %s',req_text)

            for json_entity in json_data['entities']:
                if json_entity['type'] == "mention" :
                    req_whom.append(json_entity['text'])
                    thx_to_whom.append(json_entity['mentioned']['name'])
                    req_text = req_text.replace(req_whom[number_of_mentions],"")
                    number_of_mentions += 1

            logging.info('msteams req whom: %s',req_whom)
            if number_of_mentions == 0 :
                input_data_error = True
                response_text_to_client = "No valid mention is Found!"
                logging.error('Input Error: %s',response_text_to_client)#message_format = data['textFormat']

            req_text = req_text.replace("&nbsp;","")
            logging.info('msteams req text: %s',req_text)
            data = req_text.split(" ",1)
            try:
                thx_amount = int(data[0])
                logging.info('Thx Amount: %s',thx_amount)
                if thx_amount > 0 and thx_amount <=100 :
                    thx_for_what = data[1]
                    logging.info('Thx to Whom: %s',thx_to_whom)
                    logging.info('Thx for What: %s',thx_for_what)
                else: #if thx_amount > 0
                        input_data_error = True
                        response_text_to_client = data[0] + " --> Only integer numbers beetween 1 and 100 are allowed!"
                        logging.error('Input Error: %s', response_text_to_client)
            except ValueError:
                input_data_error = True
                response_text_to_client = data[0] + "--> This is not an integer number!"
                logging.error('Input Error: %s', response_text_to_client)

#####################################################################################################################
        update_user = MoesifMiddleware(app, moesif_settings).update_user({'user_id': thx_who,'company_id': 'NDAP'})
        update_company = MoesifMiddleware(app, moesif_settings).update_company({'company_id': 'NDAP'})
#####################################################################################################################
        if not input_data_error:
            if thx_to_whom != thx_who :
                conn = None
                try:
                    #set windows env variable
                    #test database #set DATABASE_URL=postgres://gliowdvszelgsr:2f26126f6235b7c29b16cef82758b50cb4bf37009c466ba4c8d0c03d39d4c2cb@ec2-54-217-243-19.eu-west-1.compute.amazonaws.com:5432/da7fv56744pvck
                    DATABASE_URL = os.environ['DATABASE_URL']
                    # connect to the PostgreSQL server
                    logging.info('Connecting to the PostgreSQL database...')
                    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
                    # create a cursor
                    cur = conn.cursor()

                    #query data
                    postgres_data_query = """SELECT  c_who, date_part('month', created_at) AS "Month", SUM(c_amount) AS "Points" FROM thanks_data WHERE c_who = %s AND date_part('month', created_at) = date_part('month',CURRENT_DATE) GROUP BY date_part('month', created_at), c_who; """
                    cur.execute(postgres_data_query,(thx_who,))
                    # display the PostgreSQL database SQL result
                    db_sql_result_row = cur.fetchone()
                    if db_sql_result_row:
                        a_sent_points = db_sql_result_row[2]
                    else:
                        a_sent_points = 0
                    logging.info('User sent points in actual month is : %s', str(a_sent_points))

                    if (a_sent_points+(thx_amount*number_of_mentions)) <= 100 :
                        # execute a statement
                        records_to_insert = []
                        postgres_insert_query = """INSERT INTO thanks_data (c_who, c_amount, c_to_whom, c_for_what) VALUES (%s, %s, %s, %s) RETURNING id;"""
                        for i in range(number_of_mentions):
                            records_to_insert.append((thx_who,thx_amount, thx_to_whom[i],thx_for_what))
                        logging.info('Records to Insert: %s',records_to_insert)
                        psycopg2.extras.execute_batch(cur,postgres_insert_query, records_to_insert)
                        # display the PostgreSQL database SQL result
                        db_sql_result = cur.fetchone()[0]
                        logging.info('SQL Result: %s', str(db_sql_result))
                        # commit the changes to the database
                        conn.commit()
                        # close the communication with the PostgreSQL
                        cur.close()
                        response_text_to_client = ":+1: Thank you for your recognition! In this month you have spent *"+ str(a_sent_points+thx_amount) + "*/100 points"
                    else:
                        response_text_to_client = ":-1: In this month you have already spent *"+ str(a_sent_points) + "*/100, so you have not enough remaining points for this!"
                except (Exception, psycopg2.DatabaseError) as error:
                    response_text_to_client = 'Database Error :( Please send warning to Mike!'
                    logging.error('Database Error: %s', error)
                finally:
                    if conn is not None:
                        conn.close()
                        logging.info('Database connection closed.')
            else: #if thx_to_whom != thx_who
                response_text_to_client = thx_to_whom + " --> Not fair to send points to yourself!"
                logging.error('Input Error: %s',response_text_to_client)

#####################################################################################################################
        if client_type == "slack" :
            if response_text_to_client is not None:
                return jsonify(
                    response_type='in_channel',
                    text= response_text_to_client,
                    )
            else:
                return jsonify(
                    response_type='in_channel',
                    text='Something went terrible wrong :( warning to <@UCGPL6H0E>',
                    )
        else: #client_type = msteams
            if response_text_to_client is not None:
                return jsonify({
                    'type' : 'message',
                    'text' : response_text_to_client,
                    })
            else:
                return jsonify({
                                'type' : 'message',
                                'text' : 'Something went terrible wrong :( warning to <at>Mike, Zsolt (Nokia - HU/Budapest)</at>',
                                'entities': [
                                            {
                                              "type": "mention",
                                              "mentioned": {
                                                            "id": "29:1VxxSgQwN1CFYVwaeBLKjSgjxw27O2jfZgUWsLUYTcNyoV3wDSJkJZWk3ovFGbPFUulKemahFEqOLpJjRgLh1Eg",
                                                            "name": "Mike, Zsolt (Nokia - HU/Budapest)"
                                                            },
                                              "text": "<at>Mike, Zsolt (Nokia - HU/Budapest)</at>"
                                              }
                                            ],
                                })

# A welcome message to our server
@app.route('/', methods=['GET'])
def index():
    return "<h1>Welcome to NDAP Thanks!!</h1>"

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path,'favicon.ico',mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
