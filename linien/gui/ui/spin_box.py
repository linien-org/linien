# Copyright 2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien.
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

from PyQt5.QtWidgets import QDoubleSpinBox, QSpinBox


class CustomDoubleSpinBox(QDoubleSpinBox):
    """
    Custom spin box with improved keyboard controls with step size depending on the
    cursor position.
    """

    def textFromValue(self, value):
        # show + sign for positive values
        text = super().textFromValue(value)
        if value >= 0:
            text = "+" + text
        return text

    def stepBy(self, steps):
        cursor_position = self.lineEdit().cursorPosition()
        # number of characters before the decimal separator including +/- sign
        n_chars_before_sep = len(str(abs(int(self.value())))) + 1
        if cursor_position == 0:
            # set the cursor right of the +/- sign
            self.lineEdit().setCursorPosition(1)
            cursor_position = self.lineEdit().cursorPosition()
        single_step = 10 ** (n_chars_before_sep - cursor_position)
        # Handle decimal separator. Step should be 0.1 if cursor is at `1.|23` or
        # `1.2|3`.
        if cursor_position >= n_chars_before_sep + 2:
            single_step = 10 * single_step
        # Change single step and perform the step
        self.setSingleStep(single_step)
        super().stepBy(steps)
        # Undo selection of the whole text.
        self.lineEdit().deselect()
        # Handle cases where the number of characters before the decimal separator
        # changes. Step size should remain the same.
        new_n_chars_before_sep = len(str(abs(int(self.value())))) + 1
        if new_n_chars_before_sep < n_chars_before_sep:
            cursor_position -= 1
        elif new_n_chars_before_sep > n_chars_before_sep:
            cursor_position += 1
        self.lineEdit().setCursorPosition(cursor_position)


class CustomDoubleSpinBoxNoSign(QDoubleSpinBox):
    """
    Custom spin box with improved keyboard controls with step size depending on the
    cursor position.
    """

    def stepBy(self, steps):
        cursor_position = self.lineEdit().cursorPosition()
        # number of characters before the decimal separator
        n_chars_before_sep = len(str(abs(int(self.value()))))
        n_chars_before_sep_max = len(str(abs(int(self.maximum()))))
        exponent = min(
            [n_chars_before_sep - cursor_position, n_chars_before_sep_max - 1]
        )
        single_step = 10**exponent
        # Handle decimal separator. Step should be 0.1 if cursor is at `1.|23` or
        # `1.2|3`.
        if cursor_position >= n_chars_before_sep + 2:
            single_step = 10 * single_step
        # Change single step and perform the step
        self.setSingleStep(single_step)
        super().stepBy(steps)
        # Undo selection of the whole text.
        self.lineEdit().deselect()
        # Handle cases where the number of characters before the decimal separator
        # changes. Step size should remain the same.
        new_n_chars_before_sep = len(str(abs(int(self.value()))))
        if new_n_chars_before_sep < n_chars_before_sep:
            cursor_position -= 1
        elif new_n_chars_before_sep > n_chars_before_sep:
            cursor_position += 1
        self.lineEdit().setCursorPosition(cursor_position)


class CustomSpinBox(QSpinBox):
    """
    Custom spin box with improved keyboard controls with step size depending on the
    cursor position. Works for positive integers only.
    """

    def stepBy(self, steps):
        n_chars = len(str(self.value()))  # number of characters of the current value
        n_chars_max = len(str(self.maximum()))  # number of characters of the maximum
        cursor_position = self.lineEdit().cursorPosition()
        exponent = min([n_chars - cursor_position, n_chars_max - 1])
        single_step = 10**exponent
        self.setSingleStep(single_step)
        super().stepBy(steps)
        # Undo selection of the whole text.
        self.lineEdit().deselect()
        # Handle cases where the number of characters before the decimal separator
        # changes. Step size should remain the same.
        new_n_chars = len(str(self.value()))
        if new_n_chars < n_chars:
            cursor_position -= 1
        elif new_n_chars > n_chars:
            cursor_position += 1
        self.lineEdit().setCursorPosition(cursor_position)
