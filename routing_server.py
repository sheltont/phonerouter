import sys
import os
import argparse
import logging
import SocketServer
import ESL
from routing import RoutingServer
from logging.handlers import RotatingFileHandler


#Rthandler = RotatingFileHandler('/var/log/freeswitch/phonerouter.log', maxBytes=10*1024*1024, backupCount=5)
#Rthandler.setLevel(logging.DEBUG)
#formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
#Rthandler.setFormatter(formatter)


console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)



listen_port = 8040
listen_ip = "127.0.0.1"
max_sid_len = 'sofia/internal/1007@172.18.100.3:15566'

logger = logging.getLogger('routing')
voice_url = '/usr/share/freeswitch/sounds/en/us/callie/voicemail/8000/vm-enter_pass.wav'
target_mobile_url = 'sofia/internal/{0}@172.16.29.2:5060'


class ESLRequestHandler(SocketServer.BaseRequestHandler):
	def __init__(self, request, client_address, server):
		self.routing_server = RoutingServer()
		return


	def setup(self):
		logger.info("%s connected", self.client_address)
		fd = self.request.fileno()
		con = ESL.ESLconnection(fd)

		if con.connected():
			info = con.getInfo()
			uuid = info.getHeader("unique-id")
			logger.info('the incoming call uuid is: %s', uuid)
			event = con.filter("unique-id", uuid)
			con.events("plain", "all")
			con.execute("answer", "", uuid)
			msg = "%d %d 1 5000 # %s silence_stream://250".format(max_sid_len, max_sid_len, voice_url)
			logger.info('play_and_get_digits: %s', msg)
			con.execute("play_and_get_digits", msg)
			digits = []

			while con.connected():
				e = con.recvEvent()
				if e:
					name = e.getHeader("event-name")
					logger.debug("event-name: %s", name)
					if name == "DTMF":
						digit = e.getHeader("dtmf-digit")
						logger.debug("digit: %s", digit)
						digits.append(digit)
				if len(digits) == max_sid_len:
					break

			logger.debug('collecting digits: %s', digits)
			if len(digits) == max_sid_len:
				sid = ''.join(digits)
				mobile = self.routing_server.get_mobile(sid)
				if mobile:
					target = "{0} XML default".format(mobile)
					logger.info('transfer the call to %s', target)
					con.execute("transfer", target, uuid)

			logger.debug("Disconnected!")


if __name__ == '__main__':
	logger.info("listening on the TCP {0}:{1}".format(listen_ip, listen_port))
	try:
		SocketServer.ThreadingTCPServer.allow_reuse_address = True
		server = SocketServer.ThreadingTCPServer((listen_ip, listen_port), ESLRequestHandler)
		server.serve_forever()
	except KeyboardInterrupt:
		print "exit"
		sys.exit()

