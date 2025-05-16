from typing import List, Dict
import src.globals as g
from supervisely.api.dataset_api import DatasetInfo
from supervisely.project.video_project import VideoProject, OpenMode, KeyIdMap
from supervisely import logger
import supervisely as sly
from supervisely.project.download import _get_cache_dir
from supervisely import batched
import os
import shutil


def get_cache_log_message(cached: bool, to_download: List[DatasetInfo]) -> str:
    if not cached:
        log_msg = "No cached datasets found"
    else:
        log_msg = "Using cached datasets: " + ", ".join(
            f"{ds_info.name} ({ds_info.id})" for ds_info in cached
        )

    if not to_download:
        log_msg += ". All datasets are cached. No datasets to download"
    else:
        log_msg += ". Downloading datasets: " + ", ".join(
            f"{ds_info.name} ({ds_info.id})" for ds_info in to_download
        )

    return log_msg


def create_project_dir():
    if not os.path.exists(g.PROJECT_DIR):
        os.makedirs(g.PROJECT_DIR)
    if os.path.exists(os.path.join(g.PROJECT_DIR, "meta.json")):
        sly.fs.silent_remove(os.path.join(g.PROJECT_DIR, "meta.json"))
    sly.json.dump_json_file(g.PROJECT_META.to_json(), os.path.join(g.PROJECT_DIR, "meta.json"))
    if os.path.exists(os.path.join(g.PROJECT_DIR, "key_id_map.json")):
        sly.fs.silent_remove(os.path.join(g.PROJECT_DIR, "key_id_map.json"))
    sly.json.dump_json_file(KeyIdMap().to_dict(), os.path.join(g.PROJECT_DIR, "key_id_map.json"))


def create_cache_project_dir():
    if not os.path.exists(g.CACHED_PROJECT_DIR):
        os.makedirs(g.CACHED_PROJECT_DIR)
    if os.path.exists(os.path.join(g.CACHED_PROJECT_DIR, "meta.json")):
        sly.fs.silent_remove(os.path.join(g.CACHED_PROJECT_DIR, "meta.json"))
    sly.json.dump_json_file(
        g.PROJECT_META.to_json(), os.path.join(g.CACHED_PROJECT_DIR, "meta.json")
    )
    if os.path.exists(os.path.join(g.CACHED_PROJECT_DIR, "key_id_map.json")):
        sly.fs.silent_remove(os.path.join(g.CACHED_PROJECT_DIR, "key_id_map.json"))
    sly.json.dump_json_file(
        KeyIdMap().to_dict(), os.path.join(g.CACHED_PROJECT_DIR, "key_id_map.json")
    )


def get_dataset_paths(project_id: int = None):
    if project_id is None:
        project_id = g.PROJECT_ID
    all_datasets = g.API.dataset.get_list(project_id, recursive=True)
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
        dataset_name = video_metadata.dataset
        dataset_id = None

        matching_datasets = [ds for ds in all_datasets if ds.name == dataset_name]
        if len(matching_datasets) == 1:
            dataset = matching_datasets[0]
            dataset_id = dataset.id
            dataset_path = get_full_dataset_path(dataset_id)
        elif len(matching_datasets) > 1:
            logger.warning(
                f"Multiple datasets with name {dataset_name} found. Using the first one."
            )
            dataset = matching_datasets[0]
            dataset_id = dataset.id
            dataset_path = get_full_dataset_path(dataset_id)
        else:
            logger.warning(f"Dataset {dataset_name} not found for video {video_metadata.name}")
            continue

        video_dataset_info[video_metadata.video_id] = {
            "dataset_id": dataset_id,
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
            if not os.path.exists(cache_video_path) or not os.path.exists(cache_ann_path):
                logger.warning(f"Video '{video_metadata.name}' not found in cache, skipping")
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


def download_project():
    create_project_dir()
    create_cache_project_dir()
    video_dataset_info = get_dataset_paths()
    download_videos_to_cache(video_dataset_info)
    copy_videos_from_cache_to_project(video_dataset_info)

    logger.info(f"Project downloaded to {g.PROJECT_DIR}")
    return g.PROJECT_DIR
