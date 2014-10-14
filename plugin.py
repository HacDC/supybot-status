import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.world as world
import supybot.ircmsgs as ircmsgs
import pykka
import time
import _strptime # required to prevent import errors
import update
from log import debug, info, warn, error, critical, exception
from include import CatchAllExceptions
from alien import get_alien_status

class HandlerWrapper(pykka.ThreadingActor):
    def __init__(self, registry, status, updater):
        super(HandlerWrapper, self).__init__()
        self.registry = registry
        self.status = status
        self.handler = StatusHandler.start(self.actor_ref, registry, updater)
        
    def on_receive(self, message):
        if not message.get('message'): return None
        if message.get('message') == 'status':
            self.status.setall(message.get('status'))
        elif message.get('message') == 'error':
            pass
        

class StatusHandler(pykka.ThreadingActor):

    def __init__(self, parent, registry, updater):
        super(StatusHandler, self).__init__()
        self.parent = parent
        # Updater instance
        self.updater = updater
        # Pointer to the config object of the parent object.
        self.registry = registry

    def on_start(self):
        debug('StatusHandler.run: waiting for a few seconds while i join a channel')
	timer = 0
	# time.sleep() seems to do something funny in threads so i'm keeping it to 1 second at a time
        timeout = self.registry.get('connect_delay', 10)
	while timer < self.timeout:
		timer += 1
		time.sleep(1)
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
                    self.parent.tell({'message':'status', 'status':message})
		    debug('StatusHandler.run: updated registry')
		debug('StatusHandler.run.interval', str(self.registry.get('interval')))
		# Sleep for a few seconds so we don't go nuts on the processor and http server.
                time.sleep(self.registry.get('interval', 30))
		debug('StatusHandler.run: slept for %d seconds' % self.registry.get('interval', 30))
            except CatchAllExceptions as e:
	        error('StatusHandler.run: error', e)
                self.parent.tell({'message':'error','error':'Exception: %s' % repr(e)})


class Registry:

    def __init__(self, registry=None):
        self.reg = registry

    def get(self, key, default=None):
        return self.reg.registryValue(key) or default

    def update(self, key, value):
        self.reg.setRegistryValue(key, value)


class StatusRegistry(Registry):

    status_keys = ['message_default', 'message_human', 'message_raw', 'time_fetched']

    def getall(self):
	# Get the existing values in the cache.
        return [self.get(x) for x in self.status_keys]

    def setall(self, message):
	''' Update the cached status values 
	@param	message	The message dict of the status
	'''
	debug('StatusRegistry: updating cached values')
        if not message: return None
	# Set the message to cache if there is no message in the message dict.
        no_status_message = 'No status available yet.'
	# Set the values of the messages in the cache with their counterparts in the message dict.
        self.update('message_default', message.get('default', no_status_message))
        self.update('message_human', message.get('human', no_status_message))
        self.update('message_raw', message.get('raw', no_status_message))
	self.update('time_fetched', message.get('time_fetched', 0))

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
        self.statusreg = StatusRegistry(self)
	# StatusHandler thread instance
        self.status_handler = StatusHandler.start(Registry(self), self.statusreg, update.Updater(source_url=self.registryValue('source_url')))

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
	# 	command='PRIVMSG',
	# 	args=('#HacDC', '.space')
	# 	),
	# 'args': [], 
	# 'message_format': None}

        @param  irc     	supybot supybot.callbacks.NestedCommandsIrcProxy
	@param	msg		supybot IrcMsg instance (from supybot/src/ircmsgs.py).
	@param	args		command arguments as an array
	@param	message_format	message format argument
	'''
        self.__debug_callback_args(irc=irc, msg=msg, args=args, message_format=message_format)
        if not message_format:
            message_format = 'default'
        formats = {'default':self.registryValue('message_default'),
            'human':self.registryValue('message_human'),
            'raw':self.registryValue('message_raw'),
	    'alien':get_alien_status() }
        if message_format not in formats:
	    nick = msg.prefix.split('!',1)[0].strip(':')
	    irc.reply('''I'm sorry %s. I'm afraid I can't do that.''' % nick)
        else:
	    if time.mktime(time.gmtime())-self.registryValue('time_fetched') > self.registryValue('max_status_age'):
		self.status_handler.initialize_status(force=True)
		debug('Fetching fresh status ')
            irc.reply("%s" % formats.get(message_format) or 'No status is available yet.')

    def updates(self, irc, msg, args, channel, state):
        ''' <on|off>

	Turn updates on or off in the current channel.
	on - enable automatic status change notifications
	off - disable automatic status change notifications

        @param  irc             supybot supybot.callbacks.NestedCommandsIrcProxy
        @param  msg             supybot IrcMsg instance (from supybot/src/ircmsgs.py)
        @param  args            irc message line as array?
        @param  channel  	channel argument
        @param  state		state argument
	'''
        self.__debug_callback_args(irc=irc, msg=msg, args=args, channel=channel, state=state)
        qchannels = self.registryValue('quiet_channels')
        if state is None:
	    if channel in self.registryValue('quiet_channels'):
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
	    self.setRegistryValue('quiet_channels', qchannels)

    # wrap methods for use as commands
    updates = wrap(updates, ['inChannel', 'admin', optional('boolean')])
    status = wrap(status, [optional('text')])

    def die(self):
	''' Stop the plugin entirely. '''
	# Stop the StatusHandler
        self.status_handler.close()
        self.__parent.die()

Class = Status


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
