from typing import List, Dict
import src.globals as g
from supervisely.api.dataset_api import DatasetInfo
from supervisely.project.video_project import VideoProject, OpenMode, KeyIdMap
from supervisely import logger
import supervisely as sly
from supervisely.project.download import (
    _get_cache_dir,
    download_to_cache,
    copy_from_cache,
    get_cache_size,
)
from supervisely import batched
import os
import shutil
from supervisely.io.fs import mkdir


def get_dataset_paths():
    all_datasets = g.API.dataset.get_list(g.PROJECT_ID, recursive=True)
    datasets_by_id = {ds.id: ds for ds in all_datasets}

    def get_full_dataset_path(dataset_id):
        dataset = datasets_by_id[dataset_id]
        if dataset.parent_id is None:
            return dataset.name
        else:
            parent_path = get_full_dataset_path(dataset.parent_id)
            return f"{parent_path}/datasets/{dataset.name}"

    video_dataset_info = {}
    for video_metadata in g.VIDEOS_TO_UPLOAD:
        dataset_id = video_metadata.dataset_id
        dataset_name = video_metadata.dataset
        dataset_path = get_full_dataset_path(dataset_id)

        already_in = video_dataset_info.get(video_metadata.video_id, None)
        if already_in is not None:
            print(f"Video {video_metadata.name} already in video_dataset_info")
            continue

        video_dataset_info[video_metadata.video_id] = {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "dataset_path": dataset_path,
        }
    return video_dataset_info


def download_videos_to_cache(video_dataset_info):
    logger.info(f"Downloading {len(g.VIDEOS_TO_UPLOAD)} videos to cache")
    with g.PROGRESS_BAR(
        message="Downloading videos to cache", total=len(g.VIDEOS_TO_UPLOAD)
    ) as pbar:
        g.PROGRESS_BAR.show()
        for video_batch in batched(g.VIDEOS_TO_UPLOAD, batch_size=10):
            filtered_batch = []
            for video_metadata in video_batch:
                if video_metadata.video_id not in video_dataset_info:
                    logger.warning(
                        f"No dataset info for video {video_metadata.name} (id: {video_metadata.video_id}), skipping"
                    )
                    pbar.update(1)
                    continue
                filtered_batch.append(video_metadata)

            if not filtered_batch:
                continue

            video_ids = []
            cache_video_paths = []
            cache_ann_paths = []
            video_metadata_by_id = {}
            for video_metadata in filtered_batch:
                video_id = video_metadata.video_id
                dataset_path = video_dataset_info[video_id]["dataset_path"]

                cache_ds_dir = os.path.join(_get_cache_dir(g.PROJECT_ID), dataset_path)
                os.makedirs(os.path.join(cache_ds_dir, "video"), exist_ok=True)
                os.makedirs(os.path.join(cache_ds_dir, "ann"), exist_ok=True)

                cache_video_path = os.path.join(cache_ds_dir, "video", video_metadata.name)
                cache_ann_path = os.path.join(cache_ds_dir, "ann", f"{video_metadata.name}.json")
                if not os.path.exists(cache_video_path):
                    video_ids.append(video_id)
                    cache_video_paths.append(cache_video_path)
                    cache_ann_paths.append(cache_ann_path)
                    video_metadata_by_id[video_id] = {
                        "metadata": video_metadata,
                        "dataset_path": dataset_path,
                        "cache_video_path": cache_video_path,
                        "cache_ann_path": cache_ann_path,
                    }

            if len(video_ids) > 0:
                loop = sly.utils.get_or_create_event_loop()
                loop.run_until_complete(
                    g.API.video.download_paths_async(video_ids, cache_video_paths)
                )
                ann_infos = loop.run_until_complete(
                    g.API.video.annotation.download_bulk_async(video_ids)
                )

                for ann_info, cache_ann_path in zip(ann_infos, cache_ann_paths):
                    sly.json.dump_json_file(ann_info, cache_ann_path)
            pbar.update(len(filtered_batch))
    logger.info("Videos downloaded to cache")


def copy_videos_from_cache_to_project(video_dataset_info):
    logger.info(f"Retrieving {len(g.VIDEOS_TO_UPLOAD)} videos from cache")
    with g.PROGRESS_BAR(
        message="Retrieving videos from cache", total=len(g.VIDEOS_TO_UPLOAD)
    ) as pbar:
        g.PROGRESS_BAR.show()

        for video_metadata in g.VIDEOS_TO_UPLOAD:
            if video_metadata.video_id not in video_dataset_info:
                logger.warning(
                    f"No dataset info for video '{video_metadata.name}' (id: {video_metadata.video_id}), skipping"
                )
                pbar.update(1)
                continue

            dataset_path = video_dataset_info[video_metadata.video_id]["dataset_path"]
            cache_ds_dir = os.path.join(_get_cache_dir(g.PROJECT_ID), dataset_path)
            cache_video_path = os.path.join(cache_ds_dir, "video", video_metadata.name)
            cache_ann_path = os.path.join(cache_ds_dir, "ann", f"{video_metadata.name}.json")
            if not os.path.exists(cache_video_path):
                logger.warning(f"Video '{video_metadata.name}' not found in cache, skipping")
                pbar.update(1)
                continue

            if not os.path.exists(cache_ann_path):
                logger.warning(
                    f"Annotation for video '{video_metadata.name}' not found in cache, skipping"
                )
                pbar.update(1)
                continue

            project_dir_path = os.path.join(g.PROJECT_DIR, dataset_path)
            project_video_dir = os.path.join(project_dir_path, "video")
            project_ann_dir = os.path.join(project_dir_path, "ann")
            os.makedirs(project_video_dir, exist_ok=True)
            os.makedirs(project_ann_dir, exist_ok=True)

            project_video_path = os.path.join(project_video_dir, video_metadata.name)
            if not os.path.exists(project_video_path):
                shutil.copy(cache_video_path, project_video_path)

            project_ann_path = os.path.join(project_ann_dir, f"{video_metadata.name}.json")
            if not os.path.exists(project_ann_path):
                shutil.copy(cache_ann_path, project_ann_path)

            video_metadata.path = project_video_path
            pbar.update(1)
    logger.info("Videos retrieved from cache")


def download_src_project():
    logger.info("Downloading source project to cache")
    with g.PROGRESS_BAR(
        message="Downloading source project to cache", total=g.PROJECT_INFO.items_count
    ) as pbar:
        g.PROGRESS_BAR.show()
        download_to_cache(g.API, g.PROJECT_ID, progress_cb=pbar.update)
        g.PROGRESS_BAR.hide()
    logger.info("Project downloaded to cache")

    logger.info("Retrieving source project from cache")
    cache_size = get_cache_size(g.PROJECT_ID)
    with g.PROGRESS_BAR(
        message="Retrieving source project from cache",
        total=cache_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        g.PROGRESS_BAR.show()
        copy_from_cache(g.PROJECT_ID, g.PROJECT_DIR, progress_cb=pbar.update)
        g.PROGRESS_BAR.hide()
    logger.info("Source project retrieved from cache")


def download_dst_project():
    target_datasets = g.API.dataset.get_list(g.DST_PROJECT_ID, recursive=True)
    target_items = sum(ds.items_count for ds in target_datasets)
    logger.debug(
        "Downloading destination project",
        extra={"project_id": g.DST_PROJECT_ID, "items": target_items},
    )
    with g.PROGRESS_BAR(message="Downloading destination project", total=target_items) as pbar:
        g.PROGRESS_BAR.show()
        if len(target_datasets) > 0:
            download_to_cache(g.API, g.DST_PROJECT_ID, progress_cb=pbar.update)
        else:
            mkdir(g.DST_PROJECT_PATH, True)
            video_project = VideoProject(g.DST_PROJECT_PATH, OpenMode.CREATE)
            video_project.set_meta(g.DST_PROJECT_META)
        g.PROGRESS_BAR.hide()


def download_project():
    download_src_project()
    return g.PROJECT_DIR
