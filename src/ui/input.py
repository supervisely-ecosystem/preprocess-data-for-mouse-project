from supervisely.app.widgets import ProjectThumbnail, Checkbox, Text, Field
import src.globals as g
from supervisely.project.download import is_cached, _get_cache_dir
from src.scripts.video_metadata import VideoMetaData
from src.ui.base_step import BaseStep
from src.scripts.cache import download_cache, load_cache, save_cache, upload_cache
from supervisely import logger


class InputStep(BaseStep):
    def __init__(self):
        self.source_project_thumbnail = ProjectThumbnail(g.PROJECT_INFO)
        self.source_project_field = Field(
            title="Source Project",
            description="Data from this project will be prepared for training",
            content=self.source_project_thumbnail,
        )

        self.target_project_thumbnail = ProjectThumbnail(g.DST_PROJECT_INFO)
        self.target_project_field = Field(
            title="Target Project",
            description="Data from this project will be used for training",
            content=self.target_project_thumbnail,
        )

        if is_cached(g.PROJECT_ID):
            _text = "Use cached data stored on the agent to optimize project download"
        else:
            _text = "Cache data on the agent to optimize project download for future trainings"

        self.use_cache_text = Text(_text)
        self.use_cache_checkbox = Checkbox(self.use_cache_text, checked=True)
        self.use_cache_checkbox.disable()

        widgets = [
            self.source_project_field,
            self.target_project_field,
            self.use_cache_checkbox,
            g.PROGRESS_BAR_PROJECT,
        ]

        super().__init__(
            title="Input Project",
            description="Selected project from which items and annotations will be downloaded",
            widgets=widgets,
        )

        self.show_validation("", "text")
        self.hide_validation()

    def check_project(self):
        logger.info("Fetching Project Data")

        cache_data = download_cache()
        source_datasets = g.API.dataset.get_list(g.PROJECT_ID, recursive=True)
        target_datasets = g.API.dataset.get_list(g.DST_PROJECT_ID, recursive=True)
        total_datasets = len(source_datasets) + len(target_datasets)

        source_videos = {}
        target_videos_by_id = {}
        with g.PROGRESS_BAR_PROJECT(message="Fetching Datasets", total=total_datasets) as pbar:
            g.PROGRESS_BAR_PROJECT.show()
            for ds in source_datasets:
                videos = g.API.video.get_list(ds.id)
                for v in videos:
                    source_videos[str(v.id)] = {
                        "video": v,
                        "dataset_id": ds.id,
                        "dataset_name": ds.name,
                    }
                pbar.update(1)

            for ds in target_datasets:
                vids = g.API.video.get_list(ds.id)
                for v in vids:
                    target_videos_by_id[str(v.id)] = v
                pbar.update(1)
        g.PROGRESS_BAR_PROJECT.hide()

        g.VIDEOS_TO_UPLOAD = []
        g.VIDEOS_TO_DETECT = []

        # Determine videos to upload or detect
        videos_cache = cache_data.get("videos", {})
        target_map = cache_data.get("target_to_source", {})

        for src_id, src_vid_data in source_videos.items():
            video_info = src_vid_data["video"]
            if src_id not in videos_cache:
                vm = VideoMetaData.from_sly_video(
                    video_info,
                    src_vid_data["dataset_name"],
                    dataset_id=int(src_vid_data["dataset_id"]),
                )
                g.VIDEOS_TO_UPLOAD.append(vm)
            else:
                cache_entry = videos_cache[src_id]
                if not cache_entry.get("is_uploaded", False):
                    vm = VideoMetaData.from_sly_video(
                        video_info,
                        src_vid_data["dataset_name"],
                        dataset_id=int(src_vid_data["dataset_id"]),
                    )
                    g.VIDEOS_TO_UPLOAD.append(vm)
                elif not cache_entry.get("is_detected", False):
                    target_id = cache_entry.get("train_data_id")
                    if target_id and str(target_id) in target_videos_by_id:
                        g.VIDEOS_TO_DETECT.append(target_videos_by_id[str(target_id)])

        for target_id, map_info in target_map.items():
            source_video_id = map_info["source_video_id"]
            clip_id = map_info.get("clip_id")

            if source_video_id in videos_cache:
                if clip_id:
                    if clip_id in videos_cache[source_video_id].get(
                        "clips", {}
                    ) and not videos_cache[source_video_id]["clips"][clip_id].get(
                        "is_detected", False
                    ):
                        if target_id in target_videos_by_id:
                            g.VIDEOS_TO_DETECT.append(target_videos_by_id[target_id])
                else:
                    if not videos_cache[source_video_id].get("is_detected", False):
                        if target_id in target_videos_by_id:
                            g.VIDEOS_TO_DETECT.append(target_videos_by_id[target_id])

        unique_ids = set()
        unique_detect_list = []
        for v in g.VIDEOS_TO_DETECT:
            if v.id not in unique_ids:
                unique_ids.add(v.id)
                unique_detect_list.append(v)
        g.VIDEOS_TO_DETECT = unique_detect_list

        text = (
            f"Videos to process: {len(g.VIDEOS_TO_UPLOAD)}. "
            f"Undetected videos: {len(g.VIDEOS_TO_DETECT)}. "
        )
        if len(g.VIDEOS_TO_UPLOAD) == 0 and len(g.VIDEOS_TO_DETECT) == 0:
            text += "No new videos to process. Upload new data to source project"

        self.show_validation(text, "info")


input = InputStep()
