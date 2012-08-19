#!/usr/bin/env python2
#
# rootrun.py   --  Running commands as root, using pexpect with su or sudo
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
# 2011.01.10


import os, threading, pexpect
from subprocess import Popen, PIPE, STDOUT
from collections import deque

from liblarch_conf import sudo, sudoprompt

from translation import i18n_liblarch
_ = i18n_liblarch()


class FnChain:
    """Implements a simple dynamic function chain.
    The supplied function call is executed in a new thread. Further
    (pending) function calls can be added to the fifo list, self.fnlist,
    which is a queue for execution when the current function returns.
    When the list is empty, the chain is complete.
    """
    def __init__(self, fn, *args):
        self.fnlist = deque()
        self.step(fn, *args)
        self.pending = {}
        self.flagcount = 0
        threading.Thread(target=self._fnloop, args=()).start()

    def _fnloop(self):
        while True:
            try:
                fn, args = self.fnlist.popleft()
            except IndexError:
                return
            fn(*args)

    def step(self, fn, *args):
        self.fnlist.append((fn, args))

    def callback(self, cb, continuation, *args):
        if continuation:
            self.flagcount += 1
            myflag = self.flagcount
            if cb:
                self.pending[myflag] = continuation
        else:
            myflag = None
        if cb:
            cb(myflag, *args)
            # When the callback completes it needs to call the
            # callback_done method, passing the flag and the results,
            # unless the flag is None.
        elif continuation:
            self.step(continuation, *args)

    def callback_done(self, flag, *args):
        self.step(self.pending[flag], *args)
        del(self.pending[flag])



class _RootCommand:
    """This class allows shell commands to be run as root by non-root users.
    This is achieved using pexpect to negotiate with either su or sudo
    (selectable in the configuration file).
    The run method allows interaction with the running process on a
    line-by-line basis, if desired, using callbacks.
    The call method is a non-interactive wrapper to allow simple running
    of shell scripts as root, returning completion code and output text.
    N.B. IT IS NOT POSSIBLE TO USE UNESCAPED SINGLE QUOTES IN THE COMMAND.
    See the way the call is performed, using "bash -c 'cmd'", below.
    """
    def __init__(self, callback_pw):
        """Initialize the instance
        """
        self.password = None
        self.callback_pw = callback_pw
        self.fnchain = None


    def cb_done(self, flag, *args):
        """Called by a callback to pass its result back.
        """
        if flag:
            self.fnchain.callback_done(flag, *args)


    def run(self, cmd, end_callback, line_callback=None, cwd=None):
        self.cmd = cmd
        self.line_callback = line_callback
        self.end_callback = end_callback
        self.cwd = cwd
        if self.fnchain:
            debug("Previous FnChain instance not terminated")
        self.fnchain = FnChain(self._run_start)

    def _run_start(self, message=None):
        if sudo:
            self.process = pexpect.spawn("sudo -p '%s' bash -c 'echo ___ && %s'"
                    % (sudoprompt, self.cmd), cwd=self.cwd, timeout=None)
            self.password_prompt = sudoprompt
            if not message:
                message = _("Please enter (sudo) password:")

        else:       # use su
            self.process = pexpect.spawn("su -c 'echo ___ && %s'" % self.cmd,
                    cwd=self.cwd, timeout=None)
            self.password_prompt = ':'
            if not message:
                message = _("Please enter root password:")

        if self.process.expect([self.password_prompt, '\r\n']) == 0:
            if self.password:
                self.fnchain.step(self._run_sendpw)
            else:
                self.fnchain.callback(self.callback_pw, self._run_pw, message)

        else:
            self.fnchain.step(self._run_readloop)

    def _run_pw(self, ok, pw):
        if ok:
            self.password = pw
            self.fnchain.step(self._run_sendpw)
        else:
            self.process.close(force=True)
            # Avoid calling the end callback before self.fnchain is reset (threads!)
            _fnchain = self.fnchain
            self.fnchain = None
            _fnchain.callback(self.end_callback, None, False, _("Operation cancelled"))

    def _run_sendpw(self):
        self.process.sendline(self.password)
        while True:
            line1 = self.process.readline().strip()
            if line1:
                break
        if line1 == '___':
            self.fnchain.step(self._run_readloop)
        else:
            self.process.close(force=True)
            self.password = None
            self.fnchain.step(self._run_start, _("Incorrect password, try again:"))

    def _run_readloop(self):
        """The read loop collects output from the subprocess line by line
        and passes it on via the line callback. When the process has finished
        the end callback is passed the complete output text.
        """
        lines = ""
        while True:
            line = self.process.readline()
            if not line:                # Process finished
                break
            line = line.rstrip()
            lines += line + '\n'
            self.fnchain.callback(self.line_callback, None, line)

        # From the pexpect docs:
        # If you wish to get the exit status of the child you must call the
        # close() method. The exit or signal status of the child will be stored
        # in self.exitstatus or self.signalstatus. If the child exited normally
        # then exitstatus will store the exit return code and signalstatus will
        # be None. If the child was terminated abnormally with a signal then
        # signalstatus will store the signal value and exitstatus will be None.
        self.process.close()
        # Avoid calling the end callback before self.fnchain is reset (threads!)
        _fnchain = self.fnchain
        self.fnchain = None
        _fnchain.callback(self.end_callback, None, self.process.exitstatus == 0, lines)


    def interrupt(self):
        # Need to start a second pexpect to interrupt as root
        if sudo:
            pexpect.run('sudo -p "%s" kill -2 %d"' % (self.password_prompt, self.pid),
                    events={self.password_prompt: self.password+'\n'})
        else:
            pexpect.run('su -c "kill -2 %d"' % self.pid,
                    events={':': self.password+'\n'})

#    def kill(self):
#        self.process.close(force=True)

    def setpid(self, pid):
        """For kill to work as desired the pid to which the signal should
        be sent must first be set.
        """
        self.pid = pid


    def send(self, cmd):
        self.process.sendline(cmd)


    def call(self, cmd, cwd=None):
        self.event = threading.Event()
        self.run(cmd, self._end_callback0)
        self.event.wait()
        return self.retv


    def _end_callback0(self, ok, text):
        self.retv = (ok, text)
        self.event.set()



_rc = None
def init_rootrun(callback_pw):
    global _rc
    if not _rc:
        _rc = _RootCommand(callback_pw)
    return _rc


def runasroot(cmd, cwd=None, pwget=None):
    """Wrap RootCommand within a function, which waits for completion and
    returns the result as (ok (bool), output-text).
    In addition to the command to be executed it is also necessary to pass
    the callback for fetching the password, unless this has been supplied
    to a previous call, or is known to be unnecessary (unlikely, but possible).
    The cwd parameter allows the current working directory to be changed
    for the call.
    N.B. Because of the threading it is not possible to use this with
    (most?) gui libraries, if a graphical callback is needed.
    """
    if not _rc:
        init_rootrun(pwget)
    return _rc.call(cmd, cwd)
