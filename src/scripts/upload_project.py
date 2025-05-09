import os
import src.globals as g
from typing import List
from supervisely import batched
from supervisely.api.video.video_api import VideoInfo
from supervisely import logger
from src.scripts.cache import (
    add_video_to_cache,
    add_single_clip_to_cache,
    upload_cache,
)


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


def move_empty_videos_to_test_set(training_videos: dict, all_clips: dict) -> List[VideoInfo]:
    empty_videos = training_videos.keys() - all_clips.keys()
    if len(empty_videos) == 0:
        return
    logger.info(f"Found '{len(empty_videos)}' videos with no clips")
    for video_name in empty_videos:
        g.TRAIN_VIDEOS.remove(training_videos[video_name])
        g.TEST_VIDEOS.append(training_videos[video_name])
    logger.info(f"Moved '{len(empty_videos)}' videos with no clips to test set")


def upload_test_videos() -> List[VideoInfo]:
    if not g.TEST_VIDEOS:
        return

    logger.info(f"Uploading '{len(g.TEST_VIDEOS)}' test videos")
    test_dataset = g.API.dataset.get_or_create(g.DST_PROJECT_ID, "test")
    with g.PROGRESS_BAR(message=f"Uploading test videos", total=len(g.TEST_VIDEOS)) as pbar:
        g.PROGRESS_BAR.show()
        for video_metadata_batch in batched(g.TEST_VIDEOS, 10):
            validated_batch = validate_batch(video_metadata_batch, True, pbar)
            video_names = [
                f"{video_metadata.dataset_id}_{video_metadata.name}"
                for video_metadata in validated_batch
            ]
            video_links = [
                video_metadata.source_video_info.link for video_metadata in validated_batch
            ]
            video_hashes = [
                video_metadata.source_video_info.hash for video_metadata in validated_batch
            ]
            video_paths = [video_metadata.split_path for video_metadata in validated_batch]

            has_links = all(
                video_metadata.source_video_info.link for video_metadata in validated_batch
            )
            has_hashes = all(
                video_metadata.source_video_info.hash for video_metadata in validated_batch
            )

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

            for i, video_metadata in enumerate(validated_batch):
                video_metadata.is_test = True
                video_metadata.train_data_id = uploaded_batch[i].id
                add_video_to_cache(
                    video_metadata, is_uploaded=True, is_detected=False, upload=False
                )
            upload_cache()
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
        label_dataset = g.API.dataset.get_or_create(
            g.DST_PROJECT_ID, label, parent_id=train_dataset.id
        )
        label_datasets[label] = label_dataset

    training_videos = {}
    for video_metadata in g.TRAIN_VIDEOS:
        training_videos[video_metadata.video_id] = video_metadata

    all_clips = {}
    for video_metadata in g.TRAIN_VIDEOS:
        for clip_metadata in video_metadata.clips:
            src_vid_id = (
                clip_metadata.source_video.video_id
                if isinstance(clip_metadata.source_video, object)
                else None
            )
            if src_vid_id not in all_clips:
                all_clips[src_vid_id] = {}
            if clip_metadata.label not in all_clips[src_vid_id]:
                all_clips[src_vid_id][clip_metadata.label] = []
            all_clips[src_vid_id][clip_metadata.label].append(clip_metadata)

    move_empty_videos_to_test_set(training_videos, all_clips)

    if len(all_clips) > 0:
        with g.PROGRESS_BAR(
            message=f"Uploading training videos", total=len(all_clips.keys())
        ) as pbar:
            g.PROGRESS_BAR.show()
            for src_vid_id in all_clips.keys():
                for label in all_clips[src_vid_id].keys():
                    clips = all_clips[src_vid_id][label]
                    with g.PROGRESS_BAR_2(
                        message=f"Uploading '{label}' clips for video id: '{src_vid_id}'",
                        total=len(clips),
                    ) as pbar_2:
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

                            for clip_metadata, uploaded_clip in zip(
                                validated_batch, uploaded_batch
                            ):
                                clip_metadata.clip_id = uploaded_clip.id
                                clip_metadata.train_data_id = uploaded_clip.id
                                add_single_clip_to_cache(clip_metadata)

                            pbar_2.update(len(validated_batch))
                            g.VIDEOS_TO_DETECT.extend(uploaded_batch)

                add_video_to_cache(training_videos[src_vid_id], is_uploaded=True, is_detected=False)
                pbar.update(1)

    g.PROGRESS_BAR_2.hide()
    g.PROGRESS_BAR.hide()
    logger.info(f"'{len(g.TRAIN_VIDEOS)}' training clips were uploaded")


def upload_project() -> List[VideoInfo]:
    upload_train_videos()
    upload_test_videos()
