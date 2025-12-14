#!/usr/bin/env python
import argparse
import json
import os
from pathlib import Path

import numpy as np
import cv2


# ---------------- Canonical <-> pixel helpers (match author's math) ----------------
def canonical_to_pixel_coords(coords, img_shape):
    """
    coords: (..., 2) canonical (x,y), origin = image center, units = image height
    img_shape: (H, W)
    """
    coords = np.asarray(coords, dtype=np.float64)
    H, W = img_shape
    return coords * H + np.array([W, H]) * 0.5

def pixel_coords_to_canonical(pts, img_shape):
    """
    pts: (..., 2) pixel (x,y), origin = top-left
    img_shape: (H, W)
    """
    pts = np.asarray(pts, dtype=np.float64)
    H, W = img_shape
    return (pts - np.array([W, H]) * 0.5) / H


# ---------------- Drawing ----------------
def fill_polygon_pixel(mask, pts_px, value, lineType=cv2.LINE_8):
    pts_px = np.asarray(pts_px, dtype=np.int32)
    cv2.fillPoly(mask, [pts_px], color=int(value), lineType=lineType)

def fill_polygon_canonical(mask, coords_can, value, lineType=cv2.LINE_8):
    pts_px = canonical_to_pixel_coords(coords_can, mask.shape[:2])
    pts_px = np.round(pts_px).astype(np.int32)
    cv2.fillPoly(mask, [pts_px], color=int(value), lineType=lineType)


# ---------------- Mask builder from JSON ----------------
def build_masks_from_json(
    json_path: Path,
    mirror_right: bool = True,
    gripper_right: bool = False,
):
    data = json.loads(Path(json_path).read_text())
    # resolution is [H, W]
    H, W = map(int, data["resolution"])
    img_shape = (H, W)

    mask_binary = np.zeros(img_shape, dtype=np.uint8)
    mask_multi  = np.zeros(img_shape, dtype=np.uint8)

    # ---- Mirrors ----
    if "mirror_mask_pts" in data and data["mirror_mask_pts"]:
        left_mirror_px = np.array(data["mirror_mask_pts"], dtype=np.float64)
        # draw left directly
        fill_polygon_pixel(mask_multi,  left_mirror_px, value=1)
        fill_polygon_pixel(mask_binary, left_mirror_px, value=255)

        # synthesize right by mirroring in canonical space
        if mirror_right:
            left_can = pixel_coords_to_canonical(left_mirror_px, img_shape)
            right_can = left_can.copy()
            right_can[:, 0] *= -1.0
            fill_polygon_canonical(mask_multi,  right_can, value=1)
            fill_polygon_canonical(mask_binary, right_can, value=255)

    # ---- Gripper ----
    if "gripper_mask_pts" in data and data["gripper_mask_pts"]:
        left_gripper_px = np.array(data["gripper_mask_pts"], dtype=np.float64)
        # draw exactly as given
        fill_polygon_pixel(mask_multi,  left_gripper_px, value=2)
        fill_polygon_pixel(mask_binary, left_gripper_px, value=255)

        # optional mirrored gripper (off by default)
        if gripper_right:
            left_can = pixel_coords_to_canonical(left_gripper_px, img_shape)
            right_can = left_can.copy()
            right_can[:, 0] *= -1.0
            fill_polygon_canonical(mask_multi,  right_can, value=2)
            fill_polygon_canonical(mask_binary, right_can, value=255)

    return mask_binary, mask_multi


def overlay_on_image(image_bgr, mask_multi, alpha=0.4):
    """
    Visual check overlay:
      class 1 (mirror) -> G channel
      class 2 (gripper)-> R channel
    """
    r = (mask_multi == 2).astype(np.uint8) * 255
    g = (mask_multi == 1).astype(np.uint8) * 255
    b = np.zeros_like(r)
    color_mask = np.dstack([r, g, b])
    return cv2.addWeighted(image_bgr, 1.0, color_mask, alpha, 0.0)


def main():
    ap = argparse.ArgumentParser(description="Generate masks from JSON polygons.")
    ap.add_argument("--json", required=True, help="Path to JSON file with polygons.")
    ap.add_argument("--outdir", default=".", help="Where to write outputs.")
    ap.add_argument("--no-mirror-right", action="store_true",
                    help="Do NOT synthesize the right mirror (default: mirror ON).")
    ap.add_argument("--mirror-gripper", action="store_true",
                    help="Also mirror the gripper polygon to the right (default: OFF).")
    ap.add_argument("--overlay", help="Optional BGR image to save an overlay (must match resolution).")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    mask_binary, mask_multi = build_masks_from_json(
        Path(args.json),
        mirror_right=not args.no_mirror_right,
        gripper_right=args.mirror_gripper,
    )

    bin_path = outdir / "mask_binary_from_json.png"
    mul_path = outdir / "mask_multi_from_json.png"
    cv2.imwrite(str(bin_path), mask_binary)
    cv2.imwrite(str(mul_path), mask_multi)

    if args.overlay:
        frame = cv2.imread(args.overlay)  # must match HxW
        if frame is None:
            print(f"[WARN] Could not read overlay image: {args.overlay}")
        elif frame.shape[:2] != mask_multi.shape:
            print(f"[WARN] Overlay image size {frame.shape[:2]} != mask size {mask_multi.shape}")
        else:
            over = overlay_on_image(frame, mask_multi, alpha=0.35)
            ov_path = outdir / "overlay_from_json.png"
            cv2.imwrite(str(ov_path), over)

    print(f"Wrote:\n  {bin_path}\n  {mul_path}")
    if args.overlay:
        print(f"  {outdir / 'overlay_from_json.png'}")


if __name__ == "__main__":
    main()
