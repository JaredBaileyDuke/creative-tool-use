import cv2
import sys
from pathlib import Path

def create_thumbnail_from_video(video_path, thumbnail_path="thumbnail.png", frame_number=None, time_sec=None):
    """
    Extracts a specific frame from an MP4 video and saves it as a PNG thumbnail.

    Args:
        video_path (str or Path): Path to the .mp4 file.
        thumbnail_path (str or Path): Output .png file name/path.
        frame_number (int, optional): Exact frame index to extract (0-based).
        time_sec (float, optional): Timestamp in seconds to extract.
                                    If both frame_number and time_sec are given, frame_number takes priority.
    """
    video_path = Path(video_path)
    thumbnail_path = Path(thumbnail_path)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Error: Cannot open video file {video_path}")
        return

    if frame_number is not None:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    elif time_sec is not None:
        cap.set(cv2.CAP_PROP_POS_MSEC, time_sec * 1000)

    ret, frame = cap.read()
    if not ret:
        print(f"Error: Cannot read requested frame (frame={frame_number}, time={time_sec}s)")
        cap.release()
        return

    # Optional: resize for smaller thumbnails
    # frame = cv2.resize(frame, (320, 180))

    cv2.imwrite(str(thumbnail_path), frame)
    cap.release()
    print(f"✅ Thumbnail saved to {thumbnail_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_thumbnail_from_frame.py <video.mp4> [frame_number] [thumbnail.png]")
        sys.exit(1)

    video_file = sys.argv[1]
    frame_num = int(sys.argv[2]) if len(sys.argv) > 2 else None
    out_file = sys.argv[3] if len(sys.argv) > 3 else "thumbnail.png"

    create_thumbnail_from_video(video_file, out_file, frame_number=frame_num)
