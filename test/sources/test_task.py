""" Test Slicer and Task implementations """

import pytest
from time import sleep
import wx

from mock_task import MockSlicer
from task import *
from wx_task import WxSlicer

def _run_mock_task_test(test_class, task_class):
    slicer = MockSlicer(suspended=True)
    test = test_class()
    task = task_class(generator=test.run(), slicer=slicer)
    test.task = task
    slicer.resume()
    assert task.state == Task2State.DONE or task.state == Task2State.EXCEPTION
    test.check(task.state)

def _run_wx_task_test(test_class, task_class):
    app = wx.App()
    slicer = WxSlicer(msg='slice', suspended=True)
    test = test_class()
    def run_then_exit(test):
        yield from test.run()
        app.ExitMainLoop()
    task = task_class(generator=run_then_exit(test), slicer=slicer)
    test.task = task
    slicer.resume()
    #app.MainLoop()
    assert task.state == Task2State.DONE or task.state == Task2State.EXCEPTION
    test.check(task.state)

def _run_task_tests(test):
    _run_mock_task_test(test, Task2)
    _run_wx_task_test(test, Task2)


class TaskTest:
    def run(self):
        raise NotImplementedError

    def check(self, task_state):
        raise NotImplementedError


class ReturnTest(TaskTest):
    def run(self):
        yield

    def check(self, task_state):
        assert task_state == Task2State.DONE


class ExceptionTest(TaskTest):
    def run(self):
        yield
        raise ValueError

    def check(self, task_state):
        assert task_state == Task2State.EXCEPTION


class StepTest(TaskTest):
    def __init__(self):
        self.steps = []

    def run(self):
        self.steps.append(1)
        yield
        self.steps.append(2)
        return

    def check(self, task_state):
        assert task_state == Task2State.DONE
        assert len(self.steps) == 2
        assert self.steps[0] == 1
        assert self.steps[1] == 2


class OvertimeTest(TaskTest):
    def __init__(self):
        self.steps = 0
        self.after = False

    def run(self):
        while not self.task.overtime():
            self.steps += 1
            if self.steps > 100000:
                pass
        yield
        self.after = True

    def check(self, task_state):
        assert self.steps > 0
        assert self.after


class SubthreadTest(TaskTest):
    def __init__(self):
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

    def check(self, task_state):
        assert self.sub_data == 123
        assert self.run_cnt == 1
        assert self.sub_cnt == 1

def test_subthread():
    _run_task_tests(SubthreadTest)

def test_return():
    _run_task_tests(ReturnTest)

def test_exception():
    _run_task_tests(ExceptionTest)

def test_step():
    _run_task_tests(StepTest)

def test_overtime():
    _run_task_tests(OvertimeTest)

