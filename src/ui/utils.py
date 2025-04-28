from typing import List
from supervisely.app.widgets import Button, Widget

def button_toggle(button: Button, step_widgets: List[Widget], following_steps: list = []) -> None:
    if button.text == "Select":
        set_button_params(button, False)
        for w in step_widgets:
            w.disable()
        if len(following_steps) > 0:
            following_steps[0].card.unlock()
    else:
        set_button_params(button, True)
        for w in step_widgets:
            w.enable()
        for step in following_steps:
            set_button_params(step.button, True)
            step.card.lock()

def set_button_params(button: Button, is_reselect: bool = False) -> None:
    if is_reselect:
        button.text = "Select"
        button.icon = None
        button.plain = False
    else:
        button.text = "Reselect"
        button.icon = "zmdi zmdi-refresh"
        button.plain = True
