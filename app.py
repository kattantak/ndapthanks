# app.py
import os
import io
import psycopg2
import logging
import urllib.parse
from flask import Flask, request, jsonify, send_from_directory
from moesifwsgi import MoesifMiddleware
app = Flask(__name__)
#logging.basicConfig(filename='example.log')
logging.basicConfig(level=logging.INFO)

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
            moeif_user_id = parsed_body.get('user_name')[0]
            logging.debug('Parsed body: %s', parsed_body)
            logging.info('Moesif user id: %s', moeif_user_id)
            return moeif_user_id
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


def is_request_valid(request):
    is_token_valid = request.form.get('token', None) == '6mPhVZmqSZ57QFfMioqhl1Ra'
    is_team_valid = request.form.get('team_id', None) == 'T70DXRVH6'
    return is_token_valid and is_team_valid

@app.route('/', methods=['POST'])
def ndap_thanks():
    if not is_request_valid(request):
        abort(400)
    else: #Response to Slack
        response_text_to_slack = None
        # Parse the parameters you need
        command = request.form.get('command', None)
        thx_user_id = request.form.get('user_id', None)
        thx_who = request.form.get('user_name', None)
        req_text = request.form.get('text', None)
        logging.info('Thx Who: %s',thx_who)
        logging.info('Thx User id: %s',thx_user_id)
        logging.info('Thx Text: %s',req_text)

        update_user = MoesifMiddleware(app, moesif_settings).update_user({'user_id': thx_who,'company_id': 'NDAP'})
        update_company = MoesifMiddleware(app, moesif_settings).update_company({'company_id': 'NDAP'})

        #Split and convert to get the needed data
        data = req_text.split(" ",2)
        try:
            thx_amount = int(data[0])
            logging.info('Thx Amount: %s',thx_amount)
            if thx_amount > 0 :
                if data[1][0] == '@' and len(data[1]) > 1 :
                    thx_to_whom = data[1][1:]
                    logging.info('Thx to Whom: %s',thx_to_whom)
                    thx_for_what = data[2]
                    logging.info('Thx for What: %s',thx_for_what)
                    if thx_to_whom == thx_who :
                        conn = None
                        try:
                            #set windows env variable
                            #set DATABASE_URL=postgres://vxkhlsqjazuwxi:9acac04cf61d6527f61d74c2036263653c7154934a04a7c24fa55d54f694d14c@ec2-54-228-207-163.eu-west-1.compute.amazonaws.com:5432/d6fhd2k9uscss7
                            DATABASE_URL = os.environ['DATABASE_URL']
                            # connect to the PostgreSQL server
                            logging.info('Connecting to the PostgreSQL database...')
                            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
                            # create a cursor
                            cur = conn.cursor()

                            #query data
                            postgres_data_query = """SELECT  c_who, date_part('month', created_at) AS "Month", SUM(c_amount) AS "Points" FROM thanks_data WHERE c_who = 'zsolt.mike' GROUP BY date_part('month', created_at), c_who; """
                            cur.execute(postgres_data_query)
                            # display the PostgreSQL database SQL result
                            db_sql_result = cur.fetchone()[0]
                            logging.info('SQL Result: %s', str(db_sql_result))

                            # execute a statement
                            postgres_insert_query = """INSERT INTO thanks_data (c_who, c_amount, c_to_whom, c_for_what) VALUES (%s, %s, %s, %s) RETURNING id;"""
                            record_to_insert = (thx_who,thx_amount, thx_to_whom,thx_for_what)
                            cur.execute(postgres_insert_query, record_to_insert)
                            # display the PostgreSQL database SQL result
                            db_sql_result = cur.fetchone()[0]
                            logging.info('SQL Result: %s', str(db_sql_result))
                            # commit the changes to the database
                            conn.commit()
                            # close the communication with the PostgreSQL
                            cur.close()
                            response_text_to_slack = 'Thank you for your kindness!'
                        except (Exception, psycopg2.DatabaseError) as error:
                            response_text_to_slack = 'Database Error :( warning <@UCGPL6H0E>'
                            logging.error('Database Error: %s', error)
                        finally:
                            if conn is not None:
                                conn.close()
                                logging.info('Database connection closed.')
                    else: #if thx_to_whom != thx_who
                        response_text_to_slack = thx_to_whom + " --> Not allowed to send points to yourself!"
                        logging.error('Input Error: %s',response_text_to_slack)
                else: #if data[1][0] == '@' and len(data[1]) > 1
                    response_text_to_slack = data[1] + " --> This is not a valid '@mention' !"
                    logging.error('Input Error: %s',response_text_to_slack)
            else: #if thx_amount > 0
                response_text_to_slack = data[0] + " --> Only positive numbers are allowed!"
                logging.error('Input Error: %s', response_text_to_slack)
        except ValueError:
            response_text_to_slack = data[0] + "--> This is not an integer number!"
            logging.error('Input Error: %s', response_text_to_slack)

        if response_text_to_slack is not None:
            return jsonify(
                response_type='in_channel',
                text=response_text_to_slack,
                )
        else:
            return jsonify(
                response_type='in_channel',
                text='Something went terrible wrong :( warning <@UCGPL6H0E>',
                )

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
