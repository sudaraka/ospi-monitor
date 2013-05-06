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

import sys, logging, mimetypes, random
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from .config import *
from .zones import *
from cgi import parse_header, parse_multipart, parse_qs


# Make sure this script doesn't get executed directly
if '__main__' == __name__:
  sys.exit(1)


class OSPiMHTTPServer(HTTPServer):
  """
  This wrapper class for HTTPServer is used to maintain a single instance of
  GPIO handler during the life cycle of the server.
  """

  # GPIO communication handler
  _gpio = None

  # Zone data object
  _zone = OSPiMZones();

  def set_gpio_handler(self, gpio_handler):
    """ Set GPIO handler object """

    self._gpio = gpio_handler



class OSPiMRequestHandler(BaseHTTPRequestHandler):
  """
  OSPi Monitor daemon (ospimd) will forward all the HTTP request handling to
  this class.
  """

  # Web root directory location
  _root = ospim_conf.get('server', 'root_directory')

  def version_string(self):
    """ Override version string use in "Server" HTTP header to be empty """
    return ''


  def do_POST(self):
    """
    Handle HTTP POST requests

    Treat all POST requests as requests do some server side processing and
    return the result.
    """

    try:
      # Strip out leading slash to avoid blank command name after split by '/'
      if '/' == self.path[0]:
        self.path = self.path[1:]

      # POST uri must contain the command
      if 0 == len(self.path):
        self._send_403()
        return

      # command is the first block (directory) of the Uri
      command = self.path.split('/', 1)

      # Load POST variables (query data) into 'post' dictionary
      post = {}
      ctype = 'application/x-www-urlencoded'
      pdict = None

      if 'content-type' in self.headers:
        ctype, pdict = parse_header(self.headers['content-type'])

      if 'multipart/form-data' == ctype:
        post = parse_multipart(self.rfile, pdict)
      elif 'application/x-www-form-urlencoded' == ctype:
        length = int(self.headers.getheader('content-length'))
        post = parse_qs(self.rfile.read(length), keep_blank_values = 1)

      # Process commands
      command[0] = command[0].lower()

      if 'get-zones' == command[0]:
        # Send complete zone data

        self._start_json_response()
        self._send(self.server._zone.get_json(), None)

      elif 'save-zone-count' == command[0]:
        # Update the zone count

        self._start_json_response()

        if 'count' not in post:
          logging.error('/save-zone-count called without count parameter')
          self._send(json.dumps({"error": 1, "desc": "'count' parameter was not provided. Nothing to update."}))
          return

        try:
          zone_count = int(post['count'][0])
        except:
          zone_count = 1

        self.server._zone.set_count(zone_count)
        self._send(json.dumps({"error": 0, "desc": "Ok"}))

      elif 'save-zone-names' == command[0]:
        # Update zone names

        self._start_json_response()

        if 'zone_name' not in post:
          logging.error('/save-zone-names called without zone_name parameter list')
          self._send(json.dumps({"error": 1, "desc": "'zone_name' parameter list was not provided. Nothing to update."}))
          return

        self.server._zone.set_names(post['zone_name'])
        self._send(json.dumps({"error": 0, "desc": "Ok"}))

      elif 'update-zone-status' == command[0]:
        # Update the zone status

        self._start_json_response()

        if 'zone' not in post:
          logging.error('/updat-zone-status called without zone parameter')
          self._send(json.dumps({"error": 1, "desc": "'zone' (id) parameter was not provided. Nothing to update."}))
          return

        try:
          zone_id = int(post['zone'][0])
          zone_count = self.server._zone._data['zone_count']

          if 0 > zone_id or zone_count <= zone_id:
            raise Exception('Zone id out of range')
        except:
          logging.error('/updat-zone-status called with invalid zone (id) parameter')
          self._send(json.dumps({"error": 2, "desc": ("Given zone id (%s) doesn\'t exists. Nothing to update." % post['zone'][0])}))
          return

        if 'status' not in post:
          logging.error('/updat-zone-status called without status parameter')
          self._send(json.dumps({"error": 3, "desc": "'status' parameter was not provided. Nothing to update."}))
          return

        try:
          new_status = int(post['status'][0])
          if 0 != new_status:
            new_status = 1
        except:
          new_status = 0

        self.server._zone.set_status(zone_id, new_status)
        self.server._gpio.shift_register_write()

        self._send(json.dumps({"error": 0, "desc": "Ok"}))

      else:
        self._send_404('command "%s"' % command[0])

    except Exception, e:
      logging.error('Error handling request %s' % self.path)
      logging.error(str(e))
      self._report_error(str(e))



  def do_GET(self):
    """
    Handle HTTP GET requests

    Treat all GET requests as requests for a static file to be served off the
    disk.
    """

    try:
      # Check for a valid web _root
      if not os.path.isdir(self._root):
        self._send_404(self.path)
        return

      if 0 < len(self._root) and '/' == self._root[-1]:
        self._root = self._root[:-1]

      # When request uri is a directory, append index files names
      if os.path.isdir(self._root + self.path):
        if not self._get_index():
          self._send_403()
          return

      f = open(self._root + self.path)
      output = f.read();
      f.close()

      self.send_response(200)
      self.send_header(
        'Content-type',
        mimetypes.guess_type(self._root + self.path)[0]
      )

      self._send(output, None)
    except IOError:
      self._send_404(self.path)
    except Exception, e:
      logging.error('Error handling request %s' % self.path)
      logging.error(str(e))
      self._report_error(str(e))


  def _get_index(self):
    """
    Check first index.html first and use it if exists, then also check for
    index.html and do the same.

    Priority: index.html > index.htm
    """

    if os.path.isfile(self._root + self.path + 'index.html'):
      self.path += 'index.html'
      return True

    if os.path.isfile(self._root + self.path + 'index.htm'):
      self.path += 'index.htm'
      return True

    return False


  def _send_403(self):
    self.send_response(403)

    try:
      f = open(self._root + '/403.html')
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
      f = open(self._root + '/404.html')
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

    self.send_header('Cache-Control', 'max-age=3600, no-cache, must-revalidate')
    self.send_header('Etag', random.randrange(100000, 999999))
    self.send_header('Expires', self.date_time_string())
    self.send_header('Last-Modified', self.date_time_string())
    self.end_headers()

    self.wfile.write(document)


  def _start_json_response(self):
    """
    Send HTTP 200 header and content type for JSON that most of the responses
    of this server use.
    """

    self.send_response(200)
    self.send_header('Content-type', 'application/json')

