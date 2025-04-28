import os
import supervisely as sly
from supervisely.app.widgets import Button, Card, Container, Text, TrainValSplits

import src.globals as g
import src.ui.utils as utils
import src.ui.output as output

# Step 3
train_val_splits = TrainValSplits(g.PROJECT_ID, tags_splits=False, datasets_splits=False)

validation_text = Text(text="")
validation_text.hide()

button = Button(text="Select")

container = Container(widgets=[train_val_splits, validation_text, button])
card = Card(
    title="Train/Val Split",
    description="",
    content=container,
    lock_message="Connect model to unlock",
)
card.lock()

@button.click
def confirm_splits():
    g.SPLIT_RATIO = train_val_splits.get_train_split_percent() / 100
    utils.button_toggle(button, [train_val_splits, validation_text], [output])

