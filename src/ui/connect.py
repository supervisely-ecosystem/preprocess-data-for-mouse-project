import src.globals as g
from supervisely.app.widgets import SelectAppSession
from supervisely.nn.inference.session import Session
from src.ui.base_step import BaseStep

class ConnectStep(BaseStep):
    def __init__(self):
        self.session_selector = SelectAppSession(g.TEAM_ID, ["deployed_nn"], True)
        
        widgets = [self.session_selector]
        
        super().__init__(
            title="Connect Mouse Detector",
            description="Select model with exactly one class with name 'mouse'",
            widgets=widgets,
            lock_message="Select input options to unlock"
        )
    
    def validate_model(self) -> bool:
        self.hide_validation()
        session_id = self.session_selector.get_selected_id()
        
        if session_id is None:
            self.show_validation("Please select a model", "error")
            return False
            
        session = Session(g.API, session_id)
        model_meta = session.get_model_meta()
        
        if len(model_meta.obj_classes) != 1:
            self.show_validation("Model must have exactly one class with name 'mouse'", "error")
            return False
            
        if list(model_meta.obj_classes.keys())[0] != "mouse":
            self.show_validation("Model must have exactly one class with name 'mouse'", "error")
            return False
        
        self.show_validation("Model connected", "success")
        return True

connect = ConnectStep()


