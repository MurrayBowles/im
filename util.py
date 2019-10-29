""" assorted utilities """

import datetime
import os
import win32api

def date_from_yymmdd(yymmdd):
    """ return a datetime.date from a YYMMDD string """
    year = int(yymmdd[0:2])
    year += 1900 if year >= 70 else 2000
    month = int(yymmdd[2:4])
    if month == 0: month = 1
    day = int(yymmdd[4:6])
    if day == 0: day = 1
    # yymmdd used 00 to indicate 'don't know'
    return datetime.date(year, month, day)

def yymmdd_from_date(iso_date):
    """ return a YYMMDD string from a daytime.date """
    return str(iso_date)[2:].replace('-', '')

def drive(path):
    return os.path.splitdrive(path)[0]

def volume_label(path):
    d = drive(path)
    try:
        vl = win32api.GetVolumeInformation(d)[0]
    except:
        vl = ''
    return vl

def path_plus_separator(path):
    # return <db_name> plus the host separator (e.g. / or \)
    return os.path.join(path, 'a')[0:-1]

def win_path(volume, path):
    # determine which volumes are currently available
    drives = win32api.GetLogicalDriveStrings()
    drives = drives.split('\000')

    if volume.endswith(':'):
        # no volume db_name: <volume> is the drive letter
        for d in drives:
            if volume == d[0:2]:
                return volume + path
    else:
        for d in drives:
            label = volume_label(d)
            if label == volume:
                return d[0:2] + path
    return None

def last_url_component(url):
    right_slash = url.rfind('/')
    assert right_slash != -1
    return url[right_slash + 1:]

def force_list(singleton_or_list):
    if type(singleton_or_list) == list:
        return singleton_or_list
    else:
        return [singleton_or_list]

def all_descendent_classes(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])

def find_descendent_class(cls, name):
    adc = all_descendent_classes(cls)
    for c in all_descendent_classes(cls):
        if c.__name__ == name:
            return c
    raise ValueError('%s is not a descendent of %s', name, cls.__name__)
