# gpio.py: Implements the GPIO calls to operate OpenSprinkler zones
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


import logging, os
import RPi.GPIO as GPIO
from .config import *
from .zones import *


# Make sure this script doesn't get executed directly
if '__main__' == __name__:
  sys.exit(1)


class OSPiMGPIO:
  """
  Makes GPIO calls on RaspberryPi to operate OpenSprinkler hardware
  """


  # Indicator to the status of GPIO communication availability
  connected = True


  # GPIO Pins used for serial communication
  _pin_clk = ospim_conf.getint('gpio', 'pin_clk')
  _pin_noe = ospim_conf.getint('gpio', 'pin_noe')
  _pin_dat = ospim_conf.getint('gpio', 'pin_dat')
  _pin_lat = ospim_conf.getint('gpio', 'pin_lat')


  def __init__(self):
    """
    Initialize GPIO on RaspberryPi to interface with OpenSprinkler shift
    register.
    """
    try:
      GPIO.cleanup()

      GPIO.setmode(GPIO.BCM)

      GPIO.setup(self._pin_clk, GPIO.OUT)
      GPIO.setup(self._pin_noe, GPIO.OUT)

      self.shift_register_disable()

      GPIO.setup(self._pin_dat, GPIO.OUT)
      GPIO.setup(self._pin_lat, GPIO.OUT)

      # Write the current status of zones to start with
      self.shift_register_write()

      self.shift_register_enable()
    except Exception, e:
      self.connected = False
      logging.error('[__init__] Failed to communicate with OpenSprinkler: %s' %
        str(e))


  def close(self, bits = None):
    """ Write the latest zone status from data file and cleanup GPIO """

    self.shift_register_write(bits)
    GPIO.cleanup()


  def shift_register_enable(self):
    """ Set OpenSprinkler shift register status to Enable """

    if not self.connected:
      return

    try:
      GPIO.output(self._pin_noe, False)
    except Exception, e:
      self.connected = False
      logging.error('[sr_enable] Failed to communicate with OpenSprinkler: %s' %
        str(e))


  def shift_register_disable(self):
    """ Set OpenSprinkler shift register status to Disable """

    if not self.connected:
      return

    try:
      GPIO.output(self._pin_noe, True)
    except Exception, e:
      self.connected = False
      logging.error('[sr_disable] Failed to communicate with OpenSprinkler: %s' %
        str(e))


  def shift_register_write(self, bits = None):
    """ Send zone status bits to OpenSprinkler """

    if not self.connected:
      return

    if None == bits:
      bits = []
      data = OSPiMZones()._data

      for i in range(data['zone_count']):
        bits.append(data['zone'][i]['status'])

    logging.info('[sr_write] Writing: %s' % bits)

    try:
      GPIO.output(self._pin_clk, False)
      GPIO.output(self._pin_lat, False)

      # Send bits to OpenSprinkler via GPIO
      # Note: Order of the zones we have on the data structure is big-endian
      # (first to last), and for the serial communication it has to be
      # little-endian (last to first). Hence the len - pos -1
      for bit_pos in range(len(bits)):
        GPIO.output(self._pin_clk, False)
        GPIO.output(self._pin_dat, bits[len(bits) - bit_pos - 1])
        GPIO.output(self._pin_clk, True)

      GPIO.output(self._pin_lat, True)
    except Exception, e:
      self.connected = False
      logging.error('[sr_write] Failed to communicate with OpenSprinkler: %s' %
        str(e))

