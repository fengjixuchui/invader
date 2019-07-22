# -*- coding: utf-8 -*-
import unittest
import time

from ._Invader_event import MoveEvent, ButtonEvent, WheelEvent, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN, DOUBLE
from keyboard import Invader

class FakeOsInvader(object):
    def __init__(self):
        self.append = None
        self.position = (0, 0)
        self.queue = None
        self.init = lambda: None

    def listen(self, queue):
        self.listening = True
        self.queue = queue

    def press(self, button):
        self.append((DOWN, button))

    def release(self, button):
        self.append((UP, button))

    def get_position(self):
        return self.position

    def move_to(self, x, y):
        self.append(('move', (x, y)))
        self.position = (x, y)

    def wheel(self, delta):
        self.append(('wheel', delta))

    def move_relative(self, x, y):
        self.position = (self.position[0] + x, self.position[1] + y)

class TestInvader(unittest.TestCase):
    @staticmethod
    def setUpClass():
        Invader._os_Invader= FakeOsInvader()
        Invader._listener.start_if_necessary()
        assert Invader._os_Invader.listening

    def setUp(self):
        self.events = []
        Invader._pressed_events.clear()
        Invader._os_Invader.append = self.events.append

    def tearDown(self):
        Invader.unhook_all()
        # Make sure there's no spill over between tests.
        self.wait_for_events_queue()

    def wait_for_events_queue(self):
        Invader._listener.queue.join()

    def flush_events(self):
        self.wait_for_events_queue()
        events = list(self.events)
        # Ugly, but requried to work in Python2. Python3 has list.clear
        del self.events[:]
        return events

    def press(self, button=LEFT):
        Invader._os_Invader.queue.put(ButtonEvent(DOWN, button, time.time()))
        self.wait_for_events_queue()

    def release(self, button=LEFT):
        Invader._os_Invader.queue.put(ButtonEvent(UP, button, time.time()))
        self.wait_for_events_queue()

    def double_click(self, button=LEFT):
        Invader._os_Invader.queue.put(ButtonEvent(DOUBLE, button, time.time()))
        self.wait_for_events_queue()

    def click(self, button=LEFT):
        self.press(button)
        self.release(button)

    def wheel(self, delta=1):
        Invader._os_Invader.queue.put(WheelEvent(delta, time.time()))
        self.wait_for_events_queue()

    def move(self, x=0, y=0):
        Invader._os_Invader.queue.put(MoveEvent(x, y, time.time()))
        self.wait_for_events_queue()

    def test_hook(self):
        events = []
        self.press()
        Invader.hook(events.append)
        self.press()
        Invader.unhook(events.append)
        self.press()
        self.assertEqual(len(events), 1)

    def test_is_pressed(self):
        self.assertFalse(Invader.is_pressed())
        self.press()
        self.assertTrue(Invader.is_pressed())
        self.release()
        self.press(X2)
        self.assertFalse(Invader.is_pressed())

        self.assertTrue(Invader.is_pressed(X2))
        self.press(X2)
        self.assertTrue(Invader.is_pressed(X2))
        self.release(X2)
        self.release(X2)
        self.assertFalse(Invader.is_pressed(X2))

    def test_buttons(self):
        Invader.press()
        self.assertEqual(self.flush_events(), [(DOWN, LEFT)])
        Invader.release()
        self.assertEqual(self.flush_events(), [(UP, LEFT)])
        Invader.click()
        self.assertEqual(self.flush_events(), [(DOWN, LEFT), (UP, LEFT)])
        Invader.double_click()
        self.assertEqual(self.flush_events(), [(DOWN, LEFT), (UP, LEFT), (DOWN, LEFT), (UP, LEFT)])
        Invader.right_click()
        self.assertEqual(self.flush_events(), [(DOWN, RIGHT), (UP, RIGHT)])
        Invader.click(RIGHT)
        self.assertEqual(self.flush_events(), [(DOWN, RIGHT), (UP, RIGHT)])
        Invader.press(X2)
        self.assertEqual(self.flush_events(), [(DOWN, X2)])

    def test_position(self):
        self.assertEqual(Invader.get_position(), Invader._os_Invader.get_position())

    def test_move(self):
        Invader.move(0, 0)
        self.assertEqual(Invader._os_Invader.get_position(), (0, 0))
        Invader.move(100, 500)
        self.assertEqual(Invader._os_Invader.get_position(), (100, 500))
        Invader.move(1, 2, False)
        self.assertEqual(Invader._os_Invader.get_position(), (101, 502))

        Invader.move(0, 0)
        Invader.move(100, 499, True, duration=0.01)
        self.assertEqual(Invader._os_Invader.get_position(), (100, 499))
        Invader.move(100, 1, False, duration=0.01)
        self.assertEqual(Invader._os_Invader.get_position(), (200, 500))
        Invader.move(0, 0, False, duration=0.01)
        self.assertEqual(Invader._os_Invader.get_position(), (200, 500))

    def triggers(self, fn, events, **kwargs):
        self.triggered = False
        def callback():
            self.triggered = True
        handler = fn(callback, **kwargs)

        for event_type, arg in events:
            if event_type == DOWN:
                self.press(arg)
            elif event_type == UP:
                self.release(arg)
            elif event_type == DOUBLE:
                self.double_click(arg)
            elif event_type == 'WHEEL':
                self.wheel()

        Invader._listener.remove_handler(handler)
        return self.triggered

    def test_on_button(self):
        self.assertTrue(self.triggers(Invader.on_button, [(DOWN, LEFT)]))
        self.assertTrue(self.triggers(Invader.on_button, [(DOWN, RIGHT)]))
        self.assertTrue(self.triggers(Invader.on_button, [(DOWN, X)]))

        self.assertFalse(self.triggers(Invader.on_button, [('WHEEL', '')]))

        self.assertFalse(self.triggers(Invader.on_button, [(DOWN, X)], buttons=MIDDLE))
        self.assertTrue(self.triggers(Invader.on_button, [(DOWN, MIDDLE)], buttons=MIDDLE))
        self.assertTrue(self.triggers(Invader.on_button, [(DOWN, MIDDLE)], buttons=MIDDLE))
        self.assertFalse(self.triggers(Invader.on_button, [(DOWN, MIDDLE)], buttons=MIDDLE, types=UP))
        self.assertTrue(self.triggers(Invader.on_button, [(UP, MIDDLE)], buttons=MIDDLE, types=UP))

        self.assertTrue(self.triggers(Invader.on_button, [(UP, MIDDLE)], buttons=[MIDDLE, LEFT], types=[UP, DOWN]))
        self.assertTrue(self.triggers(Invader.on_button, [(DOWN, LEFT)], buttons=[MIDDLE, LEFT], types=[UP, DOWN]))
        self.assertFalse(self.triggers(Invader.on_button, [(UP, X)], buttons=[MIDDLE, LEFT], types=[UP, DOWN]))

    def test_ons(self):
        self.assertTrue(self.triggers(Invader.on_click, [(UP, LEFT)]))
        self.assertFalse(self.triggers(Invader.on_click, [(UP, RIGHT)]))
        self.assertFalse(self.triggers(Invader.on_click, [(DOWN, LEFT)]))
        self.assertFalse(self.triggers(Invader.on_click, [(DOWN, RIGHT)]))

        self.assertTrue(self.triggers(Invader.on_double_click, [(DOUBLE, LEFT)]))
        self.assertFalse(self.triggers(Invader.on_double_click, [(DOUBLE, RIGHT)]))
        self.assertFalse(self.triggers(Invader.on_double_click, [(DOWN, RIGHT)]))

        self.assertTrue(self.triggers(Invader.on_right_click, [(UP, RIGHT)]))
        self.assertTrue(self.triggers(Invader.on_middle_click, [(UP, MIDDLE)]))

    def test_wait(self):
        # If this fails it blocks. Unfortunately, but I see no other way of testing.
        from threading import Thread, Lock
        lock = Lock()
        lock.acquire()
        def t():
            Invader.wait()
            lock.release()
        Thread(target=t).start()
        self.press()
        lock.acquire()

    def test_record_play(self):
        from threading import Thread, Lock
        lock = Lock()
        lock.acquire()
        def t():
            self.recorded = Invader.record(RIGHT)
            lock.release()
        Thread(target=t).start()
        self.click()
        self.wheel(5)
        self.move(100, 50)
        self.press(RIGHT)
        lock.acquire()

        self.assertEqual(len(self.recorded), 5)
        self.assertEqual(self.recorded[0]._replace(time=None), ButtonEvent(DOWN, LEFT, None))
        self.assertEqual(self.recorded[1]._replace(time=None), ButtonEvent(UP, LEFT, None))
        self.assertEqual(self.recorded[2]._replace(time=None), WheelEvent(5, None))
        self.assertEqual(self.recorded[3]._replace(time=None), MoveEvent(100, 50, None))
        self.assertEqual(self.recorded[4]._replace(time=None), ButtonEvent(DOWN, RIGHT, None))

        Invader.play(self.recorded, speed_factor=0)
        events = self.flush_events()
        self.assertEqual(len(events), 5)
        self.assertEqual(events[0], (DOWN, LEFT))
        self.assertEqual(events[1], (UP, LEFT))
        self.assertEqual(events[2], ('wheel', 5))
        self.assertEqual(events[3], ('move', (100, 50)))
        self.assertEqual(events[4], (DOWN, RIGHT))

        Invader.play(self.recorded)
        events = self.flush_events()
        self.assertEqual(len(events), 5)
        self.assertEqual(events[0], (DOWN, LEFT))
        self.assertEqual(events[1], (UP, LEFT))
        self.assertEqual(events[2], ('wheel', 5))
        self.assertEqual(events[3], ('move', (100, 50)))
        self.assertEqual(events[4], (DOWN, RIGHT))

        Invader.play(self.recorded, include_clicks=False)
        events = self.flush_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0], ('wheel', 5))
        self.assertEqual(events[1], ('move', (100, 50)))

        Invader.play(self.recorded, include_moves=False)
        events = self.flush_events()
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0], (DOWN, LEFT))
        self.assertEqual(events[1], (UP, LEFT))
        self.assertEqual(events[2], ('wheel', 5))
        self.assertEqual(events[3], (DOWN, RIGHT))

        Invader.play(self.recorded, include_wheel=False)
        events = self.flush_events()
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0], (DOWN, LEFT))
        self.assertEqual(events[1], (UP, LEFT))
        self.assertEqual(events[2], ('move', (100, 50)))
        self.assertEqual(events[3], (DOWN, RIGHT))

if __name__ == '__main__':
    unittest.main()
