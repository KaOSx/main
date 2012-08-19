#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

# i18n.py

#2011.01.07
# Copyright 2009-2011 Michael Towers

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

"""
A script, together with i18n2.py, to ease the use of the gettext translation
system with larch. Just run it with the (short) name of your language,
e.g. "fr", as argument.
The steps it performs are roughly given below. If you prefer a gui have a
look at poedit (uses wxwidgets).

1) Generally something like: pygettext.py -p i18n -o larch.pot *.py

2) cd i18n ; msginit -i larchin.pot -l de

OR:
2a) to update a po file:

cd i18n ; msgmerge -U larchin.po larchin.pot

3) edit po file

4) generate binary file:
cd i18n ; msgfmt -c -v -o larchin.mo larchin.po

5) move the .mo file to i18n/de/LC_MESSAGES

6) Add to the main program file:

import gettext
gettext.install('larch', 'i18n', unicode=1)

5) Run, e.g.:
LANG=de_DE larchin.py
"""

pygettext = '/usr/lib/python2.7/Tools/i18n/pygettext.py'
import sys, os, shutil
from subprocess import call

thisdir = os.path.dirname(os.path.realpath(__file__))
basedir = os.path.dirname(thisdir)
os.chdir(basedir)

dbg = False
if (len(sys.argv) < 2):
    lang = "de"
else:
    if sys.argv[1] == '-d':
        lang = "de"
        dbg = True
    else:
        lang = sys.argv[1]

print "Generating internationalization for language '%s'\n" % lang
print "    If you wanted a different language run 'i18n.py <language>'"
print "    For example 'i18n.py fr'\n"

allpy = ["cli/*.py", "gui/*.py", "gui/front/*.py", "gui/layouts/*.uim"]
if dbg:
    print "Debugging ...\n"

    from glob import glob
    for d in allpy:
        pys = glob(d)
        for f in pys:
            print "Parsing '%s'" % f
            call([pygettext, "-p", "i18n", "-o", "larch.pot", f])
    exit()

call([pygettext, "-p", "i18n", "-o", "larch.pot"] + allpy)

os.chdir(thisdir)
langfile = lang + ".po"
pofile = os.path.join(lang, "LC_MESSAGES", langfile)
if os.path.isfile(pofile):
    shutil.copy(pofile, ".")
    call(["msgmerge", "-U", langfile, "larch.pot"])
else:
    call(["sed", "-i", "s|CHARSET|utf-8|", "larch.pot"])
    call(["msginit", "--no-translator", "-i", "larch.pot", "-l", lang])

lf = open("lang", "w")
lf.write(lang)
lf.close()

print "Now edit '%s' and then run 'i18n2.py'" % langfile
