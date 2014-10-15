import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.world as world
import supybot.ircmsgs as ircmsgs
import threading
import time
import _strptime # required to prevent import errors
import update
from log import debug, info, warn, error, critical, exception
from include import CatchAllExceptions
from alien import get_alien_status

debug = info

class StatusHandler(threading.Thread):

    def __init__(self, registry, updater, lock, **conf):
        threading.Thread.__init__(self)
        # Updater instance (retrieves status)
        self.updater = updater
        # configs passed as kwargs
        self.conf = conf
        # registry rw lock
        self.lock = lock
        self.reg = registry

    def run(self):
        debug('StatusHandler.run: waiting for a few seconds while i join a channel')
	timer = 0
        time.sleep(float(self.conf.get('connect_delay', 10)))
        if not self.reg.getall():
            self.reg.setall()
	# /me sings to the tune of 'the song that never ends'
	# This is the loop that never ends ...
        while True:
	    try:
		debug('StatusHandler.run: checking for updates')
		# Check for a new status.
                message = self.updater.check()
                debug('StatusHandler.run.message:', str(message))
		# Check we have all the bits we need. and continue if we do.
                if message:
		    debug('StatusHandler.run: got a message')
		    # Update the status cache (bot config values).
                    self.reg.setall(message)
		    debug('StatusHandler.run: updated registry')
		debug('StatusHandler.run.interval', str(self.conf.get('interval', 30)))
		# Sleep for a few seconds so we don't go nuts on the processor and http server.
                time.sleep(float(self.conf.get('interval', 30)))
		debug('StatusHandler.run: slept for %d seconds' % self.conf.get('interval', 30))
            except CatchAllExceptions as e:
		error('StatusHandler.run: error', e)


class Registry:

    def __init__(self, registry=None, lock=None):
        self.reg = registry
        self.lock = lock

    def acquire(self):
	''' block while waiting to acquire thread lock '''
	debug('aquiring thread lock')
        while not self.lock.acquire(True): 
            pass

    def release(self):
        '''  '''
	debug('releasing thread lock')
        self.lock.release()

    def get(self, key, default=None):
        '''  '''
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
        '''  '''
        # block while aquiring lock
        self.acquire()
	# try to set the value
        try:
            self.reg.setRegistryValue(key, value)
            debug('set: "%s" to "%s"' % (key, value))
        finally:
            # be sure to release the lock
            self.release()


class StatusRegistry(Registry):

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

class Status(callbacks.Plugin):
    '''This plugin checks an http server for updates and announces changes an IRC channel.'''

    threaded = True

    def __init__(self, irc):
	''' <status|updates|sensordata>
	
	Query occupancy sensor status.
	status - display the status in a given format (default is 'default')
	updates - manage whether this bot will announce changes in a channel.

	@param	irc	supybot IrcMsg instance (from supybot/src/ircmsgs.py).
	'''
        self.__parent = super(Status, self)
        self.__parent.__init__(irc)
        self.lock = threading.Lock()
        self.reg = StatusRegistry(self, self.lock)
	# StatusHandler thread instance
        self.status_handler = StatusHandler(self.reg, update.Updater(source_url=self.reg.get('source_url')), self.lock)
        self.status_handler.start()

    def __debug_callback_args(self, *args,**kwargs):
	args_l = [str(x) for x in args] + ['%s:%s' % (x,y) for x,y in kwargs.items()]
        debug('command callback arguments:', *args_l)

    def status(self, irc, msg, args, message_format):
	''' [default|human|raw] 

	Display the status of the space in a given format (default is 'default' ... who'da thunk).
	default - as seen in the automatic status change notifications
	human - a human friendly representation of the state of individual sensors
	raw - the verbatim string retrived from the sensor's upload

	# method arguments as dict for reference
	# {'irc': '<supybot.callbacks.NestedCommandsIrcProxy object at 0xa26e1ec>',
	# 'msg': IrcMsg(
	#	prefix="nick!~username@host",
	#	command='PRIVMSG',
	#	args=('#HacDC', '.space')
	#	),
	# 'args': [], 
	# 'message_format': None}

        @param  irc		supybot supybot.callbacks.NestedCommandsIrcProxy
	@param	msg		supybot IrcMsg instance (from supybot/src/ircmsgs.py).
	@param	args		command arguments as an array
	@param	message_format	message format argument
	'''
        self.__debug_callback_args(irc=irc, msg=msg, args=args, message_format=message_format)
        if not message_format:
            message_format = 'default'
        formats = {'alien':get_alien_status(), 'default':'', 'human':'', 'raw':''}
        msgs = self.reg.getall()
        if msgs:
            formats.update(msgs)
        if message_format not in formats:
	    nick = msg.prefix.split('!',1)[0].strip(':')
	    irc.reply('''I'm sorry %s. I'm afraid I can't do that.''' % nick)
        else:
	    if time.mktime(time.gmtime())-self.reg.get('time_fetched',0) > self.reg.get('max_status_age'):
		self.reg.setall()
            irc.reply("%s" % formats.get(message_format) or 'No status is available yet.')

    def updates(self, irc, msg, args, channel, state):
        ''' <on|off>

	Turn updates on or off in the current channel.
	on - enable automatic status change notifications
	off - disable automatic status change notifications

        @param  irc             supybot supybot.callbacks.NestedCommandsIrcProxy
        @param  msg             supybot IrcMsg instance (from supybot/src/ircmsgs.py)
        @param  args            irc message line as array?
        @param  channel		channel argument
        @param  state		state argument
	'''
        self.__debug_callback_args(irc=irc, msg=msg, args=args, channel=channel, state=state)
        qchannels = self.reg.get('quiet_channels')
        if state is None:
	    if channel in self.reg.get('quiet_channels'):
		state = "off"
	    else:
		state = "on"
            irc.reply("Updates for %s: %s" % (channel, state))
        else:
            if state == "on":
                if channel in qchannels:
		    qchannels.pop(channel)
                irc.reply("Updates for %s are now on" % channel )
            else:
		if channel not in qchannels:
		    qchannels.append(channel)
                irc.reply("Updates for %s are now off" % channel )
	    self.reg.update('quiet_channels', qchannels)

    # wrap methods for use as commands
    updates = wrap(updates, ['inChannel', 'admin', optional('boolean')])
    status = wrap(status, [optional('text')])

    def die(self):
	''' Stop the plugin entirely. '''
	# Stop the StatusHandler
        self.status_handler.join()
        self.__parent.die()

Class = Status


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
