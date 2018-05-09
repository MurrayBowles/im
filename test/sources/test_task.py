""" Test Slicer and Task implementations """

import pytest
import wx

from mock_task import MockSlicer
from task import *
from wx_task import WxSlicer


def _run_mock_task_test(task_class):
    slicer = MockSlicer(suspended=True)
    task = task_class(slicer=slicer)
    task.start()
    slicer.resume()
    assert task.state == TaskState.DONE or task.state == TaskState.EXCEPTION
    task.check()

def _run_wx_task_test(task_class):
    try:
        app = wx.App()
    except Exception as ed:
        pass
    frame = wx.Frame(
        None, -1, 'TOTO: why do i need this Frame to make MainLoop work?')
    slicer = WxSlicer(suspended=True)
    def on_done(exc_data):
        app.ExitMainLoop()
    task = task_class(slicer=slicer, on_done=on_done)
    task.start()
    slicer.resume()
    app.MainLoop()
    assert task.state == TaskState.DONE or task.state == TaskState.EXCEPTION
    task.check()

def _run_task_tests(test):
    _run_mock_task_test(test)
    _run_wx_task_test(test)


class TaskTest(Task):
    def __init__(self, slicer, **kw):
        super().__init__(slicer, **kw)
        self.setup()

    def setup(self):
        pass

    def check(self):
        raise NotImplementedError


class ReturnTest(TaskTest):
    def run(self):
        yield

    def check(self):
        assert self.state == TaskState.DONE


class ExceptionTest(TaskTest):
    def run(self):
        yield
        raise ValueError

    def check(self):
        assert self.state == TaskState.EXCEPTION


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
        assert self.state == TaskState.DONE
        assert self.steps == [1, 2]


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


class PubsubTest(TaskTest):
    def setup(self):
        self.a_calls = 0
        self.b_calls = 0
        self.sub([(self.on_a, 'a'), (self.on_b, 'b')])

    def run(self):
        self.pub('a', data='a')
        yield
        self.pub('b', data='b')
        yield
        self.pub('b', data='b')

    def on_a(self, data):
        assert data == 'a'
        self.a_calls += 1

    def on_b(self, data):
        assert data == 'b'
        self.b_calls += 1

    def check(self):
        assert self.a_calls == 1
        assert self.b_calls == 2

@pytest.mark.parametrize("task_class", [
    ReturnTest, ExceptionTest, CancelTest, SubthreadTest, StepTest, OvertimeTest,
    PubsubTest
])
def test_task(task_class):
    _run_task_tests(task_class)