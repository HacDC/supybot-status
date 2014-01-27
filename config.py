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
        registry.String('http://api.hacdc.org/OccSensor.txt', '''Source to check for updates'''))

conf.registerGlobalValue(Status, 'channels',
                            registry.String(['#hacdcbot'], ''''''))

conf.registerGlobalValue(Status, 'debug_channel',
                    registry.String('#hacdcbot', ''''''))

conf.registerGlobalValue(Status, 'interval',
                    registry.Integer(3, '''Interval to check remote status in seconds'''))

# state cache
conf.registerGlobalValue(Status, 'message_default',  registry.String('no status yet', '''Default status message'''))
conf.registerGlobalValue(Status, 'message_human',  registry.String('no status yet', '''More verbose human readable status message'''))
conf.registerGlobalValue(Status, 'message_raw',  registry.String('no status yet', '''Status message as it comes from the sensor'''))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

