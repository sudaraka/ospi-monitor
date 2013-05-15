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


import logging, os, json, copy, datetime, re
from .config import *


# =============================================================================
# Make sure this script doesn't get executed directly
if '__main__' == __name__:
  sys.exit(1)


# =============================================================================
class OSPiMStorage:
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
    Make sure the path and data file exists in the system, and load the data
    into memory snapshot if available
    """

    if not os.path.isdir(os.path.dirname(self._data_file)):
      try:
        os.makedirs(os.path.dirname(self._data_file), 0755)
      except:
        logging.warning(
          'Failed to create storage file directory %s'
          % os.path.dirname(self._data_file)
        )
        logging.warning('Changes will not be saved to ' + self._data_file)

    # load settings from disk file
    try:
      f = open(self._data_file, 'r')
      self._data = json.loads(f.read())
      f.close()
    except Exception, e:
      # Inform the sub-class via initialize_data method that new data file
      # needs to be created
      self.initialize_data()

  def initialize_data(self):
    """
    This method should be overridden in the sub-classes to generate the default
    data structure when a new file is created
    """
    pass


  def write(self):
    """ Write the current memory snapshot of zone data in to disk file """

    try:
      f = open(self._data_file, 'w')
      f.write(json.dumps(self._data))
      f.close()
    except Exception, e:
      logging.warning('Failed to write data to ' + self._data_file)
      logging.error(str(e))


  def get_json(self):
    """ Return the memory snapshot as JSON object (string) """

    return json.dumps(self._data)


# =============================================================================
class OSPiMSchedule(OSPiMStorage):
  """
  Manages the JSON data file that act as a local cache to the Google Calendar
  events.
  Every zone in the schedule must be turned on
  """

  # Data file path
  _data_file = ospim_conf.get('calendar', 'schedule_file')


  def update(self, event_list, remove_non_existing = False):
    """ Add the new events from given list in to the schedule data """

    zones = OSPiMZones()

    try:
      self.remove_past_events()

      for event_id, event in event_list.items():
        if not event.has_key('zone_id'):
          event['zone_id'] = None

        event['zone_id'] = zones.get_id(event['zone_name'])

        if None == event['zone_id']:
          continue

        self._data[event_id] = event

      if remove_non_existing:
        tmp_data = dict(self._data)

        for event_id in tmp_data:
          if event_id not in event_list:
            self.remove(event_id)

      self.write()
    except Exception, e:
      logging.error('[Schedule:update] ' + str(e))


  def remove_past_events(self):
    """
    Remove events that have the end time (turn off) earlier than current time
    """

    try:
      for event_id, event in self._data.items():
        end_time = datetime.datetime.strptime(event['turn_off'],
          '%Y-%m-%d %H:%M:%S')

        if datetime.datetime.now() > end_time:
          self.remove(event_id)

    except Exception, e:
      logging.info(str(e))


  def remove(self, event_id):
    """ Remove event from the data schedule """

    if event_id not in self._data:
      return

    self._data.pop(event_id)


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
      "status": 0
  }

  # Default zone configuration, and the memory snapshot of the disk file
  _data = {
    "zone_count": 16,
    "zone": [copy.copy(_zone_block)]
  }


  def initialize_data(self):
    """ Initialize zone blocks on new data structure """

    self.set_count(self._data['zone_count'])


  def set_count(self, count):
    """ Set the number of zones available in the connected device """

    self._data['zone_count'] = count

    # Add zone data blocks is new count is higher than what we had
    try:
      while len(self._data['zone']) < count:
        self._data['zone'].append(copy.copy(self._zone_block))
    except:
      logging.warning('Failed to add adjustment blocks to the zone data list')

    # Preserver changes by writing them back to the disk file
    self.write()


  def set_names(self, name_list):
    """
    Update the user friendly names for each zone available in the device.

    These names will only be use for the user interface, they are insignificant
    in the device operation.
    """

    for zone, name in enumerate(name_list):
      if len(self._data['zone']) <= zone:
        # Create a new zone block if list element is not available
        self._data['zone'].append(copy.copy(self._zone_block))

      self._data['zone'][zone]['name'] = name
      self.write()


  def set_status(self, zone_id, status):
    """
    Update the current status (on/off) of the given zone.

    Status that keep in this data structure merely a representation of what the
    hardware status is. Hardware needs to be update separately.
    """

    try:
      self._data['zone'][zone_id]['status'] = status
      self.write()
    except Exception, e:
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

