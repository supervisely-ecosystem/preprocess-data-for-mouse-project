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
TEAM_FILES_DIR = "/mouse-project-data/"

# Project information
PROJECT_ID: int = sly.env.project_id()
PROJECT_INFO: sly.ProjectInfo = API.project.get_info_by_id(PROJECT_ID)
PROJECT_META: sly.ProjectMeta = sly.ProjectMeta.from_json(API.project.get_meta(PROJECT_ID))

DST_PROJECT_NAME = "Training Data Test"
DST_PROJECT = API.project.get_or_create(WORKSPACE_ID, DST_PROJECT_NAME, type=sly.ProjectType.VIDEOS)
DST_PROJECT_ID = DST_PROJECT.id

# Directory paths
PROJECT_DIR: str = os.path.join(APP_DATA_DIR, "sly_project")
SPLIT_PROJECT_DIR: str = os.path.join(APP_DATA_DIR, "sly_split")

# Application settings
USE_CACHE: bool = True
SESSION_ID: int = None
SPLIT_RATIO: float = 0.8

# Progress indicators
PROGRESS_BAR: sly.app.widgets.Progress = sly.app.widgets.Progress()
PROGRESS_BAR_2: sly.app.widgets.Progress = sly.app.widgets.Progress()
PROGRESS_BAR_3: sly.app.widgets.SlyTqdm = sly.app.widgets.SlyTqdm()

# Sync manager
SYNC_MANAGER = None
NEW_VIDEOS = []
