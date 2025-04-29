import os
import src.globals as g
import pandas as pd
from supervisely.project.video_project import VideoProject, VideoDataset, OpenMode
from supervisely import batched
from supervisely.project.project import ProjectType
from supervisely.api.project_api import ProjectInfo
from supervisely.io.fs import get_file_name_with_ext

def upload_project() -> ProjectInfo:
    clips_csv = os.path.join(g.SPLIT_PROJECT_DIR, "clips.csv")
    clips_df = pd.read_csv(clips_csv)

    # source_id, start, end, label, orig_path
    clip_data_map = {}
    for index, row in clips_df.iterrows():
        clip_data_map[row["clip_file"]] = {
            "original_video": row["orig_file"],
            "start": row["start"],
            "end": row["end"],
            "label": row["label"],
        }

    project = VideoProject(g.SPLIT_PROJECT_DIR, OpenMode.READ)
    res_project = g.API.project.create(g.WORKSPACE_ID, g.DST_PROJECT_NAME, type=ProjectType.VIDEOS, change_name_if_conflict=True)

    train_ds_id = None
    with g.PROGRESS_BAR(message="Uploading Datasets", total=len(project.datasets)) as pbar:
        g.PROGRESS_BAR.show()
        for dataset in project.datasets:
            dataset: VideoDataset
            dataset_name = dataset.name
            parent_id = None
            if dataset.name.startswith("train/"):
                parent_id = train_ds_id
                dataset_name = dataset.name[len("train/"):]
                
            res_dataset = g.API.dataset.create(res_project.id, dataset_name, parent_id=parent_id)
            if dataset.name == "train":
                train_ds_id = res_dataset.id

            video_paths = [os.path.join(dataset.item_dir, video) for video in os.listdir(dataset.item_dir)]
            with g.PROGRESS_BAR_2(message="Uploading Videos", total=len(video_paths)) as pbar_video:
                g.PROGRESS_BAR_2.show()
                for video_batch in batched(video_paths, batch_size=10):
                    video_names = [get_file_name_with_ext(video) for video in video_batch]
                    metas = None
                    if dataset.name == "train":
                        metas = [clip_data_map[video] for video in video_batch]
                    g.API.video.upload_paths(
                        dataset_id=res_dataset.id,
                        names=video_names,
                        paths=video_batch,
                        metas=metas,
                    )
                    pbar_video.update(len(video_batch))
            pbar.update(1)
    g.PROGRESS_BAR.hide()
    g.PROGRESS_BAR_2.hide()
    return res_project
