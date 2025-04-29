from supervisely.app.widgets import ProjectThumbnail
from supervisely.api.project_api import ProjectInfo
import src.globals as g
from src.ui.base_step import BaseStep

class OutputStep(BaseStep):
    def __init__(self):
        self.project_thumbnail = ProjectThumbnail()
        self.project_thumbnail.hide()
        
        widgets = [self.project_thumbnail, g.PROGRESS_BAR, g.PROGRESS_BAR_2]
        
        super().__init__(
            title="Output Project",
            description="Upload project to Supervisely and apply detector. Result project will contain 'train' dataset with split clips and 'test' dataset with original videos.",
            widgets=widgets,
            lock_message="Select train/val splits to unlock"
        )
        
        self.button.text = "Upload"
    
    def set(self, project: ProjectInfo) -> None:
        g.API.task.set_output_project(g.TASK_ID, project.id, project.name, project.image_preview_url)
        self.project_thumbnail.set(project)
        self.show_validation("Project uploaded successfully", "success")
        self.project_thumbnail.show()
        self.button.disable()

output = OutputStep()