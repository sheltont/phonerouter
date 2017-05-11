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
listen_ip = '127.0.0.1'
max_sid_len = 4

logger = logging.getLogger('routing')
voice_url = '/usr/lib/freeswitch/esl/phonerouter/mj-22.wav'
#voice_url = '/usr/share/freeswitch/sounds/en/us/callie/voicemail/8000/vm-tutorial_change_pin.wav'
target_mobile_url = 'sofia/internal/{0}@172.16.29.2:5060'
default_target = 'group/service'
routing_server = RoutingServer()

class ESLRequestHandler(SocketServer.BaseRequestHandler):
	def setup(self):
		print self.client_address, ' is connected'
		fd = self.request.fileno()
		con = ESL.ESLconnection(fd)
	        if con.connected():
			info = con.getInfo()
			uuid = info.getHeader("unique-id")
			logger.info('the incoming call uuid is: %s', uuid)
			print uuid
			event = con.filter("unique-id", uuid)
			con.events("plain", "all")
			con.execute("answer", "", uuid)
			msg = "{0} {1} 1 5000 # {2} silence_stream://250".format(max_sid_len, max_sid_len, voice_url)
			print msg
			logger.info('play_and_get_digits: %s', msg)
			con.execute("play_and_get_digits", msg)
			digits = []
                        see_playback_stop = False
                        see_server_disconnected = False
			while con.connected():
				e = con.recvEvent()
				if e:
					name = e.getHeader("event-name")
					logger.debug("event-name: %s", name)
                                        print name
					if name == "DTMF":
						digit = e.getHeader("dtmf-digit")
						logger.debug("digit: %s", digit)
						digits.append(digit)
						print digit
                                        elif name == "PLAYBACK_STOP":
                                                see_playback_stop = True
                                        elif name == "SERVER_DISCONNECTED":
                                                see_server_disconnected = True
                                                break
                                        elif name == "CHANNEL_EXECUTE_COMPLETE" and see_playback_stop:
                                                break
				if len(digits) == max_sid_len:
					break

                        if see_server_disconnected:
                                logger.debug("Disconnected")
                                return
                        
			logger.debug('collecting digits: %s', digits)
			if len(digits) == max_sid_len:
				sid = ''.join(digits)
				print sid
				mobile = routing_server.get_mobile(sid)
				if mobile:
					target = "{0} XML default".format(mobile)
					logger.info('transfer the call to %s', target)
					con.execute("transfer", target, uuid)
                        else:
                                print "bridge to the default target ", default_target
                                con.execute("bridge", default_target, uuid)


if __name__ == '__main__':
	logger.info("listening on the TCP {0}:{1}".format(listen_ip, listen_port))
	try:
		SocketServer.ThreadingTCPServer.allow_reuse_address = True
		print "listening on the port", listen_port
		server = SocketServer.ThreadingTCPServer((listen_ip, listen_port), ESLRequestHandler)
		server.serve_forever()
	except KeyboardInterrupt:
		print "exit"
		sys.exit()

