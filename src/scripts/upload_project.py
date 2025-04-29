import os
import pandas as pd
import src.globals as g
from supervisely.project.video_project import VideoProject, VideoDataset, OpenMode
from supervisely import batched, logger
from supervisely.project.project import ProjectType
from supervisely.api.project_api import ProjectInfo
from supervisely.io.fs import get_file_name_with_ext
from supervisely.project.download import is_cached
from src.scripts.sync_manager import VideoMetadata, SyncManager
from supervisely.api.video.video_api import VideoInfo
from typing import List, Dict

def upload_project() -> List[VideoInfo]:
    project = VideoProject(g.SPLIT_PROJECT_DIR, OpenMode.READ)
    dataset_id_map = {}
    uploaded_videos: List[VideoInfo] = []
    with g.PROGRESS_BAR(message="Uploading Datasets", total=len(project.datasets)) as pbar:
        g.PROGRESS_BAR.show()
        for dataset in project.datasets:
            dataset: VideoDataset
            dataset_name = dataset.name
            parent_id = None
            
            if dataset.name.startswith("train/"):
                parent_id = dataset_id_map.get("train")
                dataset_name = dataset.name[len("train/"):]
                
            res_dataset = g.API.dataset.get_or_create(g.DST_PROJECT_ID, dataset_name, parent_id=parent_id)
            dataset_id_map[dataset.name] = res_dataset.id

            video_paths = [os.path.join(dataset.item_dir, video) for video in os.listdir(dataset.item_dir)]
            if not video_paths:
                pbar.update(1)
                continue
                
            with g.PROGRESS_BAR_2(message="Uploading Videos", total=len(video_paths)) as pbar_video:
                g.PROGRESS_BAR_2.show()
                for video_batch in batched(video_paths, batch_size=10):
                    video_names = [get_file_name_with_ext(video) for video in video_batch]
                    metas = None
                    if dataset.name == "train":
                        metas = []
                        for video_path in video_batch:
                            video_name = get_file_name_with_ext(video_path)
                            video_data = g.SYNC_MANAGER.get_video_data(video_name)
                            metas.append(video_data.to_dict())
                    try:
                        uploaded_videos_batch = g.API.video.upload_paths(
                            dataset_id=res_dataset.id,
                            names=video_names,
                            paths=video_batch,
                            metas=metas,
                        )
                        uploaded_videos.extend(uploaded_videos_batch)
                        for video_name, uploaded_video in zip(video_names, uploaded_videos_batch):
                            g.SYNC_MANAGER.mark_as_uploaded(video_name, uploaded_video.id)
                            logger.info(f"Successfully uploaded video {video_name} to dataset {dataset_name}")
                    except Exception as e:
                        logger.error(f"Failed to upload videos {video_names}: {str(e)}")
                        raise
                    
                    pbar_video.update(len(video_batch))
            pbar.update(1)
    g.PROGRESS_BAR.hide()
    g.PROGRESS_BAR_2.hide()
    
    g.SYNC_MANAGER.set_uploaded_videos(uploaded_videos)
    return uploaded_videos
