from typing import List
import src.globals as g
from supervisely.api.dataset_api import DatasetInfo
from supervisely.project.video_project import VideoProject, OpenMode
from supervisely import logger
import supervisely as sly
from supervisely.project.download import (
    copy_from_cache,
    download_fast,
    download_to_cache,
    get_cache_size,
    is_cached,
)

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

def download_with_cache(dataset_infos: List[DatasetInfo], total_images: int) -> None:
    to_download = [info for info in dataset_infos if not is_cached(g.PROJECT_ID, info.name)]
    cached = [info for info in dataset_infos if is_cached(g.PROJECT_ID, info.name)]

    logger.info(get_cache_log_message(cached, to_download))
    with g.PROGRESS_BAR(message="Downloading input data", total=total_images) as pbar:
        logger.debug("Downloading project data with cache")
        g.PROGRESS_BAR.show()
        download_to_cache(
            api=g.API,
            project_id=g.PROJECT_ID,
            dataset_infos=dataset_infos,
            log_progress=True,
            progress_cb=pbar.update,
        )

    total_cache_size = sum(get_cache_size(g.PROJECT_ID, ds.name) for ds in dataset_infos)
    with g.PROGRESS_BAR(
        message="Retrieving data from cache",
        total=total_cache_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        g.PROGRESS_BAR.show()
        copy_from_cache(
            project_id=g.PROJECT_ID,
            dest_dir=g.PROJECT_DIR,
            dataset_names=[ds_info.name for ds_info in dataset_infos],
            progress_cb=pbar.update,
        )
    g.PROGRESS_BAR.hide()

def download_no_cache(dataset_infos: List[DatasetInfo], total_images: int) -> None:
    with g.PROGRESS_BAR(message="Downloading input data", total=total_images) as pbar:
        logger.debug("Downloading project data without cache")
        g.PROGRESS_BAR.show()
        download_fast(
            api=g.API,
            project_id=g.PROJECT_ID,
            dest_dir=g.PROJECT_DIR,
            dataset_ids=[ds_info.id for ds_info in dataset_infos],
            log_progress=True,
            progress_cb=pbar.update,
        )
    g.PROGRESS_BAR.hide()


def download_project() -> None:
    dataset_infos = [dataset for _, dataset in g.API.dataset.tree(g.PROJECT_ID)]
    total_images = sum(ds_info.images_count for ds_info in dataset_infos)
    if not g.USE_CACHE or sly.is_development():
        download_no_cache(dataset_infos, total_images)
        VideoProject(g.PROJECT_DIR, OpenMode.READ)
        return

    try:
        download_with_cache(dataset_infos, total_images)
    except Exception:
        logger.warning("Failed to retrieve project from cache. Downloading it", exc_info=True)
        if sly.fs.dir_exists(g.PROJECT_DIR):
            sly.fs.clean_dir(g.PROJECT_DIR)
        download_no_cache(dataset_infos, total_images)
    finally:
        VideoProject(g.PROJECT_DIR, OpenMode.READ)
        logger.info(f"Project downloaded successfully to: '{g.PROJECT_DIR}'")