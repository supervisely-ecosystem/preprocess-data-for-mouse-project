import supervisely as sly
from supervisely.app.widgets import Container, Stepper

import src.globals as g
from src.ui.input import input
from src.ui.connect import connect
from src.ui.splits import splits
from src.ui.output import output
import src.ui.utils as utils
from src.scripts.download_project import download_project
from src.scripts.split_project import split_project
from src.scripts.make_training_clips import make_training_clips
from src.scripts.apply_detector import apply_detector
from src.scripts.upload_project import upload_project

stepper: Stepper = Stepper(widgets=[input.card, connect.card, splits.card, output.card])
layout: Container = Container(widgets=[stepper])

app: sly.Application = sly.Application(layout=layout)

# Step 1. Input
@input.button.click
def confirm_project():
    utils.button_toggle(input, stepper, 1, [connect, splits, output])

# Step 2. Connect
@connect.button.click
def connect_model():
    is_valid = connect.validate_model()
    if is_valid:
        g.SESSION_ID = connect.session_selector.get_selected_id()
        utils.button_toggle(connect, stepper, 2, [splits, output])

# Step 3. Splits
@splits.button.click
def confirm_splits():
    g.SPLIT_RATIO = splits.get_train_split_percent() / 100
    utils.button_toggle(splits, stepper, 3, [output])

# Step 4. Output
@output.button.click
def process_project():
    input.disable()
    connect.disable()
    splits.disable()
    output.hide_validation()
    utils.show_progress_bars()
    try:
        download_project()
        split_project()
        make_training_clips()
        project = upload_project()
        apply_detector(project.id)
        output.set(project)
    except Exception as e:
        output.show_validation(f"Error: {str(e)}", "error")
        input.enable()
        connect.enable()
        splits.enable()
    finally:
        utils.hide_progress_bars()
