import os
import src.globals as g
from typing import List
from supervisely import batched
from supervisely.api.video.video_api import VideoInfo
from supervisely import logger
from src.scripts.cache import add_video_to_cache, add_single_clip_to_cache

def upload_test_videos() -> List[VideoInfo]:
    """Uploads only new videos to the target project."""
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
                uploaded_batch = []
                for video_metadata in validated_batch:
                    vid_info = g.API.video.get_info_by_id(video_metadata.video_id)
                    uploaded_video = g.API.video.add_existing(
                        dataset_id=test_dataset.id,
                        video_info=vid_info,
                        name=video_metadata.name,
                    )

                    # Upload video
                    # uploaded_video = g.API.video.upload_path(
                    #     dataset_id=test_dataset.id,
                    #     name=video_info.name,
                    #     path=video_info.split_path
                    # )
                    uploaded_batch.append(uploaded_video)
                    pbar.update(1)
                
                # Добавляем видео в кэш
                for video_metadata in validated_batch:   
                    video_metadata.is_test = True
                    add_video_to_cache(video_metadata, is_uploaded=True, is_detected=False)
                g.VIDEOS_TO_DETECT.extend(uploaded_batch)
            g.PROGRESS_BAR.hide()

def upload_train_videos() -> List[VideoInfo]:
    # Create datasets
    train_dataset = g.API.dataset.get_or_create(g.DST_PROJECT_ID, "train")
    label_datasets = {}
    for label in g.CLIP_LABELS:
        label_dataset = g.API.dataset.get_or_create(g.DST_PROJECT_ID, label, parent_id=train_dataset.id)
        label_datasets[label] = label_dataset
    
    # Collect all clips from training videos
    all_clips = []
    for video_metadata in g.TRAIN_VIDEOS:
        all_clips.extend(video_metadata.clips)
    
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

                uploaded_batch = []
                for clip_metadata in validated_batch:
                    # Upload clip
                    uploaded_clip = g.API.video.upload_path(
                        dataset_id=label_datasets[clip_metadata.label].id,
                        name=clip_metadata.name,
                        path=clip_metadata.path,
                    )
                    
                    # Присваиваем clip_id после загрузки
                    clip_metadata.clip_id = uploaded_clip.id
                    uploaded_batch.append(uploaded_clip)
                    pbar.update(1)
                
                # Обновляем кеш после каждого батча
                for clip_metadata in validated_batch:
                    add_single_clip_to_cache(clip_metadata)
                g.VIDEOS_TO_DETECT.extend(uploaded_batch)
            g.PROGRESS_BAR.hide()
    
    # Обновляем статус исходных видео как загруженных
    for video_metadata in g.TRAIN_VIDEOS:
        # Обновляем статус самого видео как загруженного
        add_video_to_cache(video_metadata, is_uploaded=True, is_detected=False)

def upload_project() -> List[VideoInfo]:
    """Uploads only new videos to the target project."""
    upload_test_videos()
    upload_train_videos()
