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


import logging, threading, time, urllib, httplib2, json, datetime
from .config import *
from .storage import OSPiMSchedule


# =============================================================================
# Make sure this script doesn't get executed directly
if '__main__' == __name__:
  sys.exit(1)


# =============================================================================
class GoogleCalender:
  """ Subroutines for accessing Google Calender API v3 via RESTful interface """


  # Google Calendar API base URL
  base_api_url = 'https://www.googleapis.com/calendar/v3/calendars/'

  # Google API access key
  api_key = ospim_conf.get('calendar', 'api_key')

  # Google Calender is
  calender_id = ospim_conf.get('calendar', 'calendar_id')


  def fetch_events(self):
    """ Return a dictionary of upcoming events """

    # Get the current time stamp in UTC and convert to ISO format compatible
    # with Google API YYYY-MM-DDTHH:II:SS.zzzZ
    time_stamp = datetime.datetime.utcnow().isoformat()
    dot_pos = time_stamp.find('.')
    time_stamp = time_stamp[:dot_pos] + '.000Z'

    # Fetch scheduled events from now and on wards
    event_list = self._get_json({'timeMin': time_stamp})

    # When there is no events in the calendar, return an empty list
    if None == event_list or 1 > len(event_list):
      event_list = []

    return_list = {}

    for event in event_list:
      start_time = self._iso_datetime_to_py(event['start']['dateTime'])
      end_time = self._iso_datetime_to_py(event['end']['dateTime'])

      return_list[event['id']] = {
        'zone_name': event['summary'],
        'zone_id': None,
        'turn_on': str(start_time),
        'turn_off': str(end_time)
      }

    cache = OSPiMSchedule()
    cache.update(return_list, True)

    return return_list


  def _iso_datetime_to_py(self, iso_datetime_string):
    """ Convert ISO time stamp from Google API to Python datetime object """

    # Drop the timezone part
    plus_pos = iso_datetime_string.find('+')
    if plus_pos:
      iso_datetime_string = iso_datetime_string[:plus_pos]

    return datetime.datetime.strptime(iso_datetime_string, '%Y-%m-%dT%H:%M:%S')


  def _get_json(self, parameters = None):
    """
    Call the Google Calender API and return the item list.
    Otherwise return None.
    """

    url = self.base_api_url + self.calender_id + '/events'
    if not parameters:
      parameters = {'key': self.api_key}
    elif 'key' not in parameters:
      parameters['key'] = self.api_key

    url += '?' + urllib.urlencode(parameters)

    try:
      http = httplib2.Http()
      json_string = http.request(url, 'GET')
      json_obj = json.loads(json_string[1])
    except Exception, e:
      logging.error('Failed to fetch or decode calendar data: ' + str(e))
      return None

    if 'items' not in json_obj:
      return None

    return json_obj['items']


# =============================================================================
class OSPiCalendarThread(threading.Thread):
  """
  Thread that will be invoked by the main daemon process to periodically query
  the Google Calendar and update the zone status.
  """

  # Number of seconds to wait between queries
  # This also server a second purpose, to indicate that thread must keep on
  # running while > 0
  query_delay = ospim_conf.getint('calendar', 'query_delay')

  # Google calender access object
  gcal = GoogleCalender()


  def stop(self):
    """
    Set the query_delay to zero, so that run loop will exit and
    end the thread.
    """

    self.query_delay = 0


  def run(self):
    """ Execute the calendar lookup routines """

    # Make sure we wait at least a minute
    if 1 > self.query_delay and 0 < self.query_delay:
      self.query_delay = 1

    # Continue as long as we have query_delay > 0
    while 0 < self.query_delay:
      self.gcal.fetch_events()

      # Here we sleep bunch of 1 second intervals that will add up to
      # query_delay so when the stop() is called the thread will exit sooner
      # without waiting for remainder of the query_delay
      delay_count = 0
      while delay_count < self.query_delay * 60:
        delay_count += 1
        time.sleep(1)


