from supervisely.app.widgets import TrainValSplits, RandomSplitsTable
import src.globals as g
from src.ui.base_step import BaseStep

class SplitsStep(BaseStep):
    def __init__(self):
        self.train_val_splits = RandomSplitsTable(items_count=100)
        self.train_val_splits.hide()
        
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