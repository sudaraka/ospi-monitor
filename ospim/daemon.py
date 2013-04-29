# daemon.py: Daemon process handler
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

import sys, time, atexit
from signal import SIGTERM
from BaseHTTPServer import HTTPServer
from .config import *
from .webserver import *

# Make sure this script doesn't get executed directly
if '__main__' == __name__:
  sys.exit(1)


class OSPiMDaemon:
  """
  OSPi Monitor daemon
  """

  def __init__(self):
    """
    Initialize daemon settings
    """

    # Get NULL device of the OS
    # Fall back to /dev/null if os.devnull is not present
    devnull = '/dev/null'
    if hasattr(os, 'devnull'):
      devnull = os.devnull

    self.stdin = devnull
    self.stdout = devnull
    self.stderr = devnull
    self.pid_file = ospim_conf.get('daemon', 'pid_file')


  def start(self):
    """
    Start daemon
    """

    # Read current pid from the daemon pid file
    try:
      f = file(self.pid_file, 'r')
      pid = int(f.read().strip())
      f.close()
    except IOError:
      pid = None

    if pid:
      sys.stderr.write('ospimd already running or orphan pid file %s exists.\n' % self.pid_file)
      sys.exit(1)

    # Call subroutines to fork daemon process and run daemon code
    self._fork_daemon()
    self.run()


  def _fork_daemon(self):
    """
    Perform the UNIX double-for, see Stevens' "Advanced  Programming in the
    UNIX Environment" for details (ISBN 0201563177)
    """

    try:
      pid = os.fork()
      if 0 < pid:
        # Exit first parent
        sys.exit(0)
    except OSError, e:
      sys.stderr.write('fork #1 failed: %d (%s)\n' % (e.errno, e.strerror))
      sys.exit(1)

    # Adjust environment
    os.chdir('/')
    os.setsid()
    os.umask(0)

    try:
      pid = os.fork()
      if 0 < pid:
        # Exit second parent
        sys.exit(0)
    except OSError, e:
      sys.stderr.write('fork #2 failed: %d (%s)\n' % (e.errno, e.strerror))
      sys.exit(1)

    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()

    si = file(self.stdin, 'r')
    so = file(self.stdout, 'a+')
    se = file(self.stderr, 'a+')

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    # Create pid file
    atexit.register(self._remove_pid_file)
    pid = str(os.getpid())
    file(self.pid_file, 'w+').write('%s\n' % pid)


  def _remove_pid_file(self):
    """
    Remove the pid file from disk
    """

    os.remove(self.pid_file)


  def stop(self):
    """
    Stop daemon
    """

    # Read current pid from the daemon pid file
    try:
      f = file(self.pid_file, 'r')
      pid = int(f.read().strip())
      f.close()
    except IOError:
      pid = None

    if not pid:
      sys.stderr.write('ospimd is not running or pid file %s is missing.\n' % self.pid_file)

      # return here instead of exit so we allow the execution to continue for
      # a restart
      return

    # Terminate the process
    try:
      while 1:
        os.kill(pid, SIGTERM)
        time.sleep(.1)
    except OSError, e:
      e = str(e)

      if 0 < e.find('No such process'):
        if os.path.exists(self.pid_file):
          os.remove(self.pid_file)
      else:
        print err
        sys.exit(1)

  def restart(self):
    """
    Restart daemon
    """

    self.stop()
    self.start()


  def run(self):
    """
    Run the main loop
    This method should be overridden in a subclass to implement the daemon
    functionality
    """

    try:
      server_address = (
        ospim_conf.get('server', 'address'),
        ospim_conf.getint('server', 'port')
      )
      httpd = HTTPServer(server_address, OSPiMRequestHandler)
    except Exception, e:
      sys.stderr.write('Failed to create HTTP Server[%d]: %s\n' % (e.errno, e.strerror))
      sys.exit(1)

    while 1:
      httpd.handle_request()

