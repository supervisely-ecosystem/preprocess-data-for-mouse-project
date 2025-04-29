from supervisely.app.widgets import Container, Button, Card, Text, ProjectThumbnail
from supervisely.api.project_api import ProjectInfo
import src.globals as g

# Step 4
validation_text = Text(text="")
validation_text.hide()

button = Button("Upload")
project_thumbnail = ProjectThumbnail()
project_thumbnail.hide()

container = Container(widgets=[project_thumbnail, validation_text, button, g.PROGRESS_BAR, g.PROGRESS_BAR_2])
card = Card(
    title="Output Project",
    description="Upload project to Supervisely and apply detector. Result project will contain 'train' dataset with split clips and 'test' dataset with original videos.",
    content=container,
    lock_message="Select train/val splits to unlock",
)
card.lock()

def set(project: ProjectInfo):
    g.API.task.set_output_project(g.TASK_ID, project.id, project.name, project.image_preview_url)
    project_thumbnail.set(project)
    validation_text.set("Project uploaded successfully", "success")
    project_thumbnail.show()
    validation_text.show()
    button.disable()