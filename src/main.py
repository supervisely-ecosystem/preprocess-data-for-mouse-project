import os
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
from src.scripts.sync_manager import SyncManager

stepper: Stepper = Stepper(widgets=[input.card, connect.card, splits.card, output.card])
layout: Container = Container(widgets=[stepper])

app: sly.Application = sly.Application(layout=layout)

# Step 1. Input
@input.button.click
def confirm_project():
    g.SYNC_MANAGER = SyncManager()
    g.NEW_VIDEOS = g.SYNC_MANAGER.get_new_videos(g.PROJECT_ID, g.DST_PROJECT_ID)
    splits.train_val_splits.set_items_count(len(g.NEW_VIDEOS))
    splits.train_val_splits.show()
    
    if not g.NEW_VIDEOS:
        input.show_validation("No new videos to process", "info")
        return
        
    input.show_validation(f"Found {len(g.NEW_VIDEOS)} new videos to process", "success")
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
        # 1. Download project
        download_project()
        
        # 2. Split project
        split_project()
        
        # 3. Make training clips
        make_training_clips()
        
        # 4. Upload project
        upload_project()
        
        # 5. Apply detector
        apply_detector()
            
        output.set(g.DST_PROJECT)
        
    except Exception as e:
        output.show_validation(f"Error: {str(e)}", "error")
        input.enable()
        connect.enable()
        splits.enable()
    finally:
        utils.hide_progress_bars()
