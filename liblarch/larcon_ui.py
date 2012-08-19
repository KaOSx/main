#!/usr/bin/env python2
#
# larcon_self.py   --  Frame for a single larcon tool

# (c) Copyright 2009-2011 Michael Towers (larch42 at googlemail dot com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#-------------------------------------------------------------------
# 2011.01.16

from suim import Suim

class LarconGui(Suim):
    def __init__(self, appname, backend):
        self.appname = appname
        self.app_backend = backend
        # Tell the backend how to send signals to the GUI
        self.app_backend.setuisig(self.sigin)

        self._running = False
        Suim.__init__(self, appname, [appname])
        self.widgetlist(self.fss('uim_fetch', 'larcon.uim'))
        self.connect('$$$uiquit$$$', self.quit)
        self.command('larcon.title', appname)
        icon, logo = self.fss('pixmaps', appname)
        self.command('larcon.icon', icon)
        self.command('larcon:pixmap.image', logo)
        self.command('larcon:header.markup', ['h3', ['color', '#c55500',
                ['em', appname], self.fss('header')]])
        self.command('larcon:main.layout', ['VBOX', appname])
        self.connect('larcon:docs*clicked', self._showdocs)
        self._showdocs(init=True)


    def quit(self):
        Suim.quit(self)


    def interface(self, func, *args):
        """Interface between GUI and file-system accessing functions (normally
        the main, functional part of the application). The first argument is the
        function name. There may be any number of arguments, including none.
        The simplest functions, those completing quickly and without interaction,
        return a non-<None> result - the type of the result is open.
        Longer running functions, or those that require some interaction return
        <None>, and then communicate subsequently using 'signals'.
        """
        return getattr(self.app_backend, 'fss_' + func)(*args)


    def fss(self, func, *args):
        """Supply backend (file-system) services to the gui
        """
        if func:
            if self._running and (func[0] != '_'):
                self.busy(True)
            # (Repeated setting or unsetting of the busy state is just ignored)
            result = self.interface(func, *args)
        else:
            result = True
        if self._running and result != None:
            self.busy(False)
        return result


    def data(self, key):
        return self.command('larcon_data.get', key)


    def _showdocs(self, init=False):
        if init:
            self.helptext = self.fss('about')
            self.helpstate = False
        else:
            self.helpstate = not self.helpstate

        if self.helpstate:
            self.command('larcon:docview.html', self.helptext)
            state = 1
            buttontext = self.data('hidetext')
            tooltip = self.data('hidett')
        else:
            state = 0
            buttontext = self.data('showtext')
            tooltip = self.data('showtt')

        self.command('larcon:stack.set', state)
        self.command('larcon:docs.text', buttontext)
        self.command('larcon:docs.tt', tooltip)


    def go(self):
        self.command('larcon.pack')
        self.command('larcon.show')
        self.run()


    def sigin(self, signal, *args):
        if signal:
            self.idle_add(getattr(self, 'sig_' + signal), *args)


    def sig_get_password(self, message):
        """This is a callback, triggered by signal 'get_password'
        to ask the user to input the password.
        """
        self.fss('sendpassword', *self.command('textLineDialog', message,
                "%s: pw" % self.appname, "", True))


    def sig_showcompleted(self, ok, message):
        """This is a callback, triggered by signal 'showcompleted'
        to display an info dialog.
        """
        self.command('infoDialog' if ok else 'warningDialog', message)
        self.fss(None)       # Tell 'fss' that the command has terminated



