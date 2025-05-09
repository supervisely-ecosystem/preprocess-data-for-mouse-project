from supervisely.app.widgets import ProjectThumbnail, NotificationBox
import src.globals as g
from src.ui.base_step import BaseStep
from supervisely import is_production


class OutputStep(BaseStep):
    def __init__(self):
        self.project_thumbnail = ProjectThumbnail()
        self.project_thumbnail.hide()
        self.notification_box = NotificationBox(
            title="Do not shutdown or restart the agent",
            description="In case of interruption, you can resume the process from the same step by restarting the app",
            box_type="info",
        )
        self.notification_box.hide()

        widgets = [self.notification_box, self.project_thumbnail, g.PROGRESS_BAR, g.PROGRESS_BAR_2]

        super().__init__(
            title="Output Project",
            description="Upload project to Supervisely and apply detector. Result project will contain 'train' dataset with split clips and 'test' dataset with original videos.",
            widgets=widgets,
            lock_message="Select train/val splits to unlock",
        )

        self.button.text = "Start"

    def set(self) -> None:
        if is_production():
            upd_dst_pr_info = g.API.project.get_info_by_id(g.DST_PROJECT_ID)
            g.API.task.set_output_project(
                g.TASK_ID,
                upd_dst_pr_info.id,
                upd_dst_pr_info.name,
                upd_dst_pr_info.image_preview_url,
            )
        self.project_thumbnail.set(g.DST_PROJECT_INFO)
        self.show_validation("Training data processed successfully", "success")
        self.project_thumbnail.show()
        self.button.disable()


output = OutputStep()
