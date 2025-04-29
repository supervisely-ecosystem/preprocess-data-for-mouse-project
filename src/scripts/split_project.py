import os
import random
import shutil
import src.globals as g
from supervisely import logger
from supervisely.video_annotation.key_id_map import KeyIdMap
from supervisely.io.json import dump_json_file

def find_video_paths(base_dir):
    video_paths = []
    
    for root, dirs, files in os.walk(base_dir):
        if os.path.basename(root) == "video":
            video_files = [os.path.join(root, f) for f in files if f.lower().endswith('.mp4')]
            video_paths.extend(video_files)
    
    return video_paths

def get_annotation_path(video_path):
    # Given pattern:
    # video_path: .../datasets/.../video/GLXXXXXX.MP4
    # annotation_path: .../datasets/.../ann/GLXXXXXX.MP4.json
    
    video_dir = os.path.dirname(video_path)
    parent_dir = os.path.dirname(video_dir)
    
    video_filename = os.path.basename(video_path)
    ann_filename = f"{video_filename}.json"
    
    # Replace 'video' directory with 'ann' directory in the path
    ann_dir = os.path.join(parent_dir, "ann")
    ann_path = os.path.join(ann_dir, ann_filename)
    
    return ann_path

def split_project(seed=42):
    # Set random seed for reproducibility
    random.seed(seed)
    
    # Find all video paths
    video_paths = find_video_paths(g.PROJECT_DIR)
    
    if not video_paths:
        logger.warn(f"No videos found in {g.PROJECT_DIR}")
        return
    
    # Shuffle the video paths
    random.shuffle(video_paths)
    
    # Calculate split point
    train_size = int(len(video_paths) * g.SPLIT_RATIO)
    
    # Split the videos
    train_videos = video_paths[:train_size]
    test_videos = video_paths[train_size:]
    
    logger.info(f"Splitting dataset: {len(train_videos)} videos for training, {len(test_videos)} videos for testing")
    
    # Create output directories
    train_dir = os.path.join(g.SPLIT_PROJECT_DIR, "train")
    test_dir = os.path.join(g.SPLIT_PROJECT_DIR, "test")
    
    train_video_dir = os.path.join(train_dir, "video")
    train_ann_dir = os.path.join(train_dir, "ann")
    
    test_video_dir = os.path.join(test_dir, "video")
    test_ann_dir = os.path.join(test_dir, "ann")
    
    os.makedirs(train_video_dir, exist_ok=True)
    os.makedirs(train_ann_dir, exist_ok=True)
    os.makedirs(test_video_dir, exist_ok=True)
    os.makedirs(test_ann_dir, exist_ok=True)
    
    with g.PROGRESS_BAR(message="Splitting project", total=len(train_videos) + len(test_videos)) as pbar:
        g.PROGRESS_BAR.show()
        # Copy train videos and annotations
        for video_path in train_videos:
            video_filename = os.path.basename(video_path)
            ann_path = get_annotation_path(video_path)
            
            # Check if annotation exists
            if not os.path.exists(ann_path):
                logger.warn(f"Warning: Annotation not found for {video_path}")
                pbar.update(1)
                continue
            
            # Copy video
            shutil.copy2(video_path, os.path.join(train_video_dir, video_filename))
            
            # Copy annotation
            ann_filename = os.path.basename(ann_path)
            shutil.copy2(ann_path, os.path.join(train_ann_dir, ann_filename))
            pbar.update(1)
        
        # Copy test videos and annotations
        for video_path in test_videos:
            video_filename = os.path.basename(video_path)
            ann_path = get_annotation_path(video_path)
            
            # Check if annotation exists
            if not os.path.exists(ann_path):
                logger.warn(f"Warning: Annotation not found for {video_path}")
                pbar.update(1)
                continue
            
            # Copy video
            shutil.copy2(video_path, os.path.join(test_video_dir, video_filename))
            
            # Copy annotation
            ann_filename = os.path.basename(ann_path)
            shutil.copy2(ann_path, os.path.join(test_ann_dir, ann_filename))
            pbar.update(1)
    g.PROGRESS_BAR.hide()

    # Project files
    meta_path = os.path.join(g.PROJECT_DIR, "meta.json")
    shutil.copy2(meta_path, os.path.join(g.SPLIT_PROJECT_DIR, "meta.json"))
    dump_json_file(KeyIdMap().to_dict(), os.path.join(g.SPLIT_PROJECT_DIR, "key_id_map.json"))
    
    logger.info(f"Dataset split complete. Files saved to {g.SPLIT_PROJECT_DIR}")
    logger.info(f"Output structure:\n{train_dir}\n{test_dir}")
    
    return train_dir, test_dir