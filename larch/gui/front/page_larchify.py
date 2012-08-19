# page_larchify.py - Handler for the project settings page
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
# 2010.10.07

USERINFO = ['pw', 'maingroup', 'uid', 'skel', 'xgroups', 'expert']

class Larchify:
    def __init__(self):
        ui.widgetlist(fss('fetch_layout', 'page_larchify.uim'))

        ui.connectlist(
                (':build*clicked', self.build),
                (':ssh*toggled', self.sshtoggle),
                (':locales*clicked', self.locales),
                (':rcconf*clicked', self.rcconf),
                (':initcpio*clicked', self.initcpio),
                (':overlay*clicked', self.overlay),
                (':utable*clicked', self.uedit),
                (':useradd*clicked', self.useradd),
                (':userdel*clicked', self.userdel),
                (':rootpwb*clicked', self.rootpw),
                (':kernelb*clicked', self.kernelfile),
                (':kernelmkib*clicked', self.kernelpreset),
            )

        self.userheaders = self.data('uheaders')


    def data(self, key):
        return ui.command('larchify_page_data.get', key)


    def enter(self):
        """This is called when the page is entered/selected/shown.
        It performs initializations which depend on the state.
        """
        docviewer.gohome('gui_larchify.html')

        # Check that it could possibly be an Arch installation
        idir = fss('get_installation_dir')
        couldBeArch = fss('isdir', ':var/lib/pacman/local')
        ui.command(':build.enable', couldBeArch)
        if not couldBeArch:
            run_error(_("No Arch installation at %s") % idir)

        # ssh keys
        sshon = fss('isfile', ':usr/bin/ssh-keygen')
        ui.command(':ssh.enable', sshon)

        if fss('isfile', 'profile:nosshkeys'):
            sshon = False
        ui.command(":ssh.set", sshon)

        # users table
        idir_normal = idir != '/'
        ui.command(':users.enable', idir_normal)
        if idir_normal:
            # Fetch users information
            fss('newUserinfo')
            self.readuserinfo()

        # Root password
        self.showrootpw()

        # Kernel info
        self.showkernel()

        self.reenter()


    def reenter(self):
        """These also need resetting after a build run.
        """
        # Whether there is an old system.sqf to reuse?
        ossqf = fss('oldsqf')
        if not ossqf:
            ui.command(':oldsquash.set', False)
        ui.command(':oldsquash.enable', ossqf)

        # Whether there is a set of old glibc locales to reuse?
        olcl = fss('oldlocales')
        if not olcl:
            ui.command(':oldlocales.set', False)
        ui.command(':oldlocales.enable', olcl)

#TODO: Remove hack if the underlying bug gets fixed
        ui.command(":larchify_advanced.enable_hack")


    def readuserinfo(self, select=None):
        """'select' should be a username, defaulting to the first entry.
        """
        self.usersel = 0
        self.userlist = []
        i = 0
        for u in fss('allusers'):
            self.userlist.append(self.userinfolist(u))
            if u == select:
                self.usersel = i
            i += 1
        ui.command(':utable.set', self.userlist, self.usersel)


    def userinfolist(self, user):
        return [user] + fss('getuserinfo', user, USERINFO)


    def uedit(self, row, column):
        if self.usersel == row:
            uname = self.userlist[row][0]
            ulcell = self.userlist[row][column]
            if column == 4:
                ok, text = self.select_skel(ulcell)
            else:
                ok, text = ui.command('textLineDialog',
                        self.userheaders[column] + ':', 'larchify', ulcell)
            text = text.strip()
            if ok:
                try:
                    if (column == 0) and (text != ''):
                        # Rename the user, by adding a new one and deleting
                        # the old
                        uname = text
                        fss('newuser', uname)
                        i = 0
                        for f in USERINFO:
                            i += 1
                            fss('userset', uname, f, self.userlist[row][i])
                        if not fss('deluser', ulcell):
                            run_error(self.data('rn_error'))

                    else:
                        fss('userset', uname, USERINFO[column-1], text)
                        fss('saveusers')

                except:
                    run_error(self.data('ud_error'))
                self.readuserinfo(uname)

        else:
            self.usersel = row


    def select_skel(self, current):
        # Present a list of available 'skel' folders
        self.skellist = [self.data('def_skel')]
        for f in fss('listskels'):
            self.skellist.append(f.rsplit('/skel_', 1)[1])
        try:
            i = self.skellist.index(current)
        except:
            i = 0
        ok, skeli = ui.command('listDialog', self.data('skel_lbl'),
                self.data('skel_ttl'), self.skellist, i)
        if ok:
            return (True, '' if skeli == self.skellist[0]
                    else skeli.split()[0])
        return (False, '')


    def useradd(self):
        ok, name = ui.command('textLineDialog', self.data('newlogin'))
        if ok:
            name = name.strip()
            if name != '' and fss('newuser', name):
                self.userlist.append(self.userinfolist(name))
                self.usersel = len(self.userlist) -1
                ui.command(':utable.set', self.userlist, self.usersel)


    def userdel(self):
        if self.usersel >= 0:
            user = self.userlist[self.usersel][0]
            if fss('deluser', user):
                del(self.userlist[self.usersel])
                lu = len(self.userlist)
                if lu:
                    if lu <= self.usersel:
                        self.usersel -= 1
                ui.command(':utable.set', self.userlist, self.usersel)


    def showrootpw(self):
        self.rootpw = fss('readfile', 'profile:rootpw', trap=False)
        if self.rootpw == None:
            self.rootpw = ""
        ui.command(':rootpwe.text', self.rootpw)


    def rootpw(self):
        ok, pw = ui.command('textLineDialog', self.data('newrootpw'),
                "larchify", self.rootpw)
        if ok:
            pw = pw.strip()
            if pw:
                fss('savefile', 'profile:rootpw', pw)
            else:
                fss('rm_rf', 'profile:rootpw')
            self.showrootpw()


    def sshtoggle(self, on):
        """Whether the system ssh keys are pregenerated
        depends on the presence of the profile file 'nosshkeys'
        (and of course on openssh being installed).
        """
        sshoff = fss('isfile', 'profile:nosshkeys')
        if on:
            if sshoff:
                fss('rm_rf', 'profile:nosshkeys')
        elif not sshoff:
            fss('savefile', 'profile:nosshkeys', "Don't pregenerate ssh keys")


    def locales(self):
        edit('profile:rootoverlay/etc/locale.gen', 'install:etc/locale.gen')


    def rcconf(self):
        edit('profile:rootoverlay/etc/rc.conf', 'install:etc/rc.conf')


    def initcpio(self):
        edit('profile:rootoverlay/etc/mkinitcpio.conf.larch',
                'install:etc/mkinitcpio.conf.larch')


    def overlay(self):
        fss('browse', 'profile:rootoverlay')


    def showkernel(self):
        if fss('isfile', 'profile:kernel'):
            ki = fss('readfile', 'profile:kernel')
        else:
            ki = fss('readfile', 'base:data/kernel')
        self.kernel, self.kernelpreset = ki.split()
        ui.command(':kernele.text', self.kernel)
        ui.command(':kernelmkie.text', self.kernelpreset)


    def kernelfile(self):
        ok, kf = ui.command('textLineDialog', self.data('kernelf'),
                "larchify", self.kernel)
        if ok:
            kf = kf.strip()
            if not kf:
                fss('rm_rf', 'profile:kernel')

            elif (' ' in kf) or not fss('isfile', 'install:boot/' + kf):
                run_error(_("Invalid kernel binary: %s") % kf)
                return
            else:
                fss('savefile', 'profile:kernel', kf + ' ' + self.kernelpreset)
            self.showkernel()


    def kernelpreset(self):
        ok, kp = ui.command('textLineDialog', self.data('kernelp'),
                "larchify", self.kernelpreset)
        if ok:
            kp = kp.strip()
            if not kp:
                fss('rm_rf', 'profile:kernel')

            elif (' ' in kp) or not fss('isfile',
                    'install:etc/mkinitcpio.d/%s.preset' % kp):
                run_error(_("Invalid kernel mkinitcpio preset: %s") % kp)
                return
            else:
                fss('savefile', 'profile:kernel', self.kernel + ' ' + kp)
            self.showkernel()


    def build(self):
        larchcall('larchify', ui.command(':oldsquash.active'),
                ui.command(':oldlocales.active'))
