import os
import subprocess
import math
import random
import json
import pandas as pd
import src.globals as g
from supervisely import logger
from supervisely.io.fs import clean_dir
from supervisely.io.json import dump_json_file
from pathlib import Path
from supervisely.video_annotation.video_annotation import VideoAnnotation
from src.scripts.video_metadata import VideoMetaData


def get_video_dimensions(video_path):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0",
        str(video_path),
    ]
    output = subprocess.check_output(cmd).decode("utf-8").strip().split(",")
    return int(output[0]), int(output[1])


def get_fps(video_path):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=r_frame_rate",
        "-of",
        "csv=p=0",
        str(video_path),
    ]
    output = subprocess.check_output(cmd).decode("utf-8").strip()
    if "/" in output:
        numerator, denominator = output.split("/")
        return int(numerator) / int(denominator)
    else:
        return float(output)


def get_total_frames(video_path):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=nb_frames",
        "-of",
        "csv=p=0",
        str(video_path),
    ]
    output = subprocess.check_output(cmd).decode("utf-8").strip()

    if output and output != "N/A":
        return int(output)
    else:
        logger.warning("Frame count not found in metadata. Counting frames manually.")
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=duration",
            "-of",
            "csv=p=0",
            str(video_path),
        ]
        duration = float(subprocess.check_output(cmd).decode("utf-8").strip())
        fps = get_fps(video_path)
        return int(duration * fps)


def calculate_resize(original_width, original_height, target_short_edge=320):
    if original_width < original_height:
        new_width = target_short_edge
        new_height = int(original_height * (target_short_edge / original_width))
    else:
        new_height = target_short_edge
        new_width = int(original_width * (target_short_edge / original_height))

    new_width = new_width + (new_width % 2)
    new_height = new_height + (new_height % 2)

    return new_width, new_height


def extract_clip(video_path, start, end, width, height, fps, output_clip):
    start_time = start / fps
    duration = (end - start + 1) / fps
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_time),
        "-i",
        str(video_path),
        "-t",
        str(duration),
        "-vf",
        f"scale={width}:{height}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-force_key_frames",
        "expr:gte(t,0)",
        "-an",
        str(output_clip),
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr.decode('utf-8')}")
        logger.error(f"start frame: {start}, end frame: {end}")
        raise


def get_frame_ranges(ann_file: dict, tag: str):
    frame_ranges = []
    for ann in ann_file["tags"]:
        if ann["name"] == tag:
            frame_ranges.append(ann["frameRange"])
    return frame_ranges


def merge_overlapping_ranges(ranges: list) -> list:
    ranges = sorted(ranges, key=lambda x: x[0])
    merged = []
    for rng in ranges:
        if not merged or rng[0] > merged[-1][1] + 1:
            merged.append(rng)
        else:
            merged[-1][1] = max(merged[-1][1], rng[1])
    ranges = merged
    return ranges


def filter_ranges_outside_video(ranges: list, total_frames: int) -> list:
    return [
        [start, end]
        for start, end in ranges
        if 0 <= start < total_frames and 0 <= end < total_frames
    ]


def split_range(
    start: int, end: int, fps: float, total_frames: int, max_clip_duration: float = 5
) -> list:
    segments = []
    clip_frames = end - start + 1

    if clip_frames == 1:
        half = fps // 2
        start = max(0, start - half)
        end = min(total_frames - 1, start + fps - 1)
        clip_frames = end - start + 1

    ten_sec_frames = int(max_clip_duration * fps)
    if clip_frames > ten_sec_frames:
        seg_count = math.ceil(clip_frames / ten_sec_frames)
        base_seg_length = clip_frames // seg_count
        extra = clip_frames % seg_count
        current_start = start
        for i in range(seg_count):
            current_seg_length = base_seg_length + (1 if i < extra else 0)
            current_end = current_start + current_seg_length - 1
            segments.append((current_start, current_end))
            current_start = current_end + 1
    else:
        segments.append((start, end))

    return segments


def make_pos_clips_for_tag(
    video_file: str,
    ann_file: str,
    output_dir: str,
    target_short_edge: int,
    tag: str,
    label: int,
):
    video_path = Path(video_file)
    video_name = video_path.stem
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tag_name = tag.replace("/", "-").replace(" ", "_")
    tag_dir = out_dir / tag_name
    tag_dir.mkdir(parents=True, exist_ok=True)

    tag_video_dir = tag_dir / "video"
    tag_video_dir.mkdir(parents=True, exist_ok=True)

    tag_ann_dir = tag_dir / "ann"
    tag_ann_dir.mkdir(parents=True, exist_ok=True)

    fps = get_fps(video_path)
    total_frames = get_total_frames(video_path)

    with open(ann_file, "r") as f:
        ann = json.load(f)

    ranges = get_frame_ranges(ann, tag=tag)
    ranges = filter_ranges_outside_video(ranges, total_frames)
    ranges = merge_overlapping_ranges(ranges)

    info = []
    clip_counter = 1
    for frame_range in ranges:
        start, end = frame_range
        segments = split_range(start, end, fps, total_frames)

        for seg in segments:
            seg_start, seg_end = seg
            clip_name = f"{video_name}_clip_{clip_counter:03d}.mp4"

            output_clip = tag_video_dir / clip_name
            output_clip.parent.mkdir(parents=True, exist_ok=True)
            width, height = get_video_dimensions(video_path)
            new_width, new_height = calculate_resize(
                width, height, target_short_edge=target_short_edge
            )
            extract_clip(video_path, seg_start, seg_end, new_width, new_height, fps, output_clip)

            ann_file = tag_ann_dir / clip_name.replace(".mp4", ".mp4.json")
            ann = VideoAnnotation((new_width, new_height), seg_end - seg_start + 1)
            dump_json_file(ann.to_json(), ann_file)

            # orig_file, clip_file, start, end, label(1,2)
            info.append([str(video_path), str(output_clip), seg_start, seg_end, label])
            clip_counter += 1

    return info


def make_positives(input_dir: str, output_dir: str, min_size):
    p = Path(input_dir)
    paths = list(p.rglob("*.MP4"))
    paths += list(p.rglob("*.mp4"))
    logger.info(f"Found {len(paths)} video files.")

    # find duplicates
    paths = unique_video_names(paths)
    LABELS = {"Self-Grooming": 1, "Head/Body TWITCH": 2}

    infos = []
    with g.PROGRESS_BAR(message="Making positive training clips", total=len(paths)) as pbar:
        g.PROGRESS_BAR.show()
        for i, video_file in enumerate(paths):
            ann_file = video_file.parent.parent / f"ann/{video_file.name}.json"
            if not ann_file.exists():
                logger.warn(f"Annotation file not found: {ann_file}")
                pbar.update(1)
                continue

            for tag, label in LABELS.items():
                count_with_label_1 = len([i for i in infos if i[4] == 1])
                if tag == "Self-Grooming" and count_with_label_1 > 200:
                    continue  # TODO DEBUG: Only process TWITCH clips for now
                curr_video_infos = make_pos_clips_for_tag(
                    video_file, ann_file, output_dir, min_size, tag, label
                )
                if len(curr_video_infos) == 0:
                    logger.debug(f"No clips found for video: {video_file}")
                infos.extend(curr_video_infos)
            logger.info(f"Processed {i+1}/{len(paths)} videos for positive clips")
            pbar.update(1)
    g.PROGRESS_BAR.hide()

    # count each label
    label_counts = {label: 0 for label in LABELS.values()}
    for info in infos:
        label_counts[info[4]] += 1
    logger.info(f"Label counts: {label_counts}")
    return infos


def make_neg_clips_for_tag(
    video_file: str,
    output_dir: str,
    target_short_edge: int,
    target_length: int,
    skip_ranges: list,
    tag: str = "idle",
    label: int = 0,
    min_clip_duration: int = 3,
    max_clip_duration: int = 5,
):
    video_path = Path(video_file)
    video_name = video_path.stem
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tag_name = tag.replace("/", "-").replace(" ", "_")
    tag_dir = out_dir / tag_name
    tag_dir.mkdir(parents=True, exist_ok=True)

    tag_video_dir = tag_dir / "video"
    tag_video_dir.mkdir(parents=True, exist_ok=True)

    tag_ann_dir = tag_dir / "ann"
    tag_ann_dir.mkdir(parents=True, exist_ok=True)

    fps = get_fps(video_path)
    total_frames = get_total_frames(video_path)
    skip_ranges = merge_overlapping_ranges(skip_ranges)

    non_skip_intervals = []
    current = 0
    for s, e in skip_ranges:
        if current < s:
            non_skip_intervals.append([current, s - 1])
        current = e + 1
    if current < total_frames:
        non_skip_intervals.append([current, total_frames - 1])

    clip_min_frames = math.ceil(fps * min_clip_duration)
    clip_max_frames = math.floor(fps * max_clip_duration)
    clip_counter = 1
    cumulative_clip_frames = 0
    info = []

    for interval in non_skip_intervals:
        interval_start, interval_end = interval
        t = interval_start
        while t + clip_min_frames - 1 <= interval_end and cumulative_clip_frames < target_length:
            available = interval_end - t + 1
            if available < clip_min_frames:
                break
            clip_length = random.randint(clip_min_frames, min(clip_max_frames, available))
            start_frame = t
            end_frame = t + clip_length - 1
            clip_name = f"{video_name}_clip_{clip_counter:03d}.mp4"
            output_clip = tag_video_dir / clip_name
            output_clip.parent.mkdir(parents=True, exist_ok=True)
            width, height = get_video_dimensions(video_path)
            new_width, new_height = calculate_resize(
                width, height, target_short_edge=target_short_edge
            )
            extract_clip(
                video_path, start_frame, end_frame, new_width, new_height, fps, output_clip
            )

            ann_file = tag_ann_dir / clip_name.replace(".mp4", ".mp4.json")
            ann = VideoAnnotation((new_width, new_height), clip_length)
            dump_json_file(ann.to_json(), ann_file)

            # orig_file, clip_file, start, end, label=0
            info.append([str(video_path), str(output_clip), start_frame, end_frame, label])

            cumulative_clip_frames += clip_length
            clip_counter += 1
            t = end_frame + 1
            if cumulative_clip_frames >= target_length:
                break

    return info


def make_negatives(pos_df: pd.DataFrame, output_dir: str, min_size, target_length):
    grouped = pos_df.groupby("orig_file")
    infos = []

    with g.PROGRESS_BAR(message="Making negative training clips", total=len(grouped)) as pbar:
        g.PROGRESS_BAR.show()
        for i, (video_file, group_df) in enumerate(grouped):
            skip_ranges = group_df[["start", "end"]].values.tolist()
            infos += make_neg_clips_for_tag(
                video_file,
                output_dir,
                min_size,
                target_length=target_length,
                skip_ranges=skip_ranges,
            )
            logger.info(f"Processed {i+1}/{len(grouped)} videos for negative clips")
            pbar.update(1)
    g.PROGRESS_BAR.hide()
    return infos


def unique_video_names(paths: list):
    seen = set()
    unique_paths = []
    for path in paths:
        if path.stem not in seen:
            seen.add(path.stem)
            unique_paths.append(path)
    if len(unique_paths) < len(paths):
        logger.warn(
            f"Found {len(paths) - len(unique_paths)} duplicate video names in the input list."
        )
    return unique_paths


def remove_train_videos():
    train_vid_dir = os.path.join(g.SPLIT_PROJECT_DIR, "train", "video")
    train_ann_dir = os.path.join(g.SPLIT_PROJECT_DIR, "train", "ann")
    clean_dir(train_vid_dir)
    clean_dir(train_ann_dir)


def make_training_clips(min_size=480):
    csv_path = g.SPLIT_PROJECT_DIR
    train_dir = os.path.join(g.SPLIT_PROJECT_DIR, "train")
    output_dir = os.path.join(train_dir, "datasets")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    train_dir = Path(train_dir)
    train_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Creating positive clips...")
    pos_infos = make_positives(input_dir=train_dir, output_dir=output_dir, min_size=min_size)
    if not pos_infos:
        logger.error("No positive clips created. Check annotations and videos.")
        return None

    pos_df = pd.DataFrame(pos_infos, columns=["orig_file", "clip_file", "start", "end", "label"])
    pos_csv_path = os.path.join(csv_path, "positives.csv")
    pos_df.to_csv(pos_csv_path, index=False)
    logger.info(f"Saved {len(pos_infos)} positive clips to '{pos_csv_path}'")

    # Calculate average frame range length per video file
    pos_df["range_length"] = (
        pos_df["end"] - pos_df["start"] + 1
    )  # +1 because end frame is inclusive
    avg_lengths = pos_df.groupby("orig_file")["range_length"].agg(["sum", "count", "mean"])
    avg_lengths.columns = ["total_frames", "clip_count", "avg_length_per_clip"]
    avg_lengths.to_csv(os.path.join(csv_path, "avg_lengths_positives.csv"))

    target_length = int(avg_lengths["total_frames"].mean() if not avg_lengths.empty else 300)
    if avg_lengths.empty:
        logger.warning("No positive clips found in avg_lengths. Defaulting target length to 300 frames.")
        
    logger.info(f"Average target length for negatives: {target_length} frames")

    # Create negative clips
    logger.info("Creating negative clips...")
    neg_infos = make_negatives(
        pos_df=pos_df, output_dir=output_dir, min_size=min_size, target_length=target_length
    )
    neg_df = pd.DataFrame(neg_infos, columns=["orig_file", "clip_file", "start", "end", "label"])
    neg_csv_path = os.path.join(csv_path, "negatives.csv")
    neg_df.to_csv(neg_csv_path, index=False)
    logger.info(f"Saved {len(neg_infos)} negative clips to '{neg_csv_path}'")

    # concatenate positive and negative clips
    clips_df = pd.concat([pos_df, neg_df])
    clips_csv_path = os.path.join(csv_path, "clips.csv")
    clips_df.to_csv(clips_csv_path, index=False)
    logger.info(f"Saved {len(clips_df)} total clips to '{clips_csv_path}'")

    # Add clips information to g.TRAIN_VIDEOS
    # Create a dictionary for quick video search by filename
    video_dict = {}
    for video in g.TRAIN_VIDEOS:
        video_name = os.path.basename(video.path) if video.path else video.name
        video_dict[video_name] = video

    # For each clip, create a VideoMetaData object and add it to the corresponding source video
    for _, row in clips_df.iterrows():
        # Get the filename of the source video
        source_file = os.path.basename(row["orig_file"])

        # Find the corresponding VideoMetaData object
        if source_file in video_dict:
            source_video = video_dict[source_file]

            # Define the label
            if isinstance(row["label"], int):
                # Ensure the label is within the valid range
                if 0 <= row["label"] < len(g.CLIP_LABELS):
                    label = g.CLIP_LABELS[row["label"]]
                else:
                    label = f"label_{row['label']}"
            else:
                label = row["label"]

            clip = VideoMetaData.create_clip(
                source_video=source_video,
                name=os.path.basename(row["clip_file"]),
                start_frame=row["start"],
                end_frame=row["end"],
                label=label,
            )

            clip.path = row["clip_file"]
            source_video.clips.append(clip)

    # Remove original train videos
    remove_train_videos()

    return str(clips_csv_path)
