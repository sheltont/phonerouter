from flask import Flask
from flask.ext import restful
import ESL

app = Flask(__name__)
api = restful.Api(app)

esl_server = '127.0.0.1'
esl_port = 8021
esl_auth = 'ClueCon'

def get_esl_connection():
    """Open a ESL inbound connection if not existing
    """
    if not hasattr(g, 'esl_conn'):
        g.esl_conn = connect_esl_connection()
    if not g.esl_conn.connected():
    	g.esl_conn = connect_esl_connection()
    return g.esl_conn

def connection_esl_connect():
	conn = ESL.ESLconnection(esl_server, esl_port, esl_auth)
	return conn


@app.teardown_appcontext
def close_esl_conn(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'esl_conn'):
        g.esl_conn.disconnect()
        g.esl_conn = None
        delattr(g, 'esl_conn')




class Fs_Call(restful.Resource):
    def get(self):
        return {'hello': 'world'}

api.add_resource(HelloWorld, '/')

if __name__ == '__main__':
    app.run(debug=True)