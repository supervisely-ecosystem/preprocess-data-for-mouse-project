from supervisely.app.widgets import ProjectThumbnail, Checkbox, Text
import src.globals as g
from supervisely.project.download import is_cached
from src.ui.base_step import BaseStep

class InputStep(BaseStep):
    def __init__(self):
        self.project_thumbnail = ProjectThumbnail(g.PROJECT_INFO)
        
        if is_cached(g.PROJECT_ID):
            _text = "Use cached data stored on the agent to optimize project download"
        else:
            _text = "Cache data on the agent to optimize project download for future trainings"
        
        self.use_cache_text = Text(_text)
        self.use_cache_checkbox = Checkbox(self.use_cache_text, checked=True)
        
        widgets = [self.project_thumbnail, self.use_cache_checkbox]
        
        super().__init__(
            title="Input Project",
            description="Selected project from which items and annotations will be downloaded",
            widgets=widgets
        )
        
        self.show_validation("Project selected", "success")
        self.hide_validation()

input = InputStep()
