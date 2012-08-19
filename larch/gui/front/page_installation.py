# page_installation.py - Handler for the installation page
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
# 2010.08.12

class Installation:
    def __init__(self):
        ui.widgetlist(fss('fetch_layout', 'page_installation.uim'))

        ui.connectlist(
                (':addedpacks*clicked', self.edit_addedpacks),
                (':vetopacks*clicked', self.edit_vetopacks),
                (':pacmanconf*clicked', self.edit_pacmanconf),
                (':repos*clicked', self.edit_repos),
                (':editmirrorlist*clicked', self.edit_mirrorlist),
                (':cache_change*clicked', self.change_cache),
                (':editrepolist*clicked', self.edit_repolist),
                (':install*clicked', self.install),
                (':sync*clicked', self.dosync),
                (':updateall*clicked', self.doupdateall),
                (':update*clicked', self.doupdate),
                (':add*clicked', self.doadd),
                (':remove*clicked', self.doremove),
                (':installrepos*toggled', self.installrepo),
            )


    def enter(self):
        """This is called when the page is entered/selected/shown.
        It performs initializations which depend on the state.
        """
        docviewer.gohome('gui_installation.html')
        # Set package cache display
        ui.command(':cache_show.text', fss('getitem', 'pacman_cache'))
        ui.command(':installrepos.opton', fss('getbool', 'installrepo'))


    def data(self, key):
        return ui.command('install_page_data.get', key)


    def edit_addedpacks(self):
        edit('profile:addedpacks')              # In profile dir


    def edit_vetopacks(self):
        # If there is no vetopacks file, start an empty one
        edit('profile:vetopacks', "")           # In profile dir


    def edit_pacmanconf(self):
        edit('profile:pacman.conf.options',     # In profile dir
                'base:data/pacman.conf',        # Relative to base_dir
                label=self.data('edit_pc'),
                filter=pacmanoptions)


    def edit_repos(self):
        """This edits the repository list file for the live system.
        It will be used to construct the /etc/pacman.conf file.
        If the option to specify a different file for the installation
        stage is not enabled (the default), this file will also be used
        for the installation.
        """
        edit('profile:pacman.conf.repos',       # In profile dir
                'base:data/pacman.conf.repos',  # Relative to base_dir
                label=self.data('edit_pr'))


    def edit_mirrorlist(self):
        ml = '/etc/pacman.d/mirrorlist'
        if not fss('isfile', ml):
            ml = 'base:data/mirrorlist'         # Relative to base_dir
        edit('working:mirrorlist', ml,
                label=self.data('edit_mli'))


    def change_cache(self):
        # Is anything more necessary? Do I need to test the path?
        # Would a directory browser be better?
        ok, path = ui.command('textLineDialog',
                self.data('prompt_ncp'),
                None, fss('getitem', 'pacman_cache'))
        if ok:
            self.set_pacman_cache(path)


    def set_pacman_cache(self, path):
            path = path.strip().rstrip('/')
            fss('setitem', 'pacman_cache', path)
            ui.command(':cache_show.text', path)


    def edit_repolist(self):
        """This edits the repository list file used for installation,
        if the corresponding option is enabled.
        """
        # Should it be based on the default or on the profile?
        rf = 'profile:pacman.conf.repos'
        if not fss('isfile', rf):
            rf = 'base:data/pacman.conf.repos'  # Relative to base_dir
        edit('working:pacman.conf.repos', rf,
                label=self.data('edit_pri'))


    def installrepo(self, on):
        fss('setbool', 'installrepo', on)


    def install(self):
        """Start the installation.
        """
        self.archin('install')


    def dosync(self):
        self.archin('refresh')


    def doupdateall(self):
        self.archin('updateall')


    def doupdate(self):
        f = ui.fileDialog(message=self.data('msg_pu'),
                filter=(self.data('filter_pu'), '*.pkg.tar.*'))
        if f:
            self.archin('update ' + f)


    def doadd(self):
        ok, plist = ui.command('textLineDialog',
                self.data('prompt_pi'),
                'pacman -S')
        if ok:
            self.archin('sync ' + plist.strip())


    def doremove(self):
        ok, plist = ui.command('textLineDialog',
                self.data('prompt_pr'),
                'pacman -Rs')
        if ok:
            self.archin('remove ' + plist.strip())


    def archin(self, cmd):
        """This runs the 'archin' script (as root). It doesn't wait for
        completion because the output must be collected and displayed
        while it is running. The display switches the view to the
        progress reporting page. It should probably activate the busy
        cursor too.
        """
        larchcall('archin', cmd, ui.command(':installrepos.active'))



def pacmanoptions(text):
    """A filter for pacman.conf to remove the repository info.
    """
    texto = ""
    block = ""
    for line in text.splitlines():
        block += line + "\n"
        if line.startswith("#["):
            break
        if line.startswith("[") and not line.startswith("[options]"):
            break
        if not line.strip():
            texto += block
            block = ""
    return texto



