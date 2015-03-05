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
from statushandler import StatusHandler
from statusregistry import StatusRegistry
from update import Updater
from log import debug, info, warn, error, critical, exception
from alien import get_alien_status

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
	updater = Updater(source_url=self.reg.get('source_url'))
        self.status_handler = StatusHandler(self.reg, updater, self.lock)
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
        if self.reg.get('hunterkll_safe', False):
            alien_msg = ''' it was swamp gas ... '''
        else:
            alien_msg = get_alien_status()
        formats = {'alien':alien_msg, 'default':'', 'human':'', 'raw':''}
        msgs = self.reg.getall()
        if msgs:
            formats.update(msgs)
        if  self.reg.get('parked', False):
            formats = {'alien': alien_msg, 'default': self.reg.get('parked_message'), 'human': self.reg.get('parked_message'), 'raw': self.reg.get('parked_message')}
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
