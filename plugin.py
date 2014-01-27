import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.world as world
import supybot.ircmsgs as ircmsgs
import threading
import SocketServer
import select
import time
import _strptime # required to prevent import errors
import datetime
import update

class StatusHandler(threading.Thread):
    updater = None
    channel_states = {}
    registryValue = None
    setRregistryValue = None
    keep_alive = True

    def run(self):
        try:
            while self.keep_alive:
                message = self.updater.check()
                if isinstance(message, dict) and message.get('human') and message.get('raw') and message.get('default'):
                    self._update_registry(message)
                    self._notify_channels()
                time.sleep(self.registryValue('interval'))
            return None
        except BaseException as e:
            irc.error('Exception: %s' % repr(e))        

    def _notify_channels(self):
        for channel in self.registryValue('channels'):
            self._notify_channel(channel)

    def _notify_channel(self, channel):
        if self.channel_states.get(channel, "on") == "on":
            if self.registryValue('use_notice'):
               msg = ircmsgs.notice(channel, self.registryValue('message_default'))
            else:
               msg = ircmsgs.privmsg(channel, self.registryValue('message_default'))
               for irc in world.ircs:
                  if channel in irc.state.channels:
                     irc.queueMsg(msg)

    def close(self):
        self.keep_alive = False

    def _update_registry(self, message):
        self.setRegistryValue('message_default', message['default'])
        self.setRegistryValue('message_human', message['human'])
        self.setRegistryValue('message_raw', message['raw'])

class Status(callbacks.Plugin):
    '''This plugin checks an http server for updates and announces changes an IRC channel.'''
    threaded = True
    def __init__(self, irc):
        self.__parent = super(Status, self)
        self.__parent.__init__(irc)
        self.status_handler = StatusHandler()
        self.status_handler.registryValue = self.registryValue
        self.status_handler.setRegistryValue = self.setRegistryValue
        self.status_handler.channel_states = {}
        self.status_handler.updater = update.Updater(source_url=self.registryValue('source_url'))
        self.status_handler.setDaemon(True)
        self.status_handler.start()

    def status(self, irc, msg, args, message_format):
        if not message_format:
            message_format = 'default'
        formats = {'default':self.registryValue('message_default'),
            'human':self.registryValue('message_human'),
            'raw':self.registryValue('message_raw')}
        if message_format not in formats:
            irc.error('''"%s", %s''' % (message_format, ''''%s' is not a valid format. Valid formats are: default, human, raw''' % message_format))
        else:
            irc.reply("%s" % formats.get(message_format))

    def updates(self, irc, msg, args, channel, state):
        '''Turn updates on or off in the current channel.'''
        if state is None:
            irc.reply("Updates for %s: %s" % (channel,
                self.status_handler.channel_states.get(channel, "on")))
        else:
            if state:
                self.status_handler.channel_states[channel] = "on"
                irc.reply("Updates for %s are now on" % channel )
            else:
                self.status_handler.channel_states[channel] = "off"
                irc.reply("Updates for %s are now off" % channel )

    updates = wrap(updates, ['inChannel', optional('boolean')])
    status = wrap(status, [optional('text')])

    def die(self):
        self.status_handler.close()
        self.__parent.die()

Class = Status


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
