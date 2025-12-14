#!/usr/bin/env python3
"""
State machine controller for the Cheeto robot.

States:
- MOVE_CHEETO           : run move script (20s timeout)
- HOME_ROBOT            : home script (5s timeout), used after move & after cut
- CHECK_CHEETO_POSITION : YOLO model (in cv_models env) decides if Cheeto is in acceptable position
- CUT_CHEETO            : run cut script (20s timeout)
- CHECK_CHEETO_CUT      : YOLO model (in cv_models env) decides if Cheeto is in two pieces; end or loop

Transitions (logical):
1) MOVE_CHEETO -> HOME_ROBOT (next_after_home = CHECK_CHEETO_POSITION)
2) HOME_ROBOT -> next_after_home
3) CHECK_CHEETO_POSITION:
    - if NO  -> MOVE_CHEETO
    - if YES -> CUT_CHEETO
4) CUT_CHEETO -> HOME_ROBOT (next_after_home = CHECK_CHEETO_CUT)
5) CHECK_CHEETO_CUT:
    - if YES (cut ok) -> end
    - if NO  -> CHECK_CHEETO_POSITION
"""

import subprocess
import time
import logging
from enum import Enum, auto
from typing import List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)


# ---------------------------------------------------------
# State definitions
# ---------------------------------------------------------
class State(Enum):
    MOVE_CHEETO = auto()
    HOME_ROBOT = auto()
    CHECK_CHEETO_POSITION = auto()
    CUT_CHEETO = auto()
    CHECK_CHEETO_CUT = auto()


# ---------------------------------------------------------
# Config: command BASES & timeouts
# (dataset.repo_id with timestamp is added at runtime)
# ---------------------------------------------------------
MOVE_CHEETO_CMD_BASE: List[str] = [
    "conda", "run", "-n", "lerobot010_v2",
    "python", "-m", "lerobot.record",
    "--robot.type=so101_follower",
    "--robot.port=/dev/ttyACM0",
    "--robot.id=my_awesome_follower_arm",
    "--robot.cameras={ left: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 10}, right: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 10} }",
    "--policy.path=outputs/train/act_cc_v10_full_run/checkpoints/100000/pretrained_model",
    "--dataset.single_task=YellowBrickPurpleRectangle",
    "--dataset.push_to_hub=false",
    "--display_data=true",
]

HOME_ROBOT_CMD: List[str] = [
    "conda", "run", "-n", "lerobot010_v2",
    "python", "-m", "lerobot.teleoperate",
    "--robot.type=so101_follower",
    "--robot.port=/dev/ttyACM0",
    "--robot.id=my_awesome_follower_arm",
    "--teleop.type=so101_leader",
    "--teleop.port=/dev/ttyACM1",
    "--teleop.id=my_awesome_leader_arm",
]

CUT_CHEETO_CMD_BASE: List[str] = [
    "conda", "run", "-n", "lerobot010_v2",
    "python", "-m", "lerobot.record",
    "--robot.type=so101_follower",
    "--robot.port=/dev/ttyACM0",
    "--robot.id=my_awesome_follower_arm",
    # Cameras JSON must be ONE argument as a string
    "--robot.cameras={ left: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 10},  right: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 10} }",
    # Policy path
    "--policy.path=outputs/train/act_cc_v11_full_run/checkpoints/100000/pretrained_model",
    "--dataset.single_task=YellowBrickPurpleRectangle",
    "--dataset.push_to_hub=false",
    "--display_data=true",
]

MOVE_CHEETO_TIMEOUT_S = 30
HOME_ROBOT_TIMEOUT_S = 5
CUT_CHEETO_TIMEOUT_S = 30

MAX_ITERATIONS = 50  # safety guard so we don't loop forever


# ---------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------
def run_with_timeout(cmd: List[str], timeout_s: int, name: str) -> bool:
    """
    Run a command with a timeout. If it times out, kill the process.

    Returns True if it exited with code 0 within the timeout, False otherwise.
    """
    logging.info("Starting %s: %s (timeout=%ss)", name, cmd, timeout_s)
    try:
        proc = subprocess.Popen(cmd)
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        logging.warning("%s timed out after %s seconds. Killing process...", name, timeout_s)
        proc.kill()
        return False
    except Exception as e:
        logging.error("%s failed with exception: %s", name, e)
        return False

    if proc.returncode == 0:
        logging.info("%s completed successfully.", name)
        return True
    else:
        logging.error("%s exited with non-zero status: %s", name, proc.returncode)
        return False


def run_move_cheeto() -> bool:
    """Run the move Cheeto script with a timeout."""
    ts = time.strftime('%Y%m%d_%H%M%S')
    cmd = MOVE_CHEETO_CMD_BASE + [
        f"--dataset.repo_id=JaredBailey/eval_lerobot-yellow-brick_{ts}",
    ]
    return run_with_timeout(cmd, MOVE_CHEETO_TIMEOUT_S, "MoveCheeto")


def run_home_robot() -> bool:
    """Run the home robot script with a 5s timeout."""
    return run_with_timeout(HOME_ROBOT_CMD, HOME_ROBOT_TIMEOUT_S, "HomeRobot")


def run_cut_cheeto() -> bool:
    """Run the cut Cheeto script with a 20s timeout."""
    ts = time.strftime('%Y%m%d_%H%M%S')
    cmd = CUT_CHEETO_CMD_BASE + [
        f"--dataset.repo_id=JaredBailey/eval_lerobot-yellow-brick_{ts}",
    ]
    return run_with_timeout(cmd, CUT_CHEETO_TIMEOUT_S, "CutCheeto")


# ---------------------------------------------------------
# YOLO-based checks (cv_models environment, camera 2)
# ---------------------------------------------------------
def run_yolo_check(model_path: str) -> bool:
    """
    Run the YOLOv8 model in the cv_models environment on camera index 2.

    Assumes yolo_classifier.py:
      - warms up camera 2
      - captures a fresh frame
      - releases the camera
      - prints 'yes' or 'no' to stdout (on the LAST line)

    Returns True if YOLO prints 'yes' on its last non-empty stdout line, False otherwise.
    """
    cmd = [
        "conda", "run", "-n", "cv_models",
        "python", "yolo_classifier.py",
        "--model-path", model_path,
        "--camera", "2",
    ]

    logging.info("Running YOLO classifier: %s", cmd)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        logging.error("Failed to launch YOLO classifier: %s", e)
        return False

    raw_out = (proc.stdout or "").strip()
    raw_err = (proc.stderr or "").strip()

    if raw_out:
        logging.info("YOLO raw stdout:\n%s", raw_out)
    if raw_err:
        logging.info("YOLO raw stderr:\n%s", raw_err)

    if proc.returncode != 0:
        logging.warning(
            "YOLO classifier exited with code %s; treating as NOT OK.",
            proc.returncode,
        )
        return False

    # Take the last non-empty line as the prediction
    lines = [ln.strip().lower() for ln in raw_out.splitlines() if ln.strip()]
    if not lines:
        logging.warning("YOLO classifier produced no usable stdout; treating as NOT OK.")
        return False

    last_line = lines[-1]
    logging.info("YOLO parsed prediction: %s", last_line)

    if last_line == "yes":
        # YES = cheeto position/cut is OK
        return True
    elif last_line == "no":
        return False
    else:
        logging.warning("Unexpected YOLO output '%s'; treating as NOT OK.", last_line)
        return False


def check_cheeto_position() -> bool:
    """
    Use the YOLOv8 'cheeto_position' model to decide
    if the Cheeto is in an acceptable position on the board.

    Returns:
        True  -> position OK (go to CUT_CHEETO)
        False -> position NOT OK (go back to MOVE_CHEETO)
    """
    logging.info("Using YOLOv8 model to check cheeto position.")
    model_path = "yolov8_models/cheeto_position/best.pt"
    return run_yolo_check(model_path)


def check_cheeto_cut() -> bool:
    """
    Use the YOLOv8 'cheeto_cut' model to decide
    if the Cheeto has been cut into two pieces.

    Returns:
        True  -> cut successful (end program)
        False -> cut NOT successful (go back to CHECK_CHEETO_POSITION)
    """
    logging.info("Using YOLOv8 model to check cheeto cut result.")
    model_path = "yolov8_models/cheeto_cut/best.pt"
    return run_yolo_check(model_path)


# ---------------------------------------------------------
# State machine main loop
# ---------------------------------------------------------
def main():
    current_state = State.MOVE_CHEETO
    next_after_home: Optional[State] = None
    iteration = 0

    logging.info("Starting Cheeto state machine.")

    while True:
        iteration += 1
        if iteration > MAX_ITERATIONS:
            logging.error("Reached MAX_ITERATIONS=%d. Aborting for safety.", MAX_ITERATIONS)
            break

        logging.info("=== Iteration %d | State: %s ===", iteration, current_state.name)

        if current_state == State.MOVE_CHEETO:
            # Step 1: MoveCheeto
            run_move_cheeto()
            # After homing from here, we want to go to CHECK_CHEETO_POSITION
            next_after_home = State.CHECK_CHEETO_POSITION
            current_state = State.HOME_ROBOT

        elif current_state == State.HOME_ROBOT:
            # Shared state: used after MOVE_CHEETO and CUT_CHEETO
            run_home_robot()
            if next_after_home is None:
                logging.error("HOME_ROBOT reached with no next_after_home set. Aborting.")
                break
            logging.info("HomeRobot complete. Next state: %s", next_after_home.name)
            current_state = next_after_home
            next_after_home = None  # reset, just to be safe

        elif current_state == State.CHECK_CHEETO_POSITION:
            # Step 3: CheckCheetoPosition via YOLO
            position_ok = check_cheeto_position()
            if position_ok:
                logging.info("Cheeto position OK -> CutCheeto.")
                current_state = State.CUT_CHEETO
            else:
                logging.info("Cheeto position NOT OK -> MoveCheeto.")
                current_state = State.MOVE_CHEETO

        elif current_state == State.CUT_CHEETO:
            # Step 4: CutCheeto
            run_cut_cheeto()
            # After homing from here, we want to go to CHECK_CHEETO_CUT
            next_after_home = State.CHECK_CHEETO_CUT
            current_state = State.HOME_ROBOT

        elif current_state == State.CHECK_CHEETO_CUT:
            # Step 5: final check on cut via YOLO
            cut_ok = check_cheeto_cut()
            if cut_ok:
                logging.info("Cheeto cut successful. Exiting.")
                break
            else:
                logging.info("Cheeto cut NOT successful -> back to CheckCheetoPosition.")
                current_state = State.CHECK_CHEETO_POSITION

        else:
            logging.error("Unknown state: %s. Aborting.", current_state)
            break

    logging.info("State machine finished.")


if __name__ == "__main__":
    main()
