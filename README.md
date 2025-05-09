<div align="center" markdown>

<img src=""/>

# Preprocess Data for Mouse Project

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-to-Run">How to Run</a> •
</p>

[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervisely.com/apps/preprocess-data-for-mouse-project)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervisely.com/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/preprocess-data-for-mouse-project)
[![views](https://app.supervisely.com/img/badges/views/supervisely-ecosystem/preprocess-data-for-mouse-project.png)](https://supervisely.com)
[![runs](https://app.supervisely.com/img/badges/runs/supervisely-ecosystem/preprocess-data-for-mouse-project.png)](https://supervisely.com)

</div>

# Overview

Application for preprocessing video data for training. Automates the process of preparing training and test data from video project, creating training clips from labeled videos, and applying a trained model to it.

**Key features:**

- Source project will not be changed
- Loading and processing video files from Supervisely project
- Splitting videos into training and test sets
- Extracting training clips from labeled videos for three categories (videos must be pre-tagged):
  - "Self-Grooming"
  - "Head-Body_TWITCH"
  - "idle" (negative examples)
- Uploading processed data to new project called Training Data in current team on Supervisely server
- Applying a detection model to uploaded videos
- Caching system that prevents reprocessing of already processed videos when the application is rerun

After processing is complete, you will get a new project with name `[source project id] Training Data` which consists of 2 datasets: train and test.
- **train dataset** contains 3 nested datasets with short video clips: 
  - "Self-Grooming"
  - "Head-Body_TWITCH"
  - "idle"
- **test dataset** contains full-length original videos for validation purposes

The application maintains a cache that tracks which videos have been processed (uploaded and detected). When you run the application again with the same source videos, it will only process new videos that haven't been processed before. Cache file is stored in the Team Files, you can find it by this path: `/mouse-project-data/<source project id>-<training data project id>-cache.json`, **don't remove it**.

# How to Run

**Step 1.** Run the application from the context menu of a video project or ecosystem

**Step 2.** Connect to the trained mouse detection model

Run [Serve RT-DETRv2]() app and serve custom model with `mouse` class. Model must have only one class: `mouse`.

![img2](placeholder)


**Step 3.** Set the train/test split ratio

**Step 4.** Start processing. Don't shutdown or restart agent until the processing is finished. If process is interrupted restart the app.

![img3](placeholder)
