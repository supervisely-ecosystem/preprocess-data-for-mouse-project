import supervisely as sly
from supervisely.app.widgets import SelectAppSession

import src.globals as g
from src.ui.base_step import BaseStep


class ConnectStep(BaseStep):
    def __init__(self):
        self.session_selector = SelectAppSession(g.TEAM_ID, ["deployed_nn"], True)

        widgets = [self.session_selector]

        super().__init__(
            title="Connect Mouse Detector",
            description="Select model with exactly one class with name 'mouse'",
            widgets=widgets,
            lock_message="Select input options to unlock",
        )

    def validate_model(self) -> bool:
        self.hide_validation()
        session_id = self.session_selector.get_selected_id()

        if session_id is None:
            self.show_validation("Please select a model", "error")
            return False

        try:
            model_meta_json = g.API.task.send_request(
                session_id,
                "get_output_classes_and_tags",
                data={},
                timeout=10,
                retries=1,
                raise_error=True,
            )
            model_meta = sly.ProjectMeta.from_json(model_meta_json)
        except Exception:
            sly.logger.warning(
                "Could not get metadata from the selected model session",
                exc_info=True,
            )
            self.show_validation(
                "Could not connect to the selected model. Make sure it is deployed and try again.",
                "error",
            )
            return False

        if len(model_meta.obj_classes) != 1:
            self.show_validation("Model must have exactly one class with name 'mouse'", "error")
            return False

        if list(model_meta.obj_classes.keys())[0] != "mouse":
            self.show_validation("Model must have exactly one class with name 'mouse'", "error")
            return False

        self.show_validation("Model connected", "success")
        return True


connect = ConnectStep()
