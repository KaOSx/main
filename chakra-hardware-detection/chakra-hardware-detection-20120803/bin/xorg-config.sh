#!/bin/bash
#
#**************************************************************************
#   Copyright (C) 2008-2009 Jan Mette                                     *
#   Copyright (C) 2009 Phil Miller                                        *
#   Copyright (C) 2012 Manuel Tortosa and the team behind Chakra          *
#                                                                         *
#   This script is free software; you can redistribute it and/or modify   *
#   it under the terms of the GNU General Public License as published by  *
#   the Free Software Foundation; either version 2 of the License, or     *
#   (at your option) any later version.                                   *
#                                                                         *
#   This program is distributed in the hope that it will be useful,       *
#   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#   GNU General Public License for more details.                          *
#                                                                         *
#   You should have received a copy of the GNU General Public License     *
#   along with this program; if not, write to the                         *
#   Free Software Foundation, Inc.,                                       *
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.          *
#**************************************************************************


#
# source needed functions and configs
#
# rc.conf
. /etc/rc.conf
# for message stuff like printhl
. /etc/rc.d/functions
# for kernel cmdline parsing
. /etc/rc.d/functions.d/cmdline
# the main config
. /etc/chakra-hwdetect.conf

#
# CHECK KERNEL COMMANDLINE IF XDRIVER VALUE OR NONFREE DRIVERS
# HAVE BEEN ENABLED OR NOT...
#
NONFREE=`get_nonfree`
XDRIVER=`get_xdriver`

[ -n "$XDRIVER" ] || XDRIVER="vesa"
[ -n "$NONFREE" ] || NONFREE="yes"

set_free_config() {
  case "$XDRIVER" in
    vesa)
      NONFREE="no"
      #force vesa driver
      printhl "Setting up X.Org driver: vesa"
      XDRIVER_VAL="Driver\t\"vesa\""
      sed -i -e /'Section "Device"'/,/'EndSection'/s/'Driver.*'/$XDRIVER_VAL/g /etc/X11/xorg.conf
    ;;
 
    *)
      # we dont force vesa
      printhl "..."
      rm /etc/X11/xorg.conf
    ;;
  esac
}

case "$NONFREE" in
  yes)
    if [ -e "/tmp/nvidia-173xx" ] ; then
      printhl "Loading tainted kernel module: nvidia-173xx"
      modprobe nvidia &>/dev/null

      printhl "Setting up X.Org driver: nvidia-173xx"
      nvidia-xconfig 
    elif [ -e "/tmp/nvidia" ] ; then
      printhl "Loading tainted kernel module: nvidia"
      modprobe nvidia &>/dev/null
	
      printhl "Setting up X.Org driver: nvidia"
      nvidia-xconfig 
    elif [ -e "/tmp/catalyst" ] ; then
      printhl "Loading tainted kernel module: catalyst"
      modprobe fglrx &>/dev/null
  
      printhl "Setting up X.Org driver: catalyst"
      aticonfig --initial 
    elif [ -e "/tmp/catalyst-legacy" ] ; then
      printhl "Loading tainted kernel module: catalyst-legacy"
      modprobe fglrx &>/dev/null
  
      printhl "Setting up X.Org driver: catalyst-legacy"
      aticonfig --initial 
    else                   
      set_free_config
    fi                     
  ;;

  *)
    set_free_config
  ;;

esac
