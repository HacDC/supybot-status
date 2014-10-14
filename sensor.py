__authors__ = ['haxwithaxe <me@haxwithaxe.net>']

__license__ = 'GPLv3'

import time
import _strptime # required to avoid import errors
import include
from include import StatusPluginException
from log import debug, info, warn, error, critical, exception


class Sensor:
    ''' Stores the state of a sensor '''
    def __init__(self, id, label, boolean=None):
	'''
	@param	id	String referencing a key in the sensor data
	@param	label	Human readable string
	@param	boolean	valid values are: 'on', 'true', True, 'off', False, 'false', None
	'''
	# The label used in the raw sensor data for the field
        self.id = id
	# The string for humans to see as the label
	self.label = label
	# The on/off state of the sensor as reported (on==True, off==False)
	self.boolean = None
	# sanely set self.boolean with the value passed to us
        self.set_boolean(boolean)

    def set(self, value):
        ''' Set the state of the sensor appropriately 
	Sets self.boolean via self.set_boolean()
	@param	value	Value to set self.boolean to. see Sensor.set_boolean() for valid values
	'''
        self.set_boolean(value)

    def set_boolean(self, value):
        ''' Set self.boolean with a bool version of the sensor state
	Sets self.boolean via self.set_boolean()
        @param	value	Value to set self.boolean to. Valid values are: 
			'on', 'true', True, 'off', False, 'false', or None.
			None is for unset or indeterminate state.
        '''
	# map the supplied value to True, False, or None
        self.boolean = {'on':True, True:True, 'true':True, 'off':False, False:False, 'false':False, None:None}[value]

    @property
    def boolstr(self):
        ''' Return an appropriate string representation of the sensor state
	@return		A string representation of Sensor.boolean. True == 'on', False == 'off', None == 'unknown'
	'''
	# For future reference: return {True:'on', 'true':'on', False:'off', 'false':'off', None:'unknown'}[self.boolean]
        return {True:'on', False:'off', None:'unknown'}[self.boolean]

    def __dict__(self):
        ''' Return a dict representation of the Sensor object
	@return		{'id': self.id, 'label': self.label, 'boolean': self.boolean}
	'''
        return {'id': self.id, 'label': self.label, 'boolean': self.boolean}

    def __str__(self):
	return '{%s:%s, %s:%s, %s:%s}' % ('id', self.id, 'label', self.label, 'boolean', self.boolean)

    def __eq__(self, other):
        ''' Test equality of the state of two sensors 
	@return		True if values of respective self.boolean are equal, otherwise False.
	'''
        return self.boolean == other.boolean


class SensorStatus:
    ''' SensorStatus class
    For the storage and comparison of status states.
    '''

    state_field = 'lights' # key to retrive the overal state (open/closed) from Status.info

    def __init__(self, time_changed=None, sensors={}, source_string=None, info=None):
	'''
	@param	time_changed	The datatime instance with the date the sensor data was changed.
	@param	sensors		A dict of Sensor instances.
	@param	source_string	The raw sensor data string.
	@param	info		General info about the sensor status including open/closed state.
	'''
        debug('Status(sensors)', *([str(x) for x in sensors]))
        self.time_changed = time_changed
	# Set a bare message dict
	self.message = {'raw':None, 'human':None, 'default':None, 'changed':None, 'time_fetched':0}
        self.info = info
        self.sensors = sensors
        self.source_string = source_string
        if time_changed and sensors and source_string and info: 
	    # Populate the messages in the message.
            self._set_message()
        debug('Status.sensors', ', '.join(['%s: %s' % (k, str(v)) for k,v in self.sensors.items()]))

    def _sensor_status(self):
        ''' Return a human friendly string representing the status of all the sensors '''
        return ', '.join(['%s is %s' % (k.label, k.boolstr) for k in self.sensors.values() if k.label])

    def _set_message(self):
        ''' Set all formats of the status messages
	Sets values for 'raw', 'human', 'default', 'changed' in Status.message.
	'''
	self.message['changed'] = self.time_changed.strftime('%s')
        self._set_raw_message()
        self._set_human_message()
        self._set_default_message()

    def _set_default_message(self):
        ''' Set the default message with the more traditional format of status 
	Sets value for 'default' in Status.message.
	'''
        if self.time_changed:
            date = self.time_changed.strftime('%I:%M%p %A %d %b')
        else:
            date = 'date unknown'
        self.message['default'] = include.default_msg % ({True:'open', False:'closed'}[self.info.get('lights').boolean], date)

    def _set_human_message(self):
        ''' Set the human friendly message to a more verbose readout of the status.
	Sets value for 'human' in Status.message.
	'''
        self.message['human'] = self._sensor_status()

    def _set_raw_message(self):
        ''' Set the 'raw' message to be the source text.
	Sets value for 'raw' in Status.message.
	'''
        self.message['raw'] = self.source_string

    def _set_time_fetched(self):
	''' Set the time this object was created (which should be the time it was fetched) '''
	self.message['time_fetched'] = int(time.mktime(time.gmtime()) or 0)

    def __dict__(self):
        ''' Return a representation of this instance as a dict.
	@return		A representation of this instance as a dict with the keys of: 
			'time_changed', 'message', 'sensors', 'info', and 'source_string'.
	'''
        return {'time_changed': self.time_changed, 
		'message': self.message, 
		'sensors': dict((k, v.__dict__) for k,v in self.sensors.items()), 
		'info': self.info,
		'source_string':self.source_string}

    def __str__(self):
	 return '{%s: %s, %s: %s, %s: %s, %s: %s, %s: %s}' % ('time_changed', self.time_changed, 'message', self.message, 'sensors', dict((k, v.__dict__) for k,v in self.sensors.items()), 'info', self.info, 'source_string', self.source_string)

    def __eq__(self, other):
        ''' Test if the state of this status is the same value as the other state.
	@param	other	Another instance of Status.
	@return		True if Status.info.get(Status.state_field) is the same for both instances, otherwise False.
	'''
        return self.info.get(self.state_field) == other.info.get(self.state_field)

    def __ne__(self, other):
	''' Test if the state of this status is a different value from the other state
	@param	other	Another instance of Status.
	@return         False if Status.info.get(Status.state_field) is the same for both instances, otherwise True.
	'''
        return not self.__eq__(other)

    ''' The following test the time the status was updated rather than the value '''

    def __lt__(self, other):
	''' Test if this status is older than the other state.
	@param  other	Another instance of Status.
        @return         True if self.time_changed is less (older) than other.time_changed, otherwise False.
	'''
	return self.time_changed < other.time_changed

    def __le__(self, other):
	''' Test if this status is older than or the same age as the other state
	@param  other   Another instance of Status.
        @return         True if self.time_changed is less (older) than or equal 
			too (same age as) other.time_changed, otherwise False.
	'''
        return self.time_changed <= other.time_changed

    def __gt__(self, other):
        ''' Test if this status is newer than the other state
        @param  other   Another instance of Status.
        @return         True if self.time_changed is greater (newer) than other.time_changed, otherwise False.
	'''
        return self.time_changed > other.time_changed

    def __ge__(self, other):
        ''' Test if this status is newer than or the same age as the other state.
        @param  other   Another instance of Status.
        @return         True if self.time_changed is greater (newer) than or equal 
                        too (same age as) other.time_changed, otherwise False.
	'''
        return self.time_changed >= other.time_changed

    def newer(self, other):
	''' If this status is newer than the `other` status 
	@param	other	Another instance of Status.
	@return		True if time_changed is greater than the other time changed, otherwise False.
	'''
        return self.__gt__(other)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
