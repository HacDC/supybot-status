import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.world as world
import supybot.ircmsgs as ircmsgs
import threading
import select
import time
import _strptime # required to prevent import errors
import datetime
import update
import logging
from update import debug, info, warn, error, critical
from include import CatchAllExceptions

logger = logging.getLogger()
logger.setLevel(logging.WARN)

class StatusHandler(threading.Thread):
    # Updater instance
    updater = None
    # Registry of channel states and whether or not to update them.
    channel_states = {}
    # supybot.Irc instance
    irc = None
    # Pointer to the getter for the config of the parrent object.
    registryValue = None
    # Pointer to the setter for the config of the parrent object.
    setRregistryValue = None
    # Token for killing the while True loop. setting this False stops the loop.
    keep_alive = True

    def run(self):
	''' Threaded entry point. Indefinitely polls the remote server for sensor status. '''
	debug('StatusHandler.run')
	debug('StatusHandler.run: waiting for connect')
	while not self.irc.afterConnect:
		pass
        debug('StatusHandler.run: waiting for a few seconds while i join a channel')
	timer = 0
	# time.sleep() seems to do something funny in threads so i'm keeping it to 1 second at a time
	while timer < (self.registryValue('connect_delay') or 10):
		timer += 1
		time.sleep(1)
        debug('StatusHandler.run: i  hope i joined a channel ... continuing')
	# /me sings to the tune of 'the song that never ends'
	# This is the loop that never ends ...
        while True:
	    try:
		# Should we continue? If not then return from the method.
		if not self.keep_alive:
			warn('Exiting StatusHandler loop.')
			return None
		debug('StatusHandler.run: checking for updates')
		# Check for a new status.
                message = self.updater.check()
                debug('StatusHandler.run.message:', str(message))
		# Check we have all the bits we need. and continue if we do.
                if isinstance(message, dict) and message.get('human') and message.get('raw') and message.get('default'):
		    debug('StatusHandler.run: got a message')
		    # Update the status cache (bot config values).
                    self._update_registry(message)
		    debug('StatusHandler.run: updated registry')
		    # Shout the new from the rooftops
                    self._notify_channels()
		    debug('StatusHandler.run: notified channels')
		debug('StatusHandler.run.interval', str(self.registryValue('interval')))
		# Sleep for a few seconds so we don't go nuts on the processor and http server.
                time.sleep(self.registryValue('interval'))
		debug('StatusHandler.run: slept for %d seconds' % self.registryValue('interval'))
            except CatchAllExceptions as e:
	        error('StatusHandler.run: error', e)
                ircmsgs.error('Exception: %s' % repr(e))

    def _notify_channels(self):
	''' Tell the channels we're supposed to tell there has been a change in status. '''
	for irc in world.ircs:
            for channel in [x for x in irc.state.channels if x not in self.registryValue('quiet_channels')]:
            	self._notify_channel(channel)

    def _notify_channel(self, channel):
	''' Tell an individual channel about the change in status. '''
	debug('StatusHandler._notify_channel:', channel)
        if channel not in self.registryValue('quiet_channels'):
	    # If this channel is supposed to recieve updates.
            if self.registryValue('use_notice'):
	       # And it is supposed to get a /NOTICE rather than /PRIVMSG.
	       # Then send a notice.
               msg = ircmsgs.notice(channel, self.registryValue('message_default'))
            else:
	       # Otherwise just use a /PRIVMSG.
               msg = ircmsgs.privmsg(channel, self.registryValue('message_default'))
	    self.irc.queueMsg(msg)

    def close(self):
	''' Stop this thread. '''
    	self.keep_alive = False

    def initialize_status(self, force=False):
	''' Initialize the status cache if needed.
	@param	force	If True it forces the registry to be set.
	'''
	# Get the existing values in the cache.
        reg_vals = [self.registryValue('message_default'),
                self.registryValue('message_human'), 
                self.registryValue('message_raw')]
        debug('StatusHandler._initialize_status.reg_vals:', str(reg_vals))
	# If any cached values are not set or we are forcing an update.
        if (None in reg_vals or '' in [str(x).strip() for x in reg_vals]) or force:
	    # Get a fresh status.
            self.updater.get_status()
	    # And update the cache.
            self._update_registry(self.updater.status.message)

    def _update_registry(self, message):
	''' Update the cached status values 
	@param	message	The message dict of the status
	'''
	debug('StatusHandler._update_registry: updating cached values')
	# Set the message to cache if there is no message in the message dict.
        no_status_message = 'No status available yet.'
	# Set the values of the messages in the cache with their counterparts in the message dict.
        self.setRegistryValue('message_default', message['default'] or no_status_message)
        self.setRegistryValue('message_human', message['human'] or no_status_message)
        self.setRegistryValue('message_raw', message['raw'] or no_status_message)

class Status(callbacks.Plugin):
    '''This plugin checks an http server for updates and announces changes an IRC channel.'''

    threaded = True

    def __init__(self, irc):
	''' <status|updates|sensordata>
	
	Retrieve and display the status the Occupancy Sensor.
	status - display the status in a given format (default is 'default')
	updates - manage whether this bot will announce changes in a channel.
	sensordata - manage the data available to the bot.
	'''
	'''
	@param	irc	supybot IrcMsg instance (from supybot/src/ircmsgs.py).
	'''
        self.__parent = super(Status, self)
        self.__parent.__init__(irc)
	# StatusHandler thread instance
        self.status_handler = StatusHandler()
	# pass stuff along so it can access irc and config related stuff
        self.status_handler.irc = irc
        self.status_handler.registryValue = self.registryValue
        self.status_handler.setRegistryValue = self.setRegistryValue
        self.status_handler.channel_states = {}
        self.status_handler.updater = update.Updater(source_url=self.registryValue('source_url'))
	# Initialize status values so we can have them ready once we start.
        self.status_handler.initialize_status()
	# Set to run in daemon mode (see threading docs)
        self.status_handler.setDaemon(True)
	# Start the Status_handler
        self.status_handler.start()

    def status(self, irc, msg, args, message_format):
	''' [default|human|raw] 

	Display the status of the space in a given format (default is 'default').
	'''
        if not message_format:
            message_format = 'default'
        formats = {'default':self.registryValue('message_default'),
            'human':self.registryValue('message_human'),
            'raw':self.registryValue('message_raw')}
        if message_format not in formats:
            irc.error('''"%s", %s''' % (message_format, ''''%s' is not a valid format. Valid formats are: default, human, raw''' % message_format))
        else:
            irc.reply("%s" % formats.get(message_format) or 'No status is available yet.')

    def updates(self, irc, msg, args, channel, state):
        ''' <on|off>

	Turn updates on or off in the current channel.
	'''
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

    def sensordata(self, irc, msg, args, action):
	''' <reload>

	Manage sensor data.
	reload - forces a reload of the sensor data from the remote source.
	'''
        if action == 'reload':
            self.status_handler.initialize_status(force=True)
            irc.reply('Forcing update of all sensor data')
    
    # wrap methods for use as commands
    updates = wrap(updates, ['inChannel', optional('boolean')])
    status = wrap(status, [optional('text')])
    sensordata = wrap(sensordata, ['text'])

    def die(self):
	''' Stop the plugin entirely. '''
	# Stop the StatusHandler
        self.status_handler.close()
        self.__parent.die()

Class = Status


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
