#!/usr/bin/env python

# Copyright 2015 Kevin Reid <kpreid@switchb.org>
#
# This file is part of ShinySDR.
# 
# ShinySDR is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# ShinySDR is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with ShinySDR.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import absolute_import, division

from importlib import import_module


class DependencyTester(object):
    '''
    Attempt to import things and collect reports of failure.
    '''
    def __init__(self):
        self.__missing = set()
        self.__broken = set()
        self.__old = set()

    def check_module_attr(self, module_name, dep_name, attr_path, old=False):
        module = self.check_module(module_name, dep_name, old=old)
        self.check_attr(module_name, dep_name, module, attr_path, old=True)
    
    def check_attr(self, module_name, dep_name, module, attr_path, old=False):
        if not hasattr_path(module, attr_path):
            entry = (dep_name, '%s.%s not present.' % (module_name, attr_path))
            if old:
                self.__old.add(entry)
            else:
                self.__missing.add(entry)
            return
        try:
            attr = getattr_path(module, attr_path)
        except Exception as e:
            self.__broken.add((dep_name, 'Error checking for %s.%s.' % (module_name, attr_path)))  # TODO mention error
    
    def check_module(self, module_name, dep_name, old=False):
        try:
            return import_module(module_name)
        except ImportError as e:
            msg = e.message
            if msg.startswith('No module named '):
                # confirm using message contents
                if module_name.endswith(msg[len('No module named '):]):
                    self.__missing.add((dep_name, '%s not present.' % module_name))
                else:
                    # actually a loading error
                    self.__broken.add((dep_name, '%s failed to import (%s).' % (module_name, e)))
            return None
        except Exception as e:
            self.__broken.add((dep_name, '%s failed to import (%s).' % (module_name, e)))
            return None
    
    def report(self):
        report_text = ''
        if len(self.__missing) > 0:
            report_text += 'The following libraries/programs are missing:\n' + self.__format_entries(self.__missing)
        if len(self.__broken) > 0:
            report_text += 'The following libraries/programs are not installed correctly:\n' + self.__format_entries(self.__broken)
        if len(self.__old) > 0:
            report_text += 'The following libraries/programs are too old:\n' + self.__format_entries(self.__old)
        if report_text != '':
            report_text += 'Please (re)install current versions.'
            return report_text
        else:
            return None
    
    def __format_entries(self, entries):
        out = ''
        for entry in entries:
            item, check = entry
            out += '\t%s  (Check: %s)\n' % (item, check)
        return out


def hasattr_path(specimen, path):
    splat = path.split('.', 1)
    if len(splat) == 1:
        return hasattr(specimen, path)
    else:
        first, rest = splat
        return hasattr(specimen, first) and hasattr_path(getattr(specimen, first), rest)


def getattr_path(specimen, path):
    splat = path.split('.', 1)
    if len(splat) == 1:
        return getattr(specimen, path)
    else:
        first, rest = splat
        return getattr_path(getattr(specimen, first), rest)
