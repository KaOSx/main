#!/usr/bin/env python2
#
# docviewer.py
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
# 2010.06.24


import os


class DocViewer:
    def __init__(self):
        self.index = self._getPage('index.html')
        self.homepath = None
        ui.widgetlist(fss('fetch_layout', 'docviewer.uim'))

        ui.connectlist(
                ('doc:hide*clicked', self._hide),
                ('doc:back*clicked', self._back),
                ('doc:forward*clicked', self._forward),
                ('doc:home*clicked', self.gohome),
                ('doc:parent*clicked', self.goto),
                (':docs*clicked', self._show),
            )

    def _show(self):
        ui.runningtab(3)

    def _hide(self):
        ui.runningtab()

    def _back(self):
        ui.command('doc:content.prev')

    def _forward(self):
        ui.command('doc:content.next')

    def _getPage(self, page):
        return fss('get_docs_url', page)

    def gohome(self, home=None):
        if home:
            self.homepath = self._getPage(home)
        self.goto(self.homepath)

    def goto(self, path=None):
        if not path:
            path = self.index
        ui.command('doc:content.setUrl', path)
