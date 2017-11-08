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
