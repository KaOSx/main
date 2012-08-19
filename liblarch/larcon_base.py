#!/usr/bin/env python2
#
# larcon_base.py   --  Basic backend framework for larcon applications
#
# (c) Copyright 2010-2011 Michael Towers (larch42 at googlemail dot com)
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
# 2011.02.01

import os, threading
from liblarch_conf import liblarchdir
from rootrun import init_rootrun
from translation import i18n_liblarch, _

class Backend:
    def __init__(self, appname, env, basedir=None):
        """The env(ironment), i.e. the global dictionary, is needed for
        fetching uim files.
        If the basedir is not provided it can be derived from the appname.
        """
        if basedir:
            self.basedir = basedir
        else:
            self.basedir = os.path.dirname(liblarchdir) + '/' + appname
        self.appenv = env

    def fss_fetch_layout(self, uim):
        fp = os.path.join(self.basedir, 'uim', uim)
        fh = open(fp)
        r = fh.read()
        fh.close()
        return eval(r, self.appenv)

    def fss_uim_fetch(self, uim):
        fp = os.path.join(liblarchdir, 'uim', uim)
        fh = open(fp)
        r = fh.read()
        fh.close()
        return eval(r)

    def setuisig(self, fn):
        self.ui_signal = fn

    def rootcall(self, cmd, fn_done, line_cb=None):
        self.rcall = init_rootrun(self._pwget)
        self.rcall.run(cmd, fn_done, line_cb)

    def _pwget(self, cb, prompt):
        self.pw_event = threading.Event()
        self.ui_signal('get_password', prompt)
        self.pw_event.wait()
        self.rcall.cb_done(cb, *self.pw_returned)

    def fss_sendpassword(self, ok, pw):
        # The result needs to be passed to the waiting _pwget method
        # (which is running in a different thread).
        self.pw_returned = (ok, pw)
        self.pw_event.set()
        return None

    def fss_header(self):
        """Override this to get a more verbose header.
        """
        return ""

    def fss_pixmaps(self, name):
        icon = name + '.png'
        logo = name + '_logo.png'
        return (icon, logo if os.path.isfile(logo) else icon)

