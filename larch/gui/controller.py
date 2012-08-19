#!/usr/bin/env python2
#
# controller.py - Manages file-system access and calling of larch scripts
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
#2010.10.25

import sys, os, __builtin__
from liblarch.rootrun import init_rootrun
import threading
from glob import glob
from subprocess import call
try:
    import json as serialize
except:
    import simplejson as serialize

from config import *

from liblarch.translation import i18n_module, lang, i18nurl
__builtin__._ = i18n_module(base_dir, 'larch')
__builtin__.lang = lang


exports = {}
def add_exports(elist):
    for key, method in elist:
        exports[key] = method

__builtin__.add_exports = add_exports


def error0(message):
    sys.stderr.write('>>ERROR>>' + message + '\n')
    sys.stderr.flush()
__builtin__.error0 = error0


class Fs:
    """Collect file system access methods in one class.
    """
    def __init__(self):
        add_exports(    (
                ('fetch_layout', self.fetch_layout),
                ('isfile', self.isfile),
                ('isdir', self.isdir),
                ('rm_rf', self.rm_rf),
                ('get_partitions', self.get_partitions),
                ('readfile', self.readfile),
                ('savefile', self.savefile),
                ('get_docs_url', self.get_docs_url),
                ('oldsqf', self.oldsqf),
                ('oldlocales', self.oldlocales),
                ('browse', self.browse))
        )

    def fetch_layout(self, layout_file):
        fh = open(base_dir + '/gui/layouts/' + layout_file)
        r = fh.read()
        fh.close()
        return (True, eval(r))

    def rm_rf(self, path):
        call(['rm', '-rf', self._getpath(path)])
        return (True, None)

    def oldsqf(self):
        return (True,
                os.path.isfile(self._getpath('install:' + CHROOT_SYSTEMSQF))
                or os.path.isfile(self._getpath('install:' + CHROOT_DIR_MEDIUM
                        + '/larch/system.sqf')))

    def oldlocales(self):
        return (True, os.path.isdir(self._getpath('install:%s/locale'
                % CHROOT_DIR_BUILD)))

    def isfile(self, path):
        return (True, os.path.isfile(self._getpath(path)))

    def isdir(self, path):
        return (True, os.path.isdir(self._getpath(path)))


    def browse(self, path):
        fpath = self._getpath(path)
        if call(['mkdir', '-p', fpath]) == 0:
            # Start file browser at fpath
            call(project_manager.appget('filebrowser').replace('$', fpath)
                    + ' &', shell=True)
            return (True, None)
        else:
            return (False, None)

    def readfile(self, f):
        f = self._getpath(f)
        try:
            fh = open(f)
            r = fh.read()
            fh.close()
            return (True, r)
        except:
            return (False, _("Couldn't read file '%s'") % f)

    def savefile(self, f, d):
        f = self._getpath(f)
        dir = os.path.dirname(f)
        if not os.path.isdir(dir):
            os.makedirs(dir)
        try:
            fh = open(f, "w")
            fh.write(d)
            fh.close()
            return (True, None)
        except:
            return (False, _("Couldn't save file '%s'") % f)

    def _getpath(self, f):
        if f[0] != "/":
            base, f = f.split(':')
            f = '/' + f
            if base == 'base':
                f = base_dir + f
            elif base == 'profile':
                f = project_manager.profile_path + f
            elif base == 'working':
                f = project_manager.project_dir + f
            else:
                f = project_manager.get_ipath()[1] + f
        return f

    def get_docs_url(self, page):
        return (True, i18nurl(base_dir + '/docs/html/' + page))


    def get_partitions(self):
        """Get a list of available (not too small) partitions.
        """
        partlist = []
        with open('/proc/partitions') as fh:
            for l in fh:
                fields = l.split()
                if len(fields) == 4:
                    dev = fields[3]
                    if dev.startswith('sd') and (dev[-1] in '0123456789'):
                        size = (int(fields[2]) + 512) / 1024
                        if (size > 200):
                            # Keep a tuple (partition, size in MiB)
                            partlist.append(('/dev/' + dev, size))
        return (True, partlist)



class LarchScripts:
    """This class deals with calling the larch scripts.
    As they must be run as root, the rootrun module is used, which uses
    pexpect to start the subprocesses with su or sudo.
    Callbacks are used to fetch the password and return output lines
    (as they become available) and also to signal completion.
    While reading output from the subprocess the gui must remain responsive,
    and capable of updates (e.g. for logging, or cancelling of the process).
    To achieve this a separate thread is used for reading input from the
    subprocess (this is also taken care of by the rootrun module).
    The output lines and completion information are passed to the gui
    via signals/messages. The gui is responsible for handling them in the
    correct thread, e.g. by adding 'idle' calls.
    """
    def __init__(self):
        """Initialize the mechanism for making root calls.
        """
        self.rootfunc = init_rootrun(self._pwget)


    def do(self, cmdname, *args):
        """This is the larchscripts dispatcher.
        The first argument is the name of the function, the remaining ones
        are the arguments to the function.
        """
        return getattr(self, 'l_' + cmdname)(*args)


    def _pwget(self, cb, prompt):
        """Callback to fetch password, running in rootrun thread.
        """
        self.pw_event = threading.Event()
        ui_signal('get_password', prompt)
        self.pw_event.wait()
        self.rootfunc.cb_done(cb, *self.pw_returned)


    def l_sendpassword(self, ok, pw):
        """The gui passes in the password via this call.
        The result needs to be passed to the waiting self._pwget method
        (which is running in a different thread).
        """
        self.pw_returned = (ok, pw)
        self.pw_event.set()
        return None


    def _line_cb(self, cb, line):
        try:
            dline = serialize.loads(line)
        except:
            dline = line
        ui_signal('line_cb', dline)


    def _end_cb(self, cb, ok, res):
        # As the output is passed line-by-line there is no need to pass
        # it again.
        ui_signal('end_cb', ok)


    def call(self, cmd, arg=[]):
        """Start a process running as root.
        """
        args = ' '.join(['"%s"' % i for i in arg])
        cmdx = '%s/cli/%s.py -s %s' % (base_dir, cmd, args)
        self.l_rootfn(cmdx)
        return None


    def l_rootfn(self, cmd):
        """Run a command as root.
        """
        ui_signal('log', '++' + cmd)
        self.rootfunc.run(cmd, self._end_cb, self._line_cb, project_manager.project_dir)
        return None


    def l_archin(self, cmd, installrepos):
        args = ['-p', project_manager.profile_path,
                '-i', project_manager.get_ipath()[1],
                '-c', project_manager.get('pacman_cache')]
        rf = project_manager.project_dir + '/pacman.conf.repos'
        if installrepos and os.path.isfile(rf):
            args += ['-r', rf]
        return self.call('archin', args + cmd.split())


    def l_larchify(self, oldsyssqf, oldlocales):
        args = ['-p', project_manager.profile_path,
                '-i', project_manager.get_ipath()[1],]
        if oldsyssqf:
            args.append('-o')
        if oldlocales:
            args.append('-l')
        return self.call('larchify', args)


    def l_larchmedium(self, dev):
        return self.call('medium', ['-T', '-S', dev,])


    def l_writemedium(self, source, args):
        if source:
            args += ['-S', source]
        else:
            args += ['-p', project_manager.profile_path]
            args += ['-i', project_manager.get_ipath()[1]]
        return self.call('medium', args)


    def l_pid(self, pid):
        self.rootfunc.setpid(pid)
        return None


    def l_interrupt(self):
        ui_signal('log', '--Terminate--')
        self.rootfunc.interrupt()
        return None


    def l_reply(self, reply):
        self.rootfunc.send(reply)
        return None


    def l_close(self):
        # if something is running, stop it ...
        try:
            self.rootfunc.interrupt()
        except:
            pass

fs = Fs()

import project
project_manager.init()

larchscripts = LarchScripts()
add_exports((   ('larchscript', larchscripts.do),
    ))


