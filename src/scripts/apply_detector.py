from typing import List
from supervisely.project import ProjectMeta
from supervisely.api.video.video_api import VideoInfo
from supervisely.annotation.obj_class import ObjClass
import src.globals as g
from supervisely.nn.inference.session import Session
from supervisely.video_annotation.video_annotation import (
    VideoAnnotation,
    VideoObjectCollection,
    FrameCollection,
    VideoFigure,
)
from supervisely.video_annotation.frame import Frame
from supervisely.video_annotation.video_object import VideoObject
from supervisely.annotation.annotation import Annotation, ObjClassCollection
from supervisely import logger
from src.scripts.cache import update_detection_status
from supervisely.geometry.rectangle import Rectangle


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
    g.DST_PROJECT_META.add_obj_class(mouse_obj_class)
    g.API.project.update_meta(g.DST_PROJECT_ID, g.DST_PROJECT_META.to_json())
    logger.debug(f"Updated project meta with 'mouse' object class")


def apply_detector():
    detector = Session(g.API, g.SESSION_ID)
    model_meta = detector.get_model_meta()
    mouse_obj_class = g.DST_PROJECT_META.get_obj_class("mouse")
    if mouse_obj_class is None:
        update_dst_project_meta()

    with g.PROGRESS_BAR(message="Detecting videos", total=len(g.VIDEOS_TO_DETECT)) as pbar:
        g.PROGRESS_BAR.show()
        for video in g.VIDEOS_TO_DETECT:
            video_id = video.id
            video_shape = (video.frame_height, video.frame_width)

            iterator = detector.inference_video_id_async(video_id)
            g.PROGRESS_BAR_2.show()
            predictions = list(g.PROGRESS_BAR_2(iterator, message="Inferring video"))
            g.PROGRESS_BAR_2.hide()

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
            update_detection_status(str(video_id))

            pbar.update(1)
    g.PROGRESS_BAR.hide()
