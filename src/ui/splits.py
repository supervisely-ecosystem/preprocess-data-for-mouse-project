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
    description="Split project into train/val sets",
    content=container,
    lock_message="Connect model to unlock",
)
card.lock()

def disable():
    train_val_splits.disable()
    button.disable()

def enable():
    train_val_splits.enable()
    button.enable()
