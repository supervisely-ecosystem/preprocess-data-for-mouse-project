import supervisely as sly
from supervisely.app.widgets import Container, Stepper

import src.ui.connect as connect
import src.ui.input as input
import src.ui.splits as splits
import src.ui.output as output

stepper: Stepper = Stepper(widgets=[input.card, connect.card, splits.card, output.card])
layout: Container = Container(widgets=[stepper])

app: sly.Application = sly.Application(layout=layout)

# @TODO:
# Disable widgets on upload button click
# Add stepper move to next step on select click
