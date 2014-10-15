from registry import Registry
from log import debug, info, warn, error, critical, exception


class StatusRegistry(Registry):
    ''' Thread safe interface to the supybot registry '''

    status_keys = {'default':'message_default', 'human':'message_human', 'raw':'message_raw', 'time_fetched':'time_fetched'}

    def getall(self):
	''' Get the existing values in the cache. '''
        msg_list = [(x,self.get(y)) for x,y in self.status_keys.items()]
        msg = dict(msg_list)
	debug('got from registry: %s' % str(msg))
	return msg

    def setall(self, message=None):
	''' Update the cached status values 
	@param  message     The status message dict.
	'''
	debug('StatusRegistry: updating cached values: %s' % str(message))
	# Set the message to cache if there is no message in the message dict.
        notset = 'No status available yet.'
	# Set the values of the messages in the cache with their counterparts in the message dict.
	if message:
            for key, val in self.status_keys.items():
                self.update(val, message.get(key))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
