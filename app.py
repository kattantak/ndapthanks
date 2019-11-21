from bottle import run,post,request,response,route
import os
import urllib


@route('/thx',method="post")
def gen_path_3():
    postdata = request.forms.get("text")
    output_path = str("sndwserv:/" + urllib.quote(postdata))
    package = {"response_type": "in_channel", "text": "{}".format(output_path)}
    response.content_type = 'application/json'
    return package


if os.environ.get('APP_LOCATION') == 'heroku':
    run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
else:
    run(host='localhost', port=8080, debug=True)
