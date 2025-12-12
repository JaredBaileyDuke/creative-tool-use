# Final Deployment

## Overview

In the final stage of the project, the full creative tool use pipeline was deployed using the **LeRobot SO-101** system equipped with a **custom snap-click scissors end effector**. This phase integrated all prior insights and a few new ones to create a functioning multi-step manipulation system capable of **positioning** and **cutting** a food item.

While the robot ultimately achieved reliable cheese puff cutting, the process revealed important strengths, limitations, and considerations for future work in creative tool use.

---

## Custom Scissors End Effector

![scissors CAD](../assets/gif/scissor_CAD.gif)

A 3D-printed **snap-click mechanism** was designed to securely mount scissors to the SO-101 arm. This mount allowed the robot to use:

- The **sharp side of the blades** for the cutting portion of the task  
- The **flat side of the blades** for pushing, guiding, and orienting the cheese puff  

The mount performed well at full size but revealed a limitation at the smaller size: **snap-click connections become unreliable when scaled down** due to insufficient mechanical tolerance. This was overcome with the use of superglue and color matched duct tape.

---

## Subtask Performance

Due to task complexity, the larger task of moving and cutting was split into subtasks. Each subtask involved its own data collection and training.

### Cutting Subtask — **Worked Well**
The robot successfully cut the cheese puff using the scissor blades once the item was positioned within an pre-determined space on the cutting board. Sometimes the robot arm was overeager and would cut the cheese puff multiple times since the cheese puff didn't move much after the cuts.

### Push Only Subtask — **Worked Well**
Simple linear pushing with the scissor blades was reliable and consistent. Since cheese puffs roll easily, some difficulty was seen when this occurred. However, the ACT policy was often able to overcome this difficulty.

---

## YOLO Classification Models

As the subtasks would sometimes fail, correction was needed before proceeding to the next subtask. To assist, two YOLO classification models were trained on **800 labeled images** to automatically detect subtask completion:

### **1. Location Model**
Determines whether the cheese puff was moved to an acceptable region on the cutting board (orientation not required).

### **2. Cut Model**
Determines whether the cheese puff has been successfully cut.

These models replaced manual human verification and allowed the robot to autonomously:

- Check progress  
- Retry failed steps
  - For example, a missed cut may move the cheese puff and require a return to the Push Only subtask
- Advance through the state machine

---

## State Machine Framework (SMF)

| ![gif1](../assets/gif/great_work_1.gif) | ![gif2](../assets/gif/great_work_2.gif) |
|---------------------------------|---------------------------------|
| ![gif3](../assets/gif/great_work_3.gif) | ![gif4](../assets/gif/great_work_4.gif) |

The entire pipeline was orchestrated using a **State Machine Framework**, enabling robust decision making and automatic recovery.

### **State Descriptions**

**ROBOT MOVE**
- Robot pushes the cheese puff toward the center of the cutting board.

**YOLO LOCATION**
- YOLO checks whether the cheese puff is in a valid location. If not, the robot repeats the ROBOT MOVE state.

**ROBOT CUT**
- Robot attempts to cut the cheese puff using the scissors.

**YOLO CUT**
- YOLO verifies whether the cheese puff was successfully cut. If unsuccessful, the robot returns to the YOLO LOCATION state.

**ROBOT HOME**
- The robot arm returns to its home location.

Time limits were added to states to prevent the robot from becoming stuck in a failure loop.

---

## Additional Learnings

### System Design & Safety
- **Fail-safes are useful** for multi-step pipelines, especially when retries are possible.
- Use **separate Conda/virtual environments** for each model (lerobot and YOLO) to preserve dependency requirements.
- Programs often **lock access to cameras**. Always verify that no other process is using the device.
- Scissors are **surprisingly difficult to teleoperate**, especially for tasks requiring fine orientation.
- The SO-101 does **not provide enough force to cut a carrot**, which justified switching to a softer food item (cheese puff).
- Task decomposition matters: **“Move”** and **“Move + Orient”** must be treated as distinct skills.
- Faster GPUs means **faster iteration**, but also **faster failures**, which is good for debugging.

---

## Summary

The final deployment demonstrated that creative tool use with a one degree of freedom tool (scissors) is achievable using imitation learning, provided that:

- The task is decomposed into stable subtasks  
- Environmental conditions are controlled  
- A state machine governs retries and validation  
- YOLO models verify progress between stages  

Future work may extend this approach to more complex tools, less controlled environments, or multi degree of freedom tool dynamics.