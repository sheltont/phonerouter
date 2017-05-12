# -*- coding: utf-8 -*-

from flask import Flask
from flask import g
from flask_restful import Api, Resource, reqparse
from flask import jsonify
import ESL
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='/var/log/freeswitch/call_server.log',
                    filemode='w')

app = Flask(__name__)
api = Api(app)


esl_server = '127.0.0.1'
esl_port = 8021
esl_auth = 'ClueCon'
call_command_format = 'originate user/{0} {1} XML default'

######################################################################################
# Helper functions to make a ESL connection
def __get_esl_connection__():
    """Open a ESL inbound connection if not existing
    """
    if not hasattr(g, 'esl_conn'):
        g.esl_conn = __make_esl_connection__()
    if not g.esl_conn.connected():
    	g.esl_conn = __make_esl_connection__()
    return g.esl_conn

def __make_esl_connection__():
	conn = ESL.ESLconnection(esl_server, esl_port, esl_auth)
	return conn

def __call_esl_api__(command):
    conn = __get_esl_connection__()
    if not conn.connected:
        raise Exception("The connection to FreeSWITCH is not invalid")
    app.logger.info("send command: %s", command)
    e = conn.api(command)
    return e.getBody()

def __parse_esl_response__(response):
    if not response:
        return {'success': False, 'reason': 'Invalid response'}

    app.logger.info('freeswitch response: %s', response)
    tokens = response.strip().split(' ')
    if len(tokens) != 2:
        app.logger.error('unkown response %s', response)
        return {'success': False, 'reason': 'Unknown response {0}'.format(response)}

    if tokens[0] == '+OK':
        return {'success': True, 'data': tokens[1]}
    else:
        return {'sucess': False, 'reason': tokens[1]}


def query_esl_status():
    try:
        cmd = 'status'
        response = __call_esl_api__(cmd)
        return {'sucess': True, 'data': response}
            
    except Exception, e:
        return {'success': False, 'reason': repr(e)}



def make_esl_call(extension, mobile):
    try:
        cmd = call_command_format.format(extension, mobile)
        response = __call_esl_api__(cmd)
        return __parse_esl_response__(response)
    except Exception, e:
        return {'success': False, 'reason': repr(e)}
######################################################################################

class CallAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('extension', type = str, required = True, location = 'json', 
            help = 'An extension number who initial the call')
        self.reqparse.add_argument('mobile', type = str, required = True, location = 'json', 
            help = 'An external mobile phone number to be called')
        super(CallAPI, self).__init__()

    def get(self):
        result = query_esl_status()
        return jsonify(result)


    def post(self):
        args = self.reqparse.parse_args()
        extension = args['extension']
        mobile = args['mobile']
        result = make_esl_call(extension, mobile)
        return jsonify(result)
    

api.add_resource(CallAPI, '/call_server/api/v1.0/call', endpoint = 'call')


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
