#!/usr/bin/env python2
#
# (c) Copyright 2010 Michael Towers (larch42 at googlemail dot com)
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
#2010.10.12

import __builtin__
from liblarch.suim import Suim, debug
__builtin__.debug = debug



def larchcall(script, *args):
    if script[0] != '*':
        progress.start()            # initialize progress widget
        ui.setcb(None)
    else:
        # This script won't switch to the progress widget, but accepts
        # a callback to handle the resulting output
        script = script[1:]
        ui.setcb(args[0])
        args = args[1:]
    fss('larchscript', script, *args)

__builtin__.larchcall = larchcall



class Ui(Suim):
    def __init__(self):
        self.setcb(None)
        Suim.__init__(self, 'larch', busywidgets=[':larch'])

        self.connect('$$$uiclose$$$', self.quit)
        self.connect('$$$uiquit$$$', self.quit)
        self.connect('$$$cancel$$$', self.interrupt)
        self.progressing = False    # used for managing progress display


    def sigin(self, signal, *args):
        self.idle_add(getattr(self, 'sig_' + signal), *args)


    def setcb(self, cb):
        """Set a callback to run when a 'larchscript' sends an output line,
        or completes.
        """
        self._read_cb = cb


    def isbusy(self):
        return self._read_cb != None


    def runningtab(self, i=None):
        if (i == None):
            i = 1 if progress.active else 0
        if (i == 0) and hasattr(stage, 'reenter'):
            stage.reenter()
        self.command(':tabs.set', i)

    def fileDialog(self, message, startdir=None, create=False,
            dirsonly=False, file=None, filter=None):
# Actually this should access the file-system via 'fss' ...
# (that would require a new, custom widget)
        if dirsonly:
            return self.command('fileDialog_getdir', message, not create, startdir)
        if file and startdir:
            startdir = startdir + '/' + file
        if create:
            return self.command('fileDialog_save', message, startdir, filter)
        return self.command('fileDialog_open', message, startdir, filter)

    def enable_installation_page(self, on):
        self.command(':notebook.enableTab', 1, on)

    def interrupt(self):
        fss('larchscript', 'interrupt')

    def quit(self):
        """Do any tidying up which may be necessary.
        """
        fss('larchscript', 'close')
        Suim.quit(self)

    def data(self, key):
        return self.command('main_page_data.get', key)


    def sig_get_password(self, message):
        """This is a callback, triggered by signal 'get_password'
        to ask the user to input the password.
        """
        fss('larchscript', 'sendpassword', *ui.command('textLineDialog',
                message, "larch: pw", "", True))


    def sig_line_cb(self, message):
        """A line has been received from the 'larchscript' (this is a callback,
        in the main thread).
        The input lines are filtered for pacman, mksquashfs and mkisofs
        progress output so that appropriate progress reports can be given.
        """
        if message.startswith('>-'):
            if message.startswith('>-_$$_'):
                # Informing us of the pid
                fss('larchscript', 'pid', int(message.rsplit('_', 1)[1]))
            else:
                # It is a progress report
                progress.set(message[2:])
                self.progressing = True
                return

        else:
            if self.progressing:
                progress.set()
                self.progressing = False

            progress.addLine(message)
            if message.startswith('?>'):
                # a query (yes/no): pop up the query
                fss('larchscript', 'reply', '??YES' if ui.command(
                        'confirmDialog', message[2:]) else '??NO')
            elif self._read_cb:
                self._read_cb(message)


    def sig_end_cb(self, ok):
        """A callback for the end of a 'larchscript'.
        The completion code, ok, is ignored.
        """
        if self._read_cb:
            self._read_cb(None)
            self._read_cb = None
            self.busy(False)
        else:
            progress.end()


    def sig_log(self, line):
        logger.addLine(line)




def tab_changed(index):
    __builtin__.stage = pages[index]
    stage.enter()

from page_project import ProjectSettings
from page_installation import Installation
from page_larchify import Larchify
from page_medium import Medium

from docviewer import DocViewer
from editor import Editor
from logview import Logger, Progress


def run_error(message, title=None):
    ui.command('warningDialog', message, title)
__builtin__.run_error = run_error


pages = [] # Must be initialized before init() because of calls to tab_changed

def init():
    pages.append(ProjectSettings())
    pages.append(Installation())
    pages.append(Larchify())
    pages.append(Medium())

    __builtin__.docviewer = DocViewer()
    __builtin__.edit = Editor().edit

    __builtin__.progress = Progress()
    __builtin__.logger = Logger()

    MainWindow = fss('fetch_layout', 'page_main.uim')
    ui.widgetlist(MainWindow)

    ui.connect(':notebook*changed', tab_changed)

    ui.command(':larch.pack')
    # Set up the first gui page (project settings)
    pages[0].setup()
    ui.command(':larch.show')

