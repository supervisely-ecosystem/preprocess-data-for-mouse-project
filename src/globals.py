import os

from dotenv import load_dotenv

import supervisely as sly
from supervisely.app.widgets import Progress
from supervisely.project.download import _get_cache_dir

# Load environment variables
if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))
    # load_dotenv(os.path.expanduser("~/supervisely(dev).env"))

API: sly.Api = sly.Api.from_env(100)

# Environment variables
TASK_ID: int = sly.env.task_id(raise_not_found=sly.is_production())
TEAM_ID: int = sly.env.team_id()
WORKSPACE_ID: int = sly.env.workspace_id()
APP_DATA_DIR: str = sly.app.get_synced_data_dir()

# Project information
PROJECT_ID: int = sly.env.project_id()
PROJECT_INFO: sly.ProjectInfo = API.project.get_info_by_id(PROJECT_ID)
PROJECT_META: sly.ProjectMeta = sly.ProjectMeta.from_json(API.project.get_meta(PROJECT_ID))

DST_PROJECT_NAME = f"[{PROJECT_INFO.id}] Training Data"
DST_PROJECT_INFO = API.project.get_or_create(
    WORKSPACE_ID, DST_PROJECT_NAME, type=sly.ProjectType.VIDEOS
)
DST_PROJECT_INFO = API.project.get_info_by_id(DST_PROJECT_INFO.id)
DST_PROJECT_ID = DST_PROJECT_INFO.id
DST_PROJECT_META: sly.ProjectMeta = sly.ProjectMeta.from_json(API.project.get_meta(DST_PROJECT_ID))
DST_PROJECT_PATH = _get_cache_dir(DST_PROJECT_ID)
API.project.update_meta(DST_PROJECT_ID, PROJECT_META.to_json())


# Directory paths
CACHED_PROJECT_DIR: str = _get_cache_dir(PROJECT_ID)
PROJECT_DIR: str = os.path.join(APP_DATA_DIR, "sly_project")
SPLIT_PROJECT_DIR: str = os.path.join(APP_DATA_DIR, "sly_split")

# Application settings
USE_CACHE: bool = True
SESSION_ID: int = None
SPLIT_RATIO: float = 0.8

# Progress indicators
PROGRESS_BAR_PROJECT: Progress = Progress()
PROGRESS_BAR: Progress = Progress()
PROGRESS_BAR_2: Progress = Progress()

# Globals for video processing
TRAIN_VIDEOS = []
TEST_VIDEOS = []
VIDEOS_TO_UPLOAD = []
VIDEOS_TO_DETECT = []

# Constants for clips
CLIP_LABELS = ["idle", "Self-Grooming", "Head-Body_TWITCH"]

# Cache
REMOTE_CACHE_PATH = f"/mouse-project-data/[{PROJECT_ID}-{DST_PROJECT_ID}] cache.json"
LOCAL_CACHE_PATH = os.path.join(APP_DATA_DIR, f"[{PROJECT_ID}-{DST_PROJECT_ID}] cache.json")
