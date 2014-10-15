import threading
import time
import _strptime # required to prevent import errors
from log import debug, info, warn, error, critical, exception
from include import CatchAllExceptions


class StatusHandler(threading.Thread):
    '''  '''

    def __init__(self, registry, updater, lock, **conf):
        ''' 
        @param	registry	registry.Registry
        @param	updater		update.Updater
	@param	lock		threading.Lock
	@param	conf		kwargs for random config values.
        '''
	# call parent class __init__
        threading.Thread.__init__(self)
        # Updater instance (retrieves status)
        self.updater = updater
        # configs passed as kwargs
        self.conf = conf
        # registry rw lock
        self.lock = lock
	# supybot registry interface (instance of Registry)
        self.reg = registry

    def run(self):
        ''' Entry point for threading.Thread '''
        debug('StatusHandler.run: waiting for a few seconds while i join a channel')
        time.sleep(float(self.conf.get('connect_delay', 10)))
        # if there are no values set in the registry yet set defaults
        if not self.reg.getall():
            self.reg.setall()
	# /me sings to the tune of 'the song that never ends'
	# This is the loop that never ends ...
        while True:
            # catch everything that looks like an exception
            # disable this when debugging nonfatal behavior
	    try:
		debug('StatusHandler.run: checking for updates')
		# Check for a new status.
                message = self.updater.check()
                debug('StatusHandler.run: updater returned message = ', str(message))
		# Check we have all the bits we need. and continue if we do.
                if message:
		    debug('StatusHandler.run: got a real message')
		    # Update the registry.
                    self.reg.setall(message)
		    debug('StatusHandler.run: updated registry')
		# Sleep for a few seconds so we don't go nuts on the processor and http server.
                time.sleep(float(self.conf.get('interval', 30)))
		debug('StatusHandler.run: slept for: ',  self.conf.get('interval', 30))
            except CatchAllExceptions as e:
                # show error in logs
		error('StatusHandler.run: error', e)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
