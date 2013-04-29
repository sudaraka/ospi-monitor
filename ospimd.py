#!/usr/bin/python
# ospid.py: Handle user and system requests to start/stop daemon
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
#
# Based on Public Domain code by Sander Marechal <s.marechal@jejik.com>
# http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
#

import sys
from ospim.daemon import *


def exit_usage():
  """
  Print usage instructions and exit
  """

  print 'usage: %s start|stop|restart' % sys.argv[0]
  sys.exit(2)


# Run main program
if '__main__' == __name__:

  # require the action as first parameter
  if 2 > len(sys.argv):
    exit_usage()

  daemon = OSPiMDaemon()

  if 'start' == sys.argv[1]:
    daemon.start()
  elif 'stop' == sys.argv[1]:
    daemon.stop()
  elif 'restart' == sys.argv[1]:
    daemon.restart()
  else:
    exit_usage()

