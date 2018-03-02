""" Test Slicer and Task implementations """

import pytest
from time import sleep

from mock_task import MockSlicer
from task import *

class TaskTester:
    def __init__(self, slicer, task_class):
        slicer.suspend()
        self.task = task_class(generator=self.run(), slicer=slicer)
        slicer.resume()
        while self.task.state != Task2State.DONE and self.task.state != Task2State.EXCEPTION:
            sleep(1)
        self.check()

    def run(self):
        raise NotImplementedError

    def check(self):
        raise NotImplementedError

class ReturnTester(TaskTester):
    def run(self):
        yield

    def check(self):
        assert self.task.state == Task2State.DONE

class ExceptionTester(TaskTester):
    def run(self):
        yield
        raise ValueError

    def check(self):
        assert self.task.state == Task2State.EXCEPTION

class StepTester(TaskTester):
    def __init__(self, slicer, task_class):
        self.steps = []
        super().__init__(slicer, task_class)

    def run(self):
        self.steps.append(1)
        yield
        self.steps.append(2)
        return

    def check(self):
        assert self.task.state == Task2State.DONE
        assert len(self.steps) == 2
        assert self.steps[0] == 1
        assert self.steps[1] == 2

class OvertimeTester(TaskTester):
    def __init__(self, slicer, task_class):
        self.steps = 0
        self.after = False
        super().__init__(slicer, task_class)

    def run(self):
        while not self.task.overtime():
            self.steps += 1
            if self.steps > 100000:
                pass
        yield
        self.after = True

    def check(self):
        assert self.steps > 0
        assert self.after

class SubthreadTester(TaskTester):
    def __init__(self, slicer, task_class):
        self.sub_data = None
        super().__init__(slicer, task_class)

    def run(self):
        yield (self.sub, 123)

    def sub(self, data):
        self.sub_data = data

    def check(self):
        assert self.sub_data == 123

_mock_slicer = MockSlicer()

def test_return():
    ReturnTester(_mock_slicer, Task2)

def test_exception():
    ExceptionTester(_mock_slicer, Task2)

def test_step():
    StepTester(_mock_slicer, Task2)

def test_overtime():
    OvertimeTester(_mock_slicer, Task2)

def test_subthread():
    SubthreadTester(_mock_slicer, Task2)