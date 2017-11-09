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

def win_path(volume, path):
    # determine which volumes are currently available
    drives = win32api.GetLogicalDriveStrings()
    drives = drives.split('\000')

    if volume.endswith(':'):
        # no volume name: <volume> is the drive letter
        for d in drives:
            if volume == d[0:2]:
                return volume + path
    else:
        for d in drives:
            label = volume_label(d)
            if label == volume:
                return d[0:2] + path
    return None


def _hit_guess_idx(ctrl, pos):
    pos -= ctrl.GetClientAreaOrigin()
    scroll = ctrl.GetScrollPos(pos.y)
    extent = ctrl.GetTextExtent('Aq')[1]
    y = pos.y + scroll * extent
    return y / extent

def _hit_check_idx(ctrl, idx):
    if idx < 0 or idx >= ctrl.GetCount():
        return None
    # FIXME: this should integerize the index
    return idx

def hit_get_idx(event):
    ctrl = event.GetEventObject()
    return _hit_check_idx(ctrl, _hit_guess_idx(ctrl, event.GetPosition()))
