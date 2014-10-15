__authors__ = ['haxwithaxe <me@haxwithaxe.net>']

__license__ = 'GPLv3'

import time
import _strptime # required to avoid import errors
import urllib2
import include
from parse import MirageStatusParser as StatusParser
from include import StatusPluginException
from log import info, warn, error, critical, exception

debug = info

class Updater:
    ''' Update the bot from a remote status source '''

    def __init__(self, last_status_string=None, **passed_conf):
        global conf
	# add the config values passed to our dict of configs
        self.conf = {'source_url': None}
        self.conf.update(passed_conf)
	# The url to fetch the sensor data from
        self.source = self.conf.get('source_url') or self.__missing_url_config()
	# The number of seconds to sleep at the end of each loop
        self.interval_s = self.conf.get('interval_s')
	# socket timeout in seconds
	self.timeout = 30

    def __missing_url_config(self):
	''' freak out if there is no url to get data from '''
        raise StatusPluginException('Missing source_url configuration value')

    def check(self):
        ''' Get the latest status, test if it's new, update the bot if it is, and sleep so we don't go too fast. 
        return None if no change or self.status.message if there is a new status
        '''
	info('Updater.check: checking')
        status_string = self._fetch_data()      # grab the contents of the sensor upload
        debug('Updater.get_status.status_string(from server): %s' % status_string)
	if status_string:
	    parser = StatusParser()	# get a new parser
	    # parse the response
            status = parser.get_status(status_string)
	    # and update the values with the resulting Status object
            debug('Updater.get_status.status(parsed): %s' % str(status))
            return status.message
	debug('Updater.get_status: no status found')
        return None

    def _fetch_data(self, count=0):
	''' Grab the sensor data from the sensor upload url
	@param	count		the number of levels of recursion
	@return			status data string if available otherwise return None
	'''
	if count >= 3:
	    raise StatusPluginException('''Can't connect to %s''' % self.source)
	debug('Updater._fetch_data.source: %s' % self.source)
	try:
	    # fetch raw data from the server
	    request = urllib2.Request(url=self.source)
            reply = urllib2.urlopen(request, timeout=self.timeout)
	    debug('Updater._fetch_data.reply: %s' % str(reply))
	    # if the http code indicates a successful request extract the data from the reply
            if reply.getcode() == 200:
	        debug('Updater._fetch_data: reply is good')
                return reply.read()
	except urllib2.URLError as e:
	    warn('Updater._fetch_data: %s' % str(e))
	    if hasattr(e, 'reason') and str(e.reason).strip() == 'timed out':
	        time.sleep(3)
		return self._fetch_data(count+1)
	return None

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
