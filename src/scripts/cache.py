import os
import json
from typing import Dict, Any, Optional, List
import src.globals as g
from supervisely import logger
from src.scripts.video_metadata import VideoMetaData


def init_cache() -> Dict[str, Any]:
    if os.path.exists(g.LOCAL_CACHE_PATH):
        return load_cache()

    cache_data = {
        "source_project_id": g.PROJECT_ID,
        "target_project_id": g.DST_PROJECT_ID,
        "videos": {},
        "target_to_source": {},  # mapping from uploaded video/clip id to source
    }

    save_cache(cache_data)
    return cache_data


def download_cache() -> Dict[str, Any]:
    exists = g.API.file.exists(g.TEAM_ID, g.REMOTE_CACHE_PATH)
    if exists:
        g.API.file.download(g.TEAM_ID, g.REMOTE_CACHE_PATH, g.LOCAL_CACHE_PATH)
        return load_cache()
    else:
        return init_cache()


def upload_cache() -> None:
    exists = g.API.file.exists(g.TEAM_ID, g.REMOTE_CACHE_PATH)
    if exists:
        g.API.file.remove(g.TEAM_ID, g.REMOTE_CACHE_PATH)
    g.API.file.upload(g.TEAM_ID, g.LOCAL_CACHE_PATH, g.REMOTE_CACHE_PATH)


def load_cache() -> Dict[str, Any]:
    if not os.path.exists(g.LOCAL_CACHE_PATH):
        return init_cache()

    try:
        with open(g.LOCAL_CACHE_PATH, "r") as f:
            cache_data = json.load(f)

        if (
            cache_data.get("source_project_id") != g.PROJECT_ID
            or cache_data.get("target_project_id") != g.DST_PROJECT_ID
        ):
            logger.info("Project IDs have changed, initializing new cache")
            return init_cache()

        return cache_data
    except Exception as e:
        logger.warning(f"Error loading cache: {str(e)}. Initializing new cache.")
        return init_cache()


def save_cache(cache_data: Dict[str, Any]) -> None:
    try:
        with open(g.LOCAL_CACHE_PATH, "w") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving cache: {str(e)}")


def add_video_to_cache(
    video_info: VideoMetaData,
    is_uploaded: bool = True,
    is_detected: bool = False,
    upload: bool = True,
) -> None:
    cache_data = load_cache()
    video_id = str(video_info.video_id)

    if video_id not in cache_data.get("videos", {}):
        cache_data.setdefault("videos", {})[video_id] = {
            "video_id": video_id,
            "video_name": video_info.name,
            "dataset": video_info.dataset,
            "is_uploaded": is_uploaded,
            "is_detected": is_detected,
            "is_test": getattr(video_info, "is_test", False),
            "clips": {},
        }
        if hasattr(video_info, "train_data_id") and video_info.train_data_id is not None:
            cache_data["videos"][video_id]["train_data_id"] = video_info.train_data_id
            cache_data.setdefault("target_to_source", {})[str(video_info.train_data_id)] = {
                "source_video_id": video_id,
                "clip_id": None,
            }
    else:
        cache_data["videos"][video_id]["is_uploaded"] = is_uploaded
        cache_data["videos"][video_id]["is_detected"] = is_detected
        if hasattr(video_info, "train_data_id") and video_info.train_data_id is not None:
            cache_data["videos"][video_id]["train_data_id"] = video_info.train_data_id
            cache_data.setdefault("target_to_source", {})[str(video_info.train_data_id)] = {
                "source_video_id": video_id,
                "clip_id": None,
            }

    save_cache(cache_data)
    if upload:
        upload_cache()


def add_videos_to_cache(
    video_infos: List[VideoMetaData], is_uploaded: bool = True, is_detected: bool = False
) -> None:
    for video_info in video_infos:
        add_video_to_cache(video_info, is_uploaded, is_detected, False)
    upload_cache()


def add_single_clip_to_cache(clip_info: VideoMetaData) -> None:
    if not hasattr(clip_info, "source_video") or not clip_info.source_video:
        logger.warning(f"Clip {clip_info.name} has no source video")
        return

    cache_data = load_cache()
    source_video = clip_info.source_video
    video_id = str(source_video.video_id)

    if video_id not in cache_data.get("videos", {}):
        add_video_to_cache(source_video)
        cache_data = load_cache()

    clip_id = str(getattr(clip_info, "clip_id", hash(clip_info.name)))
    clip_data = {
        "clip_id": clip_id,
        "clip_name": clip_info.name,
        "label": clip_info.label,
        "dataset": clip_info.dataset,
        "start_frame": clip_info.start_frame,
        "end_frame": clip_info.end_frame,
        "is_detected": getattr(clip_info, "is_detected", False),
    }

    if hasattr(clip_info, "train_data_id") and clip_info.train_data_id is not None:
        clip_data["train_data_id"] = clip_info.train_data_id
        cache_data.setdefault("target_to_source", {})[str(clip_info.train_data_id)] = {
            "source_video_id": video_id,
            "clip_id": clip_id,
        }

    cache_data["videos"][video_id].setdefault("clips", {})[clip_id] = clip_data

    save_cache(cache_data)
    upload_cache()


def add_clips_to_cache(video_info: VideoMetaData) -> None:
    if not hasattr(video_info, "clips") or not video_info.clips:
        return

    cache_data = load_cache()
    video_id = str(video_info.video_id)

    if video_id not in cache_data.get("videos", {}):
        add_video_to_cache(video_info)
        cache_data = load_cache()

    for clip in video_info.clips:
        clip_id = str(getattr(clip, "clip_id", hash(clip.name)))
        cache_data["videos"][video_id].setdefault("clips", {})[clip_id] = {
            "clip_id": clip_id,
            "clip_name": clip.name,
            "label": clip.label,
            "dataset": clip.dataset,
            "start_frame": clip.start_frame,
            "end_frame": clip.end_frame,
            "is_detected": getattr(clip, "is_detected", False),
        }

    save_cache(cache_data)
    upload_cache()


def update_detection_status(video_id: str, is_detected: bool = True) -> None:
    cache_data = load_cache()
    video_id = str(video_id)
    videos = cache_data.get("videos", {})

    target_map = cache_data.get("target_to_source", {})
    if video_id in target_map:
        map_info = target_map[video_id]
        source_video_id = map_info["source_video_id"]
        clip_id = map_info.get("clip_id")
        if clip_id:
            videos[source_video_id]["clips"][clip_id]["is_detected"] = is_detected
            logger.debug(
                f"Detection status updated via mapping for clip target_id: '{video_id}' (source video id: '{source_video_id}')"
            )
        else:
            videos[source_video_id]["is_detected"] = is_detected
            logger.debug(
                f"Detection status updated via mapping for video target_id: '{video_id}' (source video id: '{source_video_id}')"
            )
        save_cache(cache_data)
        upload_cache()
        return

    # Fallback logic
    if video_id in videos:
        videos[video_id]["is_detected"] = is_detected
        save_cache(cache_data)
        upload_cache()
        logger.debug(f"Detection status updated for video id: '{video_id}'")
        return

    for full_video_id in videos:
        clips = videos[full_video_id].get("clips", {})
        if video_id in clips:
            clips[video_id]["is_detected"] = is_detected
            save_cache(cache_data)
            upload_cache()
            logger.debug(
                f"Detection status updated for clip: {video_id} (video id: '{full_video_id}')"
            )
            return

    for full_video_id, video_data in videos.items():
        if video_data.get("train_data_id") == video_id:
            video_data["is_detected"] = is_detected
            save_cache(cache_data)
            upload_cache()
            logger.debug(
                f"Detection status updated for video with train_data_id: '{video_id}' (source video id: '{full_video_id}')"
            )
            return

    logger.debug(f"Video ID: '{video_id}' not found in cache")
