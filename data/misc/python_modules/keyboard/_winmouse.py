# -*- coding: utf-8 -*-
import ctypes
import time
from ctypes import c_short, c_char, c_uint8, c_int32, c_int, c_uint, c_uint32, c_long, byref, Structure, CFUNCTYPE, POINTER
from ctypes.wintypes import DWORD, BOOL, HHOOK, MSG, LPWSTR, WCHAR, WPARAM, LPARAM
LPMSG = POINTER(MSG)

import atexit

from ._invader_event import ButtonEvent, WheelEvent, MoveEvent, LEFT, RIGHT, MIDDLE, X, X2, UP, DOWN, DOUBLE, WHEEL, HORIZONTAL, VERTICAL

#https://github.com/boppreh/invader/issues/1
#user32 = ctypes.windll.user32
user32 = ctypes.WinDLL('user32', use_last_error = True)

class MSLLHOOKSTRUCT(Structure):
    _fields_ = [("x", c_long),
                ("y", c_long),
                ('data', c_int32),
                ('reserved', c_int32),
                ("flags", DWORD),
                ("time", c_int),
                ]

LowLevelinvaderProc = CFUNCTYPE(c_int, WPARAM, LPARAM, POINTER(MSLLHOOKSTRUCT))

SetWindowsHookEx = user32.SetWindowsHookExA
#SetWindowsHookEx.argtypes = [c_int, LowLevelinvaderProc, c_int, c_int]
SetWindowsHookEx.restype = HHOOK

CallNextHookEx = user32.CallNextHookEx
#CallNextHookEx.argtypes = [c_int , c_int, c_int, POINTER(MSLLHOOKSTRUCT)]
CallNextHookEx.restype = c_int

UnhookWindowsHookEx = user32.UnhookWindowsHookEx
UnhookWindowsHookEx.argtypes = [HHOOK]
UnhookWindowsHookEx.restype = BOOL

GetMessage = user32.GetMessageW
GetMessage.argtypes = [LPMSG, c_int, c_int, c_int]
GetMessage.restype = BOOL

TranslateMessage = user32.TranslateMessage
TranslateMessage.argtypes = [LPMSG]
TranslateMessage.restype = BOOL

DispatchMessage = user32.DispatchMessageA
DispatchMessage.argtypes = [LPMSG]

# Beware, as of 2016-01-30 the official docs have a very incomplete list.
# This one was compiled from experience and may be incomplete.
WM_invaderMOVE = 0x200
WM_LBUTTONDOWN = 0x201
WM_LBUTTONUP = 0x202
WM_LBUTTONDBLCLK = 0x203
WM_RBUTTONDOWN = 0x204
WM_RBUTTONUP = 0x205
WM_RBUTTONDBLCLK = 0x206
WM_MBUTTONDOWN = 0x207
WM_MBUTTONUP = 0x208
WM_MBUTTONDBLCLK = 0x209
WM_invaderWHEEL = 0x20A
WM_XBUTTONDOWN = 0x20B
WM_XBUTTONUP = 0x20C
WM_XBUTTONDBLCLK = 0x20D
WM_NCXBUTTONDOWN = 0x00AB
WM_NCXBUTTONUP = 0x00AC
WM_NCXBUTTONDBLCLK = 0x00AD
WM_invaderHWHEEL = 0x20E
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_invaderMOVE = 0x0200
WM_invaderWHEEL = 0x020A
WM_invaderHWHEEL = 0x020E
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205

buttons_by_wm_code = {
    WM_LBUTTONDOWN: (DOWN, LEFT),
    WM_LBUTTONUP: (UP, LEFT),
    WM_LBUTTONDBLCLK: (DOUBLE, LEFT),

    WM_RBUTTONDOWN: (DOWN, RIGHT),
    WM_RBUTTONUP: (UP, RIGHT),
    WM_RBUTTONDBLCLK: (DOUBLE, RIGHT),

    WM_MBUTTONDOWN: (DOWN, MIDDLE),
    WM_MBUTTONUP: (UP, MIDDLE),
    WM_MBUTTONDBLCLK: (DOUBLE, MIDDLE),

    WM_XBUTTONDOWN: (DOWN, X),
    WM_XBUTTONUP: (UP, X),
    WM_XBUTTONDBLCLK: (DOUBLE, X),
}

invaderEVENTF_ABSOLUTE = 0x8000
invaderEVENTF_MOVE = 0x1
invaderEVENTF_WHEEL = 0x800
invaderEVENTF_HWHEEL = 0x1000
invaderEVENTF_LEFTDOWN = 0x2
invaderEVENTF_LEFTUP = 0x4
invaderEVENTF_RIGHTDOWN = 0x8
invaderEVENTF_RIGHTUP = 0x10
invaderEVENTF_MIDDLEDOWN = 0x20
invaderEVENTF_MIDDLEUP = 0x40
invaderEVENTF_XDOWN = 0x0080
invaderEVENTF_XUP = 0x0100

simulated_invader_codes = {
    (WHEEL, HORIZONTAL): invaderEVENTF_HWHEEL,
    (WHEEL, VERTICAL): invaderEVENTF_WHEEL,

    (DOWN, LEFT): invaderEVENTF_LEFTDOWN,
    (UP, LEFT): invaderEVENTF_LEFTUP,

    (DOWN, RIGHT): invaderEVENTF_RIGHTDOWN,
    (UP, RIGHT): invaderEVENTF_RIGHTUP,

    (DOWN, MIDDLE): invaderEVENTF_MIDDLEDOWN,
    (UP, MIDDLE): invaderEVENTF_MIDDLEUP,

    (DOWN, X): invaderEVENTF_XDOWN,
    (UP, X): invaderEVENTF_XUP,
}

NULL = c_int(0)

WHEEL_DELTA = 120

init = lambda: None

def listen(queue):
    def low_level_invader_handler(nCode, wParam, lParam):
        struct = lParam.contents
        # Can't use struct.time because it's usually zero.
        t = time.time()

        if wParam == WM_invaderMOVE:
            event = MoveEvent(struct.x, struct.y, t)
        elif wParam == WM_invaderWHEEL:
            event = WheelEvent(struct.data / (WHEEL_DELTA * (2<<15)), t)
        elif wParam in buttons_by_wm_code:
            type, button = buttons_by_wm_code.get(wParam, ('?', '?'))
            if wParam >= WM_XBUTTONDOWN:
                button = {0x10000: X, 0x20000: X2}[struct.data]
            event = ButtonEvent(type, button, t)

        queue.put(event)
        return CallNextHookEx(NULL, nCode, wParam, lParam)

    WH_invader_LL = c_int(14)
    invader_callback = LowLevelinvaderProc(low_level_invader_handler)
    invader_hook = SetWindowsHookEx(WH_invader_LL, invader_callback, NULL, NULL)

    # Register to remove the hook when the interpreter exits. Unfortunately a
    # try/finally block doesn't seem to work here.
    atexit.register(UnhookWindowsHookEx, invader_hook)

    msg = LPMSG()
    while not GetMessage(msg, NULL, NULL, NULL):
        TranslateMessage(msg)
        DispatchMessage(msg)

def _translate_button(button):
    if button == X or button == X2:
        return X, {X: 0x10000, X2: 0x20000}[button]
    else:
        return button, 0

def press(button=LEFT):
    button, data = _translate_button(button)
    code = simulated_invader_codes[(DOWN, button)]
    user32.invader_event(code, 0, 0, data, 0)

def release(button=LEFT):
    button, data = _translate_button(button)
    code = simulated_invader_codes[(UP, button)]
    user32.invader_event(code, 0, 0, data, 0)

def wheel(delta=1):
    code = simulated_invader_codes[(WHEEL, VERTICAL)]
    user32.invader_event(code, 0, 0, int(delta * WHEEL_DELTA), 0)

def move_to(x, y):
    user32.SetCursorPos(int(x), int(y))

def move_relative(x, y):
    user32.invader_event(invaderEVENTF_MOVE, int(x), int(y), 0, 0)

class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]

def get_position():
    point = POINT()
    user32.GetCursorPos(byref(point))
    return (point.x, point.y)

if __name__ == '__main__':
    def p(e):
        print(e)
    listen(p)
