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
    input.validation_text.hide()
    if input.button.text == "Reselect":
        utils.button_toggle(input, stepper, 1, [connect, splits, output])
        return

    # Initialize new videos using the project check function
    input.validation_text.set("Checking project...", status="info")
    input.validation_text.show()
    input.check_project()
    # If there are no new videos, display a message
    if len(g.VIDEOS_TO_UPLOAD) == 0 and len(g.VIDEOS_TO_DETECT) == 0:
        return

    if len(g.VIDEOS_TO_UPLOAD) > 0:
        # Update the interface for video splitting
        splits.train_val_splits.set_items_count(len(g.VIDEOS_TO_UPLOAD))
        splits.train_val_splits.show()
    else:
        splits.validation_text.set("No videos to split", status="success")
        splits.validation_text.show()

    # Move to the next step
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
    output.notification_box.show()
    utils.show_progress_bars()

    try:
        if len(g.VIDEOS_TO_UPLOAD) > 0:
            # 1. Download only new videos
            download_project()

            # 2. Split new videos into train/test
            split_project()

            # 3. Create clips from new videos
            make_training_clips()

            # 4. Upload new videos and clips
            upload_project()

        if len(g.VIDEOS_TO_DETECT) > 0:
            # 5. Apply detector to new videos
            apply_detector()

        output.set()
        app.shutdown()

    except Exception as e:
        output.show_validation(f"Error: {str(e)}", "error")
        input.enable()
        connect.enable()
        splits.enable()
        raise e
    finally:
        output.notification_box.hide()
        utils.hide_progress_bars()
