#!/usr/bin/env python2
#
# editor.py
#
# (c) Copyright 2009-2010 Michael Towers (larch42 at googlemail dot com)
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
# 2010.06.24

class Editor:
    def __init__(self):
        ui.widgetlist(fss('fetch_layout', 'editor.uim'))
        ui.connectlist(
                ('edit:ok*clicked', self.ok),
                ('edit:cancel*clicked', self.cancel),
                ('edit:revert*clicked', self.dorevert),
                ('edit:copy*clicked', self.copy),
                ('edit:cut*clicked', self.cut),
                ('edit:paste*clicked', self.paste),
                ('edit:undo*clicked', self.undo),
                ('edit:redo*clicked', self.redo),
            )

    def start(self, title, endcall, text='', revert=None):
        ui.command('edit:title.markup', ['h3', title])
        self.endcall = endcall
        self.revert = revert
        try:
            self.text0 = revert() if text == None else text
        except:
            run_error("BUG: Editor - no revert function?")
        ui.command('edit:content.text', self.text0)
        ui.runningtab(4)

    def ok(self):
        self.endcall(ui.command('edit:content.get'))
        ui.runningtab()

    def cancel(self):
        ui.runningtab()

    def dorevert(self):
        if self.revert:
            self.text0 = self.revert()
        ui.command('edit:content.text', self.text0)

    def copy(self):
        ui.command('edit:content.copy')

    def cut(self):
        ui.command('edit:content.cut')

    def paste(self):
        ui.command('edit:content.paste')

    def undo(self):
        ui.command('edit:content.undo')

    def redo(self):
        ui.command('edit:content.redo')

    def edit(self, fname, source=None, label=None, filter=None):
        """Files (<fname> and <source>) can be either an absolute path or else
        relative to the profile directory, the application base directory
        or the working directory. Relative paths are determined by the
        prefixes 'profile:', 'base:' or 'working:'.
        If the file <fname> already exists its contents will be taken as the
        starting point, otherwise the file <source>, which may also be an
        empty string, will be read in.
        Whichever file is available its contents can be filtered by an
        optional 'filter' function, which takes the file contents as a
        string as argument and returns the transformed contents as another
        string.
        """
        def revert():
            """If a file is addressed by 'source' revert to its contents,
            if source is "", clear the contents, otherwise revert to the
            contents as they were before entering the editor.
            """
            return textsrc if source != None else text0

        def endfile(text):
            t = text.encode("utf8")
            if t and (t[-1] != "\n"):
                t += "\n"
            fss('savefile', fname, text)

        if source != None:
            textsrc = "" if source == "" else fss('readfile', source,
                    filter=filter)
        # Read the file, if it exists, else return None
        text0 = fss('readfile', fname, filter=filter, trap=False)
        if text0 == None:
            assert source != None   # The file must be present
            text0 = textsrc
        if not label:
            label = ui.command('editor_data.get', 'msg_dflt') % fname
        self.start(label, endfile, text0, revert)

