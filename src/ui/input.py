from supervisely.app.widgets import Card, ProjectThumbnail, Button, Container, Text, Checkbox
import src.ui.utils as utils
import src.globals as g

import src.ui.splits as splits
import src.ui.connect as connect
import src.ui.output as output
from supervisely.project.download import is_cached


# Step 1
project_thumbnail = ProjectThumbnail(g.PROJECT_INFO)

if is_cached(g.PROJECT_ID):
    _text = "Use cached data stored on the agent to optimize project download"
else:
    _text = "Cache data on the agent to optimize project download for future trainings"

use_cache_text = Text(_text)
use_cache_checkbox = Checkbox(use_cache_text, checked=True)

validation_text = Text(text="")
validation_text.hide()

button = Button("Select")
container = Container(widgets=[project_thumbnail, use_cache_checkbox, validation_text, button])
card = Card(
    title="Input Project",
    description="Selected project from which items and annotations will be downloaded",
    content=container,
)


# @TODO: Cards lock/unlock
@button.click
def confirm_project():
    utils.button_toggle(button, [project_thumbnail], [connect, splits, output])
