# page_medium.py - Handler for the project settings page
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
# 2010.12.27

"""This page takes a directory processed by larchify. It produces a bootable
larch medium, or, in the case of CD/DVD, an iso image.
It also handles creation of a boot-iso for an existing larch medium (partition)
and can copy larch media to different devices.
"""

import os
from config import detection_methods, OKFS


class Medium:
    def __init__(self):
        self.medium = None
        self.srcmedium = None
        self.detectionmodes = detection_methods.split('|')
        ui.widgetlist(fss('fetch_layout', 'page_medium.uim'))

        ui.connectlist(
                (':vlabelb*clicked', self.newlabel),
                (':selectpart*clicked', self.choosedest),
                (':selectsrc*clicked', self.choosesrc),
                (':persist*toggled', self.persistence),
                (':ovl_journal*toggled', self.journal),
                (':mediumtype*changed', self.mediumtype),
                (':srctype*changed', self.srctype),
                (':make_medium*clicked', self.make),
                (':nolarchboot*toggled', self.bootnosearch),
                (':detection*changed', self.mediumsearch),
                (':pformat*toggled', self.setpformat),
                (':bootlines*clicked', self.editbootlines),
                (':syslinuxtemplate*clicked', self.editsyslin),
                (':cdroot*clicked', self.browsecdroot),
            )


    def enter(self):
        """This is called when the page is entered/selected/shown.
        It performs initialisations which depend on the state.
        """
        self.destinationpath = ''
        self.fsok = None
        self.source, ok = fss('testlarchify')   # check the larchified installation
        if not ok:
            run_error(self.data('msg_med') % self.source)
            self.source = ''
        self.mediumtype(None)
        if self.medium != 'medium-boot':
            self.srctype(None)
        detect = fss('getitem', 'medium_search')
        ui.command(':detection.set',
                [self.data('detectionmodes')[l] for l in self.detectionmodes],
                self.detectionmodes.index(detect))
        self.nlbenable(detect)
        ui.command(':nolarchboot.set', fss('getbool', 'boot_nosearch'))
        ui.command(':vlabele.text', fss('get_mediumlabel'))
        ui.command(':ovl_journal.set', fss('getbool', 'journal'))
        fmt = fss('getbool', 'do_format')
        ui.command(':pformat.set', fmt )
        ui.command(':ovl_journal.enable', fmt)
        ui.command(':persist.set', fss('getbool', 'do_persist'))

        ui.command(':larchpart.text')       # clear the destination
        docviewer.gohome('gui_medium.html')


    def data(self, key):
        return ui.command('medium_page_data.get', key)


    def mediumtype(self, index):
        if (index == None):
            if self.medium == None:
                self.medium = self.data('media')[0]
        else:
            self.medium = self.data('media')[index]

        if self.medium == 'medium-boot':
            label = fss('get_bootisolabel')
            ui.command(':srctype.setindex', self.data('sources').index('device'))
            ui.command(':srctype.enable', False)
            ifile = fss('getbootisofile')

        else:
            label = fss('get_mediumlabel')
            ui.command(':srctype.enable', True)

            if self.medium == 'medium-iso':
                ifile = fss('getisofile')

        self.showlabel(label)

        if self.medium == 'medium-w':
            ui.command(':mediumopts.enable', True)
            self.setdestinationpath('')

        else:
            ui.command(':mediumopts.enable', False)
            idir =  fss('getisosavedir')
            if not fss('isdir', idir):
                fss('setitem', 'isosavedir', '')
                idir =  fss('getisosavedir')
            self.setdestinationpath(os.path.join(idir, ifile))

        if index != None:
            self.enableprofile()
            self.enablemake()


    def srctype(self, index):
        if (index == None):
            if self.srcmedium == None:
                self.srcmedium = self.data('sources')[0]
        else:
            self.srcmedium = self.data('sources')[index]

        if self.srcmedium == 'larchified':
            self.setsourcepath(self.source)
            ui.command(':selectsrc.enable', False)

        elif self.srcmedium == 'device':
            self.setsourcepath('')  # clear source, it must be selected
            ui.command(':selectsrc.enable', True)

        elif self.srcmedium == 'isofile':
            isof = fss('getisofile')
            isod = fss('getisosavedir')
            self.pendingpath = os.path.join(isod, isof)
            ui.command(':selectsrc.enable', True)
            self.setsourcepath('')
            self.checklarchsource()


    def setsourcepath(self, path):
        self.sourcepath = path
        ui.command(':srclocation.text', path)
        self.enableprofile()
        self.enablemake()


    def choosesrc(self):
        # 'larchified' should not be possible - it is set on the project page
        if self.srcmedium == 'device':
            self.devices = []
            larchcall('*rootfn', self._cd_line, 'blkid -c dev/null -o list')

        elif self.srcmedium == 'isofile':
            # Pop up a file browser
            self.pendingpath = self.isopath(mode='source')
            self.checklarchsource()

        else:
            debug('page_medium: Medium.choosesrc / ' + self.srcmedium)

    def _cd_line(self, line):
        if line == None:
            # Completed - pop up device chooser
            ok, choice = ui.command('listDialog',
                    self.data('parts_src'),
                    self.data('parts_t'),
                    self.devices, len(self.devices) - 1)
            if ok:
                self.pendingpath = choice.split()[0]
                ui.idle_add(self.checklarchsource)

        else:
            l = line.strip()
            if l.startswith('/dev/'):
                i = l.find('(not mounted)')
                if i > 0:
                    ls = l[:i].split(None, 2)
                    if (ls[0] != self.destinationpath) and (len(ls) == 3):
                        self.devices.append('%-10s %s' % (ls[0], ls[2]))


    def checklarchsource(self):
        if self.pendingpath:
            # check it is really a larch medium
            self.larchok = False
            larchcall('*larchmedium', self._cs_line, self.pendingpath)

    def _cs_line(self, line):
        if line == None:
            # Completed
            if self.larchok:
                self.setsourcepath(self.pendingpath)
        else:
            l = line.strip()
            if l.startswith('##--'):
                if l.endswith('ok'):
                    self.larchok = True


    def enableprofile(self):
        """Set the enabled state of the medium profile frame,
        according to the state of the choices.
        """
        ui.command(':mediumprofile.enable', (self.medium != 'medium-boot')
                and (self.srcmedium == 'larchified'))


    def enablemake(self):
        on = bool(self.destinationpath) and bool(self.sourcepath)
        if self.medium == 'medium-w':
            formatting = fss('getbool', 'do_format')
            self.enablepersist(formatting or (self.fsok in OKFS))
            if (not formatting):
                if (self.fsok not in OKFS) and (self.fsok != 'vfat'):
                    on = False
        ui.command(':make_medium.enable', on)


    def enablepersist(self, on):
        ui.command(':persist.enable', on)
        self.persist_enabled = on


    def persistence(self, on):
        fss('setbool', 'do_persist', on)


    def journal(self, on):
        fss('setbool', 'journal', on)


    def mediumsearch(self, option):
        choice = self.detectionmodes[option]
        fss('setitem', 'medium_search', choice)
        self.nlbenable(choice)


    def nlbenable(self, choice):
        ui.command(':nolarchboot.enable', choice != 'search')


    def bootnosearch(self, on):
        fss('setbool', 'boot_nosearch', on)


    def setpformat(self, on):
        fss('setbool', 'do_format', on)
        ui.command(':ovl_journal.enable', on)
        self.enablemake()


    def editbootlines(self):
        f0 = 'profile:cd-root/boot0/bootlines'
        if not fss('isfile', f0):
            f0 = 'base:cd-root/boot0/bootlines'
        edit('profile:cd-root/boot/bootlines', 'base:cd-root/boot0/bootlines')


    def editsyslin(self):
        f0 = 'profile:cd-root/boot0/isolinux/isolinux.cfg'
        if not fss('isfile', f0):
            f0 = 'base:cd-root/boot0/isolinux/isolinux.cfg'
        edit('profile:cd-root/boot/isolinux/isolinux.cfg', f0)


    def browsecdroot(self):
        fss('browse', 'profile:cd-root')


    def newlabel(self):
        labelsrc = 'bootiso' if self.medium == 'medium-boot' else 'medium'
        ok, l = ui.command('textLineDialog',
                self.data('prompt_label'),
                None, fss('get_%slabel' % labelsrc))
        if ok:
            l = l.replace(' ', '_')
            self.showlabel(fss('set_%slabel' % labelsrc, l))


    def showlabel(self, l):
        ui.command(':vlabele.text', l)


    def choosedest(self):
        if self.medium == 'medium-w':
            # Present a list of unmounted partitions
            self.devices = []
            larchcall('*rootfn', self._sd_line, 'blkid -c /dev/null -o list')

        elif self.medium == 'medium-iso':
            # Pop up a file browser
            path = self.isopath(mode='iso')
            if path:
                self.setdestinationpath(path)

        elif self.medium == 'medium-boot':
            # Pop up a file browser
            path = self.isopath(mode='bootiso')
            if path:
                self.setdestinationpath(path)

    def _sd_line(self, line):
        if line == None:
            if not self.devices:
                return
            nmdevices = []
            for part in fss('get_partitions'):  # ->(dev, size in MiB(int))
                if part[0] == self.sourcepath:
                    continue
                found = False
                for partinfo in self.devices:
                    if partinfo[0] == part[0]:
                        if partinfo[2]:
                            nmdevices.append('%-12s %8d MiB    %-10s  %s'
                                    % (part[0], part[1], partinfo[1], partinfo[2]))
                        found = True
                        break
                if not found:
                    nmdevices.append('%-12s %-12d MiB' % (part[0], part[1]))

            # Completed - pop up device chooser
            ok, choice = ui.command('listDialog',
                    self.data('parts_dst'),
                    self.data('parts_t'),
                    nmdevices, len(nmdevices) - 1)
            if ok:
                ui.idle_add(self.setdestinationpath, choice.split()[0])

        else:
            l = line.strip()
            if l.startswith('/dev/'):
                i = l.find('(not mounted)')
                if i > 0:
                    # Try to get label for unmounted devices only
                    ls = l[:i].split(None, 2)
                    if len(ls) < 3:
                        ls.append('-')  # signifies 'no label'
                else:
                    ls = l.split(None, 2)
                    try:
                        ls[2] = None    # mark the partition as mounted
                    except:
                        #run_error("Bad device data: %s" % l)
                        while len(ls) < 3:
                            ls.append(None)
                self.devices.append(ls)


    def setdestinationpath(self, path):
        ui.command(':larchpart.text', path)
        self.destinationpath = path
        if path.startswith('/dev/'):
            # Check the file-system
            self.fsok = None
            larchcall('*rootfn', self._em_line,
                    'blkid -c /dev/null -o value -s TYPE %s' % path)
        else:
            self.enablemake()

    def _em_line(self, line):
        if line == None:
            # Completed
            self.enablemake()
        else:
            line = line.strip()
            if line:
                self.fsok = line


    def isopath(self, mode='dest'):
        sdir = fss('getisosavedir')
        ifname = fss('getbootisofile' if mode=='bootiso' else 'getisofile')
        path = ui.fileDialog(self.data('isoget' if mode=='source' else 'isopath'),
            startdir=sdir, create=(mode!='source'),
            file=ifname, filter=(self.data('iso_type'), '*.iso'))
        if path:
            f = os.path.basename(path)
            d = os.path.dirname(path)
            if d != sdir:
                fss('setitem', 'isosavedir', d)
            if f != ifname:
                fss('setitem', 'bootisofile' if mode=='bootiso' else 'isofile', f)
            return path

        return None


    def make(self):
        """Write the larch medium.
        """
        if self.srcmedium == 'larchified':
            source = None
        else:
            source = self.sourcepath
            if not source:
                debug("page_medium: make / null source")
                return

        args = ['-l', ui.command(':vlabele.get')]

        if self.medium == 'medium-boot':
            # Write a boot iso file
            args += ['-b', '-o', self.destinationpath]
            larchcall('writemedium', source, args)

        elif self.medium == 'medium-iso':
            # Write an 'iso' file
            args += ['-o', self.destinationpath]
            larchcall('writemedium', source, args)

        else:
            # Write to partition
            # Medium detection options
            detect = fss('getitem', 'medium_search')
            args += ['-d', detect]
            if (detect != 'search') and ui.command(':nolarchboot.active'):
                args.append('-n')
            # Formatting
            if fss('getbool', 'do_format'):
                # Journalling?
                if not fss('getbool', 'journal'):
                    args.append('-j')
            else:
                args.append('-F')
            # Set master boot record?
            if ui.command(':nombr.active'):
                args.append('-m')
            # Persistence
            if fss('getbool', 'do_persist') and self.persist_enabled:
                args.append('-P')
            # Add the medium to the argument list
            args.append(self.destinationpath)
            larchcall('writemedium', source, args)
