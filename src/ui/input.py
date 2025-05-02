from supervisely.app.widgets import ProjectThumbnail, Checkbox, Text, Field
import src.globals as g
from supervisely.project.download import is_cached, _get_cache_dir
from src.scripts.video_metadata import VideoMetaData
from src.ui.base_step import BaseStep
from src.scripts.cache import download_cache, load_cache, save_cache, upload_cache
import os

class InputStep(BaseStep):
    def __init__(self):
        self.source_project_thumbnail = ProjectThumbnail(g.PROJECT_INFO)
        self.source_project_field = Field(
            title="Source Project",
            description="Data from this project will be prepared for training",
            content=self.source_project_thumbnail
        )
        
        self.target_project_thumbnail = ProjectThumbnail(g.DST_PROJECT_INFO)
        self.target_project_field = Field(
            title="Target Project",
            description="Data from this project will be used for training",
            content=self.target_project_thumbnail
        )
        
        if is_cached(g.PROJECT_ID):
            _text = "Use cached data stored on the agent to optimize project download"
        else:
            _text = "Cache data on the agent to optimize project download for future trainings"
        
        self.use_cache_text = Text(_text)
        self.use_cache_checkbox = Checkbox(self.use_cache_text, checked=True)
        self.use_cache_checkbox.disable()
        
        widgets = [self.source_project_field, self.target_project_field, self.use_cache_checkbox]
        
        super().__init__(
            title="Input Project",
            description="Selected project from which items and annotations will be downloaded",
            widgets=widgets
        )
        
        # self.show_validation("Project selected", "success")
        self.show_validation("", "text")
        self.hide_validation()

    def check_project(self):
        # Проверяем наличие cache.json на сервере и скачиваем его если он есть
        cache_data = download_cache()
        
        # Получаем все видео из исходного проекта на сервере
        original_project_data = {}
        for dataset in g.API.dataset.get_list(g.PROJECT_ID, recursive=True):
            original_project_data[dataset.name] = {video.name: video for video in g.API.video.get_list(dataset.id)}
        
        # Получаем все существующие видео на сервере из целевого проекта
        target_project_data = {}
        for dataset in g.API.dataset.get_list(g.DST_PROJECT_ID, recursive=True):
            target_project_data[dataset.name] = {video.name: video for video in g.API.video.get_list(dataset.id)}
        
        # Создаем списки для видео, которые нужно загрузить и обнаружить
        g.VIDEOS_TO_UPLOAD = []
        g.VIDEOS_TO_DETECT = []
        
        # Создаем словарь для быстрого поиска видео по ID
        target_videos_by_id = {}
        target_videos_by_name = {}
        for dataset_name, videos in target_project_data.items():
            for video_name, video in videos.items():
                target_videos_by_id[video.id] = video
                target_videos_by_name[video_name] = video
        
        # Проверяем какие видео из исходного проекта ещё не были обработаны
        for dataset_name, videos in original_project_data.items():
            for video_name, video in videos.items():
                video_id = str(video.id)
                
                # Проверяем, есть ли видео в кэше
                if video_id in cache_data.get("videos", {}):
                    cached_video = cache_data["videos"][video_id]
                    
                    # Если видео уже загружено, но не обнаружено, добавляем его в список для обнаружения
                    if cached_video.get("is_uploaded", False) and not cached_video.get("is_detected", False):
                        # Пытаемся найти соответствующее видео в целевом проекте по имени
                        video_name = cached_video.get("video_name")
                        if video_name in target_videos_by_name:
                            g.VIDEOS_TO_DETECT.append(target_videos_by_name[video_name])
                else:
                    # Видео не найдено в кэше, значит его нужно загрузить и обработать
                    video_info = VideoMetaData.from_sly_video(video, dataset_name)
                    g.VIDEOS_TO_UPLOAD.append(video_info)
        
        # Проверяем клипы в кэше - возможно есть клипы, которые загружены но не обнаружены
        for video_id, video_data in cache_data.get("videos", {}).items():
            for clip_id, clip_data in video_data.get("clips", {}).items():
                if not clip_data.get("is_detected", False):
                    # Пытаемся найти клип в целевом проекте по имени
                    clip_name = clip_data.get("clip_name")
                    if clip_name in target_videos_by_name:
                        g.VIDEOS_TO_DETECT.append(target_videos_by_name[clip_name])
        
        # Обновляем и сохраняем кэш
        # @TODO: целевой и таргет проект всегда одинаковые, если нет то ошибка
        cache_data["source_project_id"] = g.PROJECT_ID
        cache_data["target_project_id"] = g.DST_PROJECT_ID
            
        save_cache(cache_data)
        
        # Отображаем информацию о новых видео
        text = ""
        text += f"Videos to upload: {len(g.VIDEOS_TO_UPLOAD)}. "
        text += f"Videos to detect: {len(g.VIDEOS_TO_DETECT)}. "
        if len(g.VIDEOS_TO_UPLOAD) == 0 and len(g.VIDEOS_TO_DETECT) == 0:
            text += "No new videos to process. Upload new data to source project"
        
        self.show_validation(text, "info")

input = InputStep()
