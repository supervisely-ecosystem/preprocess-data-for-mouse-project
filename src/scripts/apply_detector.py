from supervisely import logger
from supervisely.annotation.annotation import Annotation, ObjClassCollection
from supervisely.annotation.obj_class import ObjClass
from supervisely.api.video.video_api import VideoInfo
from supervisely.geometry.rectangle import Rectangle
from supervisely.io.fs import mkdir
from supervisely.nn.model.model_api import ModelAPI
from supervisely.project.project import OpenMode
from supervisely.project.video_project import VideoDataset, VideoProject
from supervisely.video_annotation.frame import Frame
from supervisely.video_annotation.video_annotation import (
    FrameCollection,
    VideoAnnotation,
    VideoFigure,
    VideoObjectCollection,
)
from supervisely.video_annotation.video_object import VideoObject

import src.globals as g
from src.scripts.cache import update_detection_status
from src.scripts.download_project import download_dst_project


def filter_annotation_by_classes(annotation_predictions: dict, selected_classes: list) -> dict:
    annotation_for_frame: Annotation
    for frame_name, annotation_for_frame in annotation_predictions.items():
        filtered_labels_list = []

        for label_on_frame in annotation_for_frame.labels:
            if label_on_frame.obj_class.name in selected_classes:
                filtered_labels_list.append(label_on_frame)

        annotation_predictions[frame_name] = annotation_for_frame.clone(labels=filtered_labels_list)
    return annotation_predictions


def frame_index_to_annotation(annotation_predictions, frames_range, model_meta):
    frame_index_to_annotation_dict = {}
    for frame_index, ann_pred in zip(
        range(frames_range[0], frames_range[1] + 1), annotation_predictions
    ):
        frame_index_to_annotation_dict[frame_index] = ann_pred
    return frame_index_to_annotation_dict


def annotations_to_video_annotation(
    frame_to_annotation: dict, obj_classes: ObjClassCollection, video_shape: tuple
):
    name2vid_obj_cls = {x.name: VideoObject(x) for x in obj_classes}
    video_obj_classes = VideoObjectCollection(list(name2vid_obj_cls.values()))
    frames = []
    for idx, ann in frame_to_annotation.items():
        ann: Annotation
        figures = []
        for label in ann.labels:
            vid_obj = name2vid_obj_cls[label.obj_class.name]
            geometry = label.geometry
            vid_fig = VideoFigure(vid_obj, geometry, idx)
            figures.append(vid_fig)
        frames.append(Frame(idx, figures))
    frames_coll = FrameCollection(frames)
    video_ann = VideoAnnotation(video_shape, len(frames_coll), video_obj_classes, frames_coll)
    return video_ann


def update_dst_project_meta():
    mouse_obj_class = ObjClass(name="mouse", geometry_type=Rectangle)
    g.DST_PROJECT_META = g.DST_PROJECT_META.add_obj_class(mouse_obj_class)
    g.API.project.update_meta(g.DST_PROJECT_ID, g.DST_PROJECT_META.to_json())
    logger.debug(f"Updated project meta with 'mouse' object class")


def find_video_dataset_in_dst_project_fs(
    project: VideoProject, video_info: VideoInfo
) -> VideoDataset:
    for dataset in project.datasets:
        dataset: VideoDataset
        if dataset.item_exists(video_info.name):
            if dataset.get_item_info(video_info.name).id == video_info.id:
                return dataset
    return None


def apply_detector():
    detector = ModelAPI(g.API, g.SESSION_ID)
    model_meta = detector.get_model_meta()
    mouse_obj_class = g.DST_PROJECT_META.get_obj_class("mouse")
    if mouse_obj_class is None:
        update_dst_project_meta()

    # to ensure that the dst project is up to date
    download_dst_project()

    try:
        # @TODO: READ project always fails
        dst_project_fs = VideoProject(g.DST_PROJECT_PATH, OpenMode.READ)
        logger.info("Destination project cache found")
    except:
        logger.info("Destination project cache not found, creating new one")
        mkdir(g.DST_PROJECT_PATH, True)
        dst_project_fs = VideoProject(g.DST_PROJECT_PATH, OpenMode.CREATE)
    dst_project_fs.set_meta(g.DST_PROJECT_META)

    datasets = []
    for dataset in dst_project_fs.datasets:
        datasets.append(f"{dataset.name}, {dataset.path}")
    logger.debug(
        f"Destination project datasets: {datasets}",
        extra={"datasets": datasets},
    )

    video_id_to_dataset = {}
    for dataset in dst_project_fs.datasets:
        for video_name, _, _ in dataset.items():
            video_info = dataset.get_item_info(video_name)
            video_id_to_dataset[video_info.id] = dataset

    with g.PROGRESS_BAR(message="Detecting videos", total=len(g.VIDEOS_TO_DETECT)) as pbar:
        g.PROGRESS_BAR.show()
        for video in g.VIDEOS_TO_DETECT:
            video: VideoInfo
            video_id = video.id
            video_shape = (video.frame_height, video.frame_width)

            predictions = []
            with g.PROGRESS_BAR_2(message="Inferring video", total=video.frames_count) as pbar2:
                g.PROGRESS_BAR_2.show()
                for pred in detector.predict_detached(video_id=video_id):
                    predictions.append(pred.annotation)
                    pbar2.update(1)

            frame_range = (0, video.frames_count - 1)
            frame_to_annotation = frame_index_to_annotation(predictions, frame_range, model_meta)
            frame_to_annotation = filter_annotation_by_classes(frame_to_annotation, "mouse")
            video_annotation = annotations_to_video_annotation(
                frame_to_annotation, model_meta.obj_classes, video_shape
            )
            logger.debug(
                f"Annotation for video id: '{video_id}' has been processed: {len(frame_to_annotation)} frames"
            )

            progress_cb = g.PROGRESS_BAR_2(
                message="Uploading annotation", total=len(video_annotation.figures)
            )
            g.API.video.annotation.append(video_id, video_annotation, None, progress_cb)

            video_info = g.API.video.get_info_by_id(video_id)

            dataset: VideoDataset = video_id_to_dataset[video.id]
            dataset.add_item_file(video.name, None, video_annotation, item_info=video_info)

            update_detection_status(str(video_id))

            pbar.update(1)

    g.PROGRESS_BAR_2.hide()
    g.PROGRESS_BAR.hide()
