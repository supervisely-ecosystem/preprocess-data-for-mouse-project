import os
from supervisely.app.widgets import Container, Button, Card, Text, ProjectThumbnail
import src.globals as g

from src.scripts.download_project import download_project
from src.scripts.split_project import split_project
from src.scripts.make_training_clips import make_training_clips
from src.scripts.apply_detector import apply_detector
from src.scripts.upload_project import upload_project


# Step 4
validation_text = Text(text="")
validation_text.hide()

button = Button(text="Upload")
project_thumbnail = ProjectThumbnail()
project_thumbnail.hide()

container = Container(widgets=[project_thumbnail, validation_text, button, g.PROGRESS_BAR, g.PROGRESS_BAR_ITEM])
card = Card(
    title="Output Project",
    description="",
    content=container,
    lock_message="Select train/val splits to unlock",
)
card.lock()

@button.click
def process_project():
    # @TODO: disable rest of the GUI on click
    validation_text.hide()
    # button.disable()
    g.PROGRESS_BAR.show()
    
    try:
        if not os.path.exists(g.PROJECT_DIR): # debug
            download_project()
        
        if not os.path.exists(g.SPLIT_PROJECT_DIR): # debug
            split_project()
            make_training_clips()
        
        # progress_bar.message = "Uploading project..."
        project_id = upload_project()

        # progress_bar.message = "Applying detector..."
        apply_detector(project_id)

    except Exception as e:
        validation_text.set(f"Error: {str(e)}", "error")
        validation_text.show()
    finally:
        g.PROGRESS_BAR.hide()
        g.PROGRESS_BAR_ITEM.hide()
        button.enable()
