from typing import List
from supervisely.app.widgets import Button, Widget, Stepper

def button_toggle(button: Button, stepper: Stepper, step_id: int, step_widgets: List[Widget], following_steps: list = []) -> None:
    if button.text == "Select":
        set_button_params(button, False)
        for w in step_widgets:
            w.disable()
        if len(following_steps) > 0:
            following_steps[0].card.unlock()
        stepper.set_active_step(step_id+1)
    elif button.text == "Reselect":
        set_button_params(button, True)
        for w in step_widgets:
            w.enable()
        for step in following_steps:
            set_button_params(step.button, True)
            step.card.lock()
        stepper.set_active_step(step_id)
        

def set_button_params(button: Button, is_reselect: bool = False) -> None:
    if button.text == "Upload":
        return
    elif is_reselect:
        button.text = "Select"
        button.icon = None
        button.plain = False
    else:
        button.text = "Reselect"
        button.icon = "zmdi zmdi-refresh"
        button.plain = True
