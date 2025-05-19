import os
import shutil

from supervisely import logger
from supervisely.io.fs import mkdir
from supervisely.io.json import dump_json_file
from supervisely.project.project import OpenMode
from supervisely.project.video_project import VideoDataset, VideoProject
from supervisely.video_annotation.key_id_map import KeyIdMap

import src.globals as g
from src.scripts.video_metadata import VideoMetaData


def get_annotation_path(video_path):
    return video_path.replace("/video/", "/ann/") + ".json"


def split_project():
    mkdir(g.SPLIT_PROJECT_DIR, True)

    train_dir = os.path.join(g.SPLIT_PROJECT_DIR, "train")
    train_video_dir = os.path.join(train_dir, "video")
    train_ann_dir = os.path.join(train_dir, "ann")

    test_dir = os.path.join(g.SPLIT_PROJECT_DIR, "test")
    test_video_dir = os.path.join(test_dir, "video")
    test_ann_dir = os.path.join(test_dir, "ann")

    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(train_video_dir, exist_ok=True)
    os.makedirs(train_ann_dir, exist_ok=True)
    os.makedirs(test_video_dir, exist_ok=True)
    os.makedirs(test_ann_dir, exist_ok=True)

    src_meta_path = os.path.join(g.PROJECT_DIR, "meta.json")
    dst_meta_path = os.path.join(g.SPLIT_PROJECT_DIR, "meta.json")
    if not os.path.exists(dst_meta_path) and os.path.exists(src_meta_path):
        shutil.copy(src_meta_path, dst_meta_path)
    dump_json_file(KeyIdMap().to_dict(), os.path.join(g.SPLIT_PROJECT_DIR, "key_id_map.json"))

    # get videos paths in the project
    video_paths = {}
    project = VideoProject(g.PROJECT_DIR, OpenMode.READ)
    for dataset in project.datasets:
        dataset: VideoDataset
        for name, video_path, ann_path in dataset.items():
            video_info = dataset.get_item_info(name)
            video_paths[video_info.id] = (name, video_path, ann_path)

    train_size = int(len(g.VIDEOS_TO_UPLOAD) * g.SPLIT_RATIO)
    g.TRAIN_VIDEOS = g.VIDEOS_TO_UPLOAD[:train_size]
    g.TEST_VIDEOS = g.VIDEOS_TO_UPLOAD[train_size:]
    with g.PROGRESS_BAR(message="Splitting videos", total=len(g.VIDEOS_TO_UPLOAD)) as progress_bar:
        g.PROGRESS_BAR.show()
        for video_metadata in g.TRAIN_VIDEOS.copy():
            video_metadata: VideoMetaData
            _, src_video_path, src_ann_path = video_paths[video_metadata.video_id]

            unique_name = f"{video_metadata.dataset_id}_{video_metadata.name}"
            dst_video_path = os.path.join(train_video_dir, unique_name)
            dst_ann_path = os.path.join(train_ann_dir, unique_name + ".json")

            if not os.path.exists(dst_video_path) and os.path.exists(src_ann_path):
                shutil.copy(src_video_path, dst_video_path)
                shutil.copy(src_ann_path, dst_ann_path)

                video_metadata.path = dst_video_path
                video_metadata.set_split_path(dst_video_path)
            else:
                logger.debug(
                    f"Video '{video_metadata.name}' already exists in train directory. It was removed from train videos."
                )
                g.TRAIN_VIDEOS.remove(video_metadata)
            progress_bar.update(1)

        for video_metadata in g.TEST_VIDEOS.copy():
            video_metadata: VideoMetaData
            _, src_video_path, src_ann_path = video_paths[video_metadata.video_id]

            unique_name = f"{video_metadata.dataset_id}_{video_metadata.name}"
            dst_video_path = os.path.join(test_video_dir, unique_name)
            dst_ann_path = os.path.join(test_ann_dir, unique_name + ".json")

            if not os.path.exists(dst_video_path) and os.path.exists(src_ann_path):
                shutil.copy(src_video_path, dst_video_path)
                shutil.copy(src_ann_path, dst_ann_path)

                video_metadata.path = dst_video_path
                video_metadata.set_split_path(dst_video_path)
            else:
                logger.debug(
                    f"Video '{video_metadata.name}' already exists in test directory. It was removed from test videos."
                )
                g.TEST_VIDEOS.remove(video_metadata)
            progress_bar.update(1)

    g.PROGRESS_BAR.hide()
    return g.SPLIT_PROJECT_DIR
