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

import atexit
import logging
import os
import signal
import sys
import time

from .config import ospim_conf
from .webserver import OSPiMHTTPServer, OSPiMRequestHandler
from .gpio import OSPiMGPIO
from .storage import OSPiMZones, OSPiMSchedule
from .calendar import OSPiCalendarThread


# Make sure this script doesn't get executed directly
if '__main__' == __name__:
    sys.exit(1)


class OSPiMDaemon:
    """
    OSPi Monitor daemon
    """

    # GPIO communication handler
    _gpio = None

    # Local schedule data store
    _schedule = None

    # Local zone data store
    _zone = None

    # Calender lookup thread
    _cal_thread = None

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
        pid = self._get_pid()

        if pid:
            logging.warning('PID file %s already exists.' % self.pid_file)
            logging.warning('Start procedure aborted')
            sys.stderr.write('ospimd already running.\n')
            sys.exit(1)

        # Call subroutines to fork daemon process and run daemon code
        self._fork_daemon()
        logging.info('ospimd started!')
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
        except OSError as e:
            logging.error('Error on fork #1: %d - %s' % (e.errno, e.strerror))
            sys.stderr.write(
                'Failed to start daemon. See log file for details.')
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
        except OSError as e:
            logging.error('Error on fork #2: %d - %s' % (e.errno, e.strerror))
            sys.stderr.write(
                'Failed to start daemon. See log file for details.')
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
        pid = str(os.getpid())
        file(self.pid_file, 'w+').write('%s\n' % pid)

        # Setup termination handlers
        atexit.register(self.cleanup_instance)
        signal.signal(signal.SIGTERM, self.sigterm_handler)

    def sigterm_handler(self, signum, frame):
        """ Catch the SIGTERM to exit gracefully by triggering atexit. """

        while self._cal_thread.is_alive():
            self._cal_thread.stop()

        sys.exit(0)

    def cleanup_instance(self):
        """
        Cleanup GPIO and remove the pid file from disk
        """

        if None != self._gpio:
            # Turn off all zones
            bits = [0] * self._zone._data['zone_count']

            self._gpio.close(bits)

        try:
            os.remove(self.pid_file)
        except:
            logging.warning('Failed to remove PID file.')

    def stop(self):
        """
        Stop daemon
        """

        # Read current pid from the daemon pid file
        pid = self._get_pid()

        if not pid:
            logging.warning(
                'Could not locate PID file %s during the stop procedure' %
                self.pid_file
            )
            logging.warning('Stop procedure aborted')
            sys.stderr.write('ospimd is not running.\n')

            # return here instead of exit so we allow the execution to continue
            # for a restart
            return

        # Terminate the process
        try:
            while True:
                os.kill(pid, signal.SIGTERM)
                time.sleep(.1)
        except OSError as e:
            e = str(e)

            if 0 < e.find('No such process'):
                if os.path.exists(self.pid_file):
                    os.remove(self.pid_file)
            else:
                logging.error(str(e))
                sys.stderr.write('Stop procedure aborted.\n')
                print str(e)
                sys.exit(1)

        logging.info('ospimd stopped!')

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

            httpd = OSPiMHTTPServer(server_address, OSPiMRequestHandler)

            self._gpio = OSPiMGPIO()
            self._zone = OSPiMZones()
            self._schedule = OSPiMSchedule()

            httpd.set_gpio_handler(self._gpio)
            httpd.set_zone_data(self._zone)
            httpd.set_schedule_data(self._schedule)

            self._cal_thread = OSPiCalendarThread()
            self._cal_thread.set_schedule_data(self._schedule)
            self._cal_thread.set_zone_data(self._zone)
            self._cal_thread.set_gpio_handler(self._gpio)
            self._cal_thread.start()
        except Exception as e:
            logging.error('Failed to create HTTP Server: %s\n' %
                          str(e))
            sys.exit(1)

        while True:
            httpd.handle_request()

    def _get_pid(self):
        """
        Read the pid file from disk and return the process id if exists,
        otherwise return None.
        """

        try:
            f = file(self.pid_file, 'r')
            pid = int(f.read().strip())
            f.close()
        except IOError:
            pid = None

        return pid
