import subprocess
import json

from action_parser import parse_response
from safety import safety_check
from world_state import WorldState


# ============================================================
# CONFIGURATION
# ============================================================

MODEL = "Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M"

LLAMA_SERVER = "http://127.0.0.1:8080"

MAX_GENERATION_TOKENS = "64"


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are RobotAI, an AI controller for a mobile robot.

Your job is to understand the user's command and select an
appropriate robot action.

AVAILABLE ACTIONS:

MOVE
TURN
STOP
LOOK
GET_DISTANCE
GET_BATTERY
SPEAK
WAIT


ACTION FORMAT:

MOVE:
{"action":"MOVE","direction":"FORWARD","speed":40}

MOVE BACKWARD:
{"action":"MOVE","direction":"BACKWARD","speed":40}

TURN:
{"action":"TURN","direction":"LEFT","angle":90}

STOP:
{"action":"STOP","reason":"USER_REQUEST"}

LOOK:
{"action":"LOOK"}

GET DISTANCE:
{"action":"GET_DISTANCE"}

GET BATTERY:
{"action":"GET_BATTERY"}

SPEAK:
{"action":"SPEAK","text":"Hello"}

WAIT:
{"action":"WAIT","seconds":2}


IMPORTANT SAFETY RULES:

1. Return JSON whenever a robot action is requested.

2. Return exactly ONE JSON object for robot actions.

3. Never invent unsupported actions.

4. Never directly control GPIO.

5. Never output shell commands.

6. Movement speed must be between 0 and 60.

7. ROBOT STATE is authoritative.

8. Do not assume sensor values that are not provided.

9. If front_distance is 20 cm or less, NEVER choose MOVE
   FORWARD.

10. If front_distance is 20 cm or less and the user requests
    forward movement, return:

{"action":"STOP","reason":"OBSTACLE_TOO_CLOSE"}

11. If battery is very low, avoid unnecessary movement.

12. Do not perform dangerous actions.

13. For robot actions, return only the JSON object.
"""


# ============================================================
# DISPLAY FUNCTIONS
# ============================================================

def display_world_state(world):
    """
    Display the current simulated robot world state.
    """

    state = world.get_state()

    print()
    print("========== WORLD STATE ==========")
    print(json.dumps(state, indent=4))
    print("=================================")
    print()


def display_action(action):
    """
    Display the action selected by RobotAI.
    """

    print()
    print("========== ROBOT ACTION ==========")
    print(json.dumps(action, indent=4))
    print("==================================")
    print()


# ============================================================
# ASK ROBOT AI
# ============================================================

def ask_robot_ai(user_input, world):
    """
    Send the user command and current robot state to Qwen
    through the local llama server.
    """

    state = world.get_state()

    state_json = json.dumps(state, indent=2)

    prompt = f"""
ROBOT STATE:

{state_json}


USER COMMAND:

{user_input}


DECISION RULES:

1. You MUST consider the current robot state.

2. If the user requests FORWARD movement and
   front_distance is 20 cm or less, return:

{{"action":"STOP","reason":"OBSTACLE_TOO_CLOSE"}}

3. If the battery is very low, avoid unnecessary movement.

4. Never exceed speed 60.

5. Return exactly ONE JSON object.

6. Do not provide explanations.

7. Do not output Markdown.

8. Do not output code fences.
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
        MAX_GENERATION_TOKENS
    ]

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            print()
            print("[LLM ERROR]")
            print(result.stderr)
            print()

            return None

        return result.stdout.strip()

    except FileNotFoundError:

        print()
        print("[ERROR] llama command not found.")
        print("Check whether llama is installed.")
        print()

        return None

    except Exception as error:

        print()
        print("[ERROR] Failed to communicate with LLM.")
        print(error)
        print()

        return None


# ============================================================
# EXECUTE ROBOT ACTION
# ============================================================

def execute_robot(action, world):
    """
    Execute an approved robot action.

    At this stage this is a simulation.
    Real GPIO/motor control will be added later.
    """

    if action is None:
        return

    action_type = action.get("action")

    # --------------------------------------------------------
    # MOVE
    # --------------------------------------------------------

    if action_type == "MOVE":

        direction = action.get(
            "direction",
            "FORWARD"
        )

        speed = action.get(
            "speed",
            40
        )

        print()
        print("========== EXECUTION ==========")
        print("ACTION    : MOVE")
        print("DIRECTION :", direction)
        print("SPEED     :", speed)
        print("MODE      : SIMULATION")
        print("===============================")

        world.simulate_movement(
            direction,
            speed
        )

    # --------------------------------------------------------
    # TURN
    # --------------------------------------------------------

    elif action_type == "TURN":

        direction = action.get(
            "direction",
            "LEFT"
        )

        angle = action.get(
            "angle",
            90
        )

        print()
        print("========== EXECUTION ==========")
        print("ACTION    : TURN")
        print("DIRECTION :", direction)
        print("ANGLE     :", angle)
        print("MODE      : SIMULATION")
        print("===============================")

        world.robot_speed = 0
        world.robot_direction = "STOPPED"

        world.update()

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    elif action_type == "STOP":

        reason = action.get(
            "reason",
            "NO_REASON_PROVIDED"
        )

        print()
        print("========== EXECUTION ==========")
        print("ACTION : STOP")
        print("REASON :", reason)
        print("===============================")

        world.stop_robot()

    # --------------------------------------------------------
    # LOOK
    # --------------------------------------------------------

    elif action_type == "LOOK":

        print()
        print("========== EXECUTION ==========")
        print("ACTION : LOOK")
        print("STATUS : Camera / vision requested")
        print("MODE   : SIMULATION")
        print("===============================")

    # --------------------------------------------------------
    # GET DISTANCE
    # --------------------------------------------------------

    elif action_type == "GET_DISTANCE":

        state = world.get_state()

        print()
        print("========== DISTANCE ==========")
        print(
            "FRONT :",
            state["front_distance"],
            "cm"
        )
        print(
            "LEFT  :",
            state["left_distance"],
            "cm"
        )
        print(
            "RIGHT :",
            state["right_distance"],
            "cm"
        )
        print("==============================")

    # --------------------------------------------------------
    # GET BATTERY
    # --------------------------------------------------------

    elif action_type == "GET_BATTERY":

        state = world.get_state()

        print()
        print("========== BATTERY ==========")
        print(
            "BATTERY :",
            state["battery"],
            "%"
        )
        print("==============================")

    # --------------------------------------------------------
    # SPEAK
    # --------------------------------------------------------

    elif action_type == "SPEAK":

        text = action.get(
            "text",
            ""
        )

        print()
        print("========== SPEAK ==========")
        print(text)
        print("===========================")

    # --------------------------------------------------------
    # WAIT
    # --------------------------------------------------------

    elif action_type == "WAIT":

        seconds = action.get(
            "seconds",
            1
        )

        print()
        print("========== WAIT ==========")
        print("SECONDS :", seconds)
        print("==========================")

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    else:

        print()
        print("[EXECUTION ERROR]")
        print("Unknown action:", action_type)
        print()


# ============================================================
# PROCESS ONE COMMAND
# ============================================================

def process_command(user_input, world):
    """
    Complete RobotAI pipeline:

    User command
        ↓
    Qwen
        ↓
    JSON parser
        ↓
    Safety system
        ↓
    Robot execution
    """

    # --------------------------------------------------------
    # ASK AI
    # --------------------------------------------------------

    raw_response = ask_robot_ai(
        user_input,
        world
    )

    if raw_response is None:
        return

    # --------------------------------------------------------
    # DISPLAY RAW LLM RESPONSE
    # --------------------------------------------------------

    print()
    print("========== LLM RESPONSE ==========")
    print(raw_response)
    print("===================================")

    # --------------------------------------------------------
    # PARSE RESPONSE
    # --------------------------------------------------------

    action, message = parse_response(
        raw_response
    )

    if action is None:

        print()
        print("========== PARSER ==========")
        print("STATUS :", "REJECTED")
        print("REASON :", message)
        print("============================")
        print()

        return

    print()
    print("========== PARSER ==========")
    print("STATUS :", "VALID")
    print("MESSAGE:", message)
    print("============================")

    display_action(action)

    # --------------------------------------------------------
    # GET SENSOR / WORLD STATE
    # --------------------------------------------------------

    sensor_data = world.get_state()

    print("========== SENSOR STATE ==========")

    print(
        "Front distance :",
        sensor_data["front_distance"],
        "cm"
    )

    print(
        "Left distance  :",
        sensor_data["left_distance"],
        "cm"
    )

    print(
        "Right distance :",
        sensor_data["right_distance"],
        "cm"
    )

    print(
        "Battery        :",
        sensor_data["battery"],
        "%"
    )

    print("==================================")

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    safe, safe_action = safety_check(
        action,
        sensor_data
    )

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

        execute_robot(
            safe_action,
            world
        )

    # --------------------------------------------------------
    # APPROVED ACTION
    # --------------------------------------------------------

    else:

        print()
        print("========== SAFETY ==========")
        print("STATUS : APPROVED")
        print("============================")

        execute_robot(
            action,
            world
        )

    # --------------------------------------------------------
    # DISPLAY UPDATED STATE
    # --------------------------------------------------------

    display_world_state(world)


# ============================================================
# AUTONOMOUS FORWARD MOVEMENT
# ============================================================

def autonomous_move_forward(world, max_cycles=20):
    """
    Closed-loop autonomous movement.

    Cycle:

        Observe
          ↓
        Ask AI
          ↓
        Parse
          ↓
        Safety
          ↓
        Execute
          ↓
        Observe again
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
        print("Current front distance:",
              state["front_distance"],
              "cm")

        print("Current battery:",
              state["battery"],
              "%")

        # ----------------------------------------------------
        # HARD SAFETY CHECK
        # ----------------------------------------------------

        if state["front_distance"] <= 20:

            print()
            print("[AUTONOMOUS SAFETY]")
            print("Obstacle too close.")
            print("Stopping robot.")

            stop_action = {
                "action": "STOP",
                "reason": "OBSTACLE_TOO_CLOSE"
            }

            execute_robot(
                stop_action,
                world
            )

            break

        # ----------------------------------------------------
        # ASK AI
        # ----------------------------------------------------

        command = "Move forward safely"

        raw_response = ask_robot_ai(
            command,
            world
        )

        if raw_response is None:

            print("[AUTONOMOUS] LLM failed.")
            break

        print()
        print("LLM:", raw_response)

        # ----------------------------------------------------
        # PARSE
        # ----------------------------------------------------

        action, message = parse_response(
            raw_response
        )

        if action is None:

            print()
            print("[AUTONOMOUS] Invalid AI response.")
            print("Reason:", message)

            stop_action = {
                "action": "STOP",
                "reason": "INVALID_AI_RESPONSE"
            }

            execute_robot(
                stop_action,
                world
            )

            break

        # ----------------------------------------------------
        # SAFETY
        # ----------------------------------------------------

        sensor_data = world.get_state()

        safe, safe_action = safety_check(
            action,
            sensor_data
        )

        # ----------------------------------------------------
        # EXECUTE
        # ----------------------------------------------------

        if not safe:

            print()
            print("[AUTONOMOUS] Safety override.")

            execute_robot(
                safe_action,
                world
            )

            break

        print()
        print("[AUTONOMOUS] Action approved.")

        execute_robot(
            action,
            world
        )

        # ----------------------------------------------------
        # UPDATED STATE
        # ----------------------------------------------------

        display_world_state(world)

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
    print("You can also enter normal robot commands.")
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

        # ----------------------------------------------------
        # USER INPUT
        # ----------------------------------------------------

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

        if user_input.lower() in [
            "exit",
            "quit"
        ]:

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

        if user_input.lower() in [
            "autonomous",
            "auto",
            "auto forward"
        ]:

            autonomous_move_forward(
                world
            )

            continue

        # ----------------------------------------------------
        # NORMAL ROBOT COMMAND
        # ----------------------------------------------------

        process_command(
            user_input,
            world
        )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
