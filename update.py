__authors__ = ['haxwithaxe <me@haxwithaxe.net>']

__license__ = 'GPLv3'

import json
import time
import _strptime
import datetime
import sys
import urllib2

conf = {'source_url': None}

DEBUG = True

def set_TZ(tz='GMT'):
    os.environ['TZ'] = tz
    time.tzset()

def set_GMT():
    ''' Set the current timezone to GMT '''
    set_TZ()

def set_EDT():
    ''' Set the current timezone to EST/EDT '''
    set_TZ('US/Eastern')

def debug(*strings):
    ''' Conditionally print text to STDOUT '''
    if DEBUG:
        print(' '.join(strings))

class Updater:
    ''' Update the bot from a remote status source '''
    def __init__(self, last_status_string=None, **passed_conf):
        global conf
        conf.update(passed_conf)
        self.source = conf.get('source_url') or self.__missing_url_config()
        self.interval_s = conf.get('interval_s')
        self.last_status = None
        self.status = None
        self._first_run = True

    def __missing_url_config(self):
        raise Exception('Missing source_url configuration value')

    def check(self):
        ''' Get the latest status, test if it's new, update the bot if it is, and sleep so we don't go too fast. 
        return None if no change or self.status.message if there is a new status
        '''
        self.get_status()
        debug('self.status:', self.status, '\nself.last_status:', self.last_status)
        if self.is_new_status():
            return self.status.message
        return None

    def get_status(self):
        ''' Grab the status from the sensor upload url '''
        debug('get_status')
        parser = StatusParser()
        debug('self.source:', self.source)
        request = urllib2.Request(url=self.source)
        result = urllib2.urlopen(request)
        debug('has data:', str(result.__dict__))
        if result.getcode() == 200:
            status_string = result.read()
            debug('status from server:', status_string)
            status = parser.get_status(status_string)
            if self.status:
                self.last_status = self.status
            else:
                self.last_status = status
            self.status = status
            debug('parser returned', str(self.status.__dict__))

    def is_new_status(self):
        ''' Test if the most recently grabbed status is newer than the last one '''
        debug('is_new_status')
        if self.status and self.last_status:
            debug('statuses exists and are not identical')
            try:
                debug(str(self.status.time_changed), str(self.last_status.time_changed))
                debug('time delta',str((self.status.time_changed - self.last_status.time_changed).total_seconds()))
            except Exception as e:
                debug(repr(e))
                debug('both times are not yet set')
            if self.status.time_changed and self.last_status.time_changed and (self.status.time_changed - self.last_status.time_changed).total_seconds() > 60 and self.status.info.get('lights') != self.last_status.info.get('lights'):
                debug('new status')
                return True
            elif self._first_run:
                self._first_run = False
                return True
        return False

class Sensor:
    ''' Stores the state of a sensor '''
    def __init__(self, id, label, boolean=None):
        self.id = id
	self.label = label
	self.boolean = None
        self.set_boolean(boolean)

    def set(self, value):
        ''' Set the state of the sensor appropriately '''
        self.set_boolean(value)

    def set_boolean(self, value):
        ''' Set self.boolean with a bool version of the sensor state 
        None is for unset or indeterminate state.
        '''
        self.boolean = {'on':True, True:True, 'true':True, 'off':False, False:False, 'false':False, None:None}[value]

    @property
    def boolstr(self):
        ''' Return an appropriate string representation of the sensor state '''
        return {True:'on', 'true':'on', False:'off', 'false':'off', None:'unknown'}[self.boolean]

    def __dict__(self):
        ''' Return a dict representation of the Sensor object '''
        return {'id': self.id, 'label': self.label, 'boolean': self.boolean}

    def __eq__(self, other):
        ''' Test equality of the state of two sensors '''
        return self.boolean == other.boolean


class Status:
    ''' Status class
    For the storage and comparison of status states.
    '''
    def __init__(self, time_changed, sensors, source_string, info):
        debug('Status(sensors)', *([str(x) for x in sensors]))
        self.time_changed = time_changed
        try:
            self.message = {'raw':source_string, 'human':None, 'default':None, 'changed': self.time_changed.strftime('%s')}
        except ImportError:
            time.sleep(3)
            self.message = {'raw':source_string, 'human':None, 'default':None, 'changed': self.time_changed.strftime('%s')}
        self.info = info
        self.sensors = sensors
        self.source_string = source_string
        self._set_message()
        debug('Status.sensors', ', '.join(['%s: %s' % (k, repr(v.__dict__)) for k,v in self.sensors.items()]))

    def _sensor_status(self):
        ''' Return a human friendly string representing the status of all the sensors '''
        return ', '.join(['%s is %s' % (k.label, k.boolstr) for k in self.sensors.values() if k.label])

    def _set_message(self):
        ''' Set all formats of the status messages '''
        self._set_raw_message()
        self._set_human_message()
        self._set_default_message()

    def _set_default_message(self):
        ''' Set the default message with the more traditional format of status '''
        if self.time_changed:
            try:
                date = self.time_changed.strftime('%I:%M%p %A %d %b')
            except ImportError:
                time.sleep(3)
                date = self.time_changed.strftime('%I:%M%p %A %d %b')
        else:
            date = 'date unknown'
        self.message['default'] = 'HacDC is %s since %s' % ({True:'open', False:'closed'}[self.info.get('lights').boolean], date)

    def _set_human_message(self):
        ''' Set the human friendly message to a more verbose readout of the status '''
        self.message['human'] = self._sensor_status()

    def _set_raw_message(self):
        ''' Set the "raw" message to be the source text '''
        self.message['raw'] = self.source_string

    def __dict__(self):
        ''' Return a representation of the object as a dict '''
        return {'time_changed': self.time_changed, 'message': self.message, 'sensors': dict((k, v.__dict__) for k,v in self.sensors.items()), 'info': self.info,'source_string':self.source_string}

    def __eq__(self, other):
        ''' The sensor only updates on changes so we can assume a change has occured if there has been an update '''
        return self.time_changed == other.time_changed


class StatusParser:
    ''' Parse the status returned by the current sensor in "WTF" format :P
    message format(bash):
	 subject: Lights=$lightsOn
	 body: GPIO4=$GPIO4;GPIO5=$GPIO5;FA3=$FA3;FA4=$FA4;FA5=$FA5
	 date: $( echo $(date "+%A, %b %d at %l:%M %p") | tr ' ' '_') aka %A,_%b_%d_at_%l:%M_%p and TZ='EST5EDT,M3.2.0,M11.1.0'
    message format (example):
	 date=Monday,_Jan_20_at_12:17_AM
	 subject=Lights=false
	 body=FA3=false;FA4=false;FA5=false
    '''
    _date_format = "%A,_%b_%d_at_%I:%M_%p" # C %l == py %I
    _field_sep = ";"
    _key_val_sep = "="
    _body_sensors = {'gpio4': Sensor('GPIO4', None, None), 'gpio5': Sensor('GPIO5', None, None), 'fa3': Sensor('hall_light_on', 'hall light'), 'fa4': Sensor('main_light_on', 'main room light'), 'fa5': Sensor('work_light_on','work room light')}
    _subject_sensors = {'lights': Sensor('any_lights_on', 'one or more lights')}

    def __init__(self, status_string=None):
	 self.collected_values = {}
	 self.sensor_info = self._body_sensors
	 self.last_changed_date = None
	 self.status_string = status_string

    def set_sensor(self, name, value, sensor_info=None):
        ''' Set the state of a sensor '''
        sensor_info = sensor_info or self.sensor_info
	sensor_info[name].set(value)

    def _split_dict(self, string):
        ''' Split a string formated as key-value pairs into a dict '''
        return dict(self._split_key_val(pair) for pair in self._split_list(string))

    def _split_key_val(self, string):
        ''' Split a string formatted as a key-value pair '''
        return [item.strip() for item in string.strip().split('=',1)]

    def _split_list(self, string):
        ''' Split a string formatted as a list into a list '''
	return [item.strip() for item in string.strip().split(';')]

    def _parse_body_field(self, string):
        ''' Parse an individual item in the "body" entry. '''
        sub = string.split(self._key_val_sep, 1)
        debug('StatusParser._parse_body.sub', repr(sub))
	if len(sub) == 2 and sub[0].lower() in self._body_sensors and sub[1].lower() in ('true', 'false'):
	    self.set_sensor(sub[0].lower(), sub[1].lower())

    def _parse_body(self, body):
        ''' Parse the "body" entry. '''
        if len(body) >= 1:
	    for field in self._split_list(body):
	        self._parse_body_field(field)
                debug('body field:',field)

    def _parse_subject(self, subject_string):
        ''' Parse the "subject" entry. '''
        sub = self._split_key_val(subject_string)
	if len(sub) == 2 and sub[0].lower() and sub[1].lower() in ('true', 'false', 'on', 'off'):
	    self.set_sensor(sub[0].lower(), sub[1].lower(), self._subject_sensors)

    def _parse_date(self, date_string):
        ''' Parse the "date" entry. '''
        debug('StatusParser._parse_date.date_string:', date_string)
        try:
            try:
                self.last_changed_date = datetime.datetime.strptime(date_string, self._date_format).replace(year=datetime.datetime.now().year)
                debug('StatusParser._parse_date.last_changed_date:', repr(self.last_changed_date))
            except ImportError:
                time.sleep(3)
                self.last_changed_date = datetime.datetime.strptime(date_string, self._date_format).replace(year=datetime.datetime.now().year)
                debug('StatusParser._parse_date.last_changed_date:', repr(self.last_changed_date))
	except Exception as e:
            debug(repr(e))
	    self.last_changed_date = None

    def parse_status(self, status_string=None):
        ''' Parse the whole status message. '''
        if status_string:
            self.status_string = status_string
        for line in self.status_string.strip().split('\n'):
	    line_parts = self._split_key_val(line)
	    if len(line_parts) == 2:
                key = line_parts[0].strip().lower()
                val = line_parts[1].strip()
	        if key == 'date':
	            self._parse_date(val)
	        elif key == 'subject':
	            self._parse_subject(val)
	        elif key == 'body':
	            self._parse_body(val)

    def get_status(self, status_string=None):
        ''' Return a Status object based on the remote source. '''
        self.parse_status(status_string)
        debug('StatusParser.get_status,sensor_info', str(self.sensor_info))
        return Status(self.last_changed_date, self.sensor_info, self.status_string, self._subject_sensors)
