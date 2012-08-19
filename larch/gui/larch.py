#!/usr/bin/env python2
#
# larch.py - GUI for the larch scripts
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

import sys, os, __builtin__
dirpath = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dirpath + '/front')
basedir = os.path.dirname(dirpath)
sys.path.append(basedir + '/cli')
sys.path.append(os.path.dirname(basedir))

from controller import base_dir, exports
# Note that the gui module must have a reference point for relative
# paths, so the current directory must be set to the larch base directory
# before starting the gui:
os.chdir(base_dir)

import mainwindow

_running = False
def fss(key, *args, **kargs):
    while True:
        if _running:
            ui.busy(True)
        res = exports[key](*args)
        if _running and not ui.isbusy():
            ui.busy(False)
        if res:
            result = res[1]
            if res[0]:
                filter = kargs.get('filter')
                return filter(result) if filter else result

            if kargs.get('trap', True):
                ui.command('errorDialog', result)
                # That might return, but the gui should quit (soon?).
        return None

__builtin__.fss = fss
__builtin__.ui = mainwindow.Ui()
__builtin__.ui_signal = ui.sigin

mainwindow.init()
_running = True
ui.run()
