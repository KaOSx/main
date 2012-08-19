#!/usr/bin/env python2
#
# media_common.py  - support functions for medium creation
#
# (c) Copyright 2009 - 2011 Michael Towers (larch42 at googlemail dot com)
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
# 2011.01.07

import os, re
from glob import glob
from config import *
from backend import *

class Medium:
    """This class represents a boot medium image.
    It converts a larchified system to a boot medium image, by preparing
    the bootloader directories and adding customisation stuff
    from the profile, but it does not write to any medium.
    Alternatively it can mount and prepare an existing larch medium for
    copying.
    """
    def __init__(self, options):
        self.options = options

        if options.source:
            # Mount the device or file
            runcmd('mkdir -p %s' % MPS)
            ok = False
            if options.source.endswith('.iso'):
                if mount(options.source, MPS, '-o loop'):
                    ok = True

            elif options.source.startswith('/dev/'):
                if mount(options.source, MPS):
                    ok = True

            elif options.source.startswith('/'):
                if mount(options.source, MPS, '--bind'):
                    ok = True

            elif mount(options.source, MPS, '-L'):
                ok = True

            if not ok:
                errout(_("Invalid source medium: '%s'") % options.source)

            # Paths needed for the further processing
            # - Assume no Arch installation available
            self.chrootpath = ''
            # - Temporary work area, mainly for building the boot directory
            self.build = BUILD0
            runcmd('rm -rf %s' % self.build)
            runcmd('mkdir -p %s' % self.build)
            # - The source medium
            self.medium_dir = MPS

            check_larchimage(self.medium_dir)
            if options.testmedium:
                unmount()
                comment('-- larch medium: ok')
                return

            # Fetch the existing boot directory
            runcmd('cp -r %s/boot %s' % (self.medium_dir, self.build))
            runcmd('rm -f %s/boot/isolinux/isolinux.boot' % self.build)
            runcmd('rm -f %s/boot/isolinux/ldlinux.sys' % self.build)

        else:
            # Paths needed for the further processing
            # - Using the Arch installation for chrooting
            installation_dir = get_installation_dir()
            self.chrootpath = (installation_dir
                    if installation_dir != '/' else '')
            # - Temporary work area, mainly for building the boot directory
            self.build = self.chrootpath + BUILD0
            runcmd('rm -rf %s' % self.build)
            runcmd('mkdir -p %s' % self.build)
            # - The source medium (as produced by larchify)
            self.medium_dir = self.chrootpath + CHROOT_DIR_MEDIUM
            if options.testmedium:
                return

            # Further initialisation for initial builds.
            check_larchimage(self.medium_dir)
            self.profile_dir = get_profile()
            self._bootdir()
            self._customizelarchdir()



    def _bootdir(self):
        """Prepare the boot directory for the bootloader. The
        bootloader configuration files are not generated yet, as these
        depend on the medium.
        """
        comment("Fetch kernel and initramfs")
        if not runcmd('cp -r %s/boot %s' % (self.medium_dir, self.build))[0]:
            errout(_("No kernel and/or initramfs"))

        comment("Preparing bootloader directory")
        # A basic /boot directory is provided in larch at cd-root/boot0.
        # The contents of this directory are placed in the medium's 'boot' directory.
        # Individual files can be added or substituted by
        # supplying them in the profile at cd-root/boot.
        # It is also possible to completely replace the basic boot directory
        # by having cd-root/boot0 in the profile - then the default
        # larch version will not be used.
        source0 = '%s/cd-root/boot0' % self.profile_dir
        if not os.path.isdir(source0):
            source0 = '%s/cd-root/boot0' % base_dir
        runcmd('bash -c "cp -r %s/* %s/boot"' % (source0, self.build))
        # Copy any additional profile stuff
        psource = '%s/cd-root/boot' % self.profile_dir
        if os.path.isdir(psource):
            runcmd('bash -c "cp -rf %s/* %s/boot"' % (psource, self.build))

        # Copy vesamenu.c32, chain.c32 to the boot directory
        for slfile in ('vesamenu.c32', 'chain.c32'):
            runcmd('cp %s/%s %s/boot/isolinux' %
                    (self.chrootpath + SYSLINUXDIR, slfile, self.build))
        # and rename base config file
        runcmd(('mv %s/boot/isolinux/isolinux.cfg'
                ' %s/boot/isolinux/isolinux.cfg_0')
                % (self.build, self.build))

        # Prepare utilities for copying media
        supportlibdir = BUILD0 + '/boot/support/lib'
        chroot(self.chrootpath, 'mkdir -p %s' % supportlibdir)
        for application in ('extlinux', 'syslinux',
                'mksquashfs', 'unsquashfs'):
            runnable = chroot(self.chrootpath, 'which %s' % application)
            if runnable:
                runnable = runnable[0]
            else:
# Should I output something?
                continue

            for line in chroot(self.chrootpath, 'ldd %s' % runnable):
                m = re.search(r'=> (/[^ ]+) ', line)
                if m:
                    chroot(self.chrootpath, 'cp -n %s %s' %
                            (m.group(1), supportlibdir))

            chroot(self.chrootpath, 'cp %s %s' % (runnable, supportlibdir))

        loader = None
        for l in glob(self.chrootpath + '/lib/ld-linux*.so.2'):
# Could use os.readlink() as alternative, just returning the link
            lrp = os.path.realpath(l)
            if lrp.split('/')[-2] == 'lib':
                loader = lrp
                break
        if loader:
            runcmd('cp %s %s%s/loader' % (loader, self.chrootpath, supportlibdir))
        else:
            errout(_("No loader binary, ") + u'/lib/ld-linux*.so.2')

        runcmd('cp %s/mbr.bin %s/boot/support' %
                (self.chrootpath + SYSLINUXDIR, self.build))
        runcmd('cp %s/isolinux.bin %s/boot/support' %
                (self.chrootpath + SYSLINUXDIR, self.build))


    def _customizelarchdir(self):
        """The medium's larch directory will be (re)built.
        First delete anything apart from system.sqf and mods.sqf, then
        add anything relevant from the profile.
        """
        for fd in os.listdir(self.medium_dir + '/larch'):
            if fd not in ('system.sqf', 'mods.sqf'):
                runcmd('rm -rf %s/larch/%s' % (self.medium_dir, fd))
        plarch = self.profile_dir + '/cd-root/larch'
        if os.path.isdir(plarch):
            runcmd('bash -c "cp -r %s/* %s/larch"' % (plarch, self.medium_dir))


    def setup_destination(self, device):
        """The basic preparation of a destination partition.
        """
        drive = device[:8]
        partno = device[8:]
        if not os.path.exists(device):
            errout(_("Invalid output device: %s") % device)

        def parted(cmd, optm=''):
            s = runcmd('parted -s %s %s %s' % (optm, drive, cmd))
            if s[0]:
                if s[1]:
                    return s[1]
                else:
                    return True
            return False

        # Prepare for formatting
        if self.options.format:
            fmtcmd = 'mkfs.ext4'
            self.fstype = 'ext4'
            if self.options.nojournal:
                fmtcmd += ' -O ^has_journal'
            labellength = 16
            opt = 'L'
        else:
            fmtcmd = None
            # Check device format
            ok, lines = runcmd('blkid -c /dev/null -o value -s TYPE %s' % device)
            if not ok:
                errout(_("Couldn't get format information for %s") % device)
            self.fstype = lines[0]

            fsflag = '#'
            if self.fstype in OKFS:
                fsflag = '+'
            elif self.fstype == 'vfat':
                fsflag = '-'
            if fsflag == '#':
                errout(_("Unsupported file-system: %s") % self.fstype)

        if self.options.testmedium:
            return

        # List drive content: 'parted  -m <drive>  print'
        #    - don't use 'free' because then you may get multiple lines starting '1:'.
        driveinfo = parted('print', '-m')

        if fmtcmd:
            lopt = ('-%s "%s"' % (opt, check_label(self.options.label, labellength))
                    if self.options.label else '')

            # Get partition table type from line with drive at beginning:
            #    > /dev/sdc:3898MB:scsi:512:512:msdos:Intenso Rainbow;
            #    - filter out partition table type (field 6)
            ptable = driveinfo[1].split(':')[5]

            # Filter out line for chosen partition (1):
            #    2:2000MB:3898MB:1898MB:::;
            #    - remember field 2 and 3
            pstart, pend = None, None
            for p in driveinfo[2:]:
                pinfo = p.split(':')
                if pinfo[0] == partno:
                    pstart, pend = pinfo[1:3]

            fail = True
            # Delete partition: 'parted  <drive> rm <partno>'
            if parted('rm %s' % partno):

                # Recreate partition:
                #    - if partition number > 4 AND it is an msdos partition table use
                #      'logical' instead of 'primary'
                #    'parted <drive> mkpart primary <ext2|fat32> <pstart> <pend>'
                ptype = 'logical' if (ptable == 'msdos') and (int(partno) > 4) else 'primary'
                if parted('mkpart %s %s %s %s' % (ptype, 'ext2', pstart, pend)):

                    # Format file system
                    if chroot(self.chrootpath, '%s %s %s' % (fmtcmd, lopt, device), ['dev']):
                        fail = False

            if fail:
                errout(_("Couldn't format %s") % device)

        # Set boot flag: 'parted  <drive> set <partno> boot on'
        #    and make drive bootable.
        #    Only do this if installing mbr.
        if self.options.mbr:
            # First remove boot flag from any partition which might have it ('boot'):
            # 'parted <drive> set <partno> boot off'
            for l in driveinfo[2:]:
                if 'boot' in l:
                    parted('set %s boot off' % l.split(':', 1)[0])

            parted('set %s boot on' % partno)
            runcmd('dd if=%s/boot/support/mbr.bin of=%s' % (self.build, drive))

        # Need to get the label - if not formatting (an option for experts)
        # it is probably not a good idea to change the volume label, so
        # use the old one.
        label = get_device_label(device)

        # Write bootloader configuration file
        bootconfig(self.build, label, device, self.options.detection)

        # Mount partition and remove larch and boot dirs
        runcmd('rm -rf %s' % MPD)
        runcmd('mkdir -p %s' % MPD)
        if not mount(device, MPD):
            errout(_("Couldn't mount larch partition, %s") % device)
        runcmd('rm -rf %s/larch' % MPD)
        runcmd('rm -rf %s/boot' % MPD)

        # Copy files to device
        runcmd('cp -r %s/larch %s' % (self.medium_dir, MPD))
        runcmd('cp -r %s/boot %s' % (self.build, MPD))


    def mkiso(self, xopts=''):
        """Build an iso containing the stuff in self.build, and optionally
        more - passed in xopts.
        """
        # Actually the volume label can be 32 bytes, but 16 is compatible
        # with ext2 (etc.) (though a little longer than vfat)
        label = check_label(self.options.label, 16)

        # Get fresh isolinux.bin
        runcmd('cp %s/boot/support/isolinux.bin %s/boot/isolinux'
                % (self.build, self.build))

        # Build iso
        ok, res = runcmd('mkisofs -R -l -no-emul-boot -boot-load-size 4'
                ' -b boot/isolinux/isolinux.bin -c boot/isolinux/isolinux.boot'
                ' -boot-info-table -input-charset=UTF-8'
                ' -V "%s"'
                ' -o "%s"'
                ' %s %s' % (label, self.options.isofile, xopts, self.build),
                filter=mkisofs_filter_gen())
        if not ok:
            errout(_("iso build failed"))
        comment(" *** %s ***" % (_("%s was successfully created")
                % (self.options.isofile)))



def check_larchimage(mediumdir):
    """A very simple check that the given path is that of a larch medium (image).
    """
    testfile = mediumdir + '/larch/system.sqf'
    if not os.path.isfile(testfile):
        errout(_("File '%s' doesn't exist, '%s' is not a larch medium")
                % (testfile, mediumdir))


def get_device_label(device):
    """Return the volume label of the given device.
    """
    return runcmd('blkid -c /dev/null -o value -s LABEL %s'
            % device)[1][0]


def check_label(l, n):
    if isinstance(l, unicode):
        l = l.encode('utf8')
    l = l.replace(' ', '_')
    if len(l) > n:
        if query_yn(_("The volume label is too long. Use the default (%s)?")
                % LABEL):
            return LABEL
        else:
            errout(_("Cancelled"))
    return l


def add_larchboot(idir):
    writefile("The presence of the file 'larch/larchboot' enables\n"
            "booting the device in 'search' mode.\n", idir + '/larch/larchboot')


def bootconfig(medium, label='', device='', detection=''):
    """Convert and complete the bootlines file.
    """
    kernel = readfile(medium + '/boot/kernelname').strip()
    # - add boot partition to options
    if detection == 'uuid':
        bootp = ('uuid=' +
                runcmd('blkid -c /dev/null -o value -s UUID %s'
                % device)[1][0].strip())
    elif detection == 'label':
        if not label:
            errout(_("Can't boot to label - device has no label"))
        bootp = 'label=%s' % label
    elif detection == 'partition':
        bootp = 'root=' + device
    else:
        bootp = ''

    # - convert bootfiles to the correct format,
    #      inserting necessary info
    bootconf = medium + '/boot/bootlines'
    if not os.path.isfile(bootconf):
        errout(_("Boot configuration file '%s' not found") % bootconf)
    fhi = open(bootconf)
    insert = ''
    i = 0
    block = ''
    title = ''
    opts = ''
    for line in fhi:
        line = line.strip()
        if not line:
            if title:
                i += 1
                # A block is ready
                block += 'label %02d\n' % i
                block += 'MENU LABEL %s\n' % title
                block += 'kernel /boot/%s\n' % kernel
                block += 'append initrd=/boot/larch.img %s %s\n' % (bootp, opts)
                if i > 1:
                    insert += '\n'
                insert += block
            block = ''
            title = ''
            opts = ''

        elif line.startswith('comment:'):
            block += '#%s\n' % (line.split(':', 1)[1])

        elif line.startswith('title:'):
            title = line.split(':', 1)[1].lstrip()

        elif line.startswith('options:'):
            opts = line.split(':', 1)[1].lstrip()
    fhi.close()

    # - insert the resulting string into the bootloader config file
    configfile = 'isolinux/isolinux.cfg'
    configfile0 = configfile + '_0'
    configpath = '%s/boot/%s' % (medium, configfile0)
    if not os.path.isfile(configpath):
        errout(_("Base configuration file (%s) not found") % configpath)
    fhi = open(configpath)
    fho = open('%s/boot/%s' % (medium, configfile), 'w')
    for line in fhi:
        if line.startswith("###LARCH"):
            fho.write(insert)
        else:
            fho.write(line)
    fhi.close()
    fho.close()
