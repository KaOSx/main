# project.py - Project management
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
# 2010.12.03

from config import *
import os, shutil, pwd
from glob import glob
from subprocess import call
from userinfo import Userinfo

CONFIG_DIR = '.config/larch'        # within the user's home directory
APP_CONF = 'app.conf'               # within larch config directory
PROJECT_CONF = 'project.conf'       # within project directory
PROJECT0 = 'larch-0'                # default project
PROFILE0 = 'default'                # default profile

# Some default values for the project config file
DEFAULTS = {    'installation_dir' : '',
                'pacman_cache'  : '/var/cache/pacman/pkg',
                'profile'       : PROFILE0,
                'profile_browse_dir': '',   # => use default
                'installrepo'   : '',
                'medium_iso'    : '',       # 'Yes' | ''
                'medium_search' : 'label',  # 'search' | 'uuid' | 'label' | 'device'
                'boot_nosearch' : '',       # 'Yes' | ''
                'do_persist'    : 'Yes',    # 'Yes' | ''
                'journal'       : 'Yes',    # 'Yes' | ''
                'medium_label'  : '',       # => fetch default
                'isosavedir'    : '',
                'isofile'       : '',
                'bootisofile'   : '',
                'bootisolabel'  : '',
                'do_format'     : 'Yes',    # 'Yes' | ''
    }


# Default values for the application config file
APP_DEFAULTS = {
                'project'       : PROJECT0,
                'filebrowser'   : 'xdg-open $',
    }



class ProjectManager:
    def __init__(self):
        add_exports(    (
                ('getitem', self.getitem),
                ('getbool', self.getbool),
                ('setitem', self.setitem),
                ('setbool', self.setbool),
                ('get_projects', self.list_projects),
                ('get_profiles', self.list_profiles),
                ('get_installation_dir', self.get_ipath),
                ('set_installation_dir', self.set_ipath),
                ('testlarchify', self.testlarchify),
                ('set_project', self.set_projectname),
                ('get_project', self.get_projectname),
                ('delete_project', self.delete_project),
                ('delete_profile', self.delete_profile),
                ('list_free_projects', self.list_free_projects),
                ('list_free_profiles', self.list_free_profiles),
                ('get_new_profile', self.get_new_profile),
                ('rename_profile', self.rename_profile),
                ('can_rename_profile', self.can_rename_profile),
                ('save_profile', self.save_profile),
                ('get_profile', self.get_profile),
                ('set_profile', self.set_profile),
                ('get_example_profiles', self.get_example_profiles),
                ('set_profile_browse_dir', self.set_profile_browse_dir),
                ('get_mediumlabel', self.get_mediumlabel),
                ('set_mediumlabel', self.set_mediumlabel),
                ('getisosavedir', self.getisosavedir),
                ('getisofile', self.getisofile),
                ('getbootisofile', self.getbootisofile),
                ('get_bootisolabel', self.get_bootisolabel),
                ('set_bootisolabel', self.set_bootisolabel),
                ('newUserinfo', self.newUserinfo),
                ('allusers', self.allusers),
                ('getuserinfo', self.getuserinfo),
                ('newuser', self.newuser),
                ('userset', self.userset),
                ('deluser', self.deluser),
                ('listskels', self.listskels),
                ('saveusers', self.saveusers))
            )


    def init(self):
        self.projects_base = os.path.join(os.environ['HOME'], CONFIG_DIR)
        self.profiles_dir = os.path.join(self.projects_base, 'myprofiles')
        # Ensure the presence of the larch default project folder
        dpf = '%s/p_%s' % (self.projects_base, PROJECT0)
        if not os.path.isdir(dpf):
            os.makedirs(dpf)
        # Ensure the presence of the profiles folder and the 'default' profile
        if not os.path.isdir(self.profiles_dir):
            os.mkdir(self.profiles_dir)
        self.default_profile_dir = os.path.join(self.profiles_dir, PROFILE0)
        if not os.path.isdir(self.default_profile_dir):
            call(['cp', '-a', base_dir + '/profiles/'+ PROFILE0,
                    self.profiles_dir])

        # The application configs
        self.aconfig_file = os.path.join(self.projects_base, APP_CONF)
        self.aconfig = self.getconfig(self.aconfig_file)

        # The project-specific configs
        self.set_projectname(self.appget('project'))


    def get_projectname(self):
        return (True, self.project_name)

    def set_projectname(self, name):
        self.project_dir = os.path.join(self.projects_base, 'p_' + name)
        plist = self.list_projects()[1]
        if name not in plist:
            os.mkdir(self.project_dir)

        self.pconfig_file = os.path.join(self.project_dir, PROJECT_CONF)
        self.pconfig = self.getconfig(self.pconfig_file)
        self.profile_name = self.get('profile')

        self.profile_path = os.path.join(self.profiles_dir, self.profile_name)
        self.appset('project', name)
        self.project_name = name
        return (True, None)

    def delete_project(self, name):
        # This should probably be run as root, in case the build directory
        # is inside it ... cross that bridge when we come to it!
        r = call(['rm', '-r', '--interactive=never',
                os.path.join(self.projects_base, 'p_' + name)])
        return (True, r == 0)


    def delete_profile(self, name):
        r = call(['rm', '-r', '--interactive=never',
                os.path.join(self.profiles_dir, name)])
        return (True, r == 0)


    def get_profile(self):
        return (True, self.profile_name)

    def set_profile(self, name):
        self.set('profile', name)
        self.profile_name = name
        self.profile_path = os.path.join(self.profiles_dir, self.profile_name)
        return (True, None)


    def rename_profile(self, name):
        os.rename(self.profile_path, os.path.join(self.profiles_dir, name))
        self.set_profile(name)
        return (True, None)


    def get_new_profile(self, src, name):
        if not os.path.isfile(src + '/addedpacks'):
            return (True, False)
        dst = os.path.join(self.profiles_dir, name)
        call(['rm', '-rf', dst])
        shutil.copytree(src, dst, symlinks=True)
        self.set_profile(name)
        return (True, True)


    def get_example_profiles(self):
        pd = base_dir + '/profiles'
        return (True, (pd, os.listdir(pd)))

# location of working profiles
#        self.projects_base + '/myprofiles',


# What about not allowing changes to the default profile?
# That would mean also no renaming?
# One would have to copy a profile into the project before going
# any further ...
# Is it right to share profiles between projects? (Probably)

#+++++++++++++++++++++++++++++++++++++++++++++++
### A very simple configuration file handler
    def getconfig(self, filepath):
        cfg = {}
        if os.path.isfile(filepath):
            fh = open(filepath)
            for line in fh:
                ls = line.split('=', 1)
                if len(ls) > 1:
                    cfg[ls[0].strip()] = ls[1].strip()
        return cfg


    def saveconfig(self, filepath, config):
        fh = open(filepath, 'w')
        ci = config.items()
        ci.sort()
        for kv in ci:
            fh.write('%s = %s\n' % kv)
        fh.close()
###
#-----------------------------------------------

    def list_projects(self):
        projects = [p[2:] for p in os.listdir(self.projects_base)
                if p.startswith('p_')]
        projects.sort()
        return (True, projects)


    def list_free_projects(self):
        """This returns a list of projects which are free for (e.g.) deletion.
        """
        plist = self.list_projects()[1]
        plist.remove(PROJECT0)          # this one is not 'free'
        if self.project_name in plist:
            plist.remove(self.project_name)
        return (True, plist)


    def list_profiles(self):
        profiles = [d for d in os.listdir(self.profiles_dir) if
                os.path.isfile(os.path.join(self.profiles_dir, d, 'addedpacks'))]
        profiles.sort()
        return (True, profiles)


    def list_free_profiles(self):
        """This returns a list of profiles which are not in use by any project.
        """
        plist = self.list_profiles()[1]
        plist.remove(PROFILE0)          # this one is not 'free'
        for project in self.list_projects()[1]:
            cfg = self.getconfig(os.path.join(self.projects_base,
                    'p_' + project, PROJECT_CONF))
            p = cfg.get('profile')
            if p in plist:
                plist.remove(p)
        return (True, plist)


    def can_rename_profile(self):
        if self.profile_name == PROFILE0:
            return (True, False)
        for project in self.list_projects()[1]:
            if project != self.project_name:
                cfg = self.getconfig(os.path.join(self.projects_base,
                        'p_' + project, PROJECT_CONF))
                if self.profile_name == cfg.get('profile'):
                    return (True, False)
        return (True, True)


    def save_profile(self, path, force):
        if path[0] != '/':
            # cloning, only the profile name is passed
            path = os.path.join(self.profiles_dir, path)
        else:
            # copying, the destination will have the same name
            if os.path.basename(path) != self.profile_name:
                path = os.path.join(path, self.profile_name)
        if os.path.exists(path):
            if force:
                call(['rm', '-rf', path])
            elif os.path.isfile(os.path.join(path, 'addedpacks')):
                # This is an existing profile
                return (True, False)
            else:
                # This location is otherwise in use
                return (True, None)
        shutil.copytree(self.profile_path, path, symlinks=True)
        return (True, True)


    def set_profile_browse_dir(self, path):
        if os.path.isfile(os.path.join(path, 'addedpacks')):
            # Don't set the profile browse path to a profile directory,
            # but rather tp the containing directory
            path = os.path.dirname(path)
        self.set('profile_browse_dir', path)


    def appget(self, item):
        """Read an entry in the application configuration.
        """
        v = self.aconfig.get(item)
        if v:
            return v
        elif APP_DEFAULTS.has_key(item):
            return APP_DEFAULTS[item]
        debug("Unknown application configuration option: %s" % item)
        assert False

    def appset(self, item, value):
        """Set an entry in the application configuration.
        """
        self.aconfig[item] = value.strip()
        self.saveconfig(self.aconfig_file, self.aconfig)


    def getitem(self, item):
        return (True, self.get(item))

    def getbool(self, item):
        return (True, self.get(item) == 'Yes')

    def setitem(self, item, value):
        self.set(item, value)
        return (True, None)

    def setbool(self, item, on):
        self.set(item, 'Yes' if on else 'No')
        return (True, None)


    def get(self, item):
        """Read an entry in the project configuration.
        """
        v = self.pconfig.get(item)
        if v:
            return v
        elif DEFAULTS.has_key(item):
            return DEFAULTS[item]
        debug("Unknown configuration option: %s" % item)
        assert False

    def set(self, item, value):
        """Set an entry in the project configuration.
        """
        self.pconfig[item] = value.strip()
        self.saveconfig(self.pconfig_file, self.pconfig)
#        return True


    def get_ipath(self):
        ip = self.get('installation_dir')
        if not ip:
            ip = self.set_ipath('')[1]
        return (True, ip)

    def set_ipath(self, path):
        path = path.strip()
        if path:
            path = '/' + path.strip('/')
        else:
            path = os.environ['HOME'] + '/larch_build'
        self.set('installation_dir', path)
        return (True, path)


    def testlarchify(self):
        ipath = self.get_ipath()[1]
        path = ipath + CHROOT_DIR_MEDIUM
        bl = []
        nosave = False
        ok = (os.path.isfile(path + '/larch/system.sqf')
                and os.path.isfile(ipath + SYSLINUXDIR + '/isolinux.bin'))
        return (True, (path, ok))


    def newUserinfo(self):
        self.userInfo = Userinfo(self.profile_path)
        return (True, None)

    def allusers(self):
        return (True, self.userInfo.allusers())

    def getuserinfo(self, user, fields):
        return (True, self.userInfo.userinfo(user, fields))

    def newuser(self, user):
        return (True, self.userInfo.newuser(user))

    def saveusers(self):
        return (True, self.userInfo.saveusers())

    def userset(self, uname, field, text):
        self.userInfo.userset(uname, field, text)
        return (True, None)

    def deluser(self, user):
        return (True, self.userInfo.deluser(user))

    def listskels(self):
        return (True, glob(self.profile_path + '/skel_*'))


    def get_mediumlabel(self):
        l = self.get('medium_label')
        return (True, l if l else LABEL)

    def set_mediumlabel(self, l):
        if len(l) > 16:
            l = l[:16]
        self.set('medium_label', l)
        return self.get_mediumlabel()

    def set_bootisolabel(self, l):
        if len(l) > 32:
            l = l[:32]
        self.set('bootisolabel', l)
        return self.get_bootisolabel()


    def getisosavedir(self):
        d = self.get('isosavedir')
        return (True, d if d else os.environ['HOME'])

    def getisofile(self):
        f = self.get('isofile')
        return (True, f if f else ISOFILE)

    def getbootisofile(self):
        f = self.get('bootisofile')
        return (True, f if f else BOOTISO)

    def get_bootisolabel(self):
        l = self.get('bootisolabel')
        return (True, l if l else BOOTISOLABEL)



import __builtin__
__builtin__.project_manager = ProjectManager()
