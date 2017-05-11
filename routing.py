import logging
import redis
import requests
import json
import cPickle as pickle
from datetime import datetime

logger = logging.getLogger('routing')


cache_time_of_second = 1800
service_list_url = "https://api.zuluoji.cn/api/v1/www/service-list"
service_detail_url = 'https://api.zuluoji.cn/api/v1/www/service-detail?sid={0}'


class RoutingServer:
	def __init__(self):
		self.redis = self.__intialize_redis__()
		self.is_reday = self.__fetch_all_items__()

	def get_mobile(self, sid):
		"""
		Get the mobile phone number of a service provider with its sid
		"""
		mobile = None
		key = self.__make_redis_key__(sid)
		data = self.redis.get(key)
		if not data:
			data = self.__fetch_one_item__(sid)

		if data:
			item = pickle.loads(data)
			mobile = item['mobile']

		logger.info("routing {0} => {1}".format(sid, self.__mask_mobile__(mobile)))

		return mobile


	def __intialize_redis__(self): 
		"""
		Initialize a local redis cache storage
		"""
		redis_inst = redis.StrictRedis(host='localhost', port=6379, db=0)
		redis_inst.set('initialized_time', datetime.now())
		return redis_inst


	def __fetch_all_items__(self):
		"""
		Fetch all number -> phone map relationship
		"""
		response = requests.get(service_list_url)
		if response.status_code == 200:
			result = response.json()
			if result['success'] == True:
				for item in result['data']:
					sid = item['sid']
					mobile = item['mobile']

					self.__write_redis__(sid, item)
		return True


	def __fetch_one_item__(self, sid):
		"""
		Fetch one service item with a sid
		"""
		response = requests.get(service_detail_url.format(sid))
		if response.status_code == 200:
			result = response.json()
			if result['success'] == True:
				item = result['data']
				self.__write_redis__(sid, item)
				return item
		return None


	def __write_redis__(self, sid, item):
		data = pickle.dumps(item)
		self.redis.set(self.__make_redis_key__(sid), data, cache_time_of_second)

	def __make_redis_key__(self, sid):
		return '{0}.routing.phonerouter'.format(sid)


	def __mask_mobile__(self, mobile):
		if mobile and len(mobile) == 11:
			mobile = mobile[0:4] + '****' + mobile[8:11]
		return mobile



if __name__ == '__main__':
	router = RoutingServer()
	print "1001: " + router.get_mobile("1001")
	print "1002: " + router.get_mobile("1002")
	print "1003: " + router.get_mobile("1003")
	print "1004: " + router.get_mobile("1004")