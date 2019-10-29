""" pub/sub publish functions, messages """

from wx.lib.pubsub import pub

def set_status(text):
    pub.sendMessage('top.status', data=text)

#from ie_gui.GuiIECmd / ie_db/IECmd
#
# ie.sts.begun, worklist
# ie.sts.import thumbnails, #thumbnails
# ie.sts.imported thumnails, #thumbnails
# ie.sts.import exifs, #tags
# ie.sts.imported exifs, #tags
# ie.sts.import webpage
# ie.sts.imported webpage
# ie.sts.folder done, folder-db_name
# ie.sts.done, cancel_seen
#
# ie.cmd.start item
# ie.cmd.finish item

# ie.step end


