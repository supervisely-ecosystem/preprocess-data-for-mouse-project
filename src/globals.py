import os
from typing import Optional, Any

import supervisely as sly
from dotenv import load_dotenv

# Load environment variables
if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))

API: sly.Api = sly.Api.from_env()

# Environment variables
TASK_ID: int = sly.env.task_id(raise_not_found=sly.is_production())
TEAM_ID: int = sly.env.team_id()
WORKSPACE_ID: int = sly.env.workspace_id()
APP_DATA_DIR: str = sly.app.get_synced_data_dir()

# Project information
PROJECT_ID: int = sly.env.project_id()
PROJECT_INFO: sly.ProjectInfo = API.project.get_info_by_id(PROJECT_ID)
PROJECT_META: sly.ProjectMeta = sly.ProjectMeta.from_json(API.project.get_meta(PROJECT_ID))

# Directory paths
PROJECT_DIR: str = os.path.join(APP_DATA_DIR, "sly_project")
SPLIT_PROJECT_DIR: str = os.path.join(APP_DATA_DIR, "sly_split")
DST_PROJECT_NAME: str = "Training Data" + "Test"

# Application settings
USE_CACHE: bool = True
SESSION_ID: int = None
SPLIT_RATIO: float = 0.8

# Progress indicators
PROGRESS_BAR: sly.app.widgets.Progress = sly.app.widgets.Progress()
PROGRESS_BAR_2: sly.app.widgets.Progress = sly.app.widgets.Progress()
PROGRESS_BAR_3: sly.app.widgets.SlyTqdm = sly.app.widgets.SlyTqdm()
