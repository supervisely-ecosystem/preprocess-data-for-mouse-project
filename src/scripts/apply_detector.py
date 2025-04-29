import src.globals as g
from supervisely.nn.inference.session import Session
from supervisely.video_annotation.video_annotation import VideoAnnotation, VideoObjectCollection, FrameCollection, VideoFigure
from supervisely.video_annotation.frame import Frame
from supervisely.video_annotation.video_object import VideoObject
from supervisely.annotation.annotation import Annotation, ObjClassCollection
from supervisely import logger

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

    for frame_index, annotation_json in zip(range(frames_range[0], frames_range[1] + 1), annotation_predictions):
        if isinstance(annotation_json, dict) and "annotation" in annotation_json.keys():
            annotation_json = annotation_json["annotation"]
        frame_index_to_annotation_dict[frame_index] = Annotation.from_json(annotation_json, model_meta)

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
            vid_fig = VideoFigure(vid_obj, label.geometry, idx)
            figures.append(vid_fig)
        frames.append(Frame(idx, figures))
    frames_coll = FrameCollection(frames)
    video_ann = VideoAnnotation(video_shape, len(frames_coll), video_obj_classes, frames_coll)
    logger.info(f"Annotation has been processed: {len(frame_to_annotation)} frames")
    return video_ann

def apply_detector(project_id):
    detector = Session(g.API, g.SESSION_ID)
    model_meta = detector.get_model_meta()
    obj_classes = model_meta.obj_classes

    datasets = g.API.dataset.get_list(project_id, recursive=True)
    with g.PROGRESS_BAR(message=f"Detecting datasets", total=len(datasets)) as pbar_ds:
        g.PROGRESS_BAR.show()
        for dataset in datasets:
            dataset_id = dataset.id

            videos = g.API.video.get_list(dataset_id)
            with g.PROGRESS_BAR_2(message=f"Detecting videos in dataset: '{dataset.name}'", total=len(videos)) as pbar_item:
                g.PROGRESS_BAR_2.show()
                for video in videos:
                    video_id = video.id
                    video_shape = (video.frame_width, video.frame_height)

                    iterator = detector.inference_video_id_async(video_id)
                    g.PROGRESS_BAR_3.show()
                    predictions = list(g.PROGRESS_BAR_3(iterator, message="Inferring video"))
                    g.PROGRESS_BAR_3.hide()
                    
                    frame_range = (0, video.frames_count - 1)
                    frame_to_annotation = frame_index_to_annotation(predictions, frame_range, model_meta)
                    frame_to_annotation = filter_annotation_by_classes(frame_to_annotation, "mouse")
                    video_annotation = annotations_to_video_annotation(frame_to_annotation, obj_classes, video_shape)

                    progress_cb = g.PROGRESS_BAR_3(message="Uploading annotation", total=len(video_annotation.figures))
                    g.API.video.annotation.append(video_id, video_annotation, None, progress_cb)
                    pbar_item.update(1)
            pbar_ds.update(1)
    g.PROGRESS_BAR_2.hide()
    g.PROGRESS_BAR.hide()
