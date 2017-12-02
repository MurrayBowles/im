''' wxPython implementation of Task '''

from threading import Thread
import wx
from wx.lib.pubsub import pub

class WxTask:

    def init_impl(self, **kwargs):
        for msg, method in self.subs.items():
            ps.subscribe(msg, method)
        pub.subscribe(self._call, 'Task.call')
        pass

    def pub(self, msg, data=None):
        ''' publish msg, data '''
        def do_pub(msg, data):
            pub.sendMessage(msg, data=data)
        wx.CallAfter(do_pub, msg, data=data)

    def _call(self, data):
        method, data = data
        method(data)

    def queue(self, method, data=None):
        ''' queue <method> to be called with <data> '''
        def do_pub(msg, data):
            pub.sendMessage(msg, data=data)
        wx.CallAfter(do_pub, 'Task.call', (method, data))

    def spawn(self, method, data=None):
        ''' start a thread calling <method> with <data> '''
        _WxThread(self, method, data)


class _WxThread(Thread):

    def __init__(self, ctx, method, data=None):
        super().__init__()
        self.ctx = ctx
        self.method = method
        self.data = data
        self.start()

    def run(self):
        self.method(self.ctx, self.data)
