import kivy
kivy.require('1.7.0')

from kivy.app import App
from kivy.uix.button import Label
from kivy.logger import Logger

from db import *
from tmp import *

class HelloApp(App):
    def build(self):
        return Label(text='HEY')

if __name__=='__main__':
    Logger.info("top: hello goodbye")
    # db_test()
    # HelloApp().run()
    tmp_test()
