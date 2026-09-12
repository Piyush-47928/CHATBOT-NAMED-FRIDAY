import subprocess
import json
import time

from action_parser import parse_response
from safety import safety_check
from world_state import WorldState


# ============================================================
# CONFIGURATION
# ============================================================

MODEL = "Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M"
LLAMA_SERVER = "http://127.0.0.1:8080"

# Robot responses are short JSON objects, so 24 tokens is enough
# for the current action set and helps reduce generation latency.
MAX_GENERATION_TOKENS = "24"


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """You are RobotAI.
Return exactly one JSON robot action.
No explanation. No markdown.

Actions:
MOVE: {"action":"MOVE","direction":"FORWARD|BACKWARD","speed":0-60}
TURN: {"action":"TURN","direction":"LEFT|RIGHT","angle":0-360}
STOP: {"action":"STOP"}
LOOK: {"action":"LOOK"}
GET_DISTANCE: {"action":"GET_DISTANCE"}
GET_BATTERY: {"action":"GET_BATTERY"}
SPEAK: {"action":"SPEAK","text":"..."}
WAIT: {"action":"WAIT","duration":0-10}

Safety:
Never move forward when front distance <= 20 cm.
"""

# ============================================================
# DISPLAY FUNCTIONS
# ============================================================

def display_world_state(world):
    state = world.get_state()

    print()
    print("========== WORLD STATE ==========")
    print(json.dumps(state, indent=4))
    print("=================================")
    print()


def display_action(action):
    print()
    print("========== ROBOT ACTION ==========")
    print(json.dumps(action, indent=4))
    print("==================================")
    print()


def display_sensor_state(sensor_data):
    print()
    print("========== SENSOR STATE ==========")
    print("Front distance :", sensor_data["front_distance"], "cm")
    print("Left distance  :", sensor_data["left_distance"], "cm")
    print("Right distance :", sensor_data["right_distance"], "cm")
    print("Battery        :", sensor_data["battery"], "%")
    print("==================================")

def build_world_prompt(world):
    state = world.get_state()

    return f"""
CURRENT ROBOT STATE:
Battery: {state['battery']}%
Front distance: {state['front_distance']} cm
Left distance: {state['left_distance']} cm
Right distance: {state['right_distance']} cm
Robot speed: {state['robot_speed']}
Robot direction: {state['robot_direction']}
Obstacle detected: {state['obstacle_detected']}
"""

# ============================================================
# ASK ROBOT AI
# ============================================================

def ask_robot_ai(user_input, world):
    """
    Send the current robot state and user command to Qwen.

    Pipeline:
        User -> Qwen -> JSON
    """

    state = world.get_state()

    # Compact prompt reduces input processing overhead.
    state_json = json.dumps(state, separators=(",", ":"))

    prompt = f"""STATE:
    {state_json}

    COMMAND:
    {user_input}

    Return exactly one JSON robot action.
    """

    command = [
        "llama",
        "cli",
        "--server-base",
        LLAMA_SERVER,
        "--system-prompt",
        SYSTEM_PROMPT,
        "--prompt",
        prompt,
        "--single-turn",
        "--simple-io",
        "--no-display-prompt",
        "-n",
        MAX_GENERATION_TOKENS,
    ]

    start_time = time.perf_counter()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

    except FileNotFoundError:
        print()
        print("[ERROR] llama command not found.")
        print("Make sure the llama CLI is installed and available in PATH.")
        print()
        return None

    except Exception as error:
        print()
        print("[ERROR] Failed to communicate with Qwen.")
        print(error)
        print()
        return None

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    if result.returncode != 0:
        print()
        print("[QWEN ERROR]")
        print(result.stderr.strip())
        print("Return code:", result.returncode)
        print()
        return None

    print(f"[QWEN LATENCY] {elapsed_ms:.0f} ms")

    # llama CLI may write model/UI output to either stdout or stderr.
    # Combine both streams so the generated JSON is not lost.
    
    output = "\n".join(
        part for part in [
            result.stdout.strip(),
            result.stderr.strip()
        ]
        if part
    )

    return output

# ============================================================
# EXECUTE ROBOT ACTION
# ============================================================

def execute_robot(action, world):
    action_type = action.get("action")

    print("\n========== ACTION EXECUTION ==========")
    print(f"ACTION : {action_type}")

    # -------------------------
    # MOVE
    # -------------------------
    if action_type == "MOVE":
        direction = action.get("direction")
        speed = action.get("speed", 40)

        print(f"DIRECTION : {direction}")
        print(f"SPEED     : {speed}")

        world.simulate_movement(direction, speed)

        print("RESULT    : Movement executed")

    # -------------------------
    # TURN
    # -------------------------
    elif action_type == "TURN":
        direction = action.get("direction")
        angle = action.get("angle", 90)

        print(f"DIRECTION : {direction}")
        print(f"ANGLE     : {angle}")

        world.robot_direction = f"TURN_{direction}"
        world.robot_speed = 0
        world.update()

        print("RESULT    : Turn executed")

    # -------------------------
    # STOP
    # -------------------------
    elif action_type == "STOP":
        reason = action.get("reason", "LLM_REQUEST")

        print(f"REASON    : {reason}")

        world.stop_robot()

        print("RESULT    : Robot stopped")

    # -------------------------
    # LOOK
    # -------------------------
    elif action_type == "LOOK":
        state = world.get_state()

        print("FRONT     :", state["front_distance"], "cm")
        print("LEFT      :", state["left_distance"], "cm")
        print("RIGHT     :", state["right_distance"], "cm")

        print("RESULT    : Environment observed")

    # -------------------------
    # GET_DISTANCE
    # -------------------------
    elif action_type == "GET_DISTANCE":
        direction = action.get("direction", "FRONT")

        if direction == "FRONT":
            distance = world.front_distance

        elif direction == "LEFT":
            distance = world.left_distance

        elif direction == "RIGHT":
            distance = world.right_distance

        else:
            distance = None

        print(f"DIRECTION : {direction}")
        print(f"DISTANCE  : {distance} cm")
        print("RESULT    : Distance returned")

    # -------------------------
    # GET_BATTERY
    # -------------------------
    elif action_type == "GET_BATTERY":
        battery = world.battery

        print(f"BATTERY   : {battery}%")
        print("RESULT    : Battery level returned")

    # -------------------------
    # SPEAK
    # -------------------------
    elif action_type == "SPEAK":
        text = action.get("text", "")

        print(f"ROBOT SAYS: {text}")

        print("RESULT    : Speech executed")

    # -------------------------
    # WAIT
    # -------------------------
    elif action_type == "WAIT":
        duration = action.get("duration", 1)

        print(f"WAIT      : {duration} second(s)")

        time.sleep(duration)

        print("RESULT    : Wait completed")

    # -------------------------
    # UNKNOWN
    # -------------------------
    else:
        print("RESULT    : Unknown action")

    print("======================================")

def process_command(user_input, world):
    """
    Complete RobotAI pipeline:

        User
          |
          v
        Qwen
          |
          v
        JSON parser
          |
          v
        Safety system
          |
          v
        Robot execution

    Qwen is ALWAYS used for normal robot commands.
    There is no fast-command bypass.
    """

    # --------------------------------------------------------
    # SEND COMMAND TO QWEN
    # --------------------------------------------------------

    print()
    print("[QWEN AI]")
    print("Processing command...")
    print()

    raw_response = ask_robot_ai(user_input, world)

    if raw_response is None:
        print("[ERROR] No response received from Qwen.")
        return

    # --------------------------------------------------------
    # DISPLAY RAW QWEN RESPONSE
    # --------------------------------------------------------

    print()
    print("========== QWEN RESPONSE ==========")
    print(raw_response)
    print("===================================")

    # --------------------------------------------------------
    # PARSE QWEN RESPONSE
    # --------------------------------------------------------

    parse_start = time.perf_counter()

    action, message = parse_response(raw_response)

    parse_ms = (time.perf_counter() - parse_start) * 1000

    print(f"[PARSER LATENCY] {parse_ms:.2f} ms")

    if action is None:
        print()
        print("========== PARSER ==========")
        print("STATUS : REJECTED")
        print("REASON :", message)
        print("============================")
        print()

        # Fail-safe behavior:
        # invalid AI output must not reach execution.
        stop_action = {
            "action": "STOP",
            "reason": "INVALID_AI_RESPONSE",
        }
        execute_robot(stop_action, world)
        return

    print()
    print("========== PARSER ==========")
    print("STATUS :", "VALID")
    print("MESSAGE:", message)
    print("============================")

    display_action(action)

    # --------------------------------------------------------
    # GET CURRENT SENSOR / WORLD STATE
    # --------------------------------------------------------

    sensor_data = world.get_state()

    display_sensor_state(sensor_data)

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    safety_start = time.perf_counter()

    safe, safe_action = safety_check(
        action,
        sensor_data,
    )

    safety_ms = (time.perf_counter() - safety_start) * 1000

    print(f"[SAFETY LATENCY] {safety_ms:.2f} ms")

    # --------------------------------------------------------
    # SAFETY OVERRIDE
    # --------------------------------------------------------

    if not safe:
        print()
        print("========== SAFETY ==========")
        print("STATUS : OVERRIDE")
        print("REASON : Unsafe action detected")
        print("ACTION : STOP")
        print("============================")

        execute_robot(safe_action, world)

    # --------------------------------------------------------
    # APPROVED ACTION
    # --------------------------------------------------------

    else:
        print()
        print("========== SAFETY ==========")
        print("STATUS : APPROVED")
        print("============================")

        execute_robot(action, world)

    # --------------------------------------------------------
    # UPDATED WORLD STATE
    # --------------------------------------------------------

    display_world_state(world)


def autonomous_decision(world):
    print("\n========== AUTONOMOUS DECISION ==========")

    world_prompt = build_world_prompt(world)

    prompt = f"""
{world_prompt}

The robot is operating in a simulated environment.

Choose the safest next action.

Rules:
- Do not move forward if the front distance is 20 cm or less.
- Maximum movement speed is 60.
- If an obstacle is too close, STOP.
- Return ONLY one JSON action.

Allowed actions:
MOVE
TURN
STOP
LOOK
GET_DISTANCE
GET_BATTERY
WAIT
"""

    response = ask_robot_ai(prompt, world)

    print("\nQWEN RESPONSE:")
    print(response)

    return response

# ============================================================
# AUTONOMOUS FORWARD MOVEMENT
# ============================================================

def autonomous_move_forward(world, max_cycles=20):
    """
    Closed-loop autonomous movement.

    Every cycle keeps Qwen inside the decision loop:

        Observe
          |
          v
        Qwen
          |
          v
        Parse
          |
          v
        Safety
          |
          v
        Execute
          |
          v
        Observe again

    The hard obstacle check is a final physical safety layer.
    It does NOT replace Qwen's decision-making.
    """

    print()
    print("========================================")
    print("       AUTONOMOUS FORWARD MODE")
    print("========================================")
    print()

    for cycle in range(1, max_cycles + 1):

        print()
        print("----------------------------------------")
        print("AUTONOMOUS CYCLE :", cycle)
        print("----------------------------------------")

        # ----------------------------------------------------
        # OBSERVE
        # ----------------------------------------------------

        state = world.get_state()

        print()
        print("Front distance :", state["front_distance"], "cm")
        print("Battery        :", state["battery"], "%")

        # ----------------------------------------------------
        # HARD SAFETY LAYER
        # ----------------------------------------------------
        # This does NOT bypass Qwen during normal safe operation.
        # It prevents execution when the simulated sensor already
        # reports a critical obstacle.

        if state["front_distance"] <= 20:
            print()
            print("[AUTONOMOUS SAFETY]")
            print("Obstacle too close.")
            print("Stopping robot.")

            stop_action = {
                "action": "STOP",
                "reason": "OBSTACLE_TOO_CLOSE",
            }

            execute_robot(stop_action, world)
            break

        # ----------------------------------------------------
        # ASK QWEN
        # ----------------------------------------------------

        command = "Move forward safely"

        print()
        print("[AUTONOMOUS -> QWEN]")
        print("Requesting next decision...")

        raw_response = ask_robot_ai(
            command,
            world,
        )

        if raw_response is None:
            print("[AUTONOMOUS] Qwen failed.")
            execute_robot(
                {
                    "action": "STOP",
                    "reason": "LLM_FAILURE",
                },
                world,
            )
            break

        print()
        print("Qwen:", raw_response)

        # ----------------------------------------------------
        # PARSE
        # ----------------------------------------------------

        action, message = parse_response(raw_response)

        if action is None:
            print()
            print("[AUTONOMOUS] Invalid Qwen response.")
            print("Reason:", message)

            execute_robot(
                {
                    "action": "STOP",
                    "reason": "INVALID_AI_RESPONSE",
                },
                world,
            )
            break

        print()
        print("[AUTONOMOUS] Parsed action:")
        print(json.dumps(action, indent=4))

        # ----------------------------------------------------
        # SAFETY
        # ----------------------------------------------------

        sensor_data = world.get_state()

        safe, safe_action = safety_check(
            action,
            sensor_data,
        )

        if not safe:
            print()
            print("[AUTONOMOUS] Safety override.")
            print("Executing STOP.")

            execute_robot(
                safe_action,
                world,
            )
            break

        # ----------------------------------------------------
        # EXECUTE
        # ----------------------------------------------------

        print()
        print("[AUTONOMOUS] Action approved.")

        execute_robot(
            action,
            world,
        )

        # ----------------------------------------------------
        # UPDATED STATE
        # ----------------------------------------------------

        display_world_state(world)

        # If Qwen decides to stop, autonomous mode ends.
        if action.get("action") == "STOP":
            print("[AUTONOMOUS] Qwen selected STOP.")
            break

    print()
    print("========================================")
    print("       AUTONOMOUS MODE ENDED")
    print("========================================")
    print()


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    world = WorldState()

    print()
    print("==============================================")
    print("              RobotAI Controller")
    print("==============================================")
    print("Model :", MODEL)
    print("Server:", LLAMA_SERVER)
    print("Mode  : Simulation")
    print("----------------------------------------------")
    print("Commands:")
    print("  state")
    print("  autonomous")
    print("  exit")
    print("----------------------------------------------")
    print("Normal robot commands are sent to Qwen.")
    print("Examples:")
    print("  Move forward")
    print("  Move forward at speed 40")
    print("  Turn left 90 degrees")
    print("  Stop")
    print("  What is the battery?")
    print("  What is the distance?")
    print("==============================================")
    print()

    while True:

        try:
            user_input = input("You > ").strip()

        except KeyboardInterrupt:
            print()
            print()
            print("RobotAI stopped by user.")
            break

        except EOFError:
            print()
            print()
            print("RobotAI stopped.")
            break

        # ----------------------------------------------------
        # EMPTY INPUT
        # ----------------------------------------------------

        if not user_input:
            continue

        # ----------------------------------------------------
        # EXIT
        # ----------------------------------------------------

        if user_input.lower() in {"exit", "quit"}:
            print()
            print("RobotAI shutting down...")
            break

        # ----------------------------------------------------
        # STATE
        # ----------------------------------------------------

        if user_input.lower() == "state":
            display_world_state(world)
            continue

        # ----------------------------------------------------
        # AUTONOMOUS MODE
        # ----------------------------------------------------

        if user_input.lower() in {
            "autonomous",
            "auto",
            "auto forward",
        }:
            autonomous_move_forward(world)
            continue

        # ----------------------------------------------------
        # NORMAL ROBOT COMMAND
        # ----------------------------------------------------

        process_command(
            user_input,
            world,
        )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()

