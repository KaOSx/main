# backend.py - for the cli modules: handles processes and io
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
# 2010.11.09

# There was also the vague idea of a web interface, using a sort of state-
# based approach. Connecting to a running larch process would then require
# the ability to get the logging history, but presumably not the whole
# history on every ui update, which would need to be incremental.
# The logging function would need to be modified to accommodate this.

import os, sys, signal, atexit, __builtin__
import traceback, pwd
from subprocess import Popen, PIPE, STDOUT
import pexpect
try:
    import json as serialize
except:
    import simplejson as serialize
from config import *

def debug(text):
    sys.stderr.write("DEBUG: " + text.strip() + "\n")
    sys.stderr.flush()

sys.path.append(os.path.dirname(base_dir))
from liblarch.translation import i18n_module, lang
__builtin__._ = i18n_module(base_dir, 'larch')
__builtin__.lang = lang
# Run subprocesses without i18n in case the output is parsed.
os.environ["LANGUAGE"] = "C"


def init(app, options, app_quit=None):
    global _options, _quit_function, _log, _controlled, _dontask, _quiet
    _options = options
    _quit_function = app_quit
    _controlled = options.slave
    _dontask = options.force
    _log = None
    _quiet = False if _controlled else options.quiet

    atexit.register(sys_quit)
    if _controlled:
        _out('>-_$$_%d' % os.getpid())

    def sigint(num, frame):
        """A handler for SIGINT. Tidy up properly and quit.
        """
        errout("INTERRUPTED - killing subprocesses", 0)
        if _sub_process and _sub_process.pid:
            Popen(["pkill", "-g", str(_sub_process.pid)],
                    stdout=PIPE).communicate()
        errout("QUITTING", 2)
    signal.signal(signal.SIGINT, sigint)


    # Check no other instance of the script is running
    if os.path.isfile(LOCKFILE):
        app0 = readfile(LOCKFILE)
        if not query_yn(_(
                "larch (%s) seems to be running already."
                "\nIf you are absolutely sure this is not the case,"
                "\nyou may continue. Otherwise you should cancel."
                "\n\nShall I continue?") % app0):
            sys.exit(102)
    writefile(app, LOCKFILE)
    _log = open(LOGFILE + app, 'w')

    # For systems without /sbin and /usr/sbin in the normal PATH
    p = os.environ['PATH']
    ps = p.split(':')
    for px in ('/sbin', '/usr/sbin'):
        if px not in ps:
            p = px + ':' + p
    os.environ['PATH'] = p


def _out(text, force=False):
    """Send the string to standard output.
    How it is output depends on the '-s' command line option (whether the
    script is being run on the console or as a subprocess of another script).
    In the latter case the text will be slightly encoded - to avoid newline
    characters - and sent as a single unit.
    Otherwise output the lines as they are, but all lines except
    the first get a '--' prefix.
    """
    lines = text.encode('utf-8').splitlines()
    if _log and not text.startswith('>-'):
        # Don't log the progress report lines
        _log.write(lines[0] + '\n')
        for l in lines[1:]:
            _log.write('--' + l + '\n')

    if force or not _quiet:
        if _controlled:
            sys.stdout.write(serialize.dumps(text) + '\n')
        else:
            prefix = ''
            for line in lines:
                sys.stdout.write(prefix + line + '\n')
                prefix = '--'
        sys.stdout.flush()


def sys_quit():
    unmount()
    if _quit_function:
        _quit_function()
    if _errorcount:
        _out('!! ' + (_("The backend reported %d failed calls,"
                " you may want to investigate") % _errorcount))
    if _log:
        _log.close()
        os.remove(LOCKFILE)


def comment(text):
    _out('##' + text)


def query_yn(message):
    _out('?>' + message)
    if _dontask:
        result = True

    elif _controlled:
        result = (raw_input().strip() == '??YES')

    else:
        prompt = _("Yes:y|No:n")
        py, pn = prompt.split('|')
        respy = py.lower().split(':')
        respn = pn.lower().split(':')
        while True:
            resp = raw_input("   [ %s ]: " % prompt).strip().lower()
            if resp in respy:
                result = True
                break
            if resp in respn:
                result = False
                break

    _out('#>%s' % ('Yes' if result else 'No'))
    return result


def errout(message="ERROR", quit=1):
    _out('!>' + message, True)
    if quit:
        sys_quit()
        os._exit(quit)


def error0(message):
    errout(message, 0)
__builtin__.error0 = error0


# Catch all unhandled errors.
def errortrap(type, value, tb):
    etext = "".join(traceback.format_exception(type, value, tb))
    errout(_("Something went wrong:\n") + etext, 100)
sys.excepthook = errortrap


_sub_process = None
_errorcount = 0
def runcmd(cmd, filter=None):
    global _sub_process, _errorcount
    _out('>>' + cmd)
    _sub_process = pexpect.spawn(cmd)
    result = []
    line0 = ''
    # A normal end-of-line is '\r\n', so split on '\r' but don't
    # process a line until the next character is available.
    while True:
        try:
            line0 += _sub_process.read_nonblocking(size=256, timeout=None)
        except:
            break

        while True:
            lines = line0.split('\r', 1)
            if (len(lines) > 1) and lines[1]:
                line = lines[0]
                line0 = lines[1]
                nl = (line0[0] == '\n')
                if nl:
                    # Strip the '\n'
                    line0 = line0[1:]
                if filter:
                    nl, line = filter(line, nl)
                    if line == '/*/':
                        continue
                if nl:
                    line = line.rstrip()
                    _out('>_' + line)
                    result.append(line)
                else:
                    # Probably a progress line
                    if _controlled:
                        _out('>-' + line)
                    else:
                        sys.stdout.write(line + '\r')
                        sys.stdout.flush()

            else:
                break

    _sub_process.close()
    rc = _sub_process.exitstatus
    ok = (rc == 0)
    if not ok:
        _errorcount += 1
    _out(('>?%s' % repr(rc)) + ('' if ok else (' $$$ %s $$$' % cmd)))
    return (ok, result)


def script(cmd):
    s = runcmd("%s/%s" % (script_dir, cmd))
    if s[0]:
        return ""
    else:
        return "SCRIPT ERROR: (%s)\n" % cmd + "".join(s[1])


def chroot(ip, cmd, mnts=[], filter=None):
    if ip:
        for m in mnts:
            mdir = "%s/%s" % (ip, m)
            if not os.path.isdir(mdir):
                runcmd('mkdir -p %s' % mdir)
            mount("/" + m, mdir, "--bind")
        cmd = "chroot %s %s" % (ip, cmd)

    s = runcmd(cmd, filter)

    if ip:
        unmount(["%s/%s" % (ip, m) for m in mnts])

    if s[0]:
        if s[1]:
            return s[1]
        else:
            return True
    return False


_mounts = []
def mount(src, dst, opts=""):
    if runcmd("mount %s %s %s" % (opts, src, dst))[0]:
        _mounts.append(dst)
        return True
    return False


def unmount(dst=None):
    if dst == None:
        mnts = list(_mounts)
    elif type(dst) in (list, tuple):
        mnts = list(dst)
    else:
        mnts = [dst]

    r = True
    for m in mnts:
        if runcmd("umount %s" % m)[0]:
            _mounts.remove(m)
        else:
            r = False
    return r


def get_installation_dir():
    return os.path.realpath(_options.idir if _options.idir
            else INSTALLATION)


def get_profile():
    """Get the absolute path to the profile folder given its path in any
    acceptable form, including 'user:profile-name'
    """
    pd = (_options.profile if _options.profile
            else base_dir + '/profiles/default')
    p = pd.split(':')
    if len(p) == 1:
        pd = os.path.realpath(pd)
    else:
        try:
            pd = (pwd.getpwnam(p[0])[5] + PROFILE_DIR
                    + '/' + p[1])
        except:
            errout(_("Invalid profile: %s") % pd, quit=0)
            raise
    if not os.path.isfile(pd + '/addedpacks'):
        errout(_("Invalid profile folder: %s") % pd)
    return pd



#+++++++++++++++++++++++++++++++++++++++++
#Regular expression search strings for progress reports
import re
#lit: give []() a \-prefix
#grp: surround string in ()
#opt: surround string in []

def _lit(s):
    for c in r'[()]':
        s = s.replace(c, '\\' + c)
    return s

def _grp(s, x=''):
    return '(' + s + ')' + x

def _grp0(s, x=''):
    return '(?:' + s + ')' + x

def _opt(s, x=''):
    return '[' + s + ']' + x

re_psub = re.compile(r'\[[#-]+\]')
_re_pacman = re.compile( _grp0(_lit('(') +
                            _grp(_opt('^/', '+') + '/' + _opt('^)', '+')) +
                            _lit(')'), '?') +
                        _grp('.*?') +
                        _lit('[') + _grp(_opt('-#', '+')) + _lit(r']\s+') +
                        _grp(_opt('0-9', '+')) +
                        '%'
                        )

_re_mksquashfs = re.compile(_lit('[.*]') +
                            _grp('.* ' +
                                _grp(_opt('0-9', '+')) +
                                '%')
                            )

_re_mkisofs = re.compile(_opt(' 1') + _opt(' \d') + '\d\.\d\d%')

#-----------------------------------------
class pacman_filter_gen:
    """Return a function to detect and process the progress output of
    pacman.
    """
    def __init__(self):
        self.progress = ''

    def __call__(self, line, nl):
        ms = _re_pacman.match(line)
        if ms:
            p = ms.group(3)
            if (self.progress != p) or nl:
                self.progress = p
                xfromy = ms.group(1)
                if _controlled:
                    if not xfromy:
                        xfromy = ''
                    line = 'pacman:%s|%s|%s%%' % (xfromy, ms.group(2),
                            ms.group(4))
                elif ms.group(4) == '100':
                    line = re_psub.sub('[##########]', line)
                if nl:
                    sys.stdout.write(' '*80 + '\r')
            else:
                line = '/*/'
        return (nl, line)


class mksquashfs_filter_gen:
    """Return a function to detect and process the progress output of
    mksquashfs.
    """
    def __init__(self):
        self.progress = ''

    def __call__(self, line, nl):
        ms = _re_mksquashfs.match(line)
        if ms:
            percent = ms.group(2)
            if (self.progress != percent) or nl:
                self.progress = percent
                if _controlled:
                    line = 'mksquashfs:' + ms.group(1)
                else:
                    line = re.sub(r'=[-\\/|]', '= ', line)
            else:
                line = '/*/'
        return (nl, line)


class mkisofs_filter_gen:
    """Return a function to detect and process the progress output of
    mkisofs.
    """
    def __init__(self):
        self.running = None

    def __call__(self, line, nl):
        ms = _re_mkisofs.match(line)
        if ms:
            if _controlled:
                line = 'mkisofs:' + line
            self.running = line
            nl = False
        elif self.running:
            line = self.running + '\n' + line
            self.running = None
        return (nl, line)


def readdata(filename):
    return readfile(base_dir + '/data/' + filename)


def readfile(fpath):
    try:
        fh = open(fpath)
        text = fh.read()
        fh.close()
    except:
        errout(_("Couldn't read file: %s") % fpath)
        return None
    return text


def writefile(text, path):
    try:
        pd = os.path.dirname(path)
        if not os.path.isdir(pd):
            os.makedirs(pd)
        fh = None
        fh = open(path, 'w')
        fh.write(text)
        return True
    except:
        return False
    finally:
        if fh:
            fh.close()

