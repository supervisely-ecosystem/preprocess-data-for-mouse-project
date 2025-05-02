from typing import List
from supervisely.app.widgets import Button, Stepper
import src.globals as g
from src.ui.base_step import BaseStep

def button_toggle(
    module: BaseStep,
    stepper: Stepper,
    step_id: int,
    following_steps: List[BaseStep]
) -> None:
    if module.button.text == "Select":
        _handle_select_state(module, stepper, step_id, following_steps)
    elif module.button.text == "Reselect":
        _handle_reselect_state(module, stepper, step_id, following_steps)

def _handle_select_state(module, stepper: Stepper, step_id: int, following_steps: List) -> None:
    module.validation_text.show()
    set_button_params(module.button, is_reselect=False)
    module.disable(run=False)
    
    for step in following_steps:
        step.enable(run=False)
        step.validation_text.hide()
    
    following_steps[0].card.unlock()
    stepper.set_active_step(step_id + 1)

def _handle_reselect_state(module, stepper: Stepper, step_id: int, following_steps: List) -> None:
    module.validation_text.hide()
    set_button_params(module.button, is_reselect=True)
    module.enable(run=False)
    
    for step in following_steps:
        set_button_params(step.button, is_reselect=True)
        step.validation_text.hide()
        step.card.lock()
    stepper.set_active_step(step_id)

def set_button_params(button: Button, is_reselect: bool = False) -> None:
    if button.text == "Start":
        return
    elif is_reselect:
        button.text = "Select"
        button.icon = None
        button.plain = False
    else:
        button.text = "Reselect"
        button.icon = "zmdi zmdi-refresh"
        button.plain = True

def show_progress_bars():
    g.PROGRESS_BAR.show()
    g.PROGRESS_BAR_2.show()

def hide_progress_bars():
    g.PROGRESS_BAR.hide()
    g.PROGRESS_BAR_2.hide()