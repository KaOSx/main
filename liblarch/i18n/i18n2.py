#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

#2010.08.01
# Copyright 2010 Michael Towers

"""This is part 2 of the internationalization helper.
After editing liblarch.po, run this to compile it and copy it to the
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
call(["msgfmt", "-c", "-v", "-o", "liblarch.mo", langfile])

podir = os.path.join(lang, "LC_MESSAGES")
if not os.path.isdir(podir):
    os.makedirs(podir)
os.rename(langfile, os.path.join(podir, langfile))
os.rename("liblarch.mo", os.path.join(podir, "liblarch.mo"))

print "DONE!"
