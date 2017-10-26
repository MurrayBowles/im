''' assorted utilities '''

import os
import win32api

def drive(path):
    return os.path.splitdrive(path)[0]

def volume_label(path):
    d = drive(path)
    try:
        vl = win32api.GetVolumeInformation(d)[0]
    except:
        vl = ''
    return vl
