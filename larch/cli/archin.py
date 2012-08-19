#!/usr/bin/env python2
#
# archin.py
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
# 2010.10.04

# This is a command line script to perform an Arch Linux installation
# based on a list of packages. All needed parameters are passed as options.

import os
from glob import glob
from backend import *

class Installation:
    def __init__(self, options):
        self.options = options
        self.installation_dir = get_installation_dir()
        if self.installation_dir == '/':
            errout(_("Operations on '/' are not supported ..."))

        self.profile_dir = get_profile()
        self.pacman_cmd = self.make_pacman_command()
        self.make_pacman_conf()


    def make_pacman_command(self):
        """Construct pacman command. Return the command, including options.
        This includes options for installation path, cache directory and
        for suppressing the progress bar. It assumes a temporary location
        for pacman.conf, which must also be set up.
        If there is no pacman executable in the system PATH, check that
        it is available in the larch directory.
        """
        pacman = runcmd('bash -c "which pacman || echo _FAIL_"')[1][-1].strip()
        if pacman == '_FAIL_':
            # If the host is not Arch, there will probably be no pacman
            # (if there is some other program called 'pacman' that's
            # a real spanner in the works).
            # The alternative is to provide it in the larch directory.
            pacman = base_dir + '/pacman'
            if not os.path.isfile(pacman):
                errout(_("No pacman executable found"))

        pacman += (' -r %s --config %s --noconfirm'
                % (self.installation_dir, PACMAN_CONF))
        if self.options.noprogress:
            pacman += ' --noprogressbar'
        if self.options.cache:
            pacman += ' --cachedir ' + self.options.cache
        return pacman


    def make_pacman_conf(self, final=False):
        """Construct the pacman.conf file used by larch.
        To make it a little easier to manage upstream changes to the default
        pacman.conf, a separate file (pacman.conf.repos) is used to specify
        the repositories to use. The contents of this file are used to modify
        the basic pacman.conf file, which may be the default version or one
        provided in the profile.
        The 'final' parameter determines whether the version for the resulting
        live system (True) or for the installation process (False) is
        generated. If generating the installation version, it is possible
        to specify alternative repositories, via the 'repofile' option,
        which allows the pacman.conf used for the installation to be
        different from the version in the resulting live system.
        The return value is a list of the names of the repositories which
        are included.
        It is also possible to specify just a customized mirrorlist for the
        installation by placing it in the working directory.
        """
        # Allow use of '*platform*' in pacman.conf.repos
        platform = os.uname()[4]
        if platform != 'x86_64':
            platform = 'i686'

        # Get pacman.conf header part
        pc0 = self.profile_dir + '/pacman.conf.options'
        if not os.path.isfile(pc0):
            pc0 = base_dir + '/data/pacman.conf'
        pacmanconf = self.pacmanoptions(readfile(pc0))

        # Get file with repository entries
        pc1 = self.profile_dir + '/pacman.conf.repos'
        if not os.path.isfile(pc1):
            pc1 = base_dir + '/data/pacman.conf.repos'
        if self.options.repofile and not final:
            pc1 = os.path.realpath(self.options.repofile)

        # Get repository path
        if final:
            default = 'Include = /etc/pacman.d/mirrorlist'
        else:
            mlist = cwd + '/mirrorlist'
            if not os.path.isfile(mlist):
                mlist = '/etc/pacman.d/mirrorlist'
                if not os.path.isfile(mlist):
                    mlist = base_dir + '/data/mirrorlist'
            default = 'Include = ' + mlist

        # Read repository entries
        repos = []
        for line in readfile(pc1).splitlines():
            line = line.strip()
            if (not line) or (line[0] == '#'):
                continue
            r, s = [t.strip() for t in line.split(':', 1)]
            repos.append(r)
            s = s.replace('*default*', default)
            pacmanconf += ('\n[%s]\n%s\n'
                    % (r, s.replace('*platform*', platform)))


        writefile(pacmanconf, self.installation_dir + '/etc/pacman.conf'
                if final else PACMAN_CONF)
        return repos


    def install(self):
        """Clear the chosen installation directory and install the base
        set of packages, together with any additional ones listed in the
        file 'addedpacks' (in the profile), removing the packages in
        'vetopacks' from the list.
        """
        if not query_yn(_("Install Arch to '%s'?") % self.installation_dir):
            return False
        # Can't delete the whole directory because it might be a mount point
        if os.path.isdir(self.installation_dir):
            if script('cleardir %s' % self.installation_dir):
                return False

        # Ensure installation directory exists and check that device nodes
        # can be created (creating /dev/null is also a workaround for an
        # Arch bug - which may have been fixed, but this does no harm)
        if not (runcmd('bash -c "mkdir -p %s/{dev,proc,sys}"'
                        % self.installation_dir)[0]
                and runcmd('mknod -m 666 %s/dev/null c 1 3'
                        % self.installation_dir)[0]):
            errout(_("Couldn't write to the installation path (%s)")
                    % self.installation_dir)
        if not runcmd('bash -c "echo test >%s/dev/null"'
                % self.installation_dir)[0]:
            errout(_("The installation path (%s) is mounted 'nodev'.")
                    % self.installation_dir)

        # I should also check that it is possible to run stuff in the
        # installation directory.
        runcmd('bash -c "cp $( which echo ) %s"' % self.installation_dir)
        if not runcmd('%s/echo "yes"' % self.installation_dir)[0]:
            errout(_("The installation path (%s) is mounted 'noexec'.")
                    % self.installation_dir)
        runcmd('rm %s/echo' % self.installation_dir)

        # Fetch package database
        runcmd('mkdir -p %s/var/lib/pacman' % self.installation_dir)
        self.refresh()

        # Get list of vetoed packages.
        self.packages = []
        self.veto_packages = []
        self.add_packsfile(self.profile_dir, 'vetopacks', must=False)
        self.veto_packages = self.packages

        # Include 'required' packages (these can still be vetoed, but
        # in some cases that will mean a larch system cannot be built)
        self.packages = []
        self.add_packsfile(base_dir + '/data', 'requiredpacks')

        # Add additional packages and groups, from 'addedpacks' file.
        self.add_packsfile(self.profile_dir, 'addedpacks')

        # Now do the actual installation.
        ok = self.pacmancall('-S', ' '.join(self.packages))
        if not ok:
            errout(_("Package installation failed"))

        # Some chroot scripts might need /etc/mtab
        runcmd('bash -c ":> %s/etc/mtab"' % self.installation_dir)

        # Build the final version of pacman.conf
        self.make_pacman_conf(True)
        comment(" *** %s ***" % _("Arch installation completed"))
        return True


    def add_packsfile(self, dir, packs_file, must=True):
        path = dir + '/' + packs_file
        if must and not os.path.isfile(path):
            errout(_("No '%s' file") % path)
        fh = open(path)
        for line in fh:
            line = line.strip()
            if line and (line[0] != '#'):
                if line[0] == '*':
                    self.add_group(line[1:].split()[0])
                elif line[0] == '+':
                    # Include directive
                    line = line[1:].split()[0]
                    if line[0] != '/':
                        line = dir + '/' + line
                    d, pf = line.rsplit('/', 1)
                    if not d:
                        errout(_("Invalid package file include: %s"))
                    self.add_packsfile(d, pf)
                elif line.startswith('!!!'):
                    # Ignore everything (!) entered previously.
                    # Allows requiredpacks to be overridden in addedpacks.
                    self.packages = []
                else:
                    line = line.split()[0]
                    if ((line not in self.packages)
                            and (line not in self.veto_packages)):
                        self.packages.append(line)
        fh.close()


    def add_group(self, gname):
        """Add the packages belonging to a group to the installaion list,
        removing any in the veto list.
        """
        # In the next line the call could be done as a normal user.
        for line in runcmd('%s -Sg %s' % (self.pacman_cmd, gname))[1]:
            l = line.split()
            if l and (l[0] == gname) and (l[1] not in self.veto_packages):
                self.packages.append(l[1])


    def refresh(self):
        """This updates or creates the pacman-db in the installation.
        This is done using using 'pacman ... -Sy' together with the
        customized pacman.conf file.
        """
        if not runcmd(self.pacman_cmd + ' -Sy',
                filter=pacman_filter_gen())[0]:
            errout(_("Couldn't synchronize pacman database (pacman -Sy)"))
        return True


    def pacmancall(self, op, arg=''):
        """Mount-bind the sys and proc directories before calling the
        pacman command built by make_pacman_command to perform operation
        'op' (e.g. '-S') with argument(s) 'arg' (a string).
        Then unmount sys and proc and return True if the command succeeded.
        """
        # (a) Prepare the destination environment (bind mounts)
        mount("/sys", "%s/sys" % self.installation_dir, "--bind")
        mount("/proc", "%s/proc" % self.installation_dir, "--bind")

        # (b) Call pacman
        ok = runcmd("%s %s %s" % (self.pacman_cmd, op, arg),
                filter=pacman_filter_gen())[0]

        # (c) Remove bound mounts
        unmount(("%s/sys" % self.installation_dir,
                "%s/proc" % self.installation_dir))
        return ok


    def pacmanoptions(self, text):
        """A filter for pacman.conf to remove the repository info.
        """
        texto = ""
        block = ""
        for line in text.splitlines():
            block += line + "\n"
            if line.startswith("#["):
                break
            if line.startswith("[") and not line.startswith("[options]"):
                break
            if not line.strip():
                texto += block
                block = ""
        return texto


    def sync(self, *packs):
        return self.pacmancall('-S', ' '.join(packs))


    def update(self, *files):
        return self.pacmancall('-U', ' '.join(files))


    def updateall(self, *files):
        return self.pacmancall('-Su')


    def remove(self, *packs):
        return self.pacmancall('-Rs', ' '.join(packs))



if __name__ == "__main__":
    cwd = os.getcwd()

    operations = 'install|sync|updateall|update|remove|refresh'
    from optparse import OptionParser, OptionGroup
    parser = OptionParser(usage=(_("usage: %%prog [options] %s [packages]")
            % operations))

    parser.add_option("-p", "--profile", action="store", type="string",
            default="", dest="profile",
            help=_("Profile: 'user:profile-name' or path to profile directory"))
    parser.add_option("-i", "--installation-dir", action="store", type="string",
            default="", dest="idir",
            help=_("Path to directory to be larchified (default %s)")
                    % INSTALLATION)
    parser.add_option("-s", "--slave", action="store_true", dest="slave",
            default=False, help=_("Run as a slave from a controlling program"
                    " (e.g. from a gui)"))
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
            default=False, help=_("Suppress output messages, except errors"
                    " (no effect if -s specified)"))


    parser.add_option("-f", "--force", action="store_true", dest="force",
            default=False, help=_("Don't ask for confirmation"))

    parser.add_option("-r", "--repofile", action="store", type="string",
            default="", dest="repofile",
            help=_("Supply a substitute repository list (pacman.conf.repos)"
                    " for the installation only"))
    parser.add_option("-c", "--cache-dir", action="store", type="string",
            default="", dest="cache",
            help=_("pacman cache directory (default /var/cache/pacman/pkg)"))
    parser.add_option("-n", "--noprogress", action="store_true",
            dest="noprogress",
            default=False, help=_("Don't show pacman's progress bar"))
## I think pacman is going to get support for something like '$arch', at
## which stage I could again consider architecture switching support in larch.
#    parser.add_option("-a", "--arch", action="store", type="string",
#            default="", dest="arch",
#            help=_("processor architecture (x86_64|i686) - defaults to"
#            " that of the host."
#            " This is an untested feature, which is probably only partially"
#            " implemented and may well not work."))

    (options, args) = parser.parse_args()
    if not args:
        print _("You must specify which operation to perform:\n")
        parser.print_help()
        sys.exit(1)

    if os.getuid() != 0:
        print _("This application must be run as root")
        sys.exit(1)

    init('archin', options)
    op = args[0]
    if op not in operations.split('|'):
        print (_("Invalid operation: '%s'\n") % op)
        parser.print_help()
        sys.exit(1)

    installation = Installation(options)
    method = getattr(installation, op)

    if method(*args[1:]):
        sys.exit(0)
    else:
        sys.exit(1)

