#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

#2011.01.16
# Copyright 2010 Michael Towers

"""
1) Generally something like: pygettext.py -p i18n -o liblarch.pot *.py

I think poedit can do most of the processing, but the steps are:

2) cd i18n ; msginit -i liblarch.pot -l de

OR:
2a) to update a po file:

cd i18n ; msgmerge -U liblarch.po liblarch.pot

3) edit po file

4) generate binary file:
cd i18n ; msgfmt -c -v -o liblarch.mo liblarch.po

5) move the .mo file to i18n/de/LC_MESSAGES
"""

import sys, os, shutil
from subprocess import call, Popen, PIPE, STDOUT

pygettext = Popen(['which', 'pygettext.py'],
        stdout=PIPE, stderr=PIPE).communicate()[0].strip()
if not pygettext:
    v1, v2 = sys.version_info[0:2]
    pygettext = '/usr/lib/python%d.%d/Tools/i18n/pygettext.py' % (v1, v2)

thisdir = os.path.dirname(os.path.realpath(__file__))
basedir = os.path.dirname(thisdir)
os.chdir(basedir)

if (len(sys.argv) < 2):
    lang = "de"
else:
    lang = sys.argv[1]
print "Generating internationalization for language '%s'\n" % lang
print "    If you wanted a different language run 'i18n.py <language>'"
print "    For example 'i18n.py fr'\n"

dirs = [""]
allpy = [os.path.join(d, "*.py") for d in dirs]
alluim = [os.path.join('uim', "*.uim")]
call(["pygettext.py", "-p", thisdir, "-o", "liblarch.pot"] + allpy + alluim)

os.chdir(thisdir)
langfile = lang + ".po"
pofile = os.path.join(lang, "LC_MESSAGES", langfile)
if os.path.isfile(pofile):
    shutil.copy(pofile, ".")
    call(["msgmerge", "-U", langfile, "liblarch.pot"])
else:
    call(["sed", "-i", "s|CHARSET|utf-8|", "liblarch.pot"])
    call(["msginit", "--no-translator", "-i", "liblarch.pot", "-l", lang])

lf = open("lang", "w")
lf.write(lang)
lf.close()

print "Now edit '%s' and then run 'i18n2.py'" % langfile
