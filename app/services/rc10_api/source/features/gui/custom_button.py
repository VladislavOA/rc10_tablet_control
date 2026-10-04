from __future__ import annotations
from tkinter import Button, PhotoImage, Event
from typing import Callable


class _CustomButton(Button):
    def __init__(
        self,
        *args,
        repeat_sig: bool = False,
        width: int = 40,
        height: int = 40,
        **kwargs
    ):
        Button.__init__(self, *args, **kwargs)
        self.pressed = False
        self.func = None
        self.func_args = None
        self.release_func = None
        self.release_func_args = None
        self.repeat_sig = repeat_sig
        self.bind('<ButtonRelease>', self.set_released)
        self.bind('<ButtonPress>', self.set_pressed)
        self.image = PhotoImage(width=1, height=1)
        self.unpressed_fg = self.cget('fg')
        self.configure(
            bg='#fbfbfb',
            image=self.image,
            compound='center',
            width=width,
            height=height,
            borderwidth=0,
            relief='sunken',
            activeforeground='#fbfbfb',
            activebackground=self.cget('fg')
        )

    def is_pressed(self) -> bool:
        return self.pressed

    def set_pressed(self, _: Event = None) -> None:
        if not self.is_pressed():
            self.configure(fg='#fbfbfb', bg=self.cget('fg'))
            self.pressed = True
            self._generate_signal()

    def set_released(self, _: Event = None) -> None:
        if self.is_pressed():
            self.configure(fg=self.cget('bg'), bg='#fbfbfb')
            self.pressed = False
            if self.release_func:
                self.release_func(*self.release_func_args)

    def _generate_signal(self) -> None:
        if self.is_pressed():
            if self.func:
                self.func(*self.func_args)
            if self.repeat_sig:
                self.after(1, self._generate_signal)

    def connect(self, func: Callable, *args) -> _CustomButton:
        self.func = func
        self.func_args = args
        return self

    def connect_release(self, func: Callable, *args) -> _CustomButton:
        self.release_func = func
        self.release_func_args = args
        return self

    def switch_bind(self, bind: bool = False):
        if bind:
            self.bind('<ButtonRelease>', self.set_released)
            self.bind('<ButtonPress>', self.set_pressed)
        else:
            self.unbind('<ButtonRelease>')
            self.unbind('<ButtonPress>')

    def disconnect(self) -> None:
        self.func = None
