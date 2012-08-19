#!/usr/bin/env python2
#
# medium.py
#
# (c) Copyright 2010-2011 Michael Towers (larch42 at googlemail dot com)
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
# 2011.01.29

"""This is a command line script to place a larch system on a medium.
It can handle a larchified Arch installation for the initial creation of
a larch medium (source=""), but it can also copy from one existing
medium to another, or create a boot-iso for an existing larch medium
(only relevant for partitions).
The source can be a CD/DVD, an iso file or a partition (unmounted), the
output can be an iso file or another (unmounted) partition. In the latter
case the partition detection mode can be selected and data persistence
can be enabled (or disabled). In addition, the volume label of the
destination device can be set.
Parameters are passed as options and arguments.

A further source possiblity is an already mounted larch system, this being
specified by a source path starting with '/' (except '/dev/...'). This
option is provided for use with a running live system.
"""


import os
from backend import *
from media_common import *

def build_medium(options, device):
    """Copy an existing larch medium, specified by the option 'source' to
    the partition specified as argument.
    'device' is the name (e.g. '/dev/sdb1') of the partition to
    receive the larch image.
    """
    # Basic initialisation of the larchified source
    medium = Medium(options)
    build = medium.build
    medium_dir = medium.medium_dir

    if device:      # for destination partition (not iso)
        # This handles the bulk of the destination medium setup
        medium.setup_destination(device)

    if options.testmedium:
        return

    if options.bootiso:
        unmount()
        # Get bootloader configuration file
        fconf = build + '/boot/isolinux/syslinux.cfg'
        if not os.path.isfile(fconf):
            fconf = build + '/boot/isolinux/extlinux.conf'
        ok, res = runcmd('mv %s %s/boot/isolinux/isolinux.cfg' % (fconf, build))
        if not ok:
            errout(_("Couldn't find boot configuration file"))
        medium.mkiso()

    else:           # Now not boot iso!
        runcmd('rm -f %s/boot/isolinux/syslinux.cfg' % build)
        runcmd('rm -f %s/boot/isolinux/extlinux.conf' % build)

        # Now, need to test for overlay.medium and/or mods.sqf - the presence
        # of both is not supported here (although the larch initramfs hook
        # can cope with it).
        if os.path.isfile('%s/larch/overlay.medium' % medium_dir):
            if os.path.isfile('%s/larch/mods.sqf' % medium_dir):
                errout(_("Copying of devices with both 'overlay.medium' and 'mods.sqf'\n"
                        "is not supported."))
            if device and options.persist and (medium.fstype != 'vfat'):
                # Copy the overlay files to the destination medium
                for fd in os.listdir(medium_dir):
                    if (fd[0] != '.') and (fd not in IGNOREDIRS.split()):
                        runcmd('cp -a %s/%s %s' % (medium_dir, fd, MPD))

            else:
                # Create a modifications archive, mods.sqf
                if device:
                    modsdst = MPD
                else:
                    modsdst = build
                    runcomd('mkdir -p %s/larch' % modsdst)
                if not runcmd('%s/boot/support/support mksquashfs %s %s/larch/mods.sqf'
                        ' -b 256K -Xbcj x86 -wildcards -e %s'
                        % (build, medium_dir, modsdst, IGNOREDIRS),
                        filter=mksquashfs_filter_gen())[0]:
                    errout(_("Squashing mods.sqf failed"))
                # remove execute attrib
                runcmd('chmod oga-x %s/larch/mods.sqf' % modsdst)

        elif device and options.persist and (medium.fstype != 'vfat'):
            # mods.sqf must be unpacked onto the medium
            modsfile = medium_dir + '/larch/mods.sqf'
            if os.path.isfile(modsfile):
                runcmd('rm %s/larch/mods.sqf' % MPD)
                runcmd('%s/boot/support/support unsquashfs -d %s/.mods %s/larch/mods.sqf'
                        % (build, MPD, medium_dir))
                if not os.path.isdir(MPD + '/.mods'):
                    errout(_("Unpacking of modifications archive failed, see log"))
                runcmd('bash -c "mv %s/.mods/* %s"' % (MPD, MPD))
                runcmd('rm -rf %s/.mods' % MPD)
            writefile("The presence of the file 'larch/overlay.medium' causes\n"
                    "the medium to be used as a writeable, persistent overlay\n"
                    "for the larch root file-system.\n",
                    MPD + '/larch/overlay.medium')

        if device:
            # To boot in 'search' mode the file larch/larchboot must be present.
            runcmd('rm -f %s/larch/larchboot' % MPD)
            if options.larchboot:
                add_larchboot(MPD)

            if medium.fstype != 'vfat':
                # extlinux is installed to a mounted partition.
                # The configuration file must be called extlinux.conf:
                runcmd('mv %s/boot/isolinux/isolinux.cfg %s/boot/isolinux/extlinux.conf'
                        % (MPD, MPD))
                # Install extlinux
                runcmd('%s/boot/support/support extlinux -i %s/boot/isolinux'
                        % (build, MPD))
                # Unmount device(s)
                unmount()

            else:
                # syslinux is installed to an unmounted partition.
                # The configuration file must be called syslinux.cfg:
                runcmd('mv %s/boot/isolinux/isolinux.cfg %s/boot/isolinux/syslinux.cfg'
                        % (MPD, MPD))
                unmount()
                # Install syslinux
                runcmd('%s/boot/support/support syslinux -d /boot/isolinux -i %s'
                        % (build, device))

            comment(" *** %s ***" % (_("Completed writing to %s") % device))

        else:   # iso
            # Write bootloader configuration file
            bootconfig(build)
            # At present the 'larchboot' file is not necessary for booting from
            # optical media, but it should probably be present anyway.
            if not os.path.isfile(medium_dir + '/larch/larchboot'):
                add_larchboot(build)

            medium.mkiso(' -x %s/boot %s' % (medium_dir, medium_dir))
            unmount()

    runcmd('rm -rf %s' % build)



if __name__ == '__main__':
    from optparse import OptionParser, OptionGroup
    parser = OptionParser(usage=_("usage: %prog [options] [partition (e.g. /dev/sdb1)]"))

    parser.add_option('-S', '--source', action='store', type="string",
            dest='source', default='',
            help=_("Specify source medium: base directory (mount point) starting '/',"
                    " an iso-file (path ending '.iso'), device"
                    " (starting '/dev/') or volume label"))
    parser.add_option("-l", "--label", action="store", type="string",
            default="", dest="label",
            help=_("Volume label for boot medium (default: %s - or %s if boot iso)")
                    % (LABEL, BOOTISOLABEL))
    parser.add_option("-b", "--bootiso", action="store_true",
            dest="bootiso", default=False,
            help=_("Build a boot iso for the source partition"))

    # Options for building from larchified installation (no -S)
    parser.add_option("-p", "--profile", action="store", type="string",
            default="", dest="profile",
            help=_("Profile: 'user:profile-name' or path to profile directory"))
    parser.add_option("-i", "--installation-dir", action="store", type="string",
            default="", dest="idir",
            help=_("Path to larchified directory (default %s)") % INSTALLATION)

    # Options for iso output
    parser.add_option("-o", "--isofile", action="store", type="string",
            default="", dest="isofile",
            help=_("Specify the output file (default: '%s' in the current "
                    "directory - or '%s' if boot iso)") % (ISOFILE, BOOTISO))

    # Options for writing to partition
    parser.add_option("-d", "--detect", action="store", type="string",
            default="label", dest="detection",
            help=(_("Method for boot partition detection: %s (default: label)")
                    % detection_methods))
    parser.add_option("-n", "--nosearchboot", action="store_false",
            dest="larchboot", default=True,
            help=_("Don't generate 'larch/larchboot' file"))
    parser.add_option("-F", "--noformat", action="store_false",
            default=True, dest="format",
            help=_("Don't format the medium (WARNING: Only for experts)"))
    parser.add_option("-P", "--persist", action="store_true",
            dest="persist", default=False,
            help=_("Enable data persistence (using medium as writeable"
                    " file-system). Default: disabled"))
    parser.add_option("-m", "--noboot", action="store_false",
            dest="mbr", default=True,
            help=_("Don't install the bootloader (to the MBR)"))
    parser.add_option("-j", "--nojournal", action="store_true", dest="nojournal",
            default=False, help=_("Don't use journalling on boot medium"
            " (default: journalling enabled)"))

    # General minor options
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
            default=False, help=_("Suppress output messages, except errors"
                    " (no effect if -s specified)"))
    parser.add_option("-s", "--slave", action="store_true", dest="slave",
            default=False, help=_("Run as a slave from a controlling program"
                    " (e.g. from a gui)"))
    parser.add_option('-T', '--testmedium', action='store_true',
            dest='testmedium', default=False,
            help=_("Test source or destination medium only (used by gui)"))

    (options, args) = parser.parse_args()
    options.force = False
    init('live_medium', options)

    if options.bootiso:
        if args:
            errout(_("Unexpected argument: %s") % args[0])
        if not options.source:
            errout(_("No source specified for boot iso"))
        if not options.isofile:
            options.isofile = BOOTISO
        if not options.label:
            options.label = BOOTISOLABEL
        greet = _("Generating larch boot iso file: %s\n")
    else:
        if not options.isofile:
            options.isofile = ISOFILE
        if not options.label:
            options.label = LABEL
        greet = _("Generating larch iso file: %s\n")

    # Location for the resulting iso, forcing a '.iso' suffix
    if not options.isofile.endswith('.iso'):
        options.isofile += '.iso'

    if args:
        device = args[0]
        if device.startswith('/dev/'):
            comment((_("Testing output medium: %s\n")
                    if options.testmedium
                    else _("Creating larch medium on: %s\n")) % device)
        else:
            errout(_("Invalid partition: '%s'") % device)
    else:
        options.isofile = os.path.join(os.getcwd(), options.isofile)
        comment((_("Testing source medium: %s\n") % options.source)
                if options.testmedium
                else (greet % options.isofile))
        device = ''

    if os.getuid() != 0:
        print _("This application must be run as root")
        sys.exit(1)

    build_medium(options, device)
