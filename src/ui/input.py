from supervisely.app.widgets import ProjectThumbnail, Checkbox, Text, Field
import src.globals as g
from supervisely.project.download import is_cached
from src.ui.base_step import BaseStep

class InputStep(BaseStep):
    def __init__(self):
        self.source_project_thumbnail = ProjectThumbnail(g.PROJECT_INFO)
        self.source_project_field = Field(
            title="Source Project",
            description="Data from this project will be prepared for training",
            content=self.source_project_thumbnail
        )
        
        self.target_project_thumbnail = ProjectThumbnail(g.DST_PROJECT)
        self.target_project_field = Field(
            title="Target Project",
            description="Data from this project will be used for training",
            content=self.target_project_thumbnail
        )
        
        if is_cached(g.PROJECT_ID):
            _text = "Use cached data stored on the agent to optimize project download"
        else:
            _text = "Cache data on the agent to optimize project download for future trainings"
        
        self.use_cache_text = Text(_text)
        self.use_cache_checkbox = Checkbox(self.use_cache_text, checked=True)
        
        widgets = [self.source_project_field, self.target_project_field, self.use_cache_checkbox]
        
        super().__init__(
            title="Input Project",
            description="Selected project from which items and annotations will be downloaded",
            widgets=widgets
        )
        
        # self.show_validation("Project selected", "success")
        self.show_validation("", "text")
        self.hide_validation()

input = InputStep()
