import os
import src.globals as g
from typing import List
from supervisely import batched
from supervisely.api.video.video_api import VideoInfo
from supervisely import logger
from src.scripts.cache import add_video_to_cache, add_single_clip_to_cache

def validate_batch(batch: List[VideoInfo], is_test: bool, pbar) -> List[VideoInfo]:
    validated_batch = []
    for video_metadata in batch:
        video_path = video_metadata.path
        if is_test:
            video_path = video_metadata.split_path
        if not os.path.exists(video_path):
            logger.warning(f"Video file not found: {video_path}")
            pbar.update(1)
            continue
        validated_batch.append(video_metadata)
    return validated_batch

def upload_test_videos() -> List[VideoInfo]:
    if not g.TEST_VIDEOS:
        return
    
    logger.info(f"Uploading '{len(g.TEST_VIDEOS)}' test videos")
    test_dataset = g.API.dataset.get_or_create(g.DST_PROJECT_ID, "test")
    with g.PROGRESS_BAR(message=f"Uploading test videos", total=len(g.TEST_VIDEOS)) as pbar:
        g.PROGRESS_BAR.show()
        for video_metadata_batch in batched(g.TEST_VIDEOS, 10):
            validated_batch = validate_batch(video_metadata_batch, True, pbar)
            video_names = [video_metadata.name for video_metadata in validated_batch]
            video_links = [video_metadata.source_video_info.link for video_metadata in validated_batch]
            video_hashes = [video_metadata.source_video_info.hash for video_metadata in validated_batch]
            video_paths = [video_metadata.split_path for video_metadata in validated_batch]

            has_links = all(video_metadata.source_video_info.link for video_metadata in validated_batch)
            has_hashes = all(video_metadata.source_video_info.hash for video_metadata in validated_batch)
            
            if has_links:
                uploaded_batch = g.API.video.upload_links(
                    dataset_id=test_dataset.id,
                    links=video_links,
                    names=video_names,
                )
            elif has_hashes:
                uploaded_batch = g.API.video.upload_hashes(
                    dataset_id=test_dataset.id,
                    hashes=video_hashes,
                    names=video_names,
                )
            else:
                uploaded_batch = g.API.video.upload_paths(
                    dataset_id=test_dataset.id,
                    names=video_names,
                    paths=video_paths,
                )
            
            for video_metadata in validated_batch:   
                video_metadata.is_test = True
                add_video_to_cache(video_metadata, is_uploaded=True, is_detected=False)
            g.VIDEOS_TO_DETECT.extend(uploaded_batch)
            pbar.update(len(validated_batch))
        g.PROGRESS_BAR.hide()
    logger.info(f"'{len(g.TEST_VIDEOS)}' test videos were uploaded")

def upload_train_videos() -> List[VideoInfo]:
    if not g.TRAIN_VIDEOS:
        return
    
    logger.info(f"Uploading '{len(g.TRAIN_VIDEOS)}' training clips")
    train_dataset = g.API.dataset.get_or_create(g.DST_PROJECT_ID, "train")
    label_datasets = {}
    for label in g.CLIP_LABELS:
        label_dataset = g.API.dataset.get_or_create(g.DST_PROJECT_ID, label, parent_id=train_dataset.id)
        label_datasets[label] = label_dataset

    training_videos = {}
    for video_metadata in g.TRAIN_VIDEOS:
        training_videos[video_metadata.name] = video_metadata
    
    all_clips = {}
    for video_metadata in g.TRAIN_VIDEOS:
        for clip_metadata in video_metadata.clips:
            if clip_metadata.source_video.name not in all_clips:
                all_clips[clip_metadata.source_video.name] = {}
            if clip_metadata.label not in all_clips[clip_metadata.source_video.name]:
                all_clips[clip_metadata.source_video.name][clip_metadata.label] = []
            all_clips[clip_metadata.source_video.name][clip_metadata.label].append(clip_metadata)

    # @TODO: Add empty videos to test set
    # empty_videos = training_videos.keys() - all_clips.keys()
    # for video_name in empty_videos:
    #     g.API.video.add_existing()
    #     add_video_to_cache(training_videos[video_name], is_uploaded=True, is_detected=False)
    
    if len(all_clips) > 0:
        with g.PROGRESS_BAR(message=f"Uploading training videos", total=len(all_clips.keys())) as pbar:
            g.PROGRESS_BAR.show()
            for video_name in all_clips.keys():
                for label in all_clips[video_name].keys():
                    clips = all_clips[video_name][label]
                    with g.PROGRESS_BAR_2(message=f"Uploading '{label}' clips for video: '{video_name}'", total=len(clips)) as pbar_2:
                        g.PROGRESS_BAR_2.show()
                        for clips_batch in batched(clips, 10):
                            validated_batch = validate_batch(clips_batch, False, pbar_2)
                            clip_names = [clip_metadata.name for clip_metadata in validated_batch]
                            clip_paths = [clip_metadata.path for clip_metadata in validated_batch]
                            uploaded_batch = g.API.video.upload_paths(
                                dataset_id=label_datasets[label].id,
                                names=clip_names,
                                paths=clip_paths,
                            )
                                
                            for clip_metadata, uploaded_clip in zip(validated_batch, uploaded_batch):
                                clip_metadata.clip_id = uploaded_clip.id
                                add_single_clip_to_cache(clip_metadata)

                            pbar_2.update(len(validated_batch))
                            g.VIDEOS_TO_DETECT.extend(uploaded_batch)

                add_video_to_cache(training_videos[video_name], is_uploaded=True, is_detected=False)
                pbar.update(1)

    g.PROGRESS_BAR_2.hide()
    g.PROGRESS_BAR.hide()
    logger.info(f"'{len(g.TRAIN_VIDEOS)}' training clips were uploaded")

def upload_project() -> List[VideoInfo]:
    upload_train_videos()
    upload_test_videos()
