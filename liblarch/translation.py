#!/usr/bin/env python2
#
# translation.py   --  Translation services
#
# (c) Copyright 2010-2011 Michael Towers (larch42 at googlemail dot com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#-------------------------------------------------------------------
# 2011.01.16

import os, gettext
from liblarch_conf import liblarchdir

def i18n_module(basedir, appname):
    """This doesn't use gettext.install in order not to affect the whole
    application, it allows per module translation services.
    """
    return gettext.translation(appname, basedir + '/i18n', fallback=True).ugettext


def i18n_liblarch():
    """Provides translation for liblarch itself.
    """
    return i18n_module(liblarchdir, 'liblarch')
_ = i18n_liblarch()


lang = (os.environ.get('LANGUAGE') or os.environ.get('LC_ALL')
        or os.environ.get('LC_MESSAGES') or os.environ.get('LANG'))


def i18nurl(doc):
    docbase, docfile = doc.rsplit('/', 1)
    docbase += '/'
    i18npath = docbase + lang.split('.')[0] + '/' + docfile
    if not os.path.isfile(i18npath):
        i18npath = docbase + lang.split('_')[0] + '/' + docfile
    if not os.path.isfile(i18npath):
        i18npath = doc
        if not os.path.isfile(i18npath):
            return None
    return i18npath

def i18ndoc(doc):
    p = i18nurl(doc)
    if not p:
        return _("Document '%s' not found") % i18npath
    with open(p) as fh:
        data = fh.read().decode('utf-8')
    if p != doc:
        with open(doc) as fh:
            version = fh.readline().strip().decode('utf-8')
        if (version.startswith(u'<!-- Version ')
                and (not data.startswith(version))):
            warning = _("This translation is not up-to-date, see %s for the"
                    " original, untranslated version.") % (
                            '<a href="file://%s">%s</a>' % (doc, doc))
            data = ('<div style="color: red; "><p>%s</p></div>'
                    % warning) + data
    return data

