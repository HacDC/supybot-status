__authors__ = ['haxwithaxe <me@haxwithaxe.net>']

__license__ = 'GPLv3'

import _strptime # required to avoid import errors
import datetime
import include
from include import StatusPluginException
from log import debug, info, warn, error, critical, exception

conf = {'source_url': None}

class StatusParser:
    ''' Prototype/template for status string parsers '''

    def __init__(self, status_string=None, **configs):
        '''
        @param  status_string   The contents of the sensor status upload
        '''
        self.conf = configs

    def set_sensor(self, name, value, sensor_info=None):
        ''' Set the state of a sensor.
        @param  name            Key of the sensor to update.
        @param  value           Value to set.
        @param  sensor_info     dict of label->Sensor's to stash the value in. Defaults to self.sensor_info.
        '''
        pass

    def parse_status(self, status_string=None):
        ''' Parse the whole status message from the sensor status upload.
        @param  status_string   The raw contents of the sensor status upload. Defaults to self.status_string.
        '''
        pass

    def get_status(self, status_string=None):
        ''' Return a Status object based on the remote source.
        @param  status_string   The raw contents of the sensor status upload. Defaults to self.status_string.
        @return                 A SensorStatus instance populated with the data from the sensor status upload.
        '''
        return SensorStatus()

class MirageStatusParser(StatusParser):
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

    def __init__(self, status_string=None, **configs):
	'''
	@param	status_string	The contents of the sensor status upload
	'''
        StatusParser.__init__(status_string=status_string, **configs)
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
        return SensorStatus(self.last_changed_date, self.sensor_info, self.status_string, self._subject_sensors)

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
