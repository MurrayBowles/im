''' pub/sub publish functions'''

from wx.lib.pubsub import pub

def set_status(text):
    pub.sendMessage('top.status', data=text)

