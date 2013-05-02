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

import sys, logging, mimetypes
from BaseHTTPServer import BaseHTTPRequestHandler
from .config import *

# Make sure this script doesn't get executed directly
if '__main__' == __name__:
  sys.exit(1)


class OSPiMRequestHandler(BaseHTTPRequestHandler):
  """
  OSPi Monitor daemon (ospimd) will forward all the HTTP request handling to
  this class.
  """

  root = ospim_conf.get('server', 'root_directory')


  # Override version string use in "Server" HTTP header
  def version_string(self):
    return ''


  def do_GET(self):
    """
    Handle HTTP GET requests

    Treat all GET request as requests for a static file to be served off the
    disk.
    """

    try:
      # Check for a valid web root
      if not os.path.isdir(self.root):
        self._send_404(self.path)
        return

      if 0 < len(self.root) and '/' == self.root[-1]:
        self.root = self.root[:-1]

      # When request uri is a directory, append index files names
      if os.path.isdir(self.root + self.path):
        if not self._get_index():
          self._send_403()
          return

      f = open(self.root + self.path)
      output = f.read();
      f.close()

      self.send_response(200)
      self.send_header(
        'Content-type',
        mimetypes.guess_type(self.root + self.path)[0]
      )

      self._send(output, None)
    except IOError:
      self._send_404(self.path)
    except Exception, e:
      logging.error('Error handling request %s' % self.path)
      self._report_error(str(e))


  def _get_index(self):
    """
    Check first index.html first and use it if exists, then also check for
    index.html and do the same.

    Priority: index.html > index.htm
    """

    if os.path.isfile(self.root + self.path + 'index.html'):
      self.path += 'index.html'
      return True

    if os.path.isfile(self.root + self.path + 'index.htm'):
      self.path += 'index.htm'
      return True

    return False


  def _send_403(self):
    self.send_response(403)

    try:
      f = open(self.root + '/403.html')
      text_403 = f.read()
      f.close()
      text_403 = self.path

      self.send_header('Content-type', 'text/html; encoding=utf-8;')
    except:
      self.send_header('Content-type', 'text/plain; encoding=utf-8;')
      text_403 = '403 Fobidden\nUri: %s' % uri

    self._send(text_403, None)


  def _send_404(self, uri = ''):
    self.send_response(404)

    try:
      f = open(self.root + '/404.html')
      text_404 = f.read()
      f.close()

      idx = text_404.find('#URI#')
      text_404 = '%s%s%s' % (text_404[:idx], uri, text_404[idx + 5:])

      self.send_header('Content-type', 'text/html; encoding=utf-8;')
    except:
      self.send_header('Content-type', 'text/plain; encoding=utf-8;')
      text_404 = '404 Not Found\nUri: %s' % uri

    self._send(text_404, None)


  def _report_error(self, message):
    self.send_response(500)
    self.send_header('Content-type', 'text/plain; encoding=utf-8;')
    self._send(message, None)


  def _send(self, document, response = 200):
    if response:
      self.send_response(response)

    self.end_headers()

    self.wfile.write(document)

