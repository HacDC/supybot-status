from log import debug, info, warn, error, critical, exception

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


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
