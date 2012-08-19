#!/usr/bin/env python2
#
# larchify.py
#
# (c) Copyright 2009-2011 Michael Towers (larch42 at googlemail dot com)
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
# 2011.01.30

# This is a command line script to prepare a larch live system from an
# Arch Linux installation. All needed parameters are passed as options.

import os, sys
from backend import *
from userinfo import Userinfo
from glob import glob
import random, crypt
from subprocess import Popen, PIPE, STDOUT


class Builder:
    """This class manages 'larchifying' an Arch Linux installation.
    """
    def __init__(self, options):
        self.installation_dir = get_installation_dir()
        self.installation0 = (self.installation_dir
                if self.installation_dir != "/" else "")
        testfile = self.installation0 + '/etc/pacman.conf'
        if not os.path.isfile(testfile):
            errout(_("File '%s' doesn't exist:\n"
                    "  '%s' not an Arch installation?")
                    % (testfile, self.installation_dir))

        self.profile_dir = get_profile()


    def build(self, options):
        if not (self.installation0 or query_yn(_(
                    "Building a larch live medium from the running system is"
                    "\nan error prone process. Changes to the running system"
                    "\nmade while running this function may be only partially"
                    "\nincorporated into the compressed system images."
                    "\n\nDo you wish to continue?"))):
                return False

        # Define the working area - it must be inside the installation
        # because of the use of chroot for some functions
        self.larchify_dir = self.installation0 + CHROOT_DIR_LARCHIFY
        # Location for the live medium image
        self.medium_dir = self.installation0 + CHROOT_DIR_MEDIUM
        # And potentially a saved system.sqf
        self.system_sqf = self.installation0 + CHROOT_SYSTEMSQF
        # Needed for a potentially saved locales directory
        self.locales_base = self.installation0 + CHROOT_DIR_BUILD
        # For building the (mods.sqf) overlay
        self.overlay = self.installation0 + CHROOT_DIR_OVERLAY
        comment("Initializing larchify process")

        if options.oldsqf:
            if os.path.isfile(self.medium_dir + "/larch/system.sqf"):
                runcmd("mv %s/larch/system.sqf %s" %
                        (self.medium_dir, self.system_sqf))
        else:
            runcmd("rm -f %s" % self.system_sqf)

        # Clean out larchify area and create overlay directory
        runcmd('rm -rf %s' % self.larchify_dir)
        runcmd('mkdir -p %s' % self.overlay)

        if not self.find_kernel():
            return False

        if not self.system_check():
            return False

        comment("Beginning to build larch medium files")
        # Clear out the directory
        runcmd('rm -rf %s' % self.medium_dir)
        # The medium's boot directory
        runcmd('mkdir -p %s/boot' % self.medium_dir)
        # The main larch direcory
        runcmd('mkdir -p %s/larch' % self.medium_dir)

        # Copy kernel to medium boot directory
        runcmd('cp -f %s/boot/%s %s/boot' %
                (self.installation0, self.kname, self.medium_dir))                
        if os.path.isfile("%s/boot/%s" % (self.installation0, 'vmlinuz26-lts')):
            runcmd('cp -f %s/boot/%s %s/boot' %
                (self.installation0, 'vmlinuz26-lts', self.medium_dir))
            runcmd('ln -sfv %s %s/boot/%s' %
                ('vmlinuz26-lts', self.medium_dir, 'vmlinuz26_lts'))
                
        # Remember file name
        writefile(self.kname, self.medium_dir + '/boot/kernelname')
        if os.path.isfile("%s/boot/%s" % (self.installation0, 'vmlinuz26-lts')):
            writefile('vmlinuz26-lts', self.medium_dir + '/boot/kernelname-lts')
            
        # if burg folder found we back it up and restore with tribe later
        if os.path.isdir("%s/boot/burg" % (self.installation0)):
            comment("Backup any found burg folder for tribe to restore")
            runcmd("mkdir -p %s/opt/chakra/restore" % (self.installation0))
            runcmd("cp -R %s/boot/burg %s/opt/chakra/restore" % (self.installation0, self.installation0))

        # if no saved system.sqf, squash the Arch installation at self.installation_dir
        if not os.path.isfile(self.system_sqf):
            comment("Generating system.sqf")
            # root directories which are not included in the squashed system.sqf
            ignoredirs = IGNOREDIRS + " mnt "
            # .larch and .livesys should be excluded by the '.*' entry in IGNOREDIRS
            # /var stuff
            ignoredirs += " var/log var/tmp var/lock var/cache/pacman/pkg var/lib/hwclock"
            # others
            ignoredirs += " usr/lib/locale"

            # Additional directories to ignore can also be specified in the
            # profile. This is a nasty option. It was requested, and might
            # be useful under certain special circumstances, but I recommend
            # not using it unless you are really sure what you are doing.
            veto_file = self.profile_dir + '/vetodirs'
            if os.path.isfile(veto_file):
                fh = open(veto_file)
                for line in fh:
                    line = line.strip()
                    if line and (line[0] != '#'):
                        ignoredirs += ' ' + line.lstrip('/')
                fh.close()

            if not chroot(self.installation0,
                    "/sbin/mksquashfs '/' '%s' -b 256K -Xbcj x86 -wildcards -e %s"
                    % (CHROOT_SYSTEMSQF, ignoredirs),
                    filter=mksquashfs_filter_gen()):
                errout(_("Squashing system.sqf failed"))
            # remove execute attrib
            runcmd("chmod oga-x %s" % self.system_sqf)

        # move system.sqf to medium's larch directory
        runcmd("mv %s %s/larch" % (self.system_sqf, self.medium_dir))

        # prepare overlay
        comment("Generating larch overlay")
        # Copy over the overlay from the selected profile
        if os.path.isdir("%s/rootoverlay" % self.profile_dir):
            runcmd('bash -c "cp -rf %s/rootoverlay/* %s"'
                    % (self.profile_dir, self.overlay))
        # Ensure there is an /etc directory in the overlay
        runcmd("mkdir -p %s/etc" % self.overlay)
        # Check there is no /boot
        if os.path.exists(self.overlay + '/boot'):
            error0(_("Warning: /boot in the profile's overlay will not be used"))
#        # Fix access permission on /root
#        if os.path.isdir("%s/root" % self.overlay):
#            runcmd("chmod 0750 %s/root" % self.overlay)
        # Fix sudoers if any
        if os.path.isfile("%s/etc/sudoers" % self.overlay):
            runcmd("chmod 0440  %s/etc/sudoers" % self.overlay)
            runcmd("chown root:root %s/etc/sudoers" % self.overlay)

        # Prepare inittab
        inittab = self.overlay + "/etc/inittab"
        itsave = inittab + ".larchsave"
        it0 = self.installation0 + "/etc/inittab"
        itl = self.overlay + "/etc/inittab.larch"
        if not os.path.isfile(itl):
            itl = self.installation0 + "/etc/inittab.larch"
            if not os.path.isfile(itl):
                itl = None
        # Save the original inittab if there is an inittab.larch file,
        #   ... if there isn't already a saved one
        if itl:
            if ((not os.path.isfile(it0 + ".larchsave"))
                    and (not os.path.isfile(itsave))):
                runcmd("cp %s %s" % (it0, itsave))
            # Use the .larch version in the live system
            runcmd("cp -f %s %s" % (itl, inittab))

        comment("Generating larch initcpio")
        if not self.gen_initramfs():
            return False

        lpath = self.locales_base + '/locale'
        if self.installation0:
            if options.oldlocales and os.path.isdir(lpath):
                comment("Copying saved glibc locales")
                runcmd('rm -rf %s/usr/lib/locale' % self.overlay)
                runcmd('mkdir -p %s/usr/lib' % self.overlay)
                runcmd('cp -a %s %s/usr/lib' % (lpath, self.overlay))
                runcmd('cp %s/locale.gen %s/etc'% (self.locales_base,
                        self.overlay))
            else:
                comment("Generating glibc locales")
                runcmd('rm -rf %s' % lpath)
                script('larch-locales "%s" "%s"' % (self.installation0,
                        self.overlay))
                # Save the generated locales for possible reuse
                runcmd('cp -a %s/usr/lib/locale %s' % (self.overlay,
                        self.locales_base))
                runcmd('cp %s/etc/locale.gen %s'% (self.overlay,
                        self.locales_base))

        if (os.path.isfile(self.installation0 + '/usr/bin/ssh-keygen')
                and not os.path.isfile(self.profile_dir + '/nosshkeys')):
            # ssh initialisation - done here so that it doesn't need to
            # be done when the live system boots
            comment("Generating ssh keys to overlay")
            sshdir = CHROOT_DIR_OVERLAY + "/etc/ssh"
            runcmd("mkdir -p %s" % (self.installation0 + sshdir))
            for k, f in [("rsa1", "ssh_host_key"), ("rsa", "ssh_host_rsa_key"),
                    ("dsa", "ssh_host_dsa_key")]:
                chroot(self.installation0,
                        "ssh-keygen -t %s -N '' -f %s/%s"
                        % (k, sshdir, f), ["dev"])

        # Ensure the hostname is in /etc/hosts
        script("larch-hosts %s %s" % (self.installation0, self.overlay))

        # Handle /mnt (this is done like this in case something is mounted
        # within /mnt - only the mount points should be included in the live system).
        runcmd("mkdir -p %s/mnt" % self.overlay)
        for d in os.listdir("%s/mnt" % self.installation0):
            if os.path.isdir("%s/mnt/%s" % (self.installation0, d)):
                runcmd("mkdir %s/mnt/%s" % (self.overlay, d))

        # Add an empty /var/lib/hwclock directory
        runcmd("mkdir -p %s/var/lib/hwclock" % self.overlay)

        # Run customization script
        tweak = self.profile_dir + '/build-tweak'
        if os.path.isfile(tweak):
            comment("(WARNING): Running user's build customization script")
            if runcmd(tweak + ' %s %s' % (self.installation0,
                    self.overlay))[0]:
                comment("Customization script completed")
            else:
                errout(_("Build customization script failed"))

        # Get root password
        rootpwf = self.profile_dir + '/rootpw'
        if os.path.isfile(rootpwf):
            rootpw = readfile(rootpwf).strip()
            if rootpw == '!':
                # Lock the password
                rootcmd = 'usermod -L'
            else:
                rootcmd = "usermod -p '%s'" % encryptPW(rootpw)
        else:
            rootcmd = None

        # Add users and set root password
        if self.installation0 and not self.add_users(rootcmd):
            return False

        comment("Squashing mods.sqf")
        if not chroot(self.installation0,
                "/sbin/mksquashfs '%s' '%s/larch/mods.sqf' -b 256K -Xbcj x86 -wildcards -e %s"
                % (CHROOT_DIR_OVERLAY, CHROOT_DIR_MEDIUM, IGNOREDIRS),
                filter=mksquashfs_filter_gen()):
            errout(_("Squashing mods.sqf failed"))
        # remove execute attrib
        runcmd("chmod oga-x %s/larch/mods.sqf" % self.medium_dir)

        runcmd("rm -rf %s" % self.overlay)

        comment(" *** %s ***" % _("larchify-process completed"))
        return True


    def add_users(self, rootcmd):
        userinfo = Userinfo(self.profile_dir)
        userlist = []
        for user in userinfo.allusers():
            # Only include if the user does not yet exist
            if runcmd('bash -c "grep \"^%s\" %s/etc/passwd || echo -"'
                    % (user, self.installation_dir))[1][0] != '-':
                comment("(WARNING): User '%s' exists already" % user)
            else:
                userlist.append(user)

        # Only continue if there are new users in the list
        if rootcmd:
            clist = [('root', rootcmd + ' %s')]
        else:
            if userlist == []:
                return True
            clist = []

        # Save system files and replace them by the overlay versions
        savedir = self.larchify_dir + '/save_etc'
        runcmd('rm -rf %s' % savedir)
        runcmd('mkdir -p %s/default' % savedir)
        savelist = 'group,gshadow,passwd,shadow,login.defs,skel'
        runcmd('bash -c "cp -a %s/etc/{%s} %s"'
                % (self.installation0, savelist, savedir))
        runcmd('cp -a %s/etc/default/useradd %s/default'
                % (self.installation0, savedir))
        for f in ('group', 'gshadow', 'passwd', 'shadow', 'login.defs'):
            if os.path.isfile(self.overlay + '/etc/%s'):
                runcmd('cp %s/etc/%s %s/etc'
                        % (self.overlay, f, self.installation0))
        if os.path.isfile(self.overlay + '/etc/default/useradd'):
            runcmd('cp %s/etc/default/useradd %s/etc/default'
                    % (self.overlay, self.installation0))
        if os.path.isdir(self.overlay + '/etc/skel'):
            runcmd('cp -r %s/etc/skel %s/etc'
                    % (self.overlay, self.installation0))

        # Build the useradd command
        userdir0 = '/users'
        userdir = self.larchify_dir + userdir0
        userdirs = []
        runcmd('mkdir -p %s/home' % self.overlay)
        for u in userlist:
            cline = 'useradd -m'
            pgroup = userinfo.get(u, 'maingroup')
            if pgroup:
                cline += ' -g ' + pgroup
            uid = userinfo.get(u, 'uid')
            if uid:
                cline += ' -u ' + uid
            pw = userinfo.get(u, 'pw')
            if (pw == ''):
                # Passwordless login
                pwcrypt = ''
            else:
                # Normal MD5 password
                pwcrypt = encryptPW(pw)
            cline += " -p '%s'" % pwcrypt
            skeldir = userinfo.get(u, 'skel')
            if skeldir:
                # Custom home initialization directories in the profile
                # always start with 'skel_'
                skel = 'skel_' + skeldir
                if skel not in userdirs:
                    userdirs.append(skel)
                cline += ' -k %s/%s' % (CHROOT_DIR_LARCHIFY + userdir0,
                        skel)
            # Allow for expert tweaking
            cline += ' ' + userinfo.get(u, 'expert')
            # The user and the command to be run
            clist.append((u, cline + ' %s'))
            xgroups = userinfo.get(u, 'xgroups')
            if xgroups:
                xgl = []
                for g in xgroups.split(','):
                    clist.append((u, 'usermod -a -G %s %%s' % g))

        if userdirs:
            # Copy custom 'skel' directories to build space
            runcmd('rm -rf %s' % userdir)
            runcmd('mkdir -p %s' % userdir)
            for ud in userdirs:
                runcmd('cp -r %s/%s %s/%s' %
                        (self.profile_dir, ud, userdir, ud))

        nfail = 0
        ok = True
        for u, cmd in clist:
            if not chroot(self.installation0, cmd % u):
                nfail += 1
                # Errors adding users to groups are not fatal:
                if not cmd.startswith('usermod -a -G'):
                    ok = False
            if os.path.isdir('%s/home/%s' % (self.installation0, u)):
                runcmd('mv %s/home/%s %s/home'
                        % (self.installation0, u, self.overlay))

        if nfail > 0:
            errout(_("%d user account operation(s) failed") % nfail, 0)
        # Move changed /etc/{group,gshadow,passwd,shadow} to overlay
        runcmd('bash -c "mv %s/etc/{group,gshadow,passwd,shadow} %s/etc"'
                % (self.installation0, self.overlay))
        # Restore system files in base installation
        runcmd('rm -rf %s/etc/skel' % self.installation0)
        runcmd('bash -c "cp -a %s/* %s/etc"'
                % (savedir, self.installation0))
        return ok


    def system_check(self):
        comment("Testing for necessary packages and kernel modules")
        fail = ""
        warn = ""
        nplist = ["larch-live"]

        mdep = (self.installation0 +
                "/lib/modules/%s/modules.dep" % self.kversion)
        if Popen(["grep", "/squashfs.ko", mdep], stdout=PIPE,
                stderr=STDOUT).wait() != 0:
            fail += _("No squashfs module found\n")

        if Popen(["grep", "/aufs.ko", mdep], stdout=PIPE,
                stderr=STDOUT).wait() == 0:
            self.ufs='_aufs'
            nplist.append("aufs2-util")

        elif Popen(["grep", "/unionfs.ko", mdep], stdout=PIPE,
                stderr=STDOUT).wait() == 0:
            self.ufs='_unionfs'

        else:
            fail += _("No aufs or unionfs module found\n")

        for p in nplist:
            if not self.haspack(p):
                fail += _("Package '%s' is needed by larch systems\n") % p

        if not self.haspack("syslinux"):
            warn += _("Without package 'syslinux' you will not be able\n"
                    "to create syslinux or isolinux booting media\n")

        if (not self.haspack("cdrkit")) and (not self.haspack("cdrtools")):
            warn += _("Without package 'cdrkit' (or 'cdrtools') you will\n"
                    "not be able to create CD/DVD media\n")

        if not self.haspack("eject"):
            warn += _("Without package 'eject' you will have problems\n"
                    "using CD/DVD media\n")

        if warn:
            cont = query_yn(_("WARNING:\n%s"
                    "\n    Continue building?") % warn)
        else:
            cont = True

        if fail:
            errout(_("ERROR:\n%s") % fail)

        return cont


    def haspack(self, package):
        """Check whether the given package is installed.
        """
        for p in os.listdir(self.installation0 + '/var/lib/pacman/local'):
            if p.rsplit("-", 2)[0] == package:
                return True
        return False


    def find_kernel(self):
        # The uncomfortable length of this function is deceptive,
        # most of it is for dealing with errors.
        comment("Seeking kernel information")
        kinfo = (readfile(self.profile_dir + '/kernel')
                if os.path.isfile(self.profile_dir + '/kernel')
                else readdata('kernel'))
        vmlinuz, self.kernel = kinfo.split()
        kernels = []
        files = os.listdir(self.installation0 + '/boot')
        for kf in files:
            p = Popen(['file', '-b', self.installation0 + '/boot/' + kf],
                    stdout=PIPE, stderr=STDOUT)
            if p.communicate()[0].startswith('Linux kernel'):
                kernels.append(kf)
        if vmlinuz not in kernels:
            if vmlinuz in files:
                comment("(WARNING): File '%s' not recognised as kernel"
                        % vmlinuz)
            else:
                errout(_("Kernel file '%s' not found") % vmlinuz)
        if len(kernels) > 1:
            comment("(WARNING): More than one kernel found:\n  %s" %
                    "\n  ".join(kernels))
        self.kname = vmlinuz
        
        # Try to read the kernel version from a *.kver file
        self.kversion = None
        if os.path.isfile("%s/boot/%s" % (self.installation0, 'vmlinuz26-lts')):
            self.kversionlts = None
            verfile = self.installation0 + '/etc/mkinitcpio.d/kernel26-lts.kver'
            if os.path.isfile(verfile):
                gvars = {}
                execfile(verfile, gvars)
                self.kversionlts = gvars.get('ALL_kver')
                
        verfile = self.installation0 + '/etc/mkinitcpio.d/%s.kver' % self.kernel
        if os.path.isfile(verfile):
            gvars = {}
            execfile(verfile, gvars)
            self.kversion = gvars.get('ALL_kver')
        else:
            comment("(WARNING): No kernel version file (%s)" % verfile)

        # mkinitcpio preset file for the kernel
        self.presetfile = self.installation0 + '/etc/mkinitcpio.d/%s.preset' % self.kernel
        if not os.path.isfile(self.presetfile):
            errout(_("No mkinitcpio preset file (%s)") % self.presetfile)

        # Now check module directories
        moduledirs = []
        kvfound = False
        dirs = os.listdir(self.installation0 + '/lib/modules')
        for kv in dirs:
            if os.path.isfile(self.installation0
                    + ('/lib/modules/%s/modules.dep' % kv)):
                moduledirs.append(kv)
                if kv == self.kversion:
                    kvfound = True

            else:
                kmpath = self.installation0 + ('/lib/modules/%s' % kv)
                comment("Unexpected kernel files at %s" % kmpath)
                # Try to find packages concerned
                p = Popen(["find", ".", "-name", "*.ko"], cwd=kmpath,
                        stdout=PIPE, stderr=STDOUT)
                r = p.communicate()[0]
                if p.returncode == 0:
                    packs = []
                    for km in r.split():
                        a = chroot(self.installation0,
                                'pacman -Qoq /lib/modules/%s/%s'
                                % (kv, km))

                        if a:
                            pack = "-".join(a[0].split())
                            if pack not in packs:
                                packs.append(pack)
                                comment(" Package: %s" % pack)

                else:
                    comment("Couldn't determine guilty packages")

                if not query_yn(_("WARNING:"
                        "\n  You seem to have installed a package containing modules"
                        "\nwhich aren't compatible with your kernel (see log)."
                        "\nPlease check that this won't cause problems."
                        "\nMaybe you need the corresponding package for your kernel?"
                        "\n\n    Continue building?")):
                    return False

        if len(moduledirs) > 1:
            comment("(WARNING): More than one kernel module directory found:\n  %s" %
                    "\n  ".join(moduledirs))
        if not kvfound:
            if len(moduledirs) == 1:
                self.kversion = moduledirs[0]
                comment("Assuming kernel version = '%s'" % self.kversion)
                comment("Kernel updates will probably fail.")
            else:
                errout(_("Couldn't find kernel modules"))

        comment("Kernel: %s   -   version: %s" % (self.kname, self.kversion))
        chroot(self.installation0, "depmod %s" % self.kversion)
        if os.path.isfile("%s/boot/%s" % (self.installation0, 'vmlinuz26-lts')):
            comment("LTS-Kernel: %s   -   version: %s" % ('vmlinuz26-lts', self.kversionlts))
            chroot(self.installation0, "depmod %s" % self.kversionlts)
        return True


    def gen_initramfs(self):
        # Determine larch mkinitcpio.conf file
        conf = '/etc/mkinitcpio.conf.larch'
        if os.path.isfile(self.overlay + conf):
            conf = CHROOT_DIR_OVERLAY + conf

        # Save original preset file (unless a '*.larchsave' is already present)
        oldir = self.overlay + "/etc/mkinitcpio.d"
        runcmd("mkdir -p %s" % oldir)
        olpreset = '%s/%s.preset' % (oldir, self.kernel)
        if not os.path.isfile("%s.larchsave" % self.presetfile):
            runcmd("cp %s %s.larchsave" % (self.presetfile, olpreset))
        if os.path.isfile("%s/boot/%s" % (self.installation0, 'vmlinuz26-lts')):
            self.presetfilelts = self.installation0 + '/etc/mkinitcpio.d/kernel26-lts.preset'
            olpresetlts = '%s/%s.preset' % (oldir, 'kernel26-lts')
            if not os.path.isfile("%s.larchsave" % self.presetfilelts):
                runcmd("cp %s %s.larchsave" % (self.presetfilelts, olpresetlts))
            
        # Adapt larch.preset file for kernel name and replace standard preset
        writefile(readfile(self.installation0 + '/etc/mkinitcpio.d/larch.preset'
                ).replace('_k_', self.kernel), olpreset)
        if os.path.isfile("%s/boot/%s" % (self.installation0, 'vmlinuz26-lts')):
            writefile(readfile(self.installation0 + '/etc/mkinitcpio.d/larch.preset'
                    ).replace('_k_', 'kernel26-lts').replace('larch.img', 'larch-lts.img'), olpresetlts)

        # Generate initramfs
        chroot(self.installation0,
                "mkinitcpio -k %s -c %s -g %s" %
                (self.kversion, conf,
                 CHROOT_DIR_MEDIUM + "/boot/larch.img"))            
        if os.path.isfile("%s/boot/%s" % (self.installation0, 'vmlinuz26-lts')):
            chroot(self.installation0,
                "mkinitcpio -k %s -c %s -g %s" %
                (self.kversionlts, conf,
                 CHROOT_DIR_MEDIUM + "/boot/larch-lts.img"))
            runcmd('ln -sfv %s %s/boot/%s' %
                ('larch-lts.img', self.medium_dir, 'larch_lts.img'))
        return True


def encryptPW(pw):
    """Encrypt a password - needed for user account generation.
    """
    salt = '$1$'
    for i in range(8):
        salt += random.choice("./0123456789abcdefghijklmnopqrstuvwxyz"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return crypt.crypt(pw, salt)



if __name__ == "__main__":
    from optparse import OptionParser, OptionGroup
    parser = OptionParser(usage=_("usage: %prog [options]"))

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
    parser.add_option("-o", "--oldsqf", action="store_true", dest="oldsqf",
            default=False, help=_("Reuse previously generated system.sqf"))
    parser.add_option("-l", "--oldlocales", action="store_true",
            dest="oldlocales", default=False,
            help=_("Reuse previously generated locales"))
    parser.add_option("-f", "--force", action="store_true", dest="force",
            default=False, help=_("Don't ask for confirmation"))

    (options, args) = parser.parse_args()

    if os.getuid() != 0:
        print _("This application must be run as root")
        sys.exit(1)
    init('larchify', options)
    builder = Builder(options)
    if builder.build(options):
        sys.exit(0)
    else:
        sys.exit(1)
