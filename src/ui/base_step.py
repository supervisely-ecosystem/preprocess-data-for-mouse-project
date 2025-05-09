from typing import List, Optional
from supervisely.app.widgets import Card, Button, Container, Text, Widget


class BaseStep:
    def __init__(
        self,
        title: str,
        description: str,
        widgets: List[Widget],
        lock_message: Optional[str] = None,
    ):
        self.validation_text = Text("")
        self.validation_text.hide()

        self.button = Button("Select")

        all_widgets = widgets + [self.validation_text, self.button]
        self.container = Container(widgets=all_widgets)

        self.card = Card(
            title=title, description=description, content=self.container, lock_message=lock_message
        )

        if lock_message:
            self.card.lock()

    def disable(self, run: bool = True) -> None:
        for widget in self.container._widgets:
            if widget != self.button or run:
                widget.disable()

    def enable(self, run: bool = True) -> None:
        for widget in self.container._widgets:
            if widget != self.button or run:
                widget.enable()

    def show_validation(self, text: str, status: str = "success") -> None:
        self.validation_text.set(text, status)
        self.validation_text.show()

    def hide_validation(self) -> None:
        self.validation_text.hide()
