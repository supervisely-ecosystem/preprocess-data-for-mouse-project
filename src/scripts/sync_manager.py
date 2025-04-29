import os
import json
from typing import Dict, List, Optional
import src.globals as g
from supervisely import logger
from supervisely.api.dataset_api import DatasetInfo
from supervisely.api.video.video_api import VideoInfo

class VideoMetadata:
    def __init__(
        self, 
        name: str, 
        original_name: str, 
        dataset: str, is_clip: bool = False, 
        original_video: Optional[str] = None, 
        start_frame: Optional[int] = None,
        end_frame: Optional[int] = None, 
        label: Optional[int] = None,
        original_video_id: Optional[int] = None, 
        target_video_id: Optional[int] = None
    ):
        self.name = name
        self.original_name = original_name
        self.dataset = dataset
        self.is_clip = is_clip
        self.original_video = original_video
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.label = label
        self.processed = False
        self.original_video_id = original_video_id
        self.target_video_id = target_video_id
        self.uploaded = False
        self.detected = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "original_name": self.original_name,
            "dataset": self.dataset,
            "is_clip": self.is_clip,
            "original_video": self.original_video,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "label": self.label,
            "processed": self.processed,
            "original_video_id": self.original_video_id,
            "target_video_id": self.target_video_id,
            "uploaded": self.uploaded,
            "detected": self.detected
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'VideoMetadata':
        return cls(
            name=data["name"],
            original_name=data["original_name"],
            dataset=data["dataset"],
            is_clip=data["is_clip"],
            original_video=data.get("original_video"),
            start_frame=data.get("start_frame"),
            end_frame=data.get("end_frame"),
            label=data.get("label"),
            original_video_id=data.get("original_video_id"),
            target_video_id=data.get("target_video_id")
        )

class SyncManager:
    def __init__(self):
        self.cache_file = "cache.json"
        self.remote_cache_path = os.path.join(g.TEAM_FILES_DIR, self.cache_file)
        self.local_cache_path = os.path.join(g.APP_DATA_DIR, self.cache_file)
        self.videos: Dict[str, VideoMetadata] = {}
        self._uploaded_videos: List[VideoInfo] = []
        self.download_cache()

    def download_cache(self) -> None:
        try:
            if g.API.file.exists(g.TEAM_ID, self.cache_file):
                g.API.file.download(g.TEAM_ID, self.cache_file, self.remote_cache_path)
                with open(self.local_cache_path, 'r') as f:
                    data = json.load(f)
                    self.videos = {name: VideoMetadata.from_dict(video_data) 
                                 for name, video_data in data.items()}
            else:
                logger.info("Cache file not found, creating new one")
        except Exception as e:
            logger.warning(f"Failed to load cache: {str(e)}")
            self.videos = {}

    def upload_cache(self) -> None:
        try:
            data = {name: video.to_dict() for name, video in self.videos.items()}
            with open(self.local_cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            g.API.file.upload(g.TEAM_ID, self.local_cache_path, self.remote_cache_path)
        except Exception as e:
            logger.error(f"Failed to save cache: {str(e)}")

    def get_new_videos(self, source_project_id: int, target_project_id: int) -> List[VideoMetadata]:
        source_videos = []
        for dataset in g.API.dataset.get_list(source_project_id, recursive=True):
            videos = g.API.video.get_list(dataset.id)
            for video in videos:
                source_videos.append(VideoMetadata(
                    name=video.name,
                    original_name=video.name,
                    dataset=dataset.name,
                    is_clip=False,
                    original_video_id=video.id
                ))

        target_videos = set()
        for dataset in g.API.dataset.get_list(target_project_id, recursive=True):
            videos = g.API.video.get_list(dataset.id)
            for video in videos:
                target_videos.add(video.name)

        new_videos = []
        for video in source_videos:
            if video.name not in self.videos and video.name not in target_videos:
                new_videos.append(video)
                self.videos[video.name] = video

        return new_videos

    def add_clip(self, clip_info: VideoMetadata) -> None:
        self.videos[clip_info.name] = clip_info

    def get_clips_for_video(self, video_name: str) -> List[VideoMetadata]:
        return [video for video in self.videos.values() 
                if video.original_video == video_name and video.is_clip]

    def mark_as_processed(self, video_name: str) -> None:
        if video_name in self.videos:
            self.videos[video_name].processed = True

    def mark_as_uploaded(self, video_name: str, target_video_id: int) -> None:
        if video_name in self.videos:
            self.videos[video_name].uploaded = True
            self.videos[video_name].target_video_id = target_video_id

    def mark_as_detected(self, video_name: str) -> None:
        if video_name in self.videos:
            self.videos[video_name].detected = True

    def is_processed(self, video_name: str) -> bool:
        return video_name in self.videos and self.videos[video_name].processed

    def is_uploaded(self, video_name: str) -> bool:
        return video_name in self.videos and self.videos[video_name].uploaded

    def is_detected(self, video_name: str) -> bool:
        return video_name in self.videos and self.videos[video_name].detected

    def get_video_data(self, video_name: str) -> Optional[VideoMetadata]:
        return self.videos.get(video_name)

    def get_uploaded_video_ids(self) -> List[int]:
        return [video.target_video_id for video in self.videos.values() 
                if video.uploaded and video.target_video_id is not None]
    
    def get_uploaded_video_info(self) -> List[VideoInfo]:
        return [g.API.video.get_info_by_id(video_id) for video_id in self.get_uploaded_video_ids()]

    def clear_cache(self) -> None:
        self.videos = {}

    def set_uploaded_videos(self, videos: List[VideoInfo]) -> None:
        self._uploaded_videos = videos

    def get_uploaded_videos(self) -> List[VideoInfo]:
        return self._uploaded_videos 