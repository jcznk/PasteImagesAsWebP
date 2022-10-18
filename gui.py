# Paste Images As WebP add-on for Anki 2.1
# Copyright (C) 2021  Ren Tatsumoto. <tatsu at autistici.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Any modifications to this file must keep this entire header intact.

import itertools
from typing import NamedTuple, Iterable, List

from anki.notes import Note
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

from .config import config, write_config
from .consts import *
from .utils import FilePathFactory
from .utils import ShowOptions
from .widgets import FieldSelector
from .widgets import ImageSliderBox
from .widgets import PresetsEditor


class SettingsDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle(ADDON_NAME)
        self.setMinimumWidth(WINDOW_MIN_WIDTH)
        self._sliders = ImageSliderBox(
            "Image parameters",
            max_width=config['max_image_width'],
            max_height=config['max_image_height'],
        )
        self.presets_editor = PresetsEditor("Presets", sliders=self._sliders)
        self._main_vbox = QVBoxLayout()
        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

    def setup_ui(self):
        self.setLayout(self.create_main_layout())
        self.populate_main_vbox()
        self.setup_logic()
        self.set_initial_values()

    def exec(self):
        self.setup_ui()
        return super().exec()

    def create_main_layout(self):
        layout = QVBoxLayout()
        layout.addLayout(self._main_vbox)
        layout.addStretch()
        layout.addWidget(self._button_box)
        return layout

    def populate_main_vbox(self):
        self._main_vbox.addWidget(self._sliders)
        self._main_vbox.addWidget(self.presets_editor)

    def setup_logic(self):
        qconnect(self._button_box.accepted, self.accept)
        qconnect(self._button_box.rejected, self.reject)
        self._button_box.button(QDialogButtonBox.Ok).setFocus()

    def set_initial_values(self):
        self._sliders.populate(config)
        self.presets_editor.add_items(config.get('saved_presets', []))

    def accept(self):
        config.update(self._sliders.as_dict())
        config['saved_presets'] = self.presets_editor.as_list()
        write_config()
        return super().accept()


def get_all_keys(notes: Iterable[Note]) -> List[str]:
    return sorted(set(itertools.chain(*(note.keys() for note in notes))))


class BulkConvertDialog(SettingsDialog):
    """Dialog shown on bulk-convert."""

    def __init__(self, *args, **kwargs):
        self._field_selector = FieldSelector()
        self._reconvert_checkbox = QCheckBox("Reconvert existing WebP images")
        super().__init__(*args, **kwargs)

    def selected_fields(self) -> List[str]:
        return self._field_selector.selected_fields()

    def selected_notes(self) -> Iterable[Note]:
        return (mw.col.get_note(nid) for nid in self.parent().selectedNotes())  # parent: Browser

    def populate_main_vbox(self):
        super().populate_main_vbox()
        self._main_vbox.addWidget(self._field_selector)
        self._main_vbox.addWidget(self._reconvert_checkbox)

    def set_initial_values(self):
        self._field_selector.add_fields(get_all_keys(self.selected_notes()))
        self._field_selector.set_fields(config.get('bulk_convert_fields'))
        self._reconvert_checkbox.setChecked(config.get('bulk_reconvert_webp'))
        super().set_initial_values()

    def accept(self):
        if self._field_selector.isChecked() and not self._field_selector.selected_fields():
            showInfo(title="Can't accept settings", text="No fields selected. Nothing to convert.")
        else:
            config['bulk_convert_fields'] = self._field_selector.selected_fields()
            config['bulk_reconvert_webp'] = self._reconvert_checkbox.isChecked()
            return super().accept()


class ImageDimensions(NamedTuple):
    width: int
    height: int


class PasteDialog(SettingsDialog):
    """Dialog shown on paste."""

    def __init__(self, *args, image: ImageDimensions, **kwargs):
        self.image = image
        super().__init__(*args, **kwargs)

    def populate_main_vbox(self):
        super().populate_main_vbox()
        self._main_vbox.addWidget(self.create_scale_settings_group_box())

    def create_scale_settings_group_box(self):
        gbox = QGroupBox(f"Original size: {self.image.width} x {self.image.height} px")
        gbox.setLayout(self.create_scale_options_grid())
        return gbox

    def adjust_sliders(self, factor: float):
        if self._sliders.width > 0:
            self._sliders.width = int(self.image.width * factor)
        if self._sliders.height > 0:
            self._sliders.height = int(self.image.height * factor)

    def create_scale_options_grid(self):
        grid = QGridLayout()
        factors = (1 / 8, 1 / 4, 1 / 2, 1, 1.5, 2)
        columns = 3
        for index, factor in enumerate(factors):
            i = int(index / columns)
            j = index - (i * columns)
            button = QPushButton(f"{factor}x")
            qconnect(button.clicked, lambda _, f=factor: self.adjust_sliders(f))
            grid.addWidget(button, i, j)
        return grid


class SettingsMenuDialog(SettingsDialog):
    """Settings dialog available from the main menu."""

    __checkboxes = {
        'drag_and_drop': 'Convert images on drag and drop',
        'copy_paste': 'Convert images on copy-paste',
        'avoid_upscaling': 'Avoid upscaling',
        'preserve_original_filenames': 'Preserve original filenames, if available',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.when_show_dialog_combo_box = self.create_when_show_dialog_combo_box()
        self.filename_pattern_combo_box = self.create_filename_pattern_combo_box()
        self.checkboxes = {key: QCheckBox(text) for key, text in self.__checkboxes.items()}

    @staticmethod
    def create_when_show_dialog_combo_box() -> QComboBox:
        combobox = QComboBox()
        for option in ShowOptions:
            combobox.addItem(option.value, option.name)
        return combobox

    @staticmethod
    def create_filename_pattern_combo_box() -> QComboBox:
        combobox = QComboBox()
        for option in FilePathFactory().patterns_populated:
            combobox.addItem(option)
        return combobox

    def populate_main_vbox(self):
        super().populate_main_vbox()
        self._main_vbox.addWidget(self.create_additional_settings_group_box())

    def create_additional_settings_group_box(self) -> QGroupBox:
        def create_inner_vbox():
            vbox = QVBoxLayout()
            vbox.addLayout(self.create_combo_boxes_layout())
            for widget in self.checkboxes.values():
                vbox.addWidget(widget)
            return vbox

        gbox = QGroupBox("Behavior")
        gbox.setLayout(create_inner_vbox())
        return gbox

    def set_initial_values(self):
        super().set_initial_values()
        self.when_show_dialog_combo_box.setCurrentIndex(ShowOptions.index_of(config.get("show_settings")))
        self.filename_pattern_combo_box.setCurrentIndex(config.get("filename_pattern_num", 0))

        for key, widget in self.checkboxes.items():
            widget.setChecked(config[key])

    def create_combo_boxes_layout(self):
        layout = QFormLayout()
        layout.addRow("Show this dialog", self.when_show_dialog_combo_box)
        layout.addRow("Filename pattern", self.filename_pattern_combo_box)
        return layout

    def accept(self):
        config['show_settings'] = self.when_show_dialog_combo_box.currentData()
        config['filename_pattern_num'] = self.filename_pattern_combo_box.currentIndex()
        for key, widget in self.checkboxes.items():
            config[key] = widget.isChecked()

        return super().accept()
