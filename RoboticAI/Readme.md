# 🤖 RobotAI

> **A local LLM-powered robotic intelligence system for safe, structured, and autonomous robot control.**

RobotAI is a robotics AI project designed to build the **decision-making brain of a mobile robot** using a locally running Large Language Model (LLM).

The system is designed around one core principle:

> **The LLM decides WHAT the robot should do. The deterministic control system decides WHETHER it is safe and HOW it should be executed.**

---

## 🧠 Architecture

```text
                         USER
                           │
                           ▼
                 ┌──────────────────┐
                 │   RobotAI LLM    │
                 │ Qwen 2.5 1.5B    │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Decision/Planner │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │  Action Parser   │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │  Safety Layer    │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Hardware Abstraction
                 │      Layer       │
                 └────────┬─────────┘
                          │
                          ▼
                    Raspberry Pi
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
           Motors      Sensors      Camera
              │           │           │
              └───────────┼───────────┘
                          ▼
                     World State
                          │
                          └──────► RobotAI
```

---

# 🎯 Project Goal

The goal of RobotAI is to develop a **real robotic AI architecture**, rather than simply creating an AI chatbot or an API wrapper.

The final robot should be able to:

* Understand natural-language commands
* Observe its environment
* Maintain a representation of the world state
* Decide what action should be performed
* Generate a structured robot action
* Validate the action
* Check the action against deterministic safety rules
* Execute the approved action
* Observe the result
* Continue operating autonomously

---

# ⚡ Core Design Principle

RobotAI separates **AI decision-making** from **physical control**.

```text
LLM
 │
 │ WHAT?
 ▼
Decision
 │
 ▼
Action JSON
 │
 ▼
Parser
 │
 ▼
Safety Layer
 │
 │ SAFE?
 ├───────────────┐
 │               │
 ▼               ▼
Execute         STOP
```

The LLM does **not** directly control:

* GPIO
* Motors
* Shell commands
* Operating-system commands
* Arbitrary Python code
* Hardware drivers

This separation is important because LLM output is probabilistic, while robot safety should be deterministic.

---

# 🤖 Supported Actions

RobotAI currently supports:

| Action         | Description                   |
| -------------- | ----------------------------- |
| `MOVE`         | Move forward/backward         |
| `TURN`         | Turn left/right               |
| `STOP`         | Stop robot                    |
| `LOOK`         | Observe environment           |
| `GET_DISTANCE` | Get directional distance      |
| `GET_BATTERY`  | Get battery state             |
| `SPEAK`        | Produce robot speech          |
| `WAIT`         | Wait for a specified duration |

---

# 📦 Action Protocol

RobotAI requires the LLM to generate **exactly one JSON object**.

## MOVE

```json
{
  "action": "MOVE",
  "direction": "FORWARD",
  "speed": 40
}
```

Allowed directions:

```text
FORWARD
BACKWARD
```

Speed:

```text
0–60
```

---

## TURN

```json
{
  "action": "TURN",
  "direction": "LEFT",
  "angle": 90
}
```

Allowed directions:

```text
LEFT
RIGHT
```

Angle:

```text
0–360 degrees
```

---

## STOP

```json
{
  "action": "STOP",
  "reason": "OBSTACLE_TOO_CLOSE"
}
```

---

## LOOK

```json
{
  "action": "LOOK"
}
```

---

## GET_DISTANCE

```json
{
  "action": "GET_DISTANCE",
  "direction": "FRONT"
}
```

Allowed directions:

```text
FRONT
LEFT
RIGHT
```

---

## GET_BATTERY

```json
{
  "action": "GET_BATTERY"
}
```

---

## SPEAK

```json
{
  "action": "SPEAK",
  "text": "I have detected an obstacle."
}
```

---

## WAIT

```json
{
  "action": "WAIT",
  "duration": 2
}
```

> `duration` is the valid field. `seconds` is intentionally rejected.

Maximum duration:

```text
10 seconds
```

---

# 🔐 Safety Layer

Every AI-generated action passes through the safety layer before execution.

```text
                LLM
                 │
                 ▼
          Raw AI Response
                 │
                 ▼
          Action Parser
                 │
                 ▼
        Action Validation
                 │
                 ▼
           Safety Layer
              /     \
             /       \
          SAFE       UNSAFE
           │            │
           ▼            ▼
        Execute        STOP
```

## Safety Limits

```text
MAX_SPEED          = 60
MIN_SPEED          = 0
MAX_TURN_ANGLE     = 360°
MAX_WAIT_SECONDS   = 10
OBSTACLE_LIMIT_CM  = 20
```

---

# 🚧 Obstacle Safety

Forward movement requires valid front-distance information.

If:

```text
front_distance <= 20 cm
```

RobotAI rejects the movement and generates a STOP condition.

Example:

```json
{
  "action": "STOP",
  "reason": "OBSTACLE_TOO_CLOSE"
}
```

If the required sensor information is missing or invalid, forward movement is also rejected.

---

# 🛑 Fail-Safe Behavior

RobotAI follows a **fail-closed** design.

The robot should stop when:

* LLM is unavailable
* LLM request times out
* LLM response is invalid
* Multiple actions are returned
* Unknown action is returned
* Invalid movement speed is provided
* Speed exceeds the maximum
* Invalid turn angle is provided
* Turn angle exceeds the maximum
* WAIT duration is invalid
* WAIT duration exceeds the maximum
* Required sensor data is missing
* Obstacle is too close
* Safety validation fails

Example:

```text
Qwen Server
     │
     X
Unavailable
     │
     ▼
LLM_UNREACHABLE
     │
     ▼
   STOP
```

---

# 🧠 Local AI Model

Current model:

```text
Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M
```

The model runs locally through the `llama` runtime.

Current development configuration:

```text
Context Size:       2048
Temperature:        0.1
Maximum Tokens:     32
Maximum Attempts:   2
Inference:          CPU
```

The LLM is intentionally constrained to short structured responses.

Instead of generating long explanations, the model primarily performs:

```text
Natural Language
       │
       ▼
Robot Decision
       │
       ▼
JSON Action
```

---

# ⚡ Fast Command Path

Simple deterministic commands can bypass the LLM.

Examples:

```text
stop
halt
emergency stop
move forward
move backward
turn left
turn right
look
distance
battery
```

This reduces unnecessary inference and improves response time for simple commands.

---

# 🌎 World State

RobotAI contains a simulated world-state system.

The simulation represents:

```text
Position
Heading
Speed
Direction
Battery
Front Distance
Left Distance
Right Distance
Obstacles
```

Example:

```text
             WORLD
 ┌─────────────────────────────┐
 │                             │
 │          █████              │
 │          █████  Obstacle    │
 │                             │
 │             🤖              │
 │            Robot            │
 │                             │
 └─────────────────────────────┘
```

The simulation allows the AI control system to be tested before connecting physical hardware.

---

# 🔄 Autonomous Mode

The planned autonomous control loop is:

```text
┌───────────────┐
│    OBSERVE    │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  AI DECISION  │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│     PARSE     │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│     SAFETY    │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    EXECUTE    │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    OBSERVE    │
└───────┬───────┘
        │
        └──────────► Repeat
```

Every movement decision is checked by the safety layer.

---

# 📁 Project Structure

```text
RobotAI/
│
├── robo_controller.py
├── action_parser.py
├── safety.py
├── world_state.py
├── config.py
├── requirements.txt
├── README.md
│
└── tests/
    ├── test_action_parser.py
    ├── test_safety.py
    ├── test_world_state.py
    └── test_controller.py
```

---

# 🧩 Main Components

## `robo_controller.py`

Main RobotAI controller.

Responsibilities:

* User interaction
* Fast command processing
* Qwen communication
* AI response handling
* Action execution
* Autonomous mode
* Error handling

---

## `action_parser.py`

Responsible for:

* JSON extraction
* Action detection
* Action normalization
* Parameter validation
* Default values
* Invalid response rejection
* Multiple-action rejection

---

## `safety.py`

Responsible for deterministic safety checks.

Checks:

* Movement speed
* Turn angle
* WAIT duration
* Obstacle distance
* Sensor availability
* Supported actions

Unsafe commands fail closed to STOP.

---

## `world_state.py`

Responsible for simulation.

Models:

* Position
* Heading
* Speed
* Direction
* Battery
* Sensors
* Obstacles

---

# 🧪 Testing

The current RobotAI core has been tested at the **simulation/control level**.

### Action Parser

```text
12 / 12 tests passed
```

Tests include:

* Valid actions
* Invalid JSON
* Multiple action objects
* Invalid actions
* Invalid parameters
* WAIT validation

---

### World State

```text
4 / 4 tests passed
```

Tests include:

* Sensor overrides
* Directional obstacle handling
* Blocked movement
* Sensor override clearing

---

### Controller Integration

The following action paths have been tested:

```text
MOVE
TURN
STOP
LOOK
GET_DISTANCE
GET_BATTERY
SPEAK
WAIT
```

Safety scenarios tested:

```text
Obstacle detection
Blocked movement
Invalid actions
Invalid speed
Excessive turn angle
Excessive WAIT duration
Missing sensor data
LLM failure handling
Fast-path commands
```

---

# 📊 Project Status

| Component              | Status        |
| ---------------------- | ------------- |
| RobotAI architecture   | ✅ Complete    |
| Action protocol        | ✅ Complete    |
| Action parser          | ✅ Tested      |
| Safety layer           | ✅ Tested      |
| World simulation       | ✅ Tested      |
| Robot controller       | ✅ Tested      |
| Fast command path      | ✅ Implemented |
| Fail-safe STOP         | ✅ Implemented |
| Autonomous pipeline    | ✅ Implemented |
| Live Qwen server test  | 🔄 Pending    |
| Hardware abstraction   | 🔄 Planned    |
| Raspberry Pi           | 🔄 Planned    |
| Motor control          | 🔄 Planned    |
| Physical sensors       | 🔄 Planned    |
| Camera perception      | 🔄 Planned    |
| Physical robot testing | 🔄 Planned    |

> **Note:** The current verification is at the software simulation/control level. Physical robot functionality has not yet been verified.

---

# 💻 Development Environment

```text
OS:          Kali Linux Rolling
Platform:    VMware
Architecture: x86-64
Python:      3.14.x
LLM Runtime: llama
Inference:   CPU
```

Project directory:

```bash
~/RoboticAI
```

---

# 🚀 Hardware Roadmap

The eventual physical architecture will be:

```text
              Camera
                │
                ▼
          Computer Vision
                │
                ▼
Sensors ──► World State ◄── Robot State
                │
                ▼
             RobotAI
                │
                ▼
          Action Contract
                │
                ▼
          Safety Layer
                │
                ▼
       Hardware Abstraction
                │
                ▼
          Raspberry Pi
                │
                ▼
          Motor Driver
                │
                ▼
             Motors
```

The LLM remains isolated from direct GPIO access.

---

# 🛠️ Development Roadmap

## Phase 1 — RobotAI Software Brain

* [x] Robot architecture
* [x] Action contract
* [x] JSON parser
* [x] Safety layer
* [x] World simulation
* [x] Controller
* [x] Fast command path
* [x] Fail-safe handling
* [x] Core testing

## Phase 2 — Live LLM

* [ ] Verify live Qwen communication
* [ ] Measure inference latency
* [ ] Test repeated requests
* [ ] Optimize local inference
* [ ] Test malformed responses

## Phase 3 — Hardware Abstraction

* [ ] Motor interface
* [ ] Sensor interface
* [ ] Hardware-independent control
* [ ] Connect simulation to HAL

## Phase 4 — Raspberry Pi

* [ ] Raspberry Pi setup
* [ ] RobotAI deployment
* [ ] Runtime optimization
* [ ] Communication testing

## Phase 5 — Motors & Sensors

* [ ] Motor driver
* [ ] Motor control
* [ ] Distance sensors
* [ ] Battery monitoring
* [ ] Physical safety testing

## Phase 6 — Computer Vision

* [ ] Camera integration
* [ ] Vision pipeline
* [ ] Object detection
* [ ] Obstacle perception
* [ ] World-state integration

## Phase 7 — Autonomous Robot

```text
PERCEIVE
   ↓
UNDERSTAND
   ↓
REASON
   ↓
DECIDE
   ↓
SAFETY CHECK
   ↓
ACT
   ↓
OBSERVE
   ↓
RE-EVALUATE
   ↓
REPEAT
```

---

# 🔒 Security Philosophy

RobotAI follows a critical rule:

> **LLM output is data, not permission.**

For example, if the LLM generates:

```json
{
  "action": "MOVE",
  "direction": "FORWARD",
  "speed": 100
}
```

the command is **not** directly executed.

Instead:

```text
LLM
 │
 ▼
Parser
 │
 ▼
Validation
 │
 ▼
Safety Layer
 │
 ├── Safe ───────► Execute
 │
 └── Unsafe ─────► STOP
```

This architecture helps protect the robot against unexpected or malformed AI output.

---

# 🎯 Long-Term Vision

RobotAI aims to combine:

* 🤖 Robotics
* 🧠 Local LLMs
* 👁️ Computer Vision
* 📡 Sensor Fusion
* 🔌 Embedded Systems
* 🐍 Python
* 🍓 Raspberry Pi
* ⚡ Edge AI
* 🛡️ Deterministic Safety
* 🚗 Autonomous Navigation

The long-term objective is a robot that can:

```text
PERCEIVE
   ↓
UNDERSTAND
   ↓
REASON
   ↓
DECIDE
   ↓
ACT
   ↓
OBSERVE
   ↓
CONTINUE AUTONOMOUSLY
```

---

# 📌 Current Milestone

### RobotAI Software Brain — Core Complete

The current system contains:

```text
Local LLM
    +
Action Parser
    +
Safety Layer
    +
World State
    +
Robot Controller
    +
Fail-Safe Handling
```

The next major milestone is:

```text
Live Qwen Integration
        ↓
Hardware Abstraction Layer
        ↓
Raspberry Pi
        ↓
Motors + Sensors
        ↓
Camera
        ↓
Physical Autonomous Robot
```

---

# 👨‍💻 Development Philosophy

RobotAI is developed incrementally.

The priority is:

```text
Correctness
    ↓
Safety
    ↓
Testability
    ↓
Performance
    ↓
Hardware Integration
    ↓
Autonomy
```

Working components should not be unnecessarily redesigned.

Every major modification should be:

```text
Implement
   ↓
Test
   ↓
Regression Test
   ↓
Simulation Verification
   ↓
Hardware Verification
```

---

# ⭐ Final Goal

```text
Natural Language
       ↓
Local LLM
       ↓
Robot Decision
       ↓
Structured Action
       ↓
Deterministic Safety
       ↓
Hardware Abstraction
       ↓
Raspberry Pi
       ↓
Physical Robot
       ↓
Sensors / Camera
       ↓
World State
       ↓
RobotAI
```

> **RobotAI — From Natural Language to Safe Physical Action.**

---

## 📜 License

This project is currently under development.

License information will be added when the project is prepared for public release.

