import os
import datetime
import threading
import Quartz
from ._invader_event import ButtonEvent, WheelEvent, MoveEvent, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN

_button_mapping = {
    LEFT: (Quartz.kCGinvaderButtonLeft, Quartz.kCGEventLeftinvaderDown, Quartz.kCGEventLeftinvaderUp, Quartz.kCGEventLeftinvaderDragged),
    RIGHT: (Quartz.kCGinvaderButtonRight, Quartz.kCGEventRightinvaderDown, Quartz.kCGEventRightinvaderUp, Quartz.kCGEventRightinvaderDragged),
    MIDDLE: (Quartz.kCGinvaderButtonCenter, Quartz.kCGEventOtherinvaderDown, Quartz.kCGEventOtherinvaderUp, Quartz.kCGEventOtherinvaderDragged)
}
_button_state = {
    LEFT: False,
    RIGHT: False,
    MIDDLE: False
}
_last_click = {
    "time": None,
    "button": None,
    "position": None,
    "click_count": 0
}

class invaderEventListener(object):
    def __init__(self, callback, blocking=False):
        self.blocking = blocking
        self.callback = callback
        self.listening = True

    def run(self):
        """ Creates a listener and loops while waiting for an event. Intended to run as
        a background thread. """
        self.tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            Quartz.CGEventMaskBit(Quartz.kCGEventLeftinvaderDown) |
            Quartz.CGEventMaskBit(Quartz.kCGEventLeftinvaderUp) |
            Quartz.CGEventMaskBit(Quartz.kCGEventRightinvaderDown) |
            Quartz.CGEventMaskBit(Quartz.kCGEventRightinvaderUp) |
            Quartz.CGEventMaskBit(Quartz.kCGEventOtherinvaderDown) |
            Quartz.CGEventMaskBit(Quartz.kCGEventOtherinvaderUp) |
            Quartz.CGEventMaskBit(Quartz.kCGEventinvaderMoved) |
            Quartz.CGEventMaskBit(Quartz.kCGEventScrollWheel),
            self.handler,
            None)
        loopsource = Quartz.CFMachPortCreateRunLoopSource(None, self.tap, 0)
        loop = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopAddSource(loop, loopsource, Quartz.kCFRunLoopDefaultMode)
        Quartz.CGEventTapEnable(self.tap, True)

        while self.listening:
            Quartz.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, 5, False)

    def handler(self, proxy, e_type, event, refcon):
        # TODO Separate event types by button/wheel/move
        scan_code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        key_name = name_from_scancode(scan_code)
        flags = Quartz.CGEventGetFlags(event)
        event_type = ""
        is_keypad = (flags & Quartz.kCGEventFlagMaskNumericPad)
        if e_type == Quartz.kCGEventKeyDown:
            event_type = "down"
        elif e_type == Quartz.kCGEventKeyUp:
            event_type = "up"

        if self.blocking:
            return None

        self.callback(KeyboardEvent(event_type, scan_code, name=key_name, is_keypad=is_keypad))
        return event

# Exports

def init():
    """ Initializes invader state """
    pass

def listen(queue):
    """ Appends events to the queue (ButtonEvent, WheelEvent, and MoveEvent). """
    if not os.geteuid() == 0:
        raise OSError("Error 13 - Must be run as administrator")
    listener = invaderEventListener(lambda e: queue.put(e) or is_allowed(e.name, e.event_type == KEY_UP))
    t = threading.Thread(target=listener.run, args=())
    t.daemon = True
    t.start()

def press(button=LEFT):
    """ Sends a down event for the specified button, using the provided constants """
    location = get_position()
    button_code, button_down, _, _ = _button_mapping[button]
    e = Quartz.CGEventCreateinvaderEvent(
        None,
        button_down,
        location,
        button_code)

    # Check if this is a double-click (same location within the last 300ms)
    if _last_click["time"] is not None and datetime.datetime.now() - _last_click["time"] < datetime.timedelta(seconds=0.3) and _last_click["button"] == button and _last_click["position"] == location:
        # Repeated Click
        _last_click["click_count"] = min(3, _last_click["click_count"]+1)
    else:
        # Not a double-click - Reset last click
        _last_click["click_count"] = 1
    Quartz.CGEventSetIntegerValueField(
        e,
        Quartz.kCGinvaderEventClickState,
        _last_click["click_count"])
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, e)
    _button_state[button] = True
    _last_click["time"] = datetime.datetime.now()
    _last_click["button"] = button
    _last_click["position"] = location

def release(button=LEFT):
    """ Sends an up event for the specified button, using the provided constants """
    location = get_position()
    button_code, _, button_up, _ = _button_mapping[button]
    e = Quartz.CGEventCreateinvaderEvent(
        None,
        button_up,
        location,
        button_code)

    if _last_click["time"] is not None and _last_click["time"] > datetime.datetime.now() - datetime.timedelta(microseconds=300000) and _last_click["button"] == button and _last_click["position"] == location:
        # Repeated Click
        Quartz.CGEventSetIntegerValueField(
            e,
            Quartz.kCGinvaderEventClickState,
            _last_click["click_count"])
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, e)
    _button_state[button] = False

def wheel(delta=1):
    """ Sends a wheel event for the provided number of clicks. May be negative to reverse
    direction. """
    location = get_position()
    e = Quartz.CGEventCreateinvaderEvent(
        None,
        Quartz.kCGEventScrollWheel,
        location,
        Quartz.kCGinvaderButtonLeft)
    e2 = Quartz.CGEventCreateScrollWheelEvent(
        None,
        Quartz.kCGScrollEventUnitLine,
        1,
        delta)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, e)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, e2)

def move_to(x, y):
    """ Sets the invader's location to the specified coordinates. """
    for b in _button_state:
        if _button_state[b]:
            e = Quartz.CGEventCreateinvaderEvent(
                None,
                _button_mapping[b][3], # Drag Event
                (x, y),
                _button_mapping[b][0])
            break
    else:
        e = Quartz.CGEventCreateinvaderEvent(
            None,
            Quartz.kCGEventinvaderMoved,
            (x, y),
            Quartz.kCGinvaderButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, e)

def get_position():
    """ Returns the invader's location as a tuple of (x, y). """
    e = Quartz.CGEventCreate(None)
    point = Quartz.CGEventGetLocation(e)
    return (point.x, point.y)