import numpy as np
import cv2

def canonical_to_pixel_coords(coords, img_shape=(2028, 2704)):
    """
    coords: (..., 2) canonical (x,y), origin=center, units=image height.
    img_shape: (H, W)
    """
    pts = np.asarray(coords, dtype=np.float64)
    H, W = img_shape
    return pts * H + np.array([W, H]) * 0.5

def pixel_coords_to_canonical(pts, img_shape=(2028, 2704)):
    """
    pts: (..., 2) pixel (x,y), origin=top-left
    img_shape: (H, W)
    """
    pts = np.asarray(pts, dtype=np.float64)
    H, W = img_shape
    return (pts - np.array([W, H]) * 0.5) / H

def get_mirror_canonical_polygon():
    # Left mirror polygon in pixel coords
    left_pts = [
        [540, 1700],
        [680, 1450],
        [590, 1070],
        [290, 1130],
        [290, 1770],
        [550, 1770]
    ]
    resolution = (2028, 2704)  # (H, W)
    left_coords = pixel_coords_to_canonical(left_pts, resolution)
    right_coords = left_coords.copy()
    right_coords[:, 0] *= -1  # mirror across vertical center
    return np.stack([left_coords, right_coords])  # shape (2, N, 2)

def get_gripper_canonical_polygon():
    # Gripper polygon (left) in pixel coords, extends down to y=2704
    left_pts = [
        [1352, 1730],
        [1100, 1700],
        [650, 1500],
        [0, 1350],
        [0, 2028],
        [1352, 2704]
    ]
    resolution = (2028, 2704)
    left_coords = pixel_coords_to_canonical(left_pts, resolution)
    right_coords = left_coords.copy()
    right_coords[:, 0] *= -1
    return np.stack([left_coords, right_coords])  # (2, N, 2)

def get_finger_canonical_polygon(height=0.37, top_width=0.25, bottom_width=1.4):
    """
    trapezoid + a vertical rectangle whose width exactly matches the
    trapezoid's *top* width. The rectangle extends 300 px upward from the top edge.
    Returns two polygons in canonical coords: [trapezoid, rectangle].
    """
    # base resolution (H, W)
    resolution = (2028, 2704)
    img_h, img_w = resolution

    # original trapezoid
    top_y = 1.0 - height
    bottom_y = 1.0
    width_in_H = img_w / img_h
    middle_x = width_in_H / 2.0

    top_left_x     = middle_x - top_width    / 2.0
    top_right_x    = middle_x + top_width    / 2.0
    bottom_left_x  = middle_x - bottom_width / 2.0
    bottom_right_x = middle_x + bottom_width / 2.0

    # convert to pixel coordinates
    top_y_px       = top_y      * img_h
    bottom_y_px    = bottom_y   * img_h
    tlx_px         = top_left_x     * img_h
    trx_px         = top_right_x    * img_h
    blx_px         = bottom_left_x  * img_h
    brx_px         = bottom_right_x * img_h

    trapezoid_px = [
        [blx_px, bottom_y_px],
        [tlx_px, top_y_px],
        [trx_px, top_y_px],
        [brx_px, bottom_y_px]
    ]

    # rectangle: same width as trapezoid top, 300 px upward
    rect_height_px = 100.0
    rect_top_px = max(0.0, top_y_px - rect_height_px)  # clamp to image top

    rect_px = [
        [tlx_px, top_y_px],      # left bottom
        [tlx_px, rect_top_px],   # left top
        [trx_px, rect_top_px],   # right top
        [trx_px, top_y_px]       # right bottom
    ]

    # stack both polygons and convert to canonical coords
    points_px = [trapezoid_px, rect_px]
    coords = pixel_coords_to_canonical(points_px, img_shape=resolution)
    return np.asarray(coords)  # (2, 4, 2)



# Drawing utilities (multi-class & binary)

def fill_canonical_polygon_scalar(mask, canonical_coords, value):
    """
    Draw a single canonical polygon into a single-channel mask with scalar 'value'.
    """
    pts_px = canonical_to_pixel_coords(canonical_coords, mask.shape[:2])
    pts_px = np.round(pts_px).astype(np.int32)
    cv2.fillPoly(mask, [pts_px], color=int(value), lineType=cv2.LINE_8)

def build_masks(H=2028, W=2704, include_finger=True):
    """
    Returns:
      mask_binary: uint8, 0/255 union of all shapes
      mask_multi: uint8, 0=bg, 1=mirror, 2=gripper, 3=finger
    """
    img_shape = (H, W)
    mask_binary = np.zeros(img_shape, dtype=np.uint8)
    mask_multi  = np.zeros(img_shape, dtype=np.uint8)

    # 1) Mirrors (both sides)
    for coords in get_mirror_canonical_polygon():
        # multi-class: class 1
        fill_canonical_polygon_scalar(mask_multi, coords, value=1)
        # binary union
        fill_canonical_polygon_scalar(mask_binary, coords, value=255)

    # 2) Grippers (both sides)
    for coords in get_gripper_canonical_polygon():
        # multi-class: class 2 (overwrite background only)
        fill_canonical_polygon_scalar(mask_multi, coords, value=2)
        fill_canonical_polygon_scalar(mask_binary, coords, value=255)

    # 3) Finger (single trapezoid)
    if include_finger:
        for coords in get_finger_canonical_polygon():
            # multi-class: class 3
            fill_canonical_polygon_scalar(mask_multi, coords, value=3)
            fill_canonical_polygon_scalar(mask_binary, coords, value=255)

    return mask_binary, mask_multi

def overlay_on_image(image_bgr, mask_multi, alpha=0.4):
    """
    Quick visual QA: overlays mask classes onto the BGR image.
    Class 1 -> G, Class 2 -> R, Class 3 -> B (simple channel mapping)
    """
    h, w = mask_multi.shape
    overlay = image_bgr.copy()

    # simple per-class RGB channels
    r = (mask_multi == 2).astype(np.uint8) * 255
    g = (mask_multi == 1).astype(np.uint8) * 255
    b = (mask_multi == 3).astype(np.uint8) * 255
    color_mask = np.dstack([r, g, b])

    return cv2.addWeighted(overlay, 1.0, color_mask, alpha, 0.0)


if __name__ == "__main__":
    H, W = 2028, 2704  # Resolution basis
    mask_binary, mask_multi = build_masks(H, W, include_finger=True)

    cv2.imwrite("mask_binary.png", mask_binary)
    cv2.imwrite("mask_multi.png",  mask_multi)

    # Overlay (uncomment if you have a matching-size image)
    frame = cv2.imread("thumbnail.png")  # must be 2028x2704 to overlay directly
    if frame is not None and frame.shape[:2] == (H, W):
        over = overlay_on_image(frame, mask_multi, alpha=0.35)
        cv2.imwrite("overlay.png", over)

    print("Wrote mask_binary.png and mask_multi.png")
