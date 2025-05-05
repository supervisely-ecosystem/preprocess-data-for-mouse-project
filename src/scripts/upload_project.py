import os
import src.globals as g
from typing import List
from supervisely import batched
from supervisely.api.video.video_api import VideoInfo
from supervisely import logger
from src.scripts.cache import add_video_to_cache, add_single_clip_to_cache

def upload_test_videos() -> List[VideoInfo]:
    if g.TEST_VIDEOS:
        # Get or create a dataset for test videos
        test_dataset = g.API.dataset.get_or_create(g.DST_PROJECT_ID, "test")
        with g.PROGRESS_BAR(message=f"Uploading test videos", total=len(g.TEST_VIDEOS)) as pbar:
            g.PROGRESS_BAR.show()
            for video_metadata_batch in batched(g.TEST_VIDEOS, 10):
                validated_batch = []
                for video_metadata in video_metadata_batch:
                    if not os.path.exists(video_metadata.split_path):
                        logger.warning(f"Test video file not found: {video_metadata.split_path}")
                        pbar.update(1)
                        continue
                    validated_batch.append(video_metadata)

                video_names = [video_metadata.name for video_metadata in validated_batch]
                video_links = [video_metadata.source_video_info.link for video_metadata in validated_batch]
                uploaded_batch = g.API.video.upload_links(
                    dataset_id=test_dataset.id,
                    links=video_links,
                    names=video_names,
                )
                
                # Добавляем видео в кэш
                for video_metadata in validated_batch:   
                    video_metadata.is_test = True
                    add_video_to_cache(video_metadata, is_uploaded=True, is_detected=False)
                g.VIDEOS_TO_DETECT.extend(uploaded_batch)
                pbar.update(len(validated_batch))
            g.PROGRESS_BAR.hide()

def upload_train_videos() -> List[VideoInfo]:
    train_dataset = g.API.dataset.get_or_create(g.DST_PROJECT_ID, "train")
    label_datasets = {}
    for label in g.CLIP_LABELS:
        label_dataset = g.API.dataset.get_or_create(g.DST_PROJECT_ID, label, parent_id=train_dataset.id)
        label_datasets[label] = label_dataset
    
    all_clips = {}
    for video_metadata in g.TRAIN_VIDEOS:
        for clip_metadata in video_metadata.clips:
            all_clips[clip_metadata.label] = clip_metadata
    
    if len(all_clips) > 0:
        with g.PROGRESS_BAR(message=f"Uploading training clips", total=len(all_clips)) as pbar:
            g.PROGRESS_BAR.show()
            for clips_batch in batched(all_clips, 10):
                validated_batch = []
                for clip_metadata in clips_batch:
                    if not os.path.exists(clip_metadata.path):
                        logger.warning(f"Clip file not found: {clip_metadata.path}")
                        pbar.update(1)
                        continue
                    validated_batch.append(clip_metadata)

                video_names = [clip_metadata.name for clip_metadata in validated_batch]
                video_paths = [clip_metadata.path for clip_metadata in validated_batch]
                uploaded_batch = g.API.video.upload_paths(
                    dataset_id=label_datasets[clip_metadata.label].id,
                    names=video_names,
                    paths=video_paths,
                )
                    
                for clip_metadata in validated_batch:
                    clip_metadata.clip_id = uploaded_batch[clip_metadata.name].id
                pbar.update(len(validated_batch))
                
                for clip_metadata in validated_batch:
                    add_single_clip_to_cache(clip_metadata)
                g.VIDEOS_TO_DETECT.extend(uploaded_batch)
            g.PROGRESS_BAR.hide()
    
    for video_metadata in g.TRAIN_VIDEOS:
        add_video_to_cache(video_metadata, is_uploaded=True, is_detected=False)

def upload_project() -> List[VideoInfo]:
    upload_train_videos()
    upload_test_videos()
