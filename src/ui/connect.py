import requests

import src.globals as g
import src.ui.utils as utils
import supervisely as sly

from supervisely.app.widgets import SelectAppSession, Text, Button, Card, Container
from supervisely.nn.inference.session import Session
import src.ui.splits as splits
import src.ui.output as output

# Step 2
session_selector = SelectAppSession(g.TEAM_ID, "deployed_nn", True)

validation_text = Text(text="")
validation_text.hide()

button = Button("Select")

container = Container(widgets=[session_selector, validation_text, button])
card = Card(
    title="Connect Mouse Detector",
    description="Select model with exactly one class with name 'mouse'",
    content=container,
    lock_message="Select input options to unlock",
)
card.lock()

def disable():
    session_selector.disable()
    button.disable()

def enable():
    session_selector.enable()
    button.enable()

def validate_model():
    validation_text.hide()
    session_id = session_selector.get_selected_id()
    if session_id is None:
        validation_text.set("Please select a model", "error")
        validation_text.show()
        return False
    session = Session(g.API, session_id)
    model_meta = session.get_model_meta()
    if len(model_meta.obj_classes) != 1:
        validation_text.set("Model must have exactly one class with name 'mouse'", "error")
        validation_text.show()
        return False
    if model_meta.obj_classes[0].name != "mouse":
        validation_text.set("Model must have exactly one class with name 'mouse'", "error")
        validation_text.show()
        return False
    
    validation_text.set("Model connected", "success")
    validation_text.show()
    return True


