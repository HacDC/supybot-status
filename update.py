__authors__ = ['haxwithaxe <me@haxwithaxe.net>']

__license__ = 'GPLv3'

import json
import time
import _strptime # required to avoid import errors
import datetime
import sys
import urllib2
import include
from log import debug, info, warn, error, critical, exception

conf = {'source_url': None}

def set_TZ(tz='GMT'):
    os.environ['TZ'] = tz
    time.tzset()

def set_GMT():
    ''' Set the current timezone to GMT '''
    set_TZ()

def set_EDT():
    ''' Set the current timezone to EST/EDT '''
    set_TZ('US/Eastern')

class Updater:
    ''' Update the bot from a remote status source '''

    def __init__(self, last_status_string=None, **passed_conf):
        global conf
	# add the config values passed to our dict of configs
        conf.update(passed_conf)
	# The url to fetch the sensor data from
        self.source = conf.get('source_url') or self.__missing_url_config()
	# The number of seconds to sleep at the end of each loop
        self.interval_s = conf.get('interval_s')
	# The Status retrived before the most recent Status
        self.last_status = None
	# The most recent Status retrived
        self.status = None
	# Token indicating if this is the first time through the loop
        self._first_run = True

    def __missing_url_config(self):
	''' freak out if there is no url to get data from '''
        raise Exception('Missing source_url configuration value')

    def check(self):
        ''' Get the latest status, test if it's new, update the bot if it is, and sleep so we don't go too fast. 
        return None if no change or self.status.message if there is a new status
        '''
	info('Updater.check: checking')
	# get the Status for the latest sensor upload
        self.get_status()
        debug('Updater.check: self.status:', repr(self.status), '\nself.last_status:', repr(self.last_status))
	# Test if the Status is a newer status than the last one fetched
        if self.is_new_status():
            info('Updater.check: new status')
	    # if it is then return the messages for use by the bot
            return self.status.message
	debug('Updater.check: old status')
        return None

    def get_status(self):
        ''' Grab the status from the sensor
	Sets self.last_status and  self.status
	'''
        parser = StatusParser()	# get a new parser
	status_string = self._fetch_data()	# grab the contents of the sensor upload
	# if there is a response from the server
        if status_string:
            debug('Updater.get_status.status_string(from server):', status_string)
	    # parse the response
            status = parser.get_status(status_string)
	    # and update the values with the resulting Status object
            self.last_status = self.status
            self.status = status
            debug('Updater.get_status.status(parsed):', str(self.status))
	debug('Updater.get_status: done')

    def _fetch_data(self):
	''' Grab the sensor data from the sensor upload url
	@return			status data string if available otherwise return None
	'''
	debug('Updater._fetch_data.source:', self.source)
	try:
	    # fetch raw data from the server
	    request = urllib2.Request(url=self.source)
            reply = urllib2.urlopen(request)
	    debug('Updater._fetch_data.reply:', str(reply))
	    # if the http code indicates a successful request extract the data from the reply
            if reply.getcode() == 200:
	        debug('Updater._fetch_data: reply is good')
                return reply.read()
	except urllib2.URLError as e:
	    warn('Updater._fetch_data: ',e)
	return None

    def is_new_status(self):
        ''' Test if the most recently grabbed status is newer than the last one 
	@return			True if status has changed or False if it has not.
	'''
	# If both the current and previous statuses exist check if the current is different from the pervious
        if self.status and self.last_status and self.status.time_changed and self.last_status.time_changed:
            debug('Updater.is_new_status: both statuses exist')
            if self.status >= self.last_status and self.status != self.last_status:
        	# if the new status is newer than or the same age as the last status found
	        # and if they are not equal there has been a status change it's new
                debug('Updater.is_new_status: new status')
                return True
            elif self._first_run:
		# if this is the first run on start up pretend this is a new 
		# status so we notify of the current status
		debug('Updater.is_new_status: first run')
		# make sure we don't think subsequent runs are the first
                self._first_run = False
                return True
        debug('Updater.is_new_status: old status')
        return False

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


class Status:
    ''' Status class
    For the storage and comparison of status states.
    '''

    state_field = 'lights' # key to retrive the overal state (open/closed) from Status.info

    def __init__(self, time_changed, sensors, source_string, info):
	'''
	@param	time_changed	The datatime instance with the date the sensor data was changed.
	@param	sensors		A dict of Sensor instances.
	@param	source_string	The raw sensor data string.
	@param	info		General info about the sensor status including open/closed state.
	'''
        debug('Status(sensors)', *([str(x) for x in sensors]))
        self.time_changed = time_changed
	# Set a bare message dict
	self.message = {'raw':None, 'human':None, 'default':None, 'changed':None}
        self.info = info
        self.sensors = sensors
        self.source_string = source_string
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


class StatusParser:
    ''' Parse the status returned by the current sensor in "WTF" format :P
    message format(bash):
	 subject: Lights=$lightsOn
	 body: GPIO4=$GPIO4;GPIO5=$GPIO5;FA3=$FA3;FA4=$FA4;FA5=$FA5
	 date: $( echo $(date "+%A, %b %d at %l:%M %p") | tr ' ' '_') 
		aka %A,_%b_%d_at_%l:%M_%p and TZ='EST5EDT,M3.2.0,M11.1.0'
    message format (example):
	 date=Monday,_Jan_20_at_12:17_AM
	 subject=Lights=false
	 body=FA3=false;FA4=false;FA5=false
    '''
    # Format of the date as passed to us by the sensor
    _date_format = "%A,_%b_%d_at_%I:%M_%p" # C %l == py %I
    # Field seperator (for items on a line).
    _field_sep = ";"
    # Key value seperator (for items within a field).
    _key_val_sep = "="
    # dict of label->Sensor's to find in the 'body' portion of the status string
    _body_sensors = {'gpio4': Sensor('GPIO4', None, None), 'gpio5': Sensor('GPIO5', None, None), 'fa3': Sensor('hall_light_on', 'hall light'), 'fa4': Sensor('main_light_on', 'main room light'), 'fa5': Sensor('work_light_on','work room light')}
    # dict of label->Sensor's to find in the 'subject' portion of the status string
    _subject_sensors = {'lights': Sensor('any_lights_on', 'one or more lights')}

    def __init__(self, status_string=None):
	'''
	@param	status_string	The contents of the sensor status upload
	'''
	# All the values collected from the status_string.
	self.collected_values = {}
	# dict of label->Sensor's to stash the values found
	self.sensor_info = self._body_sensors
	# The value of the 'date' field as a datetime object
	self.last_changed_date = None
	# the raw status string from the sensor status upload
	self.status_string = status_string

    def set_sensor(self, name, value, sensor_info=None):
        ''' Set the state of a sensor.
	@param	name		Key of the sensor to update.
	@param	value		Value to set.
	@param	sensor_info	dict of label->Sensor's to stash the value in. Defaults to self.sensor_info.
	'''
        sensor_info = sensor_info or self.sensor_info
	sensor_info[name].set(value)

    def _split_dict(self, string):
        ''' Split a string formated as key-value pairs into a dict.
	@param	string	String containing a series of key-value pairs, formatted using the seperators specified above.
	@return		dict representation of string parameter.
	'''
	# Split the sting into a list of strings, and then split each string into a key value pair.
        return dict(self._split_key_val(pair) for pair in self._split_list(string))

    def _split_key_val(self, string):
        ''' Split a string formatted as a key-value pair.
	@param	string	String formatted as a key-value pair, formatted using the seperators specified above.
	@return         A list representation of the key-value pair in the string parameter.
	'''
        return [item.strip() for item in string.strip().split('=',1)]

    def _split_list(self, string):
        ''' Split a string formatted as a list into a list
	@param  string  A list represented as a string, formatted using the seperators specified above.
        @return         A list representation of the list in the string parameter.
	'''
	return [item.strip() for item in string.strip().split(';')]

    def _parse_body_field(self, string):
        ''' Parse an individual item in the 'body' field of the sensor status upload.
	Sets self.sensor_info value via self.set_sensor().
	@param	string	String representing an item in the 'body' field of the sensor status upload.
	'''
        sub = string.split(self._key_val_sep, 1)
        debug('StatusParser._parse_body.sub', repr(sub))
	if len(sub) == 2 and sub[0].lower() in self._body_sensors and sub[1].lower() in ('true', 'false'):
	    self.set_sensor(sub[0].lower(), sub[1].lower())

    def _parse_body(self, body_string):
        ''' Parse the 'body' field.
	Sets self.sensor_info value via self.set_sensor().
	@param	body_string	String representation of the dict in the body field of the sensor status upload.
	@return 		dict representation of the body field of the sensor status upload.
	'''
        if len(body_string) >= 1:
	    for field in self._split_list(body_string):
		self._parse_body_field(field)
                debug('body field:',field)

    def _parse_subject(self, subject_string):
        ''' Parse the 'subject' field.
        Sets self.sensor_info value via self.set_sensor().
	@param	subject_string	String representation of the key-value pair in the 'subject' field of the sensor status upload.
	'''
        sub = self._split_key_val(subject_string)
	if len(sub) == 2 and sub[0].lower() and sub[1].lower() in ('true', 'false', 'on', 'off'):
	    self.set_sensor(sub[0].lower(), sub[1].lower(), self._subject_sensors)

    def _parse_date(self, date_string):
        ''' Parse the 'date' field.
	Sets self.last_changed_date.
	@param	date_string	String representation of the date in the 'date' field of the sensor status upload.
	'''
        debug('StatusParser._parse_date.date_string:', date_string)
        try:
	    # turn the date string into a datetime instance and add a year field because it is missing from the data from the sensor
            self.last_changed_date = datetime.datetime.strptime(date_string, self._date_format).replace(year=datetime.datetime.now().year)
            debug('StatusParser._parse_date.last_changed_date:', repr(self.last_changed_date))
	except Exception as e:
            error(e)
	    self.last_changed_date = None

    def parse_status(self, status_string=None):
        ''' Parse the whole status message from the sensor status upload.
	@param	status_string	The raw contents of the sensor status upload. Defaults to self.status_string.
	'''
        if status_string:
	    # If status_string was passed use it instead of self.status_string.
            self.status_string = status_string
	# Split the multiline string into a list by newlines.
        for line in self.status_string.strip().split('\n'):
	    # Split the line into key-value pairs
	    line_parts = self._split_key_val(line)
	    if len(line_parts) == 2:
		# If the line has 2 components
		# Use the lowercase version of the first as the key
                key = line_parts[0].strip().lower()
		# And the second as the value (with leading and trailing spaces removed)
                val = line_parts[1].strip()
		# based on the key parse the value with the appropriate parser
		if key == 'date':
		    self._parse_date(val)
		elif key == 'subject':
		    self._parse_subject(val)
		elif key == 'body':
		    self._parse_body(val)

    def get_status(self, status_string=None):
        ''' Return a Status object based on the remote source.
        @param  status_string   The raw contents of the sensor status upload. Defaults to self.status_string.
	@return			A Status instance populated with the data from the sensor status upload.
	'''
	# Parse the input string and set self.sensor_info with the result
        self.parse_status(status_string)
        debug('StatusParser.get_status,sensor_info', str(self.sensor_info))
	# Populate a Status instance and return it.
        return Status(self.last_changed_date, self.sensor_info, self.status_string, self._subject_sensors)

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
