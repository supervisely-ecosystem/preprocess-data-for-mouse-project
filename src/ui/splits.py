from supervisely.app.widgets import TrainValSplits
import src.globals as g
from src.ui.base_step import BaseStep

class SplitsStep(BaseStep):
    def __init__(self):
        self.train_val_splits = TrainValSplits(g.PROJECT_ID, tags_splits=False, datasets_splits=False)
        
        widgets = [self.train_val_splits]
        
        super().__init__(
            title="Train/Val Split",
            description="Split project into train/val sets",
            widgets=widgets,
            lock_message="Connect model to unlock"
        )
        
        self.show_validation("Train/Val split selected", "success")
        self.hide_validation()
    
    def get_train_split_percent(self) -> float:
        return self.train_val_splits.get_train_split_percent()

splits = SplitsStep()