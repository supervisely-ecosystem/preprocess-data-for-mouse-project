from supervisely.api.video.video_api import VideoInfo

class VideoMetaData:
    def __init__(self, name, dataset, video_id=None, path=None):
        self.name = name
        self.dataset = dataset
        self.video_id = video_id
        self.path = path
        self.split_path = None
        self.split_ann_path = None
        self.is_detected = False
        
        self.clips = []
        self.clips_anns = []
        
        self.is_clip = False
        self.source_video = None
        self.start_frame = None
        self.end_frame = None
        self.label = None
        self.source_video_info = None
    
    def to_dict(self):
        return {
            "name": self.name,
            "dataset": self.dataset,
            "video_id": self.video_id,
            "path": self.path,
            "is_detected": self.is_detected,
            "clips": [clip.to_dict() if isinstance(clip, VideoMetaData) else clip for clip in self.clips],
            "is_clip": self.is_clip,
            "source_video": self.source_video.name if isinstance(self.source_video, VideoMetaData) else self.source_video,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "label": self.label
        }
    
    @staticmethod
    def from_sly_video(video: VideoInfo, dataset_name: str):
        video_info = VideoMetaData(
            name=video.name,
            dataset=dataset_name,
            video_id=video.id,
        )
        video_info.source_video_info = video
        return video_info
    
    @staticmethod
    def create_clip(source_video, name, start_frame, end_frame, label):
        clip = VideoMetaData(
            name=name,
            dataset=f"train/{label}"
        )
        clip.is_clip = True
        clip.source_video = source_video
        clip.start_frame = start_frame
        clip.end_frame = end_frame
        clip.label = label
        return clip 
    
    def set_split_path(self, split_path):
        self.split_path = split_path
        self.split_ann_path = split_path.replace("/video/", "/ann/") + '.json'
