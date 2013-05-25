# makefile: Source installer for the OpenSprinkler Pi Monitor
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

.PHONY: install uninstall dist-clean

install:
	install -b ospim.conf-dist /etc/ospim.conf
	install -d /var/www/ospim/{,js,css,img}
	install html/*.html /var/www/ospim
	install html/css/* /var/www/ospim/css
	install html/js/* /var/www/ospim/js
	install html/img/* /var/www/ospim/img
	install -d /var/lib/ospim

uninstall:
	$(RM) -fr /var/www/ospim

dist-clean: uninstall
	$(RM) -fr /var/lib/ospim
	$(RM) -f /etc/ospim.conf

