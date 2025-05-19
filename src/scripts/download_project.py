from supervisely import logger
from supervisely.io.fs import mkdir
from supervisely.project.download import _get_cache_dir, download_to_cache
from supervisely.project.video_project import OpenMode, VideoProject

import src.globals as g


def download_src_project():
    logger.info("Downloading source project to cache")
    with g.PROGRESS_BAR(
        message="Downloading source project to cache", total=g.PROJECT_INFO.items_count
    ) as pbar:
        g.PROGRESS_BAR.show()
        download_to_cache(g.API, g.PROJECT_ID, progress_cb=pbar.update)
        g.PROGRESS_BAR.hide()
    logger.info("Project downloaded to cache")


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
    return g.CACHED_PROJECT_DIR
