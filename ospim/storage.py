# zones.py: Manages a JSON based data file for OpenSprinkler zones
#
# Copyright 2013 Sudaraka Wijesinghe <sudaraka.wijesinghe@gmail.com>
#
# This file is part of OpenSprinkler Pi Monitor (OSPi Monitor)
#
# OSPi Monitor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OSPi Monitor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OSPi Monitor.  If not, see <http://www.gnu.org/licenses/>.
#


import copy
import datetime
import hashlib
import json
import logging
import os
import re
import sys

from .config import ospim_conf


# =============================================================================
# Make sure this script doesn't get executed directly
if '__main__' == __name__:
    sys.exit(1)


# =============================================================================
class OSPiMStorage(object):

    """
    Implements the common functionality that will be used by OSPiM local data
    storage classes.
    """

    # Data file path. Must be overridden in the sub-class
    _data_file = None

    # Data (Python dictionary) that will be written to the disk file as a
    # JSON string.
    _data = {}

    def __init__(self):
        """
        Make sure the path and data file exists in the system, and load the
        data into memory snapshot if available
        """

        if not os.path.isdir(os.path.dirname(self._data_file)):
            try:
                os.makedirs(os.path.dirname(self._data_file), 0o755)
            except:
                logging.warning(
                    'Failed to create storage file directory %s'
                    % os.path.dirname(self._data_file)
                )
                logging.warning(
                    'Changes will not be saved to ' + self._data_file)

        # load settings from disk file
        try:
            f = open(self._data_file, 'r')
            self._data = json.loads(f.read())
            f.close()
        except:
            # Inform the sub-class via initialize_data method that new data
            # file needs to be created
            self.initialize_data()

        self.sanity_check()

    def initialize_data(self):
        """
        This method should be overridden in the sub-classes to generate the
        default data structure when a new file is created
        """
        pass

    def sanity_check(self):
        """
        This method should be overridden in the sub-classes to verify and
        adjust data that is loaded from the file when the object is initialized
        """
        pass

    def write(self):
        """ Write the current memory snapshot of zone data in to disk file """

        try:
            f = open(self._data_file, 'w')
            f.write(json.dumps(self._data))
            f.close()
        except Exception as e:
            logging.warning('Failed to write data to ' + self._data_file)
            logging.error(str(e))

    def get_json(self, hash=None):
        """ Return the memory snapshot as JSON object (string) """

        # Calculate the hash of the current data
        data_hash = hashlib.md5(json.dumps(self._data)).hexdigest()

        # If the given hash is equal to current data hash we only return a
        # skeleton data structure with the hash indicating that data has not
        # changed
        if hash == data_hash:
            return json.dumps({'_data_hash': data_hash})

        # Clone and mutate the data structure pass hash to client without
        # modifying the internal data
        return_data = dict(self._data)
        return_data['_data_hash'] = data_hash

        return json.dumps(return_data)


# =============================================================================
class OSPiMSchedule(OSPiMStorage):

    """
    Manages the JSON data file that act as a local cache to the Google Calendar
    events.
    Every zone in the schedule must be turned on
    """

    # Data file path
    _data_file = ospim_conf.get('calendar', 'schedule_file')

    # Google Calendar Id and event list
    _data = {
        "calendar_id": None,
        "events": {}
    }

    # Zone data object
    _zone = None

    def set_zone_data(self, zone_data):
        """ Set zone data store object """

        self._zone = zone_data

    def update(self, event_list, remove_non_existing=False):
        """ Add the new events from given list in to the schedule data """

        try:
            self.remove_past_events()

            for event_id, event in event_list.items():
                if 'zone_id' not in event:
                    event['zone_id'] = None

                # Get zone it from the name (event summary text)
                event['zone_id'] = self._zone.get_id(event['zone_name'])

                # Don't add unidentified zones
                if None == event['zone_id']:
                    continue

                self._data['events'][event_id] = event

            if remove_non_existing:
                self._remove_non_existing(event_list)

            self.write()
        except Exception as e:
            logging.error('[Schedule:update] ' + str(e))

    def _remove_non_existing(self, event_list):
        """
        Check the current event list against the supplied list based on event
        id, and remove non existing events
        """

        tmp_data = dict(self._data['events'])

        for event_id in tmp_data:
            if event_id not in event_list:
                self.remove(event_id)

    def remove_past_events(self):
        """
        Remove events that have the end time (turn off) earlier than current
        time
        """

        try:
            for event_id, event in self._data['events'].items():
                end_time = datetime.datetime.strptime(event['turn_off'],
                                                      '%Y-%m-%d %H:%M:%S')

                if datetime.datetime.now() > end_time:
                    self.remove(event_id)

        except Exception as e:
            logging.error('[Schedule:remove_past]' + str(e))

    def remove(self, event_id):
        """ Remove event from the data schedule """

        try:
            if event_id not in self._data['events']:
                return

            self._zone.set_status(self._data['events'][event_id]['zone_id'], 0)

            self._data['events'].pop(event_id)
        except Exception as e:
            logging.error('[Schedule:remove] ' + str(e))

    def set_calendar_id(self, id):
        """
        Set the ID of Google calendar to be used.
        Note: When setting a new ID, existing event data will be cleared from
        the cache until next fetch cycle.
        """

        if id != self._data['calendar_id']:
            self._data = {
                "calendar_id": None,
                "events": {}
            }

        self._data['calendar_id'] = id

        # Preserver changes by writing them back to the disk file
        self.write()

    def get_sorted(self):
        """ Return the schedule data structure sorted by event start time """

        # Work on a separate copy of data
        data = dict(self._data)

        sorted_events = sorted(data['events'].items(),
                               key=lambda k: k[1]['turn_on'])

        server_time = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        data['server_time'] = server_time

        data['events'] = []
        for id, event in sorted_events:
            event['event_id'] = id
            data['events'].append(event)

        return data

    def get_json(self, hash=None):
        """ Override parent class to sort by event start time """

        # Calculate the hash of the current data
        data_hash = hashlib.md5(json.dumps(self._data)).hexdigest()

        # If the given hash is equal to current data hash we only return a
        # skeleton data structure with the hash indicating that data has not
        # changed
        if hash == data_hash:
            return json.dumps({'_data_hash': data_hash})

        data = self.get_sorted()
        data['_data_hash'] = data_hash

        return json.dumps(data)


# =============================================================================
class OSPiMZones(OSPiMStorage):

    """
    Manages the JSON data file that maintains the sprinkler zone information
    """

    # Data file path
    _data_file = ospim_conf.get('opensprinkler', 'zone_file')

    # Skeleton data structure for a single zone
    _zone_block = {
        "name": "",
        "status": 0,
        "state_owner": "M",
        "start_time": ""
    }

    # Default zone configuration, and the memory snapshot of the disk file
    _data = {
        "zone_count": 16,
        "max_run": 3,
        "zone": [copy.copy(_zone_block)]
    }

    def initialize_data(self):
        """ Initialize zone blocks on new data structure """

        self.set_count(self._data['zone_count'])

    def sanity_check(self):
        """ Check the data structure loaded """

        if 'max_run' not in self._data:
            self._data['max_run'] = 3

        for event in self._data['zone']:
            if 'state_owner' not in event:
                event['state_owner'] = ''

            if 'start_time' not in self._data['zone']:
                event['start_time'] = str(datetime.datetime.now())

    def set_max_run(self, hours):
        """ Set the number of hours a zone can be turned on for """

        self._data['max_run'] = hours

        # Preserver changes by writing them back to the disk file
        self.write()

    def set_count(self, count):
        """ Set the number of zones available in the connected device """

        self._data['zone_count'] = count

        # Add zone data blocks is new count is higher than what we had
        try:
            while len(self._data['zone']) < count:
                self._data['zone'].append(copy.copy(self._zone_block))
        except:
            logging.warning(
                'Failed to add adjustment blocks to the zone data list')

        # Preserver changes by writing them back to the disk file
        self.write()

    def set_names(self, name_list):
        """
        Update the user friendly names for each zone available in the device.

        These names will only be use for the user interface, they are
        insignificant in the device operation.
        """

        for zone, name in enumerate(name_list):
            if len(self._data['zone']) <= zone:
                # Create a new zone block if list element is not available
                self._data['zone'].append(copy.copy(self._zone_block))

            self._data['zone'][zone]['name'] = name
            self.write()

    def set_status(self, zone_id, status, owner='M'):
        """
        Update the current status (on/off) of the given zone.

        Status that keep in this data structure merely a representation of what
        the hardware status is. Hardware needs to be update separately.
        """

        if 'state_owner' not in self._data['zone'][zone_id]:
            self._data['zone'][zone_id]['state_owner'] = owner

        # Manually turned on zones can't be turned off by the calendar
        if 0 == status and \
                'M' == self._data['zone'][zone_id]['state_owner'] and \
                'S' == owner:
            return

        # When chanting the zone status on or off set the start time to track
        # maximum allowable run time.
        if status != self._data['zone'][zone_id]['status']:
            self._data['zone'][zone_id]['start_time'] = \
                str(datetime.datetime.now())

        try:
            self._data['zone'][zone_id]['status'] = status
            self._data['zone'][zone_id]['state_owner'] = owner

            self.write()
        except Exception as e:
            logging.error('[zone:set_status]: %s' % str(e))

    def get_id(self, zone_name):
        """
        Return the id of given zone name, or None when the zone doesn't exist
        """

        if 1 > len(zone_name):
            return None

        # If the given zone name is in the pattern of "Zone #" match the # with
        # zone id with a zone that has an empty name.
        match = re.match('^Zone\s+(\d+)$', zone_name)
        if None != match:
            lookup_id = int(match.group(1)) - 1

            if 0 <= lookup_id \
                and len(self._data['zone']) > lookup_id \
                and self._data['zone_count'] > lookup_id \
                    and 1 > len(self._data['zone'][lookup_id]['name']):
                return lookup_id

        for zone_id, zone in enumerate(self._data['zone']):
            if zone['name'].lower() == zone_name.lower():
                return zone_id

        return None

    def clear_long_running_zones(self):
        """
        Iterate through the (running manually started) zone list and turn them
        off if running over the max_run hours
        """

        data_changed = False

        for event in self._data['zone']:
            if 'M' == event['state_owner'] and 1 == event['status']:
                start = datetime.datetime.strptime(
                    event['start_time'],
                    '%Y-%m-%d %H:%M:%S.%f'
                )

                if datetime.timedelta(hours=self._data['max_run']) <= \
                        datetime.datetime.now() - start:
                    event['status'] = 0
                    data_changed = True

        if data_changed:
            self.write()
