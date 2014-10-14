__authors__ = ['haxwithaxe <me@haxwithaxe.net>']

__license__ = 'GPLv3'

import time
import _strptime # required to avoid import errors
import urllib2
import include
from include import StatusPluginException
from log import debug, info, warn, error, critical, exception


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
	# The Status retrived before the most recent Status
        self.last_status = None
	# The most recent Status retrived
        self.status = None
	# Token indicating if this is the first time through the loop
        self._first_run = True

    def __missing_url_config(self):
	''' freak out if there is no url to get data from '''
        raise StatusPluginException('Missing source_url configuration value')

    def check(self):
        ''' Get the latest status, test if it's new, update the bot if it is, and sleep so we don't go too fast. 
        return None if no change or self.status.message if there is a new status
        '''
	info('Updater.check: checking')
	# get the Status for the latest sensor upload
        return self._get_status()

    def _get_status(self):
        ''' Grab the status from the sensor
	Sets self.last_status and  self.status
	'''
        parser = StatusParser()	# get a new parser
	status_string = self._fetch_data()	# grab the contents of the sensor upload
	# if there is a response from the server
        if status_string:
            debug('Updater.get_status.status_string(from server):', status_string)
	    # parse the response
            status = parser.get_status(status_string)
	    # and update the values with the resulting Status object
            self.last_status = self.status
            self.status = status
            debug('Updater.get_status.status(parsed):', str(self.status))
            return self.status.message
	debug('Updater.get_status: done')
        return None

    def _fetch_data(self, count=0):
	''' Grab the sensor data from the sensor upload url
	@param	count		the number of levels of recursion
	@return			status data string if available otherwise return None
	'''
	if count >= 3:
	    raise StatusPluginException('''Can't connect to %s''' % self.source)
	debug('Updater._fetch_data.source:', self.source)
	try:
	    # fetch raw data from the server
	    request = urllib2.Request(url=self.source)
            reply = urllib2.urlopen(request, timeout=self.timeout)
	    debug('Updater._fetch_data.reply:', str(reply))
	    # if the http code indicates a successful request extract the data from the reply
            if reply.getcode() == 200:
	        debug('Updater._fetch_data: reply is good')
                return reply.read()
	except urllib2.URLError as e:
	    warn('Updater._fetch_data: ',e)
	    if hasattr(e, 'reason') and str(e.reason).strip() == 'timed out':
	        time.sleep(3)
		return self._fetch_data(count+1)
	return None

    def _is_new_status(self):
        ''' Test if the most recently grabbed status is newer than the last one 
	@return			True if status has changed or False if it has not.
	'''
	# If both the current and previous statuses exist check if the current is different from the pervious
        if self.status and self.last_status and self.status.time_changed and self.last_status.time_changed:
            debug('Updater.is_new_status: both statuses exist')
            if self.status >= self.last_status and self.status != self.last_status:
        	# if the new status is newer than or the same age as the last status found
	        # and if they are not equal there has been a status change it's new
                debug('Updater.is_new_status: new status')
                return True
            elif self._first_run:
		# if this is the first run on start up pretend this is a new 
		# status so we notify of the current status
		debug('Updater.is_new_status: first run')
		# make sure we don't think subsequent runs are the first
                self._first_run = False
                return True
        debug('Updater.is_new_status: old status')
        return False


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
