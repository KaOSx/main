#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

# i18n2.py

#2009-06-07
# Copyright 2009 Michael Towers

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

"""This is part 2 of the internationalization helper.
After editing ??.po, run this to compile it and copy it to the
correct location.
"""

import os
from subprocess import call

thisdir = os.path.dirname(os.path.realpath(__file__))
os.chdir(thisdir)
lf = open("lang", "r")
lang = lf.read()
lf.close()
langfile = lang + ".po"

print "Compiling internationalization for language '%s'\n" % lang
call(["msgfmt", "-c", "-v", "-o", "larch.mo", langfile])

podir = os.path.join(lang, "LC_MESSAGES")
if not os.path.isdir(podir):
    os.makedirs(podir)
os.rename(langfile, os.path.join(podir, langfile))
os.rename("larch.mo", os.path.join(podir, "larch.mo"))

print "DONE!"
