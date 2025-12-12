# COPILOT INSTRUCTIONS — creative-tool-use

Purpose
- Help an AI coding agent become productive quickly in this repository.

Big picture (what to know first)
- This repo implements a robot imitation-learning pipeline focused on "creative tool use" (scissors as a multi-purpose tool). See [README.md](README.md).
- Pipeline is organized as a State Machine Framework (SMF) with modular subtasks; YOLO classifiers validate subtask completion.
- Hardware: development moved from a Franka Research 3 (initial_exploration) to SO-101 arms for final deployment. CAD for end effector is in `CAD/`.

Where to look first (key files/dirs)
- `README.md` — project overview and primary run instructions.
- [initial_exploration/README.md](initial_exploration/README.md) — experiment notes, UMI data-collection details, and end-effector design decisions.
- `assets/` — example gifs, images and visual masks used in documentation and debugging.
- `CAD/` — custom end effector source (3D models) used by experiments.
- `pick_and_place/` and `final_deployment/` — phase folders (their READMEs are currently empty; check for code or notebooks in these directories).

Entry points & run commands (discoverable)
- README suggests the primary controller is launched with `python3 main.py`. If `main.py` is missing, search for controller/entrypoint files and ask the maintainer before assuming a new entrypoint name.
- Two separate environments are expected: a LeRobot (SO-101) environment (follow HuggingFace LeRobot instructions) and a YOLO/`ultralytics` environment for classification.

Project-specific patterns and conventions
- State Machine Framework (SMF): look for modules that implement discrete substates and recovery paths; tests and models expect the SMF to re-run prior subtasks on failure.
- YOLO models: custom classifiers (trained with `ultralytics`) are used to detect subtask completion — examine any `models/`, `weights/`, or training scripts if present.
- UMI pipeline: data collection used the Stanford UMI toolchain; image masks were modified to extend the tool field-of-view (see `initial_exploration/README.md`).

Integration points & external deps
- LeRobot v0.1 (SO-101) — hardware driver; README links to HuggingFace docs. Verify local copy or dependency management if code is included.
- YOLO/ultralytics — only `ultralytics` required for classification environment per README.
- Cameras: two physical cameras are expected in deployed runs (note this when writing mocks or simulation code).

Tasks an AI agent can do safely and immediately
- Search the repo for `main.py`, controller/state machine modules, and YOLO model loader code.
- Extract and summarize where model weights and training scripts live (if present).
- Generate small README improvements and explicit run/debug steps when entrypoints are found.

Missing or unclear items to ask the user about
- Confirm the actual runtime entrypoint (README references `main.py` but none was found). Provide the correct file if different.
- Provide environment setup details (conda env names, exact LeRobot package snapshot) if available.

Examples (phrases/actions to prefer)
- "Search for controller or `state` classes to find the SMF implementation." 
- "Look for YOLO/`ultralytics` model loaders and `weights` folders before retraining models." 

Editing guidance
- Preserve `CAD/` and `assets/` contents. Do not modify binary model weights without maintainer approval.
- When adding scripts that run hardware, include a clear `--dry-run` or `--simulate` mode.

If you update this file
- Keep it concise and example-driven. Point to the exact files above when you add new actionable instructions.

---
If anything in these notes is unclear or you want additional detail (entrypoint discovery, environment files, or model locations), tell me which piece to inspect next.
