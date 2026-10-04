from dataclasses import dataclass
from tkinter import Entry, Label

from rc10_api.source.features.gui.custom_button import _CustomButton


@dataclass
class Binding:
    name: str
    button: _CustomButton | None


class Bindings:
    j0_max: Binding
    j0_min: Binding
    j1_max: Binding
    j1_min: Binding
    j2_max: Binding
    j2_min: Binding
    j3_max: Binding
    j3_min: Binding
    j4_max: Binding
    j4_min: Binding
    j5_max: Binding
    j5_min: Binding

    x_max: Binding
    x_min: Binding
    y_max: Binding
    y_min: Binding
    z_max: Binding
    z_min: Binding

    rx_max: Binding
    rx_min: Binding
    ry_max: Binding
    ry_min: Binding
    rz_max: Binding
    rz_min: Binding

    ctrl_j_c: Binding
    ctrl_l_c: Binding

    move: Binding

    free_drive: Binding


@dataclass
class CoordinateEntryGroup:
    entries: tuple[Entry, ...] = None
    move_btn: _CustomButton = None
    shift_btn: _CustomButton = None


@dataclass
class RTDGroup:
    name: str
    type_: str
    labels: tuple[Label, ...] = None
    copy_btn: _CustomButton = None
    paste_btn: _CustomButton = None
