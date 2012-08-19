# page_project.py - Handler for the project settings page
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
# 2010.08.15

import os

class ProjectSettings:
    def __init__(self):
        ui.widgetlist(fss('fetch_layout', 'page_project.uim'))
        ui.widgetlist(fss('fetch_layout', 'profile_browse.uim'))
        ui.command('dialog:profile_browser.pack')

        ui.connectlist(
                (':choose_profile_combo*changed', self.switch_profile),
                (':profile_rename*clicked', self.rename_profile),
                (':profile_browse*clicked', self.browse_profile),
                (':profile_delete*clicked', self.delete_profile),
                (':profile_save*clicked', self.copy_profile),
                (':profile_clone*clicked', self.clone_profile),
                (':installation_path_change*clicked', self.new_build_path),
                (':choose_project_combo*changed', self.switch_project),
                (':new_project*clicked', self.get_new_project_name),
                (':project_delete*clicked', self.delete_project),
                ('dpb:example_list*changed', self.dpb_example),
                ('dpb:browse*clicked', self.dpb_browse),
                ('dpb:name_s*clicked', self.dpb_source),
            )


    def setup(self):
        # Initialize project combobox
        self.projects = fss('get_projects')
        self.project_name = fss('get_project')
        try:
            pix = self.projects.index(self.project_name)
        except:
            self.switch_project(0)
            return
        ui.command(':choose_project_combo.set', self.projects, pix)
        # Initialize profile combobox
        self.profiles = fss('get_profiles')
        self.profile_name = fss('get_profile')
        try:
            pfix = self.profiles.index(self.profile_name)
        except:
            self.switch_profile(0)
            pfix = 0
        ui.command(':choose_profile_combo.set', self.profiles, pfix)
        # Initialize installation_dir display
        self.set_build_dir(fss('get_installation_dir'))


    def enter(self):
        """This is called when the page is entered/selected/shown.
        It performs initializations which depend on the state.
        """
        docviewer.gohome('gui_project_settings.html')


    def data(self, key):
        return ui.command('project_page_data.get', key)


    def set_build_dir(self, path):
        self.build_dir = path
        ui.command(':installation_path_show.text', self.build_dir)
        ui.enable_installation_page(self.build_dir != '/')


    def switch_profile(self, index):
        """This has no effect on the display!
        It is assumed that the display is already updated, or will be
        updated later, and that the index is valid, so that the operation
        cannot fail.
        """
        self.profile_name =  self.profiles[index]
        fss('set_profile', self.profile_name)


    def browse_profile(self):
        self.example_profile_dir, self.dpb_example_list = fss('get_example_profiles')
        ui.command('dpb:example_list.set', self.dpb_example_list, -1)
        if ui.command('dialog:profile_browser.showmodal'):
            source = ui.command('dpb:source.get')
            name = ui.command('dpb:name.get')
            if name in self.profiles:
                if not ui.command('confirmDialog', self.data('prompt_pr')):
                    return
            if fss('get_new_profile', source, name):
                self.setup()
            else:
                run_error(self.data('msg_npd') % source)


    def dpb_example(self, index):
        name = self.dpb_example_list[index]
        ui.command('dpb:source.text', self.example_profile_dir + '/' + name)
        ui.command('dpb:name.text', name)


    def dpb_browse(self):
        source = ui.fileDialog(self.data('file_ps'), dirsonly=True,
                startdir=fss('getitem', 'profile_browse_dir'))
        if source:
            fss('setitem', 'profile_browse_dir', os.path.dirname(source))
            ui.command('dpb:source.text', source)
            ui.command('dpb:name.text', os.path.basename(source))
            ui.command('dpb:example_list.set', self.dpb_example_list, -1)


    def dpb_source(self):
        ok, name = ui.command('textLineDialog', _("Name for new profile:"), None,
                os.path.basename(ui.command('dpb:source.get')))
        if ok:
            ui.command('dpb:name.text', name)


    def rename_profile(self):
        if fss('can_rename_profile'):
            ok, new = ui.command('textLineDialog',
                    self.data('prompt_pn'),
                    None, self.profile_name)
            if ok:
                new = new.strip()
                if new in self.profiles:
                    ui.command('warningDialog', self.data('prompt_pe') % new)
                else:
                    fss('rename_profile', new)
                    self.setup()
        else:
            ui.command('infoDialog', self.data('msg_pu'))


    def clone_profile(self):
        ok, name = ui.command('textLineDialog', self.data('prompt_clone'), self.profile_name)
        if ok:
            name = name.strip()
            self.save_profile(name)
            fss('set_profile', name)
            self.setup()

    def copy_profile(self):
        startdir = fss('getitem', 'profile_browse_dir')
        path = ui.fileDialog(self.data('file_sp'),
                create=True, dirsonly=True, file=self.profile_name,
                startdir=startdir)
        if path:
            fss('set_profile_browse_dir', path)
            self.save_profile(path)

    def save_profile(self, path):
        ok = fss('save_profile', path, False)
        if ok == False:
            if ui.command('confirmDialog', self.data('prompt_dr')):
                # Force overwrite
                fss('save_profile', path, True)
        elif ok == None:
            run_error(self.data('msg_piu'))
        else:
            self.setup()


    def delete_profile(self):
        plist = fss('list_free_profiles')
        if plist:
            ok, item = ui.command('listDialog', self.data('prompt_dp'),
                    self.data('delprof'), plist)
            if ok:
                if fss('delete_profile', item):
                    self.setup()
                else:
                    ui.command('infoDialog', self.data('msg_dpff') % item)
        else:
            ui.command('infoDialog', self.data('msg_npf'))


    def new_build_path(self):
        # Is anything more necessary? Do I need to test or create the path?
        # I don't think so, the installation code does that.
        # If the path is "/", the installation page should be inhibited,
        # but that is handled by 'setup'.
        ok, path = ui.command('textLineDialog',
                self.data('prompt_ip'),
                None, self.build_dir)
        if ok:
            path = fss('set_installation_dir', path)
            if path:
                self.set_build_dir(path)


    def switch_project(self, index):
        fss('set_project', self.projects[index])
        self.setup()


    def get_new_project_name(self):
        ok, name = ui.command('textLineDialog',
                self.data('prompt_np'),
                None, self.project_name)
        if ok:
            if name in self.projects:
                run_error(self.data('msg_pe') % name)
            else:
                fss('set_project', name)
                self.setup()


    def delete_project(self):
        """Pop up a list of eligible project names, the selected one
        will be deleted.
        """
        plist = fss('list_free_projects')
        if plist:
            ok, item = ui.command('listDialog', self.data('prompt_pd'),
                    self.data('delproj'), plist)
            if ok:
                fss('delete_project', item)
                self.setup()
        else:
            ui.command('infoDialog', self.data('msg_np'))


