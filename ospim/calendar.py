# calendar.py: Query google calendar and adjust zone status
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


import datetime
import hashlib
import httplib2
import json
import logging
import sys
import threading
import time
import urllib

from .config import ospim_conf


# =============================================================================
# Make sure this script doesn't get executed directly
if '__main__' == __name__:
    sys.exit(1)


# =============================================================================
class GoogleCalender:

    """
    Subroutines for accessing Google Calender API v3 via RESTful interface
    """

    # Google Calendar API base URL
    base_api_url = 'https://www.googleapis.com/calendar/v3/calendars/'

    # Google API access key
    api_key = ospim_conf.get('calendar', 'api_key')

    def fetch_events(self, cache):
        """ Return a dictionary of upcoming events """

        # Get the current time stamp in UTC and convert to ISO format
        # compatible with Google API YYYY-MM-DDTHH:II:SS.zzzZ
        time_stamp = datetime.datetime.utcnow().isoformat()
        dot_pos = time_stamp.find('T')
        time_stamp = time_stamp[:dot_pos] + 'T00:00:00.000Z'

        # Fetch scheduled events from now and on wards
        event_list = self._get_json(
            cache._data['calendar_id'], {'timeMin': time_stamp}
        )

        # When there is no events in the calendar, return an empty list
        if None == event_list or 1 > len(event_list):
            event_list = []

        return_list = {}

        for event in event_list:
            if 'summary' not in event:
                continue

            start_time = self._iso_datetime_to_py(event['start']['dateTime'])
            end_time = self._iso_datetime_to_py(event['end']['dateTime'])

            if datetime.datetime.now() > end_time:
                continue

            # Flag to indicate whether the event is running
            # (zone is on or not)
            is_running = 0
            if datetime.datetime.now() >= start_time and \
                    datetime.datetime.now() <= end_time:
                is_running = 1

            return_list[event['id']] = {
                'zone_name': event['summary'],
                'zone_id': None,
                'turn_on': str(start_time),
                'turn_off': str(end_time),
                'running': is_running
            }

        cache.update(return_list, True)

        return return_list

    def _iso_datetime_to_py(self, iso_datetime_string):
        """
        Convert ISO time stamp from Google API to Python datetime object
        """

        # Drop the timezone part (GMT + time zones)
        plus_pos = iso_datetime_string.find('+')
        if plus_pos:
            iso_datetime_string = iso_datetime_string[:plus_pos]

        # Drop the timezone part (GMT - time zones)
        minus_pos = iso_datetime_string.rfind('-')
        if minus_pos and 10 < minus_pos:
            iso_datetime_string = iso_datetime_string[:minus_pos]

        return datetime.datetime.strptime(
            iso_datetime_string,
            '%Y-%m-%dT%H:%M:%S'
        )

    def _get_json(self, calendar_id, parameters=None):
        """
        Call the Google Calender API and return the item list.
        Otherwise return None.
        """

        url = self.base_api_url + calendar_id + '/events'

        if not parameters:
            parameters = {'key': self.api_key}
        elif 'key' not in parameters:
            parameters['key'] = self.api_key

        parameters['singleEvents'] = 'True'
        parameters['orderBy'] = 'startTime'

        url += '?' + urllib.urlencode(parameters)

        try:
            http = httplib2.Http()
            json_string = http.request(url, 'GET')
            json_obj = json.loads(json_string[1])
        except Exception as e:
            logging.error('Failed to fetch or decode calendar data: ' + str(e))
            return None

        if 'items' not in json_obj:
            return None

        return json_obj['items']


# =============================================================================
class OSPiCalendarThread(threading.Thread):

    """
    Thread that will be invoked by the main daemon process to periodically
    query the Google Calendar and update the zone status.
    """

    # Number of seconds to wait between queries
    # This also server a second purpose, to indicate that thread must keep on
    # running while > 0
    query_delay = ospim_conf.getint('calendar', 'query_delay')

    # Google calender access object
    gcal = GoogleCalender()

    # Schedule data local storage
    _schedule = None

    # Zone data object
    _zone = None

    # GPIO communication handler
    _gpio = None

    def set_gpio_handler(self, gpio_handler):
        """ Set GPIO handler object """

        self._gpio = gpio_handler

    def set_zone_data(self, zone_data):
        """ Set zone data store object """

        self._zone = zone_data

        if None != self._schedule:
            self._schedule.set_zone_data(zone_data)

    def set_schedule_data(self, schedule_data):
        """ Set schedule data store object """

        self._schedule = schedule_data

    def stop(self):
        """
        Set the query_delay to zero, so that run loop will exit and
        end the thread.
        """

        self.query_delay = 0

    def run(self):
        """ Execute the calendar lookup routines """

        # Make sure we wait at least a minute
        if 10 > self.query_delay and 0 < self.query_delay:
            self.query_delay = 10

        # Continue as long as we have query_delay > 0
        while 0 < self.query_delay:
            # Only run the Google Calendar API query if there is a calendar Id
            # present.
            try:
                if None != self._schedule._data['calendar_id'] \
                        and 1 < len(self._schedule._data['calendar_id']):
                    zone_hash = hashlib.md5(json.dumps(self._zone._data))

                    self.gcal.fetch_events(self._schedule)

                    # Update zone status from schedule
                    self._update_zone_from_schedule(zone_hash)

            except Exception, e:
                logging.error('[calendar:run] ' + str(e))

            # Here we sleep bunch of 1 second intervals that will add up to
            # query_delay so when the stop() is called the thread will exit
            # sooner without waiting for remainder of the query_delay
            delay_count = 0
            while delay_count < self.query_delay:
                delay_count += 1
                time.sleep(1)

    def _update_zone_from_schedule(self, zone_hash):
        """
        Find the currently running zones from scheduled events and update local
        zone status data.
        If the zone data changed, also send the new data to GPIO.
        """

        for eid, e in self._schedule._data['events'].items():
            #if 1 == e['running']:
            self._zone.set_status(e['zone_id'], e['running'], 'S')

        new_hash = hashlib.md5(json.dumps(self._zone._data))

        if new_hash.hexdigest() != zone_hash.hexdigest():
            self._gpio.shift_register_write()
