from supervisely.app.widgets import Container, Button, Card, Text, ProjectThumbnail
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
    description="",
    content=container,
    lock_message="Select train/val splits to unlock",
)
card.lock()
