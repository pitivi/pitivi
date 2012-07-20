import os
from dogtail.predicate import GenericPredicate
import dogtail.rawinput
from time import sleep


def improved_drag(fromcord, tocord, middle=[], absolute=True, moveAround=True):
    dogtail.rawinput.press(fromcord[0], fromcord[1])
    if moveAround:
        dogtail.rawinput.relativeMotion(5, 5)
        dogtail.rawinput.relativeMotion(-5, -5)
    if absolute:
        fun = dogtail.rawinput.absoluteMotion
    else:
        fun = dogtail.rawinput.relativeMotion
    for mid in middle:
        fun(mid[0], mid[1])
        if moveAround:
            dogtail.rawinput.relativeMotion(5, 5)
            dogtail.rawinput.relativeMotion(-5, -5)
    dogtail.rawinput.absoluteMotion(tocord[0], tocord[1])
    if moveAround:
        dogtail.rawinput.relativeMotion(5, 5)
        dogtail.rawinput.relativeMotion(-5, -5)
    dogtail.rawinput.release(tocord[0], tocord[1])
