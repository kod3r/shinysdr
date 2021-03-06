# Copyright 2013, 2014, 2015 Kevin Reid <kpreid@switchb.org>
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


'''
Type definitions for ShinySDR value cells etc.
'''


from __future__ import absolute_import, division


import bisect
import math


def to_value_type(typeoid):
    if isinstance(typeoid, ValueType):
        return typeoid
    elif isinstance(typeoid, type):
        # TODO: Stricten this to only allow a specific set
        return BareType(typeoid)
    else:
        raise TypeError('Don\'t know how to make a ValueType of %r' % (typeoid,))


class ValueType(object):
    '''
    A type in the sense of "set of values", plus coercion and other hints.
    '''
    def type_to_json(self):
        '''
        Serialize this type for the client.
        '''
        raise NotImplementedError()
    
    def __call__(self, specimen):
        '''
        Coerce the specimen to this type.
        
        If the specimen is not of a suitable type, raise TypeError.
        
        If the specimen is of a suitable type but out of range and this type does not choose to make it in range, raise ValueError.
        '''
        raise NotImplementedError()


class BareType(ValueType):
    '''
    ValueType wrapper for Python types.
    '''
    def __init__(self, python_type):
        self.__python_type = python_type
    
    def type_to_json(self):
        if self.__python_type == bool:
            return u'boolean'
        else:
            # TODO
            return None
    
    def __call__(self, specimen):
        return self.__python_type(specimen)


class Constant(ValueType):
    '''
    A single-valued type.
    '''
    
    def __init__(self, value):
        self.__value = value
    
    def type_to_json(self):
        return {
            u'type': u'constant',
            u'value': self.__value
        }
    
    def __call__(self, specimen):
        return self.__value


class Enum(ValueType):
    def __init__(self, values, strict=False, base_type=unicode):
        """values: dict of {value: description}"""
        self.__values = dict(values)  # paranoid copy
        self.__strict = bool(strict)
        self.__base_type = base_type
    
    def values(self):
        return self.__values
    
    def type_to_json(self):
        return {'type': 'enum', 'values': self.__values}
    
    def __call__(self, specimen):
        specimen = self.__base_type(specimen)
        if specimen not in self.__values and self.__strict:
            raise ValueError('Not a permitted value: ' + repr(specimen))
        return specimen


class Range(ValueType):
    def __init__(self, subranges, strict=True, logarithmic=False, integer=False):
        # TODO validate subranges are sorted
        self.__mins = [min_value for (min_value, max_value) in subranges]
        self.__maxes = [max_value for (min_value, max_value) in subranges]
        self.__strict = strict
        self.__logarithmic = logarithmic
        self.__integer = integer
    
    def type_to_json(self):
        return {
            'type': 'range',
            'subranges': zip(self.__mins, self.__maxes),
            'logarithmic': self.__logarithmic,
            'integer': self.__integer
        }
    
    def __call__(self, specimen):
        specimen = float(specimen)
        
        if self.__integer:
            if self.__logarithmic:
                # We may eventually want other log base options; currently only 2
                if specimen <= 0:
                    specimen = self.__mins[0]
                specimen = 2 ** int(round(math.log(specimen, 2)))
            else:
                specimen = int(round(specimen))
        
        if self.__strict:
            mins = self.__mins
            maxes = self.__maxes
            
            i = bisect.bisect_right(mins, specimen) - 1
            if i < 0: i = 0
            # i is now the index of the subrange whose lower endpoint is closest to the specimen.
            
            # Round to nearest range instead of lower one.
            if i < len(mins) - 1 and mins[i + 1] - specimen < specimen - maxes[i]:
                i = i + 1
            
            # Clamp to chosen range.
            if specimen < mins[i]:
                specimen = mins[i]
            elif specimen > maxes[i]:
                specimen = maxes[i]
        
        return specimen
    
    def __repr__(self):
        return '%s(%r, strict=%r, logarithmic=%r, integer=%r)' % (self.__class__.__name__, zip(self.__mins, self.__maxes), self.__strict, self.__logarithmic, self.__integer)
    
    def __eq__(self, other):
        # pylint: disable=unidiomatic-typecheck
        return (
            type(self) == type(other) and
            self.__mins == other.__mins and
            self.__maxes == other.__maxes and
            self.__strict == other.__strict and
            self.__logarithmic == other.__logarithmic and
            self.__integer == other.__integer
        )
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    __hash__ = None
    
    def shifted_by(self, offset):
        mins = self.__mins
        maxes = self.__maxes
        return Range(
            [(mins[i] + offset, maxes[i] + offset) for i in xrange(len(mins))],
            strict=self.__strict,
            logarithmic=self.__logarithmic,
            integer=self.__integer and offset % 1 == 0)
    
    def get_min(self):
        return self.__mins[0]
    
    def get_max(self):
        return self.__maxes[-1]
    
    def get_single_point(self):
        '''
        If this Range contains only a single value, return it, else None.
        '''
        if len(self.__mins) != 1:
            return None
        else:
            a = self.__mins[0]
            b = self.__maxes[0]
            if a == b:
                return a
            else:
                return None


class Notice(ValueType):
    def __init__(self, always_visible=False):
        self.__always_visible = always_visible
    
    def type_to_json(self):
        return {
            'type': 'notice',
            'always_visible': self.__always_visible
        }
    
    def __call__(self, specimen):
        return unicode(specimen)


class BulkDataType(ValueType):
    def __init__(self, info_format, array_format):
        self.__info_format = info_format
        self.__array_format = array_format
    
    def type_to_json(self):
        return {
            u'type': u'bulk_data',
            u'info_format': self.__info_format,
            u'array_format': self.__array_format,
        }
    
    def get_info_format(self):
        return self.__info_format
    
    def get_array_format(self):
        return self.__array_format
    
    def __call__(self, specimen):
        raise Exception('Coerce not implemented for BulkDataType')
    
    # TODO implement coerce behavior, generally make this more well-defined
