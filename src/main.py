import os
import supervisely as sly
from supervisely.app.widgets import Container, Stepper

import src.globals as g
import src.ui.connect as connect
import src.ui.input as input
import src.ui.splits as splits
import src.ui.output as output
import src.ui.utils as utils
from src.scripts.download_project import download_project
from src.scripts.split_project import split_project
from src.scripts.make_training_clips import make_training_clips
from src.scripts.apply_detector import apply_detector
from src.scripts.upload_project import upload_project

stepper: Stepper = Stepper(widgets=[input.card, connect.card, splits.card, output.card])
layout: Container = Container(widgets=[stepper])

app: sly.Application = sly.Application(layout=layout)


@input.button.click
def confirm_project():
    utils.button_toggle(input.button, stepper, 1, [input.project_thumbnail], [connect, splits, output])

@connect.button.click
def connect_model():
    # is_valid = connect.validate_model()
    is_valid = True
    if is_valid:
        g.SESSION_ID = connect.session_selector.get_selected_id()
        utils.button_toggle(connect.button, stepper, 2, [connect.session_selector], [splits, output])

@splits.button.click
def confirm_splits():
    g.SPLIT_RATIO = splits.train_val_splits.get_train_split_percent() / 100
    utils.button_toggle(splits.button, stepper, 3, [splits.train_val_splits, splits.validation_text], [output])

@output.button.click
def process_project():
    input.disable()
    connect.disable()
    splits.disable()
    output.validation_text.hide()
    g.PROGRESS_BAR.show()
    g.PROGRESS_BAR_2.show()
    g.PROGRESS_BAR_3.show()
    try:
        # if not os.path.exists(g.PROJECT_DIR): # debug
        download_project()
        
        # if not os.path.exists(g.SPLIT_PROJECT_DIR): # debug
        split_project()
        make_training_clips()
        
        project_id = upload_project()
        apply_detector(project_id)

    except Exception as e:
        output.validation_text.set(f"Error: {str(e)}", "error")
        output.validation_text.show()
        input.enable()
        connect.enable()
        splits.enable()
    finally:
        g.PROGRESS_BAR.hide()
        g.PROGRESS_BAR_2.hide()
        g.PROGRESS_BAR_3.hide()
        output.button.enable()
