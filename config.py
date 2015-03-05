import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Status', True)

Status = conf.registerPlugin('Status')
conf.registerGlobalValue(Status, 'use_notice',
    registry.Boolean(False, '''Use notices instead of privmsgs'''))

conf.registerGlobalValue(Status, 'source_url',
        registry.String('http://api.hacdc.org/OccSensor.txt', '''Source to check for updates.'''))

conf.registerGlobalValue(Status, 'quiet_channels',
                            registry.SpaceSeparatedListOfStrings(' #hacdcbot2 ', '''Channels to not announce changes in.'''))

conf.registerGlobalValue(Status, 'debug_channel',
                    registry.String('#hacdcbot', '''Channel to print debug info to.'''))

conf.registerGlobalValue(Status, 'interval',
                    registry.Integer(3, '''Interval to check remote status in seconds'''))

conf.registerGlobalValue(Status, 'connect_delay',
                    registry.Integer(15, '''Number of seconds to wait before announcing a new status when connecting to the IRC server. This is the number of seconds to wait from startup not after joining channels.'''))

conf.registerGlobalValue(Status, 'max_status_age',
                    registry.Integer(30, '''Maximum age of the cached status in minutes. The status will be fetched before replying to the status command if it is older than this.'''))

conf.registerGlobalValue(Status, 'hunterkll_safe',
                    registry.Boolean(False, '''Make the mean extended unicode go away T_T.'''))

conf.registerGlobalValue(Status, 'parked',
                    registry.Boolean(False, '''Display the parked_message instead of the status.'''))

conf.registerGlobalValue(Status, 'parked_message',
                    registry.String('Status unavailable. Call 202-556-4225 to check if the space is open.', '''Message printed inplace of the status when in parked mode.'''))


# state cache
conf.registerGlobalValue(Status, 'message_default',  registry.String('no status yet', '''Default status message'''))
conf.registerGlobalValue(Status, 'message_human',  registry.String('no status yet', '''More verbose human readable status message'''))
conf.registerGlobalValue(Status, 'message_raw',  registry.String('no status yet', '''Status message as it comes from the sensor'''))
conf.registerGlobalValue(Status, 'time_fetched',
                    registry.Integer(0, '''Unix timestamp of the time of the most recently fetched status'''))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
