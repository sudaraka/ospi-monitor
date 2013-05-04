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


import logging, os, json, copy
from .config import *


# Make sure this script doesn't get executed directly
if '__main__' == __name__:
  sys.exit(1)


class OSPiMZones:
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


  def __init__(self):
    """
    Make sure the path and zone data file exists in the system, and load the
    data into memory snapshot if available
    """

    if not os.path.isdir(os.path.dirname(self._data_file)):
      try:
        os.makedirs(os.path.dirname(self._data_file), 0755)
      except:
        logging.warning(
          'Failed to create zone file directory %s'
          % os.path.dirname(self._data_file)
        )
        logging.warning('Zone setting changes will not be saved')

    # load zone settings from disk file
    try:
      f = open(self._data_file, 'r')
      self._data = json.loads(f.read())
      f.close()
    except Exception, e:
      logging.warning('Failed to load zone settings from %s' % self._data_file)
      logging.error(str(e))


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


  def write(self):
    """ Write the current memory snapshot of zone data in to disk file """

    try:
      f = open(self._data_file, 'w')
      f.write(json.dumps(self._data))
      f.close()
    except Exception, e:
      logging.warning('Failed to save the zone data')
      logging.error(str(e))


  def get_json(self):
    """ Return the memory snapshot as JSON object (string) """

    return json.dumps(self._data)

