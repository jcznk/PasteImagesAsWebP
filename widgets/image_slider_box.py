# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import Dict

from aqt.qt import *

from .rich_slider import RichSlider


class ImageSliderBox(QGroupBox):
    def __init__(self, *args, max_width: int, max_height: int, **kwargs):
        super().__init__(*args, **kwargs)
        self._sliders = {
            'image_width': RichSlider("Width", "px", limit=max_width),
            'image_height': RichSlider("Height", "px", limit=max_height),
            'image_quality': RichSlider("Quality", "%", limit=100),
        }
        self.setLayout(self.create_layout())
        self.set_tooltips()

    def as_dict(self) -> Dict[str, int]:
        return {key: slider.value for key, slider in self._sliders.items()}

    @property
    def quality(self) -> int:
        return self._sliders['image_quality'].value

    @property
    def width(self) -> int:
        return self._sliders['image_width'].value

    @width.setter
    def width(self, value: int):
        self._sliders['image_width'].value = value

    @property
    def height(self) -> int:
        return self._sliders['image_height'].value

    @height.setter
    def height(self, value: int):
        self._sliders['image_height'].value = value

    def create_layout(self) -> QLayout:
        grid = QGridLayout()
        for y_index, slider in enumerate(self._sliders.values()):
            grid.addWidget(QLabel(slider.title), y_index, 0)
            for x_index, widget in enumerate(slider.widgets):
                grid.addWidget(widget, y_index, x_index + 1)
        return grid

    def populate(self, config: Dict[str, int]):
        for key, slider in self._sliders.items():
            slider.value = config.get(key)

    def set_tooltips(self):
        side_tooltip = str(
            "Desired %s.\n"
            "If either of the width or height parameters is 0,\n"
            "the value will be calculated preserving the aspect-ratio.\n"
            "If both values are 0, no resizing is performed (not recommended)."
        )
        quality_tooltip = str(
            "Specify the compression factor between 0 and 100.\n"
            "A small factor produces a smaller file with lower quality.\n"
            "Best quality is achieved by using a value of 100."
        )
        self._sliders['image_width'].set_tooltip(side_tooltip % 'width')
        self._sliders['image_height'].set_tooltip(side_tooltip % 'height')
        self._sliders['image_quality'].set_tooltip(quality_tooltip)
