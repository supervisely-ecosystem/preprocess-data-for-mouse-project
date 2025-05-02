from typing import List, Dict
import src.globals as g
from supervisely.api.dataset_api import DatasetInfo
from supervisely.project.video_project import VideoProject, OpenMode, KeyIdMap
from supervisely import logger
import supervisely as sly
from supervisely.project.download import _get_cache_dir
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

def get_project_dir_path(dataset_path: str) -> str:
    parts = dataset_path.split('/')
    if len(parts) == 1:
        return os.path.join(g.PROJECT_DIR, parts[0])
    else:
        result_path = os.path.join(g.PROJECT_DIR, parts[0])
        current_path = result_path
        
        for part in parts[1:]:
            current_path = os.path.join(current_path, "datasets", part)
        
        return current_path

def download_video_to_cache(video_metadata, dataset_path: str):
    video_id = video_metadata.video_id
    logger.info(f"Downloading video {video_metadata.name} (id: {video_id}) to cache")
    
    cache_ds_dir = os.path.join(_get_cache_dir(g.PROJECT_ID), dataset_path)
    cache_video_path = os.path.join(cache_ds_dir, "video", video_metadata.name)
    cache_ann_path = os.path.join(cache_ds_dir, "ann", f"{video_metadata.name}.json")
    
    if os.path.exists(cache_video_path) and os.path.exists(cache_ann_path):
        logger.info(f"Video {video_metadata.name} already in cache, skipping download")
        return cache_video_path, cache_ann_path
    
    os.makedirs(os.path.dirname(cache_video_path), exist_ok=True)
    os.makedirs(os.path.dirname(cache_ann_path), exist_ok=True)
    
    g.API.video.download_path(video_id, cache_video_path)
    ann_json = g.API.video.annotation.download(video_id)
    sly.json.dump_json_file(ann_json, cache_ann_path)
    return cache_video_path, cache_ann_path

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
    sly.json.dump_json_file(g.PROJECT_META.to_json(), os.path.join(g.CACHED_PROJECT_DIR, "meta.json"))
    if os.path.exists(os.path.join(g.CACHED_PROJECT_DIR, "key_id_map.json")):
        sly.fs.silent_remove(os.path.join(g.CACHED_PROJECT_DIR, "key_id_map.json"))
    sly.json.dump_json_file(KeyIdMap().to_dict(), os.path.join(g.CACHED_PROJECT_DIR, "key_id_map.json"))

def download_project():
    def get_full_dataset_path(dataset_id):
        dataset = datasets_by_id[dataset_id]
        if dataset.parent_id is None:
            return dataset.name
        else:
            parent_path = get_full_dataset_path(dataset.parent_id)
            return f"{parent_path}/datasets/{dataset.name}"
    
    create_project_dir()
    create_cache_project_dir()
    
    all_datasets = g.API.dataset.get_list(g.PROJECT_ID, recursive=True)
    datasets_by_id = {ds.id: ds for ds in all_datasets}
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
            logger.warning(f"Multiple datasets with name {dataset_name} found. Using the first one.")
            dataset = matching_datasets[0]
            dataset_id = dataset.id
            dataset_path = get_full_dataset_path(dataset_id)
        else:
            logger.warning(f"Dataset {dataset_name} not found for video {video_metadata.name}")
            continue
        
        video_dataset_info[video_metadata.video_id] = {
            'dataset_id': dataset_id,
            'dataset_path': dataset_path
        }
    
    with g.PROGRESS_BAR(message="Downloading and processing videos", total=len(g.VIDEOS_TO_UPLOAD)) as pbar:
        g.PROGRESS_BAR.show()
        
        for video_metadata in g.VIDEOS_TO_UPLOAD:
            video_id = video_metadata.video_id
            
            if video_id not in video_dataset_info:
                logger.warning(f"No dataset info for video {video_metadata.name} (id: {video_id}), skipping")
                pbar.update(1)
                continue
            
            dataset_info = video_dataset_info[video_id]
            dataset_path = dataset_info['dataset_path']
            
            cache_dir = _get_cache_dir(g.PROJECT_ID, dataset_path)
            cache_video_path = os.path.join(cache_dir, "video", video_metadata.name)
            cache_ann_path = os.path.join(cache_dir, "ann", f"{video_metadata.name}.json")
            
            if not (os.path.exists(cache_video_path) and os.path.exists(cache_ann_path)):
                try:
                    cache_video_path, cache_ann_path = download_video_to_cache(video_metadata, dataset_path)
                except Exception as e:
                    logger.error(f"Error downloading video {video_metadata.name}: {str(e)}")
                    pbar.update(1)
                    continue
            
            project_video_dir = os.path.join(g.PROJECT_DIR, dataset_path, "video")
            project_ann_dir = os.path.join(g.PROJECT_DIR, dataset_path, "ann")
            os.makedirs(project_video_dir, exist_ok=True)
            os.makedirs(project_ann_dir, exist_ok=True)
            
            project_video_path = os.path.join(project_video_dir, video_metadata.name)
            project_ann_path = os.path.join(project_ann_dir, f"{video_metadata.name}.json")
            
            if not os.path.exists(project_video_path):
                shutil.copy(cache_video_path, project_video_path)
            
            if not os.path.exists(project_ann_path):
                shutil.copy(cache_ann_path, project_ann_path)
            
            video_metadata.path = project_video_path
            pbar.update(1)
    