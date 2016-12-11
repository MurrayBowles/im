import kivy
kivy.require('1.7.0')

from kivy.app import App
from kivy.uix.button import Label
from kivy.logger import Logger

from fs import *

class HelloApp(App):
    def build(self):
        return Label(text='HEY')

if __name__=='__main__':
    Logger.info("top: hello goodbye")
    ds = DirSet(DirSetType.Internal, 'e:/photos')
    d = FsDir(ds, 'foo')
    dc = FsDir(ds, '1', d)
    i = FsImg(dc, '120344-1234')
    for x in dc.fs_imgs.values():
        Logger.info('top: %s', str(x))
    i.delete()
    for x in dc.fs_imgs.values():
        Logger.info('top: %s', str(x))
    #HelloApp().run()
    t = Tag('venues')
    gt = Tag('gilman', t)
    for x in t.children:
        Logger.info('top: %s', str(x))
    gt.delete()
    for x in t.children:
        Logger.info('top: %s', str(x))
    ddc = DbDir('foo-1')
    dc.set_db_dir(ddc)
    for x in ddc.fs_dirs:
        Logger.info('top: %s', str(x))
    di = DbImg(ddc, '120344-1234')
    i.set_db_img(di)
