""" Test Slicer and Task implementations """

import pytest
from time import sleep
import wx

from mock_task import MockSlicer
from task import *
from wx_task import WxSlicer

def _run_mock_task_test(task_class):
    slicer = MockSlicer(suspended=True)
    task = task_class(slicer=slicer)
    task.start()
    slicer.resume()
    assert task.state == Task2State.DONE or task.state == Task2State.EXCEPTION
    task.check()

def _run_wx_task_test(task_class):
    app = wx.App()
    frame = wx.Frame(None, -1, 'TOTO: why do i need this Frame to make MainLoop work?')
    slicer = WxSlicer(msg='slice', suspended=True)
    def on_done(exc_data):
        app.ExitMainLoop()
    task = task_class(slicer=slicer, on_done=on_done)
    task.start()
    slicer.resume()
    app.MainLoop()
    assert task.state == Task2State.DONE or task.state == Task2State.EXCEPTION
    task.check()

def _run_task_tests(test):
    _run_mock_task_test(test)
    _run_wx_task_test(test)


class TaskTest(Task2):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.setup()

    def setup(self):
        pass

    def check(self):
        raise NotImplementedError


class ReturnTest(TaskTest):
    def run(self):
        yield

    def check(self):
        assert self.state == Task2State.DONE


class ExceptionTest(TaskTest):
    def run(self):
        yield
        raise ValueError

    def check(self):
        assert self.state == Task2State.EXCEPTION


class CancelTest(TaskTest):
    def run(self):
        assert not self.cancelled()
        self.cancel()
        yield

    def check(self):
        assert self.cancelled()
        assert self.cancel_seen

class StepTest(TaskTest):
    def setup(self):
        self.steps = []

    def run(self):
        self.steps.append(1)
        yield
        self.steps.append(2)
        return

    def check(self):
        assert self.state == Task2State.DONE
        assert len(self.steps) == 2
        assert self.steps[0] == 1
        assert self.steps[1] == 2


class OvertimeTest(TaskTest):
    def setup(self):
        self.steps = 0
        self.after = False

    def run(self):
        while not self.overtime():
            self.steps += 1
            if self.steps > 100000:
                pass
        yield
        self.after = True

    def check(self):
        assert self.steps > 0
        assert self.after


class SubthreadTest(TaskTest):
    def setup(self):
        self.sub_data = None
        self.run_cnt = 0
        self.sub_cnt = 0

    def run(self):
        self.run_cnt += 1
        yield lambda: self.sub(123)
        pass

    def sub(self, data):
        self.sub_cnt = 1
        self.sub_data = data

    def check(self):
        assert self.sub_data == 123
        assert self.run_cnt == 1
        assert self.sub_cnt == 1

def test_cancel():
    _run_task_tests(CancelTest)

def test_return():
    _run_task_tests(ReturnTest)

def test_exception():
    _run_task_tests(ExceptionTest)

def test_subthread():
    _run_task_tests(SubthreadTest)

def test_step():
    _run_task_tests(StepTest)

def test_overtime():
    _run_task_tests(OvertimeTest)
