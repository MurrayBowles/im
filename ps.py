''' pub/sub publish functions, messages '''

from wx.lib.pubsub import pub

def set_status(text):
    pub.sendMessage('top.status', data=text)

#from ie_gui.GuiIECmd / ie_db/IECmd
#
# ie.begun, worklist
# ie.import thumbnails, #thumbnails
# ie.imported thumnails, #thumbnails
# ie.import tags, #tags
# ie.imported tags, #tags
# ie.background done
# ie.folder done, folder-name
# ie.done, cancelling

