# userinfo.py
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
# 2010.07.11

import os
from ConfigParser import SafeConfigParser

# Default list of 'additional' groups for a new user
BASEGROUPS = 'video,audio,optical,storage,scanner,power,camera'

class Userinfo:
    def __init__(self, profile):
        self.profile_dir = profile

    def getusers(self):
        """Read user information by means of a SafeConfigParser instance.
        This is then available as self.userconf.
        """
        self.userconf = SafeConfigParser({'pw':'', 'maingroup':'', 'uid':'',
                'skel':'', 'xgroups':BASEGROUPS, 'expert':''})
        users = self.profile_dir + '/users'
        if os.path.isfile(users):
            try:
                self.userconf.read(users)
            except:
                error0(_("Invalid 'users' file"))

    def allusers(self):
        self.getusers()
        return self.userconf.sections()

    def get(self, user, field):
        return self.userconf.get(user, field)

    def userinfo(self, user, fields):
        """Get an ordered list of the given field data for the given user.
        """
        return [self.userconf.get(user, f) for f in fields]

    def userset(self, uname, field, text):
        self.userconf.set(uname, field, text)

    def newuser(self, user):
        try:
            self.userconf.add_section(user)
            return self.saveusers()
        except:
            error0(_("Couldn't add user '%s'") % user)
            return False

    def deluser(self, user):
        try:
            self.userconf.remove_section(user)
            return self.saveusers()
        except:
            error0(_("Couldn't remove user '%s'") % user)
            return False

    def saveusers(self):
        """Save the user configuration data (in 'INI' format)
        """
        try:
            fh = None
            fh = open(self.profile_dir + '/users', 'w')
            self.userconf.write(fh)
            fh.close()
            return True
        except:
            if fh:
                fh.close()
            error0(_("Couldn't save 'users' file"))
            self.getusers()
            return False

