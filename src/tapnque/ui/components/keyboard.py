"""
Touchscreen On-Screen Virtual Keyboard Widget for Student Kiosk.
Supports alphanumeric and numeric keypad modes with automated student ID formatting.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)


class TouchKeyboardWidget(QFrame):
    """Touchscreen keyboard dock for kiosk input fields."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_input = None
        self.symbol_mode = False
        self.alpha_rows = []
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("touchKeyboard")
        self.setFixedSize(920, 404)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 22)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 4)
        header_layout.addStretch()
        self.close_button = self._make_key("CLOSE", width=108, object_name="keyboardCloseKey")
        self.close_button.clicked.connect(self._enter)
        header_layout.addWidget(self.close_button)
        layout.addLayout(header_layout)

        self.row1_buttons = []
        self.row2_buttons = []
        self.row3_buttons = []

        self.alpha_rows.append(self._build_alpha_row(list("QWERTYUIOP"), self.row1_buttons))
        self.alpha_rows.append(self._build_alpha_row(list("ASDFGHJKL"), self.row2_buttons))

        row3 = QHBoxLayout()
        row3.setSpacing(10)
        self.shift_button = self._make_key("SHIFT", width=108)
        self.shift_button.clicked.connect(self._toggle_shift)
        row3.addWidget(self.shift_button)
        for key in list("ZXCVBNM"):
            button = self._make_key(key)
            button.clicked.connect(lambda checked=False, value=key: self._insert_text(value))
            self.row3_buttons.append(button)
            row3.addWidget(button)
        self.backspace_button = self._make_key("⌫", width=108, object_name="keyboardDeleteKey")
        self.backspace_button.clicked.connect(self._backspace)
        row3.addWidget(self.backspace_button)
        layout.addLayout(row3)
        self.alpha_rows.append(row3)

        row4 = QHBoxLayout()
        row4.setSpacing(10)
        self.toggle_button = self._make_key("?123", width=96)
        self.toggle_button.clicked.connect(self._toggle_symbol_mode)
        row4.addWidget(self.toggle_button)

        self.space_button = self._make_key("SPACE", width=420)
        self.space_button.clicked.connect(lambda: self._insert_text(" "))
        row4.addWidget(self.space_button, 1)

        self.enter_button = self._make_key("ENTER", width=160, object_name="keyboardEnterKey")
        self.enter_button.clicked.connect(self._enter)
        row4.addWidget(self.enter_button)
        layout.addLayout(row4)
        self.alpha_rows.append(row4)

        numeric_grid = QGridLayout()
        numeric_grid.setContentsMargins(20, 20, 20, 20)
        numeric_grid.setHorizontalSpacing(24)
        numeric_grid.setVerticalSpacing(64)
        for value, row, column in [
            ("1", 0, 0), ("2", 0, 1), ("3", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
            ("0", 3, 0), ("⌫", 3, 1), ("ENTER", 3, 2),
        ]:
            object_name = "keyboardKey"
            if value == "⌫":
                object_name = "keyboardDeleteKey"
            elif value == "ENTER":
                object_name = "keyboardEnterKey"
            button = self._make_key(value, object_name=object_name)
            button.setFixedSize(104, 56)
            if value == "⌫":
                button.clicked.connect(self._backspace)
            elif value == "ENTER":
                button.clicked.connect(self._enter)
            else:
                button.clicked.connect(lambda checked=False, text=value: self._insert_text(text))
            numeric_grid.addWidget(button, row, column)

        self.numeric_container = QFrame()
        numeric_wrap = QHBoxLayout(self.numeric_container)
        numeric_wrap.setContentsMargins(0, 8, 0, 56)
        numeric_wrap.addStretch()
        numeric_wrap.addLayout(numeric_grid)
        numeric_wrap.addStretch()
        self.numeric_container.setMinimumWidth(460)
        self.numeric_container.hide()
        layout.addWidget(self.numeric_container)

    def _build_alpha_row(self, keys, button_store):
        row = QHBoxLayout()
        row.setSpacing(10)
        for key in keys:
            button = self._make_key(key)
            button.clicked.connect(lambda checked=False, value=key: self._insert_text(value))
            row.addWidget(button)
            button_store.append(button)
        self.layout().addLayout(row)
        return row

    def _make_key(self, text, width=68, object_name="keyboardKey"):
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(68)
        button.setMinimumWidth(width)
        return button

    def attach_target(self, line_edit, keyboard_type):
        self.target_input = line_edit
        self.symbol_mode = False
        self._set_keyboard_type(keyboard_type)
        if self.parentWidget() is not None:
            self.raise_()
        self.show()

    def _set_keyboard_type(self, keyboard_type):
        show_alpha = keyboard_type == "alpha"
        for row in self.alpha_rows:
            self._set_layout_visible(row, show_alpha)
        self.numeric_container.setVisible(keyboard_type == "numeric")
        if show_alpha:
            self._refresh_alpha_keys()

    def _set_layout_visible(self, layout, visible):
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget is not None:
                widget.setVisible(visible)

    def _toggle_shift(self):
        if self.symbol_mode:
            return
        buttons = self.row1_buttons + self.row2_buttons + self.row3_buttons
        use_lower = any(button.text().isupper() for button in buttons)
        for button in buttons:
            button.setText(button.text().lower() if use_lower else button.text().upper())

    def _toggle_symbol_mode(self):
        self.symbol_mode = not self.symbol_mode
        self._refresh_alpha_keys()

    def _refresh_alpha_keys(self):
        if self.symbol_mode:
            row1 = list("1234567890")
            row2 = ["@", ".", "_", "-", "+", "/", ":"]
            row3 = ["[", "]", "{", "}", "!", "?", "&"]
            self.toggle_button.setText("ABC")
        else:
            row1 = list("QWERTYUIOP")
            row2 = list("ASDFGHJKL")
            row3 = list("ZXCVBNM")
            self.toggle_button.setText("?123")

        for buttons, values in (
            (self.row1_buttons, row1),
            (self.row2_buttons, row2),
            (self.row3_buttons, row3),
        ):
            for index, button in enumerate(buttons):
                if index < len(values):
                    button.setText(values[index])
                    button.show()
                else:
                    button.hide()

    def _insert_text(self, text):
        if self.target_input is None:
            return
        numeric_format = self.target_input.property("numeric_format")
        if numeric_format == "student_id" and text.isdigit():
            digits = self._student_id_digits() + text
            digits = digits[:9]
            self.target_input.setText(self._format_student_id(digits))
            self.target_input.setCursorPosition(len(self.target_input.text()))
            self.target_input.setFocus()
            return
        self.target_input.insert(text)
        self.target_input.setFocus()

    def _backspace(self):
        if self.target_input is None:
            return
        numeric_format = self.target_input.property("numeric_format")
        if numeric_format == "student_id":
            digits = self._student_id_digits()[:-1]
            self.target_input.setText(self._format_student_id(digits))
            self.target_input.setCursorPosition(len(self.target_input.text()))
            self.target_input.setFocus()
            return
        self.target_input.backspace()
        self.target_input.setFocus()

    def _student_id_digits(self):
        if self.target_input is None:
            return ""
        return "".join(ch for ch in self.target_input.text() if ch.isdigit())

    def _format_student_id(self, digits):
        if len(digits) <= 4:
            return digits
        return f"{digits[:4]}-{digits[4:9]}"

    def _enter(self):
        self.hide()
        if self.target_input is not None:
            self.target_input.clearFocus()
        self.target_input = None
