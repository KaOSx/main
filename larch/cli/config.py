# config.py
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
# 2010.10.23

# Basic (default) configuration information for larch
# Some of these can be changed ...????

# Default volume label
LABEL = 'LARCH-8'
# Default iso file
ISOFILE = 'larch8.iso'
# Default volume label for boot iso
BOOTISOLABEL = 'LARCH-8-BOOT'
# Default boot iso file
BOOTISO = 'larch8boot.iso'
# Used as a mount point for destination medium
MPD = '/tmp/larch_mnt'
# Used as a mount point for source medium
MPS = '/tmp/larch_source_mnt'
# Mount point (within chroot) for bind-mounting iso build directory
ISOBUILDMNT = '/tmp/isodir_mnt'
# Mount point for medium sources
SOURCEMOUNT = '/tmp/larch_mntsrc'
# Temporary directory for building medium boot directory
BUILD0 = '/tmp/larch_build'

SYSLINUXDIR = '/usr/lib/syslinux'

# A customized pacman.conf file is used for the installation, generated
# dynamically according to the options and the profile.
PACMAN_CONF = '/tmp/larch_pacman.conf'

# Medium detection alternatives
detection_methods = 'label|uuid|device|search'
# Directories to ignore when squashing mods.sqf
IGNOREDIRS = 'boot dev larch media proc sys tmp .*'
# Valid file-system types for extlinux
OKFS = ('ext2', 'ext3', 'ext4', 'btrfs')

# Some basic paths
import os, sys
module_dir = os.path.dirname(os.path.realpath(__file__))
base_dir = os.path.dirname(module_dir)
script_dir = base_dir + '/buildscripts'

# File to prevent two instances of larch from running
LOCKFILE = '/tmp/larch_lock'
# File (stem) for log
LOGFILE = '/tmp/larch_log_'
# The path to the Arch installation which is to be larchified
INSTALLATION = '/home/larchbuild'

# These paths are intended for use in 'chroot installation_dir', etc.
# The base directory of the larchified stuff
CHROOT_DIR_BUILD = '/.larch'
# This is the base of all stuff to be cleared on a rerun of larchify
CHROOT_DIR_LARCHIFY = CHROOT_DIR_BUILD + '/larchify'
# The base directory of the medium building area
CHROOT_DIR_MEDIUM = CHROOT_DIR_LARCHIFY + '/medium'
# Area for building the (mods) overlay
CHROOT_DIR_OVERLAY = CHROOT_DIR_LARCHIFY + '/overlay'
# Location for saving the system.sqf (outside of the larchify area)
CHROOT_SYSTEMSQF = CHROOT_DIR_BUILD + '/system.sqf'

