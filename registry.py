from log import debug, info, warn, error, critical, exception

class Registry:
    ''' Generic thread safe interface to the supybot registry '''

    def __init__(self, registry=None, lock=None):
        ''' Initialize Registry object
        @param	registry	An object with registryValue() and setRegistryValue() methods.
	@param	lock		threading.Lock instance
        '''
        self.reg = registry
        self.lock = lock

    def acquire(self):
	''' Block while waiting to acquire threading lock '''
	debug('aquiring thread lock')
        while not self.lock.acquire(True): 
            pass

    def release(self):
        ''' Release threading lock '''
	debug('releasing thread lock')
        self.lock.release()

    def get(self, key, default=None):
        ''' Get registry values 
        @param	key	key of the requested item in the supybot registry.
        @param	default	value to return in leu of the requested value (optional)
        @returns	value of entry `key` or `default` (defult None)
        '''
	value = None
	# acquire lock
        self.acquire()
	# try to retrieve the value
        try:
            # retrieve the value or use the default
            value = self.reg.registryValue(key) or default
        finally:
            # be sure to release the lock
            self.release()
        debug('got: "%s" as "%s"' % (key, value))
	return value

    def update(self, key, value):
        ''' Set/update registry entries 
        @param	key	key of the item in the supybot registry to set.
        @param	value	value to set the entry specified by `key` to.
        '''
        # block while aquiring lock
        self.acquire()
	# try to set the value
        try:
            self.reg.setRegistryValue(key, value)
            debug('set: "%s" to "%s"' % (key, value))
        finally:
            # be sure to release the lock
            self.release()
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
