from __future__ import annotations
from tkinter import (
    CENTER, Checkbutton, Entry, Frame, IntVar, Label, PhotoImage, Scale, Tk,
    font, ttk
)

from rc10_api.source.ap_interface.motion.coordinate_system import CoordinateSystem
from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.features.gui.bindings import CoordinateEntryGroup, RTDGroup
from rc10_api.source.features.gui.custom_button import _CustomButton
from rc10_api.source.models.classes.enum_classes.various_types import (
    AngleUnitTypes, GUICoordinateSystem, MotionTypes
)
from rc10_api.source.models.constants import JOINTS_COUNT


validate_gui_entry = validation.validate_gui_entry


class _WindowUI:
    rotation_frame: Frame
    movement_frame: Frame
    motor_frame: Frame
    coordinate_system_frame: Frame
    orientation_units_frame: Frame
    speed_scale_frame: Frame
    offset_entry_frame: Frame
    coordinate_entry_frame: Frame
    rtd_frame: Frame
    free_drive_frame: Frame

    rz_max_btn: _CustomButton
    rz_min_btn: _CustomButton
    ry_max_btn: _CustomButton
    ry_min_btn: _CustomButton
    rx_max_btn: _CustomButton
    rx_min_btn: _CustomButton
    z_max_btn: _CustomButton
    z_min_btn: _CustomButton
    y_max_btn: _CustomButton
    y_min_btn: _CustomButton
    x_max_btn: _CustomButton
    x_min_btn: _CustomButton

    j0_min_btn: _CustomButton
    j0_max_btn: _CustomButton
    j1_min_btn: _CustomButton
    j1_max_btn: _CustomButton
    j2_min_btn: _CustomButton
    j2_max_btn: _CustomButton
    j3_min_btn: _CustomButton
    j3_max_btn: _CustomButton
    j4_min_btn: _CustomButton
    j4_max_btn: _CustomButton
    j5_min_btn: _CustomButton
    j5_max_btn: _CustomButton

    q0_label: Label
    q1_label: Label
    q2_label: Label
    q3_label: Label
    q4_label: Label
    q5_label: Label

    x0_label: Label
    x1_label: Label
    x2_label: Label
    x3_label: Label
    x4_label: Label
    x5_label: Label

    q_copy_btn: _CustomButton
    x_copy_btn: _CustomButton
    tmp_btn: _CustomButton
    free_drive_btn: _CustomButton
    move_btn: _CustomButton
    label: Label

    coordinate_system_combobox: ttk.Combobox
    orientation_units_combobox: ttk.Combobox

    free_drive_switch: Checkbutton

    entry: Entry

    speed_scale: Scale

    def __init__(
        self,
        main_window: Tk,
        coordinate_system: CoordinateSystem | None
    ):
        main_window.title('RC simple JOG')
        main_window.resizable(False, False)
        main_window.configure(bg='#e9e9e9')
        self.spacer_image = PhotoImage()
        self.move_entry_group: CoordinateEntryGroup = None
        self.offset_entry_group: CoordinateEntryGroup = None
        self.rtd_groups: list[RTDGroup] = []
        self.coordinate_system = coordinate_system

        # ---------------- Body
        self.main_frame = Frame(main_window, padx=20, pady=20, bg='#fbfbfb')
        self.main_frame.pack(
            expand=True,
            fill='both',
            side='right',
            padx=(10, 10),
            pady=(10, 10)
        )

        label = Label(
            self.main_frame,
            bg='#fbfbfb',
            text='Положение сочленения',
            fg='#3c3f41'
        )
        label.grid(row=1, column=1, columnspan=3, sticky='n')
        self.motor_frame = Frame(
            self.main_frame,
            bg='#e9e9e9',
            borderwidth=0,
            relief='solid',
            padx=2,
            pady=2
        )
        self.motor_frame.grid(
            row=2, rowspan=7, column=1, columnspan=3, sticky='n'
        )

        spacer = Label(
            self.main_frame,
            image=self.spacer_image,
            compound=CENTER,
            width=40,
            height=288,
            bg='#fbfbfb'
        )
        spacer.grid(row=2, rowspan=7, column=4, sticky='n')

        label = Label(
            self.main_frame, bg='#fbfbfb', text='Перемещение', fg='#3c3f41'
        )
        label.grid(row=1, column=5, columnspan=3, sticky='n')
        self.movement_frame = Frame(
            self.main_frame, bg='#e9e9e9', borderwidth=0, padx=2, pady=2
        )
        self.movement_frame.grid(
            row=2, rowspan=3, column=5, columnspan=3, sticky='n'
        )

        label = Label(
            self.main_frame, bg='#fbfbfb', text='Вращение', fg='#3c3f41'
        )
        label.grid(row=1, column=9, columnspan=3, sticky='n')
        self.rotation_frame = Frame(
            self.main_frame, bg='#e9e9e9', borderwidth=0, padx=2, pady=2
        )
        self.rotation_frame.grid(
            row=2, rowspan=3, column=9, columnspan=1, sticky='n'
        )

        label = Label(
            self.main_frame,
            bg='#fbfbfb',
            text='Система координат:',
            fg='#3c3f41'
        )
        label.grid(row=8, column=1, columnspan=2, sticky='w')
        self.coordinate_system_frame = Frame(
            self.main_frame, bg='#fbfbfb', borderwidth=0
        )
        self.coordinate_system_frame.grid(
            row=8, column=3, columnspan=1, sticky='e',
        )

        label = Label(
            self.main_frame,
            bg='#fbfbfb',
            text='Единицы измерения:',
            fg='#3c3f41'
        )
        label.grid(row=9, column=1, columnspan=2, sticky='e')
        self.orientation_units_frame = Frame(
            self.main_frame, bg='#fbfbfb', borderwidth=0
        )
        self.orientation_units_frame.grid(
            row=9, column=3, columnspan=1, sticky='e',
        )

        label = Label(
            self.main_frame,
            bg='#fbfbfb',
            text='Скорость:',
            fg='#3c3f41'
        )
        label.grid(row=10, column=1, columnspan=2, sticky='w')
        self.speed_scale_frame = Frame(
            self.main_frame, bg='#fbfbfb', borderwidth=0
        )
        self.speed_scale_frame.grid(row=10, column=3, columnspan=1, pady=10)

        self.offset_entry_frame = Frame(
            self.main_frame, bg='#fbfbfb', borderwidth=0
        )
        self.offset_entry_frame.grid(
            row=5, rowspan=1, column=4, columnspan=7, sticky='s', padx=(45, 0)
        )

        self.coordinate_entry_frame = Frame(
            self.main_frame, bg='#fbfbfb', borderwidth=0
        )
        self.coordinate_entry_frame.grid(
            row=7, rowspan=1, column=4, columnspan=7, sticky='s', padx=(45, 0)
        )

        self.rtd_frame = Frame(self.main_frame, bg='#fbfbfb', borderwidth=0)
        self.rtd_frame.grid(
            row=9, rowspan=4, column=5, columnspan=8, sticky='s'
        )

        spacer = Label(
            self.main_frame,
            image=self.spacer_image,
            compound=CENTER,
            width=40,
            height=40,
            bg='#fbfbfb'
        )
        spacer.grid(row=2, column=12, rowspan=4, sticky='n')

        self.free_drive_frame = Frame(
            self.main_frame, bg='#e9e9e9', borderwidth=0, padx=2, pady=2
        )
        self.free_drive_frame.grid(
            row=2, rowspan=6, column=13, columnspan=2, sticky='n'
        )

        self.set_joint_buttons()
        self.set_movement_joystick()
        self.set_rotation_joystick()
        self.set_coordinate_system()
        self.set_orientation_units()
        self.set_speed_scale()
        self.set_offset_entry()
        self.set_move_entry()
        self.set_rtd()
        self.set_free_drive_btn()

    def set_joint_buttons(self):
        # Buttons
        joint_font = font.Font(size=10)
        self.j0_min_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#4e7ada',
            text='➖'
        )
        self.j0_min_btn.grid(row=1, column=1, padx=2, pady=2)
        label = Label(
            self.motor_frame,
            font=joint_font,
            text='Основание',
            image=self.spacer_image,
            compound=CENTER,
            width=90,
            height=40,
            bg='#fbfbfb',
            fg='#3c3f41',
            borderwidth=1
        )
        label.grid(row=1, column=2, padx=2, pady=2)
        self.j0_max_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#db5c42',
            text='➕'
        )
        self.j0_max_btn.grid(row=1, column=3, padx=2, pady=2)
        self.j1_min_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#4e7ada',
            width=35,
            height=35,
            text='➖'
        )
        self.j1_min_btn.grid(row=2, column=1, padx=2, pady=2)
        label = Label(
            self.motor_frame,
            text='Плечо',
            font=joint_font,
            image=self.spacer_image,
            compound=CENTER,
            width=90,
            height=40,
            bg='#fbfbfb',
            fg='#3c3f41',
            borderwidth=1
        )
        label.grid(row=2, column=2, padx=2, pady=2)
        self.j1_max_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#db5c42',
            width=35,
            height=35,
            text='➕'
        )
        self.j1_max_btn.grid(row=2, column=3, padx=2, pady=2)
        self.j2_min_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#4e7ada',
            text='➖'
        )
        self.j2_min_btn.grid(row=3, column=1, padx=2, pady=2)
        label = Label(
            self.motor_frame,
            font=joint_font,
            text='Локоть',
            image=self.spacer_image,
            compound=CENTER,
            width=90,
            height=40,
            bg='#fbfbfb',
            fg='#3c3f41',
            borderwidth=1
        )
        label.grid(row=3, column=2, padx=2, pady=2)
        self.j2_max_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#db5c42',
            text='➕'
        )
        self.j2_max_btn.grid(row=3, column=3, padx=2, pady=2)
        self.j3_min_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#4e7ada',
            text='➖\n'
        )
        self.j3_min_btn.grid(row=4, column=1, padx=2, pady=2)
        label = Label(
            self.motor_frame,
            font=joint_font,
            text='Запястье 1',
            image=self.spacer_image,
            compound=CENTER,
            width=90,
            height=40,
            bg='#fbfbfb',
            fg='#3c3f41',
            borderwidth=1
        )
        label.grid(row=4, column=2, padx=2, pady=2)
        self.j3_max_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#db5c42',
            text='➕'
        )
        self.j3_max_btn.grid(row=4, column=3, padx=2, pady=2)
        self.j4_min_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#4e7ada',
            text='➖'
        )
        self.j4_min_btn.grid(row=5, column=1, padx=2, pady=2)
        label = Label(
            self.motor_frame,
            font=joint_font,
            text='Запястье 2',
            image=self.spacer_image,
            compound=CENTER,
            width=90,
            height=40,
            bg='#fbfbfb',
            fg='#3c3f41',
            borderwidth=1
        )
        label.grid(row=5, column=2, padx=2, pady=2)
        self.j4_max_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#db5c42',
            text='➕'
        )
        self.j4_max_btn.grid(row=5, column=3, padx=2, pady=2)
        self.j5_min_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#4e7ada',
            text='➖'
        )
        self.j5_min_btn.grid(row=6, column=1, padx=2, pady=2)
        label = Label(
            self.motor_frame,
            font=joint_font,
            text='Запястье 3',
            image=self.spacer_image,
            compound=CENTER,
            width=90,
            height=40,
            bg='#fbfbfb',
            fg='#3c3f41',
            borderwidth=1
        )
        label.grid(row=6, column=2, padx=2, pady=2)
        self.j5_max_btn = _CustomButton(
            self.motor_frame,
            repeat_sig=True,
            fg='#db5c42',
            text='➕'
        )
        self.j5_max_btn.grid(row=6, column=3, padx=2, pady=2)

    def set_movement_joystick(self):
        # Buttons
        self.z_max_btn = _CustomButton(
            self.movement_frame,
            repeat_sig=True,
            fg='#4e7ada',
            text='Z ➕'
        )
        self.z_max_btn.grid(row=1, column=3, padx=2, pady=2)
        self.z_min_btn = _CustomButton(
            self.movement_frame,
            repeat_sig=True,
            fg='#4e7ada',
            text='Z ➖'
        )
        self.z_min_btn.grid(row=1, column=1, padx=2, pady=2)
        self.y_max_btn = _CustomButton(
            self.movement_frame,
            repeat_sig=True,
            fg='#72b043',
            text='Y ➕'
        )
        self.y_max_btn.grid(row=2, column=3, padx=2, pady=2)
        self.y_min_btn = _CustomButton(
            self.movement_frame,
            repeat_sig=True,
            fg='#72b043',
            text='Y ➖'
        )
        self.y_min_btn.grid(row=2, column=1, padx=2, pady=2)
        self.x_max_btn = _CustomButton(
            self.movement_frame,
            repeat_sig=True,
            fg='#db5c42',
            text='X ➕'
        )
        self.x_max_btn.grid(row=1, column=2, padx=2, pady=2)
        self.x_min_btn = _CustomButton(
            self.movement_frame,
            repeat_sig=True,
            fg='#db5c42',
            text='X ➖'
        )
        self.x_min_btn.grid(row=3, column=2, padx=2, pady=2)
        spacer = Label(
            self.movement_frame,
            image=self.spacer_image,
            compound=CENTER,
            width=40,
            height=40,
            bg='#fbfbfb'
        )
        spacer.grid(row=3, column=1, padx=2, pady=2)
        spacer = Label(
            self.movement_frame,
            image=self.spacer_image,
            compound=CENTER,
            width=40,
            height=40,
            bg='#fbfbfb'
        )
        spacer.grid(row=2, column=2, padx=2, pady=2)
        spacer = Label(
            self.movement_frame,
            image=self.spacer_image,
            compound=CENTER,
            width=40,
            height=40,
            bg='#fbfbfb'
        )
        spacer.grid(row=3, column=3, padx=2, pady=2)

    def set_rotation_joystick(self):
        # Buttons
        self.rz_max_btn = _CustomButton(
            self.rotation_frame,
            repeat_sig=True,
            fg='#4e7ada',
            text='RZ ➕'
        )
        self.rz_max_btn.grid(row=1, column=3, padx=2, pady=2)
        self.rz_min_btn = _CustomButton(
            self.rotation_frame,
            repeat_sig=True,
            fg='#4e7ada',
            text='RZ ➖'
        )
        self.rz_min_btn.grid(row=1, column=1, padx=2, pady=2)
        self.ry_max_btn = _CustomButton(
            self.rotation_frame,
            repeat_sig=True,
            fg='#72b043',
            text='RY ➕'
        )
        self.ry_max_btn.grid(row=2, column=3, padx=2, pady=2)
        self.ry_min_btn = _CustomButton(
            self.rotation_frame,
            repeat_sig=True,
            fg='#72b043',
            text='RY ➖'
        )
        self.ry_min_btn.grid(row=2, column=1, padx=2, pady=2)
        self.rx_max_btn = _CustomButton(
            self.rotation_frame,
            repeat_sig=True,
            fg='#db5c42',
            text='RX ➕'
        )
        self.rx_max_btn.grid(row=1, column=2, padx=2, pady=2)
        self.rx_min_btn = _CustomButton(
            self.rotation_frame,
            repeat_sig=True,
            fg='#db5c42',
            text='RX ➖'
        )
        self.rx_min_btn.grid(row=3, column=2, padx=2, pady=2)
        spacer = Label(
            self.rotation_frame,
            image=self.spacer_image,
            compound=CENTER,
            width=40,
            height=40,
            bg='#fbfbfb'
        )
        spacer.grid(row=3, column=1, padx=2, pady=2)
        spacer = Label(
            self.rotation_frame,
            image=self.spacer_image,
            compound=CENTER,
            width=40,
            height=40,
            bg='#fbfbfb'
        )
        spacer.grid(row=2, column=2, padx=2, pady=2)
        spacer = Label(
            self.rotation_frame,
            image=self.spacer_image,
            compound=CENTER,
            width=40,
            height=40,
            bg='#fbfbfb'
        )
        spacer.grid(row=3, column=3, padx=2, pady=2)

    def set_free_drive_btn(self):
        self.free_drive_btn = _CustomButton(
            self.free_drive_frame,
            repeat_sig=True,
            fg='#4e7ada',
            height=320,
            width=92,
            text='С\nВ\nО\nБ\nО\nД\nН\nЫ\nЙ\n\nП\nР\nИ\nВ\nО\nД'
        )
        self.free_drive_btn.grid(row=1, column=1, padx=2, pady=2)
        self.enabled = IntVar()
        self.free_drive_switch = Checkbutton(
            self.free_drive_frame,
            text='Зафиксировать',
            variable=self.enabled
        )
        self.free_drive_switch.grid(row=7, column=1, rowspan=2)

    def set_coordinate_system(self):
        combobox_values = (
            [
                GUICoordinateSystem.GLOBAL.value,
                GUICoordinateSystem.LOCAL.value,
                GUICoordinateSystem.CTI.value
            ]
            if self.coordinate_system else [
                GUICoordinateSystem.GLOBAL.value, GUICoordinateSystem.CTI.value
            ]
        )
        self.coordinate_system_combobox = ttk.Combobox(
            self.coordinate_system_frame,
            font=font.Font(size=10),
            values=combobox_values
        )
        self.coordinate_system_combobox.grid(
            row=1, column=1, columnspan=1, padx=10
        )
        self.coordinate_system_combobox.set(combobox_values[0])

    def set_orientation_units(self):
        self.orientation_units_combobox = ttk.Combobox(
            self.orientation_units_frame,
            font=font.Font(size=10),
            values=[AngleUnitTypes.DEG.value, AngleUnitTypes.RAD.value]
        )
        self.orientation_units_combobox.grid(
            row=1, column=1, columnspan=1, padx=10
        )
        self.orientation_units_combobox.set(AngleUnitTypes.DEG)

    def set_speed_scale(self):
        self.speed_scale = Scale(
            self.speed_scale_frame,
            activebackground='#1e90ff',
            bg='#fbfbfb',
            fg='#3c3f41',
            orient='horizontal',
            length=200,
            from_=0.01,
            to=1.0,
            resolution=0.01
        )
        self.speed_scale.grid(row=1, column=1, columnspan=4)
        self.speed_scale.set(0.1)

    def set_offset_entry(self):
        label = Label(
            self.offset_entry_frame,
            bg='#fbfbfb',
            text='Координаты для смещения ( м )',
            fg='#3c3f41'
        )
        label.grid(
            row=1, rowspan=1, column=1, columnspan=7, sticky='w', pady=(20, 0)
        )
        frame = Frame(
            self.offset_entry_frame,
            bg='#e9e9e9',
            borderwidth=0,
            padx=2,
            pady=6
        )
        frame.grid(row=2, column=1, columnspan=7, sticky='w')

        entries = []
        validate_symbols = self.main_frame.register(validate_gui_entry)
        offset_entry_group = CoordinateEntryGroup()
        for j in range(1, JOINTS_COUNT + 1):
            entry = Entry(
                frame,
                bg='#fbfbfb',
                fg='#3c3f41',
                borderwidth=1,
                font=font.Font(size=7),
                width=8,
                validate='key',
                validatecommand=(validate_symbols, '%P')
            )
            entry.insert(0, '0')
            entry.grid(row=2, column=j, padx=2, pady=2, ipady=5)
            entries.append(entry)
        self.shift_btn = _CustomButton(
                frame,
                repeat_sig=False,
                width=80,
                height=20,
                fg='#4e7ada',
                text='Сместить',
                anchor=CENTER
            )
        self.shift_btn.grid(row=2, column=7, padx=2, pady=2)
        offset_entry_group.entries = tuple(entries)
        offset_entry_group.shift_btn = self.shift_btn
        self.offset_entry_group = offset_entry_group

    def set_move_entry(self):
        label = Label(
            self.coordinate_entry_frame,
            bg='#fbfbfb',
            text='Координаты для перемещения ( м )',
            fg='#3c3f41'
        )
        label.grid(
            row=1, rowspan=1, column=1, columnspan=7, sticky='w'
        )
        frame = Frame(
            self.coordinate_entry_frame,
            bg='#e9e9e9',
            borderwidth=0,
            padx=2,
            pady=6
        )
        frame.grid(row=2, column=1, columnspan=7, sticky='w')

        entries = []
        validate_symbols = self.main_frame.register(validate_gui_entry)
        move_entry_group = CoordinateEntryGroup()
        for j in range(1, JOINTS_COUNT + 1):
            entry = Entry(
                frame,
                bg='#fbfbfb',
                fg='#3c3f41',
                borderwidth=1,
                font=font.Font(size=7),
                width=8,
                validate='key',
                validatecommand=(validate_symbols, '%P')
            )
            entry.grid(row=2, column=j, padx=2, pady=2, ipady=5)
            entries.append(entry)
        self.move_btn = _CustomButton(
                frame,
                repeat_sig=False,
                width=80,
                height=20,
                fg='#4e7ada',
                text='Переместить',
                anchor=CENTER
            )
        self.move_btn.grid(row=2, column=7, padx=2, pady=2)
        move_entry_group.entries = tuple(entries)
        move_entry_group.move_btn = self.move_btn
        self.move_entry_group = move_entry_group

    def set_rtd(self):
        for i in range(0, 4, 2):
            rtd_group = RTDGroup(
                name='Углы поворотов моторов'
                if i == 0 else 'Положение ЦТИ ( м )',
                type_=MotionTypes.JOINT
                if i == 0 else MotionTypes.LINEAR
            )
            labels = []
            label = Label(
                self.rtd_frame, bg='#fbfbfb', text=rtd_group.name, fg='#3c3f41'
            )
            label.grid(
                row=i,
                column=1,
                sticky='w',
                padx=(0 if i == 2 else 20),
                pady=(15 if i == 2 else 0, 0)
            )
            frame = Frame(
                self.rtd_frame, bg='#e9e9e9', borderwidth=0, padx=2, pady=2
            )
            frame.grid(row=i+1, column=1, columnspan=7 if i == 2 else 6)
            for j in range(JOINTS_COUNT):
                label = Label(
                    frame,
                    text='-000.000',
                    image=self.spacer_image,
                    compound=CENTER,
                    width=55,
                    height=20,
                    bg='#fbfbfb',
                    fg='#3c3f41',
                    borderwidth=1,
                    anchor=CENTER,
                    font=font.Font(size=7)
                )
                label.grid(row=1, column=j, padx=2, pady=2)
                labels.append(label)
            copy_btn = _CustomButton(
                frame,
                font=font.Font(size=9),
                repeat_sig=False,
                width=60,
                height=20,
                fg='#4e7ada',
                text='Копировать',
                anchor=CENTER
            )
            if i == 2:
                paste_btn = _CustomButton(
                    frame,
                    font=font.Font(size=9),
                    repeat_sig=False,
                    width=60,
                    height=20,
                    fg='#4e7ada',
                    text=' Вставить',
                    anchor=CENTER
                )
                paste_btn.grid(row=1, column=8, padx=2, pady=2)
                rtd_group.paste_btn = paste_btn
            copy_btn.grid(row=1, column=7, padx=2, pady=2)
            rtd_group.labels = tuple(labels)
            rtd_group.copy_btn = copy_btn
            self.rtd_groups.append(rtd_group)
