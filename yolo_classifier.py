#!/usr/bin/env python3
"""
Runs a YOLOv8 model (Ultralytics) to classify the robot's camera feed.
Usage:
    python yolo_classifier.py --model-path path/to/model.pt --camera 2
Prints ONLY 'yes' or 'no' to stdout.
"""

import argparse
import time
import cv2
from ultralytics import YOLO


def open_camera_with_retry(camera_idx: int, retries: int = 10, delay: float = 0.3):
    """Try multiple times to open the camera before failing."""
    cap = None
    for attempt in range(retries):
        cap = cv2.VideoCapture(camera_idx)
        if cap.isOpened():
            return cap
        time.sleep(delay)
    raise RuntimeError(f"Camera {camera_idx} could not be opened after {retries} retries.")


def capture_fresh_frame(camera_idx: int, warmup_frames: int = 5):
    # Open camera with retry logic
    cap = open_camera_with_retry(camera_idx)

    # Warm up camera
    for _ in range(warmup_frames):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError("Failed to capture a frame from the camera.")

    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--camera", type=int, default=2)
    args = parser.parse_args()

    # Load YOLO model
    model = YOLO(args.model_path)

    # Capture frame safely
    frame = capture_fresh_frame(args.camera)

    # Run inference
    results = model(frame)

    # Assume model outputs class names "yes" or "no"
    pred = results[0].probs.top1
    class_name = results[0].names[pred]

    # Print ONLY yes/no for subprocess reading
    print(class_name.strip().lower())


if __name__ == "__main__":
    main()
