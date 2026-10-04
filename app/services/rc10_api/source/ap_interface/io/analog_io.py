from __future__ import annotations
from struct import pack
from typing import TYPE_CHECKING

from rc10_api.source.features.tools import sleep
from rc10_api.source.models.classes.data_classes.command_templates import (
    SetOutputTemplate
)
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    Setters as Set
)
from rc10_api.source.models.classes.enum_classes.various_types import PowerUnitsCode
from rc10_api.source.models.constants import (
    AMPERAGE_VALUES_RANGE, CHECK_FREQUENCY_SEC, CTRLR_IO_SET_VALUE_PACK_FORMAT,
    AVAILABLE_AN_IN_INDEX_COUNT, AVAILABLE_AN_OUT_INDEX_COUNT,
    VOLTAGE_INPUT_INDEXES_RANGE, VOLTAGE_VALUES_RANGE
)
from rc10_api.source.models.type_aliases import (
    AnalogIndex, CompareSigns, PowerUnits
)
from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.features.tools import dataclass_to_tuple

if TYPE_CHECKING:
    from logging import Logger

    from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver
    from rc10_api.source.core.network.controller_socket import Controller


validate_index = validation.validate_index
validate_literal = validation.validate_literal
validate_value = validation.validate_value


class AnalogIO:
    _controller: Controller
    _rtd_receiver: RTDReceiver
    _logger: Logger

    def __init__(
        self, controller: Controller, rtd_receiver: RTDReceiver, logger: Logger
    ):

        self._controller = controller
        self._rtd_receiver = rtd_receiver
        self._logger = logger

    def get_input(self, index: AnalogIndex) -> tuple[int, float]:
        """
        Получить текущее значение силы тока / напряжения на 'index' аналоговом
        входе.

        Args:
            index: Индекс входа (0-3).
                (0-1) - индексы входов, отвечающих за напряжение (V).
                (2-3) - индексы входов, отвечающих за силу тока (мА).
        Returns:
            tuple: Индекс входа и его значение.
        """

        validate_index(index, range(AVAILABLE_AN_IN_INDEX_COUNT))
        return index, self._rtd_receiver.rt_data.an_in_value[index]

    def set_output(self, index: int, value: float, units: PowerUnits) -> bool:
        """
        Установить взаимоисключающее значение силы тока / напряжения на
        определенный выход.
        Тип устанавливаемого значения зависит от переменной units.

        Args:
            index: Индекс выхода (0-3).
            value: Значение силы тока (4 — 20 мА) / напряжения (0 — 10 В).
            units: Единицы измерения. 'mA' - сила тока. 'V' - напряжение.
        Returns:
            True: В случае успешной отправки команды.
        """

        validate_literal('power', units)
        validate_index(index, range(AVAILABLE_AN_OUT_INDEX_COUNT))
        validate_value(
            value,
            AMPERAGE_VALUES_RANGE if units == 'mA' else VOLTAGE_VALUES_RANGE
        )
        set_output_template = SetOutputTemplate()
        set_output_template.an_out_mask[index] = 1
        set_output_template.an_out_curr_mode[index] = PowerUnitsCode[units]
        set_output_template.an_out_value[index] = value
        return self._controller.send(
            Set.ctrlr_coms_set_outputs,
            pack(
                CTRLR_IO_SET_VALUE_PACK_FORMAT,
                *dataclass_to_tuple(set_output_template)
            )
        )

    def wait_input(
        self,
        index: AnalogIndex,
        threshold_value: float,
        greater_or_less: CompareSigns,
        await_sec: int = -1
    ) -> bool:
        """
        Ожидать преодоление порогового значения на 'index' аналоговом входе.

        Args:
            index: Индекс входа (0 — 3).
                (0 — 1) — индексы входов, отвечающих за напряжение (В).
                (2 — 3) — индексы входов, отвечающих за силу тока (мА).
            threshold_value: Пороговое значение силы тока (4 — 20 мА)
                напряжения (0 — 10 В).
            greater_or_less: Устанавливает тип ожидания.
                '>' — ждать преодоления высокого порогового значения.
                '<' — ждать преодоления низкого порогового значения.
            await_sec: Лимит времени ожидания.
                -1 — безлимитное ожидание.
                0 — одна итерация цикла ожидания (эквивалентно разовому
                    условию).
        Returns:
            True: В случае преодоления порогового значения.
            False: В случае таймаута (если await_sec >= 0).
        Raises:
            ArgIndexError: При некорректно указанном индексе.
            ArgComparisonError: При некорректно указанном знаке сравнения.
        """

        validate_index(index, range(AVAILABLE_AN_IN_INDEX_COUNT))
        validate_value(
            threshold_value,
            VOLTAGE_VALUES_RANGE if index in range(VOLTAGE_INPUT_INDEXES_RANGE)
            else AMPERAGE_VALUES_RANGE
        )
        validate_literal('compare', greater_or_less)
        self._logger.info(f'Waiting analog signal on {index} input...')
        for _ in sleep(await_sec=await_sec, frequency=CHECK_FREQUENCY_SEC):
            match greater_or_less:
                case '<':
                    if self.get_input(index)[1] <= threshold_value:
                        self._logger.info(
                            (
                                f'Analog signal on {index}: '
                                f'{self.get_input(index)[1]} < '
                                f'{threshold_value}'
                            )
                        )
                        return True
                case '>':
                    if self.get_input(index)[1] >= threshold_value:
                        self._logger.info(
                            (
                                f'Analog signal on {index}: '
                                f'{self.get_input(index)[1]} > '
                                f'{threshold_value}'
                            )
                        )
                        return True
        self._logger.info(f'Analog signal on {index} input timeout')
        return False
