# webserver.py: Web server request handling implementation
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
# Based on the OpenSprinkler Pi sample code from rayshobby.net
# https://github.com/rayshobby/opensprinkler
#

import sys
from BaseHTTPServer import BaseHTTPRequestHandler

# Make sure this script doesn't get executed directly
if '__main__' == __name__:
  sys.exit(1)


class OSPiMRequestHandler(BaseHTTPRequestHandler):
  """
  OSPi Monitor daemon (ospimd) will forward all the HTTP request handling to
  this class.
  """

  def do_GET(self):
    """
    Handle HTTP GET requests
    """

    self.wfile.write('Hello web user')

