#!/usr/bin/env python2
#
# logview.py
#
# (c) Copyright 2009-2010 Michael Towers (larch42 at googlemail dot com)
#
# This file is part of the larch project.
#
#    larch is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    larch is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with larch; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#----------------------------------------------------------------------------
# 2010.08.10

import locale
# Try to work around problems when the system encoding is not utf8
encoding = locale.getdefaultlocale()[1]

#TODO: progress bar?
class Progress:
    def __init__(self):
        self.active = False
        ui.widgetlist(fss('fetch_layout', 'progress.uim'))
        ui.connect('progress:done*clicked', self._done)

    def _done(self):
        self.active = False
        ui.runningtab(0)

    def start(self):
        # Set busy cursor on the progress area
        ui.command('progress:page.busycursor', True)
        # Initialize widgets
        ui.command("progress:text.text")
        ui.command("progress:progress.text")
        ui.command("progress:done.enable", False)
        ui.command("progress:cancel.enable", True)
        self.active = True
        ui.runningtab(1)

    def end(self, auto=False):
        ui.command("progress:cancel.enable", False)
        ui.command("progress:done.enable", True)
        # Clear busy cursor on the progress area
        ui.command('progress:page.busycursor', True)
        ui.command('progress:page.busycursor', False)
        if auto:
            self._done()

    def addLine(self, line):
        # Try to work around problems when the system encoding is not utf8
        if isinstance(line, str):
            line = line.decode(encoding, 'replace')
        ui.command("progress:text.append_and_scroll", line)
        logger.addLine(line)

    def set(self, text=""):
        ui.command("progress:progress.text", text)


class Logger:
    def __init__(self):
        ui.widgetlist(fss('fetch_layout', 'logger.uim'))
        ui.connectlist(
                ('log:clear*clicked', self.clear),
                ('log:hide*clicked', self._hide),
                (':showlog*clicked', self._show),
            )

    def clear(self):
        ui.command('log:text.text')

    def addLine(self, line):
        # Try to work around problems when the system encoding is not utf8
        if isinstance(line, str):
            line = line.decode(encoding, 'replace')
        ui.command('log:text.append_and_scroll', line)

    def _show(self):
        ui.runningtab(2)

    def _hide(self):
        ui.runningtab()
