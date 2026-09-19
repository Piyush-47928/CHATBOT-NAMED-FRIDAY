import difflib
import json
import re
import time

import requests

from action_parser import parse_response, normalize_action, validate_action
from safety import safety_check
from world_state import WorldState


# ============================================================
# CONFIGURATION
# ============================================================

MODEL = "Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M"
LLAMA_SERVER = "http://127.0.0.1:8080"
COMPLETION_ENDPOINT = f"{LLAMA_SERVER}/completion"

MAX_GENERATION_TOKENS = 24
TEMPERATURE = 0.1
REQUEST_TIMEOUT_SECONDS = 15
VERBOSE = True

# How many times to retry Qwen if it returns unparseable/ambiguous
# JSON before giving up and falling back to STOP.
MAX_QWEN_ATTEMPTS = 2

_session = requests.Session()


def log(*args):
    if VERBOSE:
        print(*args)


# ============================================================
# DEV COMMANDS (state / autonomous / exit) -- fuzzy-matched so a
# typo like "autonoumous" still resolves correctly instead of
# accidentally being sent to Qwen as a robot command.
# ============================================================

DEV_COMMAND_MAP = {
    "state": "state",
    "autonomous": "autonomous",
    "auto": "autonomous",
    "auto forward": "autonomous",
    "exit": "exit",
    "quit": "exit",
}


def match_dev_command(text):
    """Return the canonical dev command ('state' / 'autonomous' /
    'exit') if text matches one closely enough, else None. Tolerates
    small typos via difflib so 'autonoumous' still resolves."""
    normalized = text.strip().lower()

    if normalized in DEV_COMMAND_MAP:
        return DEV_COMMAND_MAP[normalized]

    close = difflib.get_close_matches(
        normalized, DEV_COMMAND_MAP.keys(), n=1, cutoff=0.75
    )
    return DEV_COMMAND_MAP[close[0]] if close else None


# ============================================================
# BOT NAME / WAKE WORD
# ============================================================

BOT_NAME_FILE = "bot_name.json"
DEFAULT_BOT_NAME = "RobotAI"


def load_bot_name():
    try:
        with open(BOT_NAME_FILE, "r") as f:
            return json.load(f).get("name", DEFAULT_BOT_NAME)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_BOT_NAME


def save_bot_name(name):
    with open(BOT_NAME_FILE, "w") as f:
        json.dump({"name": name}, f)


BOT_NAME = load_bot_name()


def build_wake_pattern(name):
    return re.compile(rf"^\s*hey\s+{re.escape(name)}\b[,:]?\s*(.*)$", re.I)


_wake_pattern = build_wake_pattern(BOT_NAME)

_NAME_CHANGE_PATTERN = re.compile(
    r"(?:call you|change your name to|your name is|i(?:'ll| will) call you)\s+(\w+)",
    re.I,
)


def try_name_change(command_text):
    global BOT_NAME, _wake_pattern

    match = _NAME_CHANGE_PATTERN.search(command_text)
    if not match:
        return None

    new_name = match.group(1).strip().capitalize()

    BOT_NAME = new_name
    save_bot_name(new_name)
    _wake_pattern = build_wake_pattern(new_name)

    log(f"[NAME CHANGE] Bot is now called '{new_name}'")

    return {"action": "SPEAK", "text": f"Okay, call me {new_name} from now on."}


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are RobotAI, the decision-making brain of a mobile robot.

Your job is to convert the user's command and current robot state
into exactly ONE executable robot action.

IMPORTANT RULES:

1. Return ONLY ONE valid JSON object.
2. Do NOT return explanations.
3. Do NOT return markdown.
4. Do NOT return the world state.
5. Do NOT return multiple actions.
6. Never write ranges such as 0-60 or 0-360 as JSON values.
7. Always use actual numeric values.
8. If you are unsure what the user means, respond with a SPEAK
   action asking them to clarify. Never guess by returning more
   than one action.

CONVERSATIONAL RULE (read this carefully):
Sensor data (front distance, battery, etc.) is ONLY relevant when the
user is asking the robot to MOVE or TURN. If the user is greeting you,
asking a question, making small talk, or saying anything that is not
a request to move, ALWAYS respond with a SPEAK action containing a
short, friendly reply -- completely ignore the obstacle/distance
values for these. Never return STOP for a conversational message.
STOP is reserved ONLY for an actual movement request that is blocked
by a genuine obstacle.

Allowed actions:

MOVE:
{"action":"MOVE","direction":"FORWARD","speed":40}

MOVE backward:
{"action":"MOVE","direction":"BACKWARD","speed":40}

TURN:
{"action":"TURN","direction":"LEFT","angle":90}

TURN right:
{"action":"TURN","direction":"RIGHT","angle":90}

STOP:
{"action":"STOP"}

LOOK:
{"action":"LOOK"}

GET_DISTANCE:
{"action":"GET_DISTANCE","direction":"FRONT"}

GET_BATTERY:
{"action":"GET_BATTERY"}

SPEAK:
{"action":"SPEAK","text":"Hello"}

WAIT:
{"action":"WAIT","duration":2}

Rules for values:

MOVE speed must be between 0 and 60.
Use a real number such as 20, 30, 40, or 50.

TURN angle must be between 0 and 360.
Use a real number such as 45, 90, or 180.

WAIT duration must be between 0 and 10 seconds.
Use a real number such as 1, 2, or 5.

MOVEMENT EXAMPLES:

If the user says "stop", return:
{"action":"STOP"}

If the user says "move forward", return:
{"action":"MOVE","direction":"FORWARD","speed":40}

If the user says "move backward", return:
{"action":"MOVE","direction":"BACKWARD","speed":40}

If the user says "turn left", return:
{"action":"TURN","direction":"LEFT","angle":90}

If the user says "turn right", return:
{"action":"TURN","direction":"RIGHT","angle":90}

If the user requests movement AND an obstacle is too close, return:
{"action":"STOP","reason":"OBSTACLE_TOO_CLOSE"}

CONVERSATION EXAMPLES (ignore sensor data for these):

If the user says "how are you", return:
{"action":"SPEAK","text":"I'm doing well, thanks for asking!"}

If the user says "what is your name", return:
{"action":"SPEAK","text":"You can call me RobotAI."}

If the user says "can I call you hulk", return:
{"action":"SPEAK","text":"Sure, you can call me Hulk!"}

If the user says "good morning", return:
{"action":"SPEAK","text":"Good morning! Ready when you are."}

If the user says something unclear or unrecognized, return:
{"action":"SPEAK","text":"Sorry, I didn't understand that -- could you rephrase?"}

Always output exactly one valid JSON object.
"""

# ============================================================
# DISPLAY FUNCTIONS
# ============================================================

def display_world_state(world):
    if not VERBOSE:
        return
    state = world.get_state()
    print()
    print("========== WORLD STATE ==========")
    print(json.dumps(state, indent=4))
    print("=================================")
    print()


def display_action(action):
    if not VERBOSE:
        return
    print()
    print("========== ROBOT ACTION ==========")
    print(json.dumps(action, indent=4))
    print("==================================")
    print()


def display_sensor_state(sensor_data):
    if not VERBOSE:
        return
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

def ask_robot_ai(user_input, world, extra_instruction=""):
    """
    Send the current robot state and user command to Qwen via
    llama-server's HTTP API. `extra_instruction` lets a retry
    attempt append a corrective note without duplicating the whole
    system prompt.
    """

    state = world.get_state()
    state_json = json.dumps(state, separators=(",", ":"))

    prompt = f"""STATE:
    {state_json}

    COMMAND:
    {user_input}
    {extra_instruction}

    Return exactly one JSON robot action.
    """

    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"

    payload = {
        "prompt": full_prompt,
        "n_predict": MAX_GENERATION_TOKENS,
        "temperature": TEMPERATURE,
        "stop": ["\n\n"],
        "cache_prompt": True,
    }

    start_time = time.perf_counter()

    try:
        response = _session.post(
            COMPLETION_ENDPOINT,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.ConnectionError:
        print()
        print("[ERROR] Could not reach llama-server at", LLAMA_SERVER)
        print("Make sure llama-server is running and listening there.")
        print()
        return None

    except requests.exceptions.Timeout:
        print()
        print(f"[ERROR] Qwen did not respond within {REQUEST_TIMEOUT_SECONDS}s.")
        print()
        return None

    except Exception as error:
        print()
        print("[ERROR] Failed to communicate with Qwen.")
        print(error)
        print()
        return None

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    log(f"[QWEN LATENCY] {elapsed_ms:.0f} ms")

    timings = data.get("timings")
    if timings:
        log(f"[PROMPT PROCESSING] {timings.get('prompt_ms', '?')} ms "
            f"({timings.get('prompt_n', '?')} tokens)")
        log(f"[GENERATION]        {timings.get('predicted_ms', '?')} ms "
            f"({timings.get('predicted_n', '?')} tokens)")

    return data.get("content", "").strip()

# ============================================================
# FAST PATH
# ============================================================

_FAST_PATTERNS = [
    (re.compile(r"^\s*stop\s*$", re.I),
        lambda m: {"action": "STOP", "reason": "USER_REQUEST"}),
    (re.compile(r"^\s*move forward(?:\s+(?:at\s+)?speed\s+(\d+))?\s*$", re.I),
        lambda m: {"action": "MOVE", "direction": "FORWARD",
                   "speed": int(m.group(1)) if m.group(1) else 40}),
    (re.compile(r"^\s*move backward(?:\s+(?:at\s+)?speed\s+(\d+))?\s*$", re.I),
        lambda m: {"action": "MOVE", "direction": "BACKWARD",
                   "speed": int(m.group(1)) if m.group(1) else 40}),
    (re.compile(r"^\s*turn left(?:\s+(\d+)\s*degrees?)?\s*$", re.I),
        lambda m: {"action": "TURN", "direction": "LEFT",
                   "angle": int(m.group(1)) if m.group(1) else 90}),
    (re.compile(r"^\s*turn right(?:\s+(\d+)\s*degrees?)?\s*$", re.I),
        lambda m: {"action": "TURN", "direction": "RIGHT",
                   "angle": int(m.group(1)) if m.group(1) else 90}),
    (re.compile(r"^\s*what(?:'s| is) the battery\??\s*$", re.I),
        lambda m: {"action": "GET_BATTERY"}),
    (re.compile(r"^\s*what(?:'s| is) the distance\??\s*$", re.I),
        lambda m: {"action": "GET_DISTANCE", "direction": "FRONT"}),
]


def try_fast_path(user_input):
    for pattern, builder in _FAST_PATTERNS:
        match = pattern.match(user_input)
        if match:
            return builder(match)
    return None

# ============================================================
# EXECUTE ROBOT ACTION
# ============================================================

def execute_robot(action, world):
    action_type = action.get("action")

    log("\n========== ACTION EXECUTION ==========")
    log(f"ACTION : {action_type}")

    if action_type == "MOVE":
        direction = action.get("direction")
        speed = action.get("speed", 40)

        log(f"DIRECTION : {direction}")
        log(f"SPEED     : {speed}")

        world.simulate_movement(direction, speed)

        log("RESULT    : Movement executed")

    elif action_type == "TURN":
        direction = action.get("direction")
        angle = action.get("angle", 90)

        log(f"DIRECTION : {direction}")
        log(f"ANGLE     : {angle}")

        world.simulate_turn(direction, angle)

        log("RESULT    : Turn executed")

    elif action_type == "STOP":
        reason = action.get("reason", "LLM_REQUEST")

        log(f"REASON    : {reason}")

        world.stop_robot()

        log("RESULT    : Robot stopped")

    elif action_type == "LOOK":
        state = world.get_state()

        log("FRONT     :", state["front_distance"], "cm")
        log("LEFT      :", state["left_distance"], "cm")
        log("RIGHT     :", state["right_distance"], "cm")

        log("RESULT    : Environment observed")

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

        log(f"DIRECTION : {direction}")
        log(f"DISTANCE  : {distance} cm")
        log("RESULT    : Distance returned")

    elif action_type == "GET_BATTERY":
        battery = world.battery

        log(f"BATTERY   : {battery}%")
        log("RESULT    : Battery level returned")

    elif action_type == "SPEAK":
        text = action.get("text", "")

        log(f"ROBOT SAYS: {text}")
        log("RESULT    : Speech executed")

    elif action_type == "WAIT":
        duration = action.get("duration", 1)

        log(f"WAIT      : {duration} second(s)")

        time.sleep(duration)

        log("RESULT    : Wait completed")

    else:
        log("RESULT    : Unknown action")

    log("======================================")


def process_command(user_input, world):
    """
    Complete RobotAI pipeline:

        User -> [name change | fast path | Qwen (w/ bounded retry)]
             -> Safety -> Execute

    If Qwen returns unparseable or ambiguous (multi-object) JSON,
    we retry up to MAX_QWEN_ATTEMPTS times with a corrective note
    before falling back to STOP -- rather than giving up on the
    first bad generation.
    """

    name_change_action = try_name_change(user_input)

    if name_change_action is not None:
        action = name_change_action

    else:
        fast_action = try_fast_path(user_input)

        if fast_action is not None:
            log()
            log("[FAST PATH] Matched -- skipping Qwen")

            action = normalize_action(fast_action)
            valid, message = validate_action(action)

            if not valid:
                execute_robot(
                    {"action": "STOP", "reason": "INVALID_AI_RESPONSE"},
                    world,
                )
                return

        else:
            action = None
            extra_instruction = ""

            for attempt in range(1, MAX_QWEN_ATTEMPTS + 1):
                log()
                log(f"[QWEN AI] Attempt {attempt}/{MAX_QWEN_ATTEMPTS}")
                log("Processing command...")
                log()

                raw_response = ask_robot_ai(
                    user_input, world, extra_instruction=extra_instruction
                )

                if raw_response is None:
                    log()
                    log("[ERROR] No response received from Qwen (server unreachable or timed out).")
                    execute_robot(
                        {"action": "STOP", "reason": "LLM_UNREACHABLE"},
                        world,
                    )
                    return

                log()
                log("========== QWEN RESPONSE ==========")
                log(raw_response)
                log("===================================")

                parse_start = time.perf_counter()
                action, message = parse_response(raw_response)
                parse_ms = (time.perf_counter() - parse_start) * 1000
                log(f"[PARSER LATENCY] {parse_ms:.2f} ms")

                if action is not None:
                    log()
                    log("========== PARSER ==========")
                    log("STATUS :", "VALID")
                    log("MESSAGE:", message)
                    log("============================")
                    break

                log()
                log("========== PARSER ==========")
                log("STATUS : REJECTED")
                log("REASON :", message)
                log("============================")

                extra_instruction = (
                    "IMPORTANT: your previous reply was invalid "
                    f"({message}). Return ONLY ONE single JSON object "
                    "and nothing else."
                )

            if action is None:
                log()
                log(f"[QWEN AI] Giving up after {MAX_QWEN_ATTEMPTS} attempts.")
                execute_robot(
                    {"action": "STOP", "reason": "INVALID_AI_RESPONSE"},
                    world,
                )
                return

    display_action(action)

    sensor_data = world.get_state()
    display_sensor_state(sensor_data)

    safety_start = time.perf_counter()
    safe, safe_action = safety_check(action, sensor_data)
    safety_ms = (time.perf_counter() - safety_start) * 1000
    log(f"[SAFETY LATENCY] {safety_ms:.2f} ms")

    if not safe:
        log()
        log("========== SAFETY ==========")
        log("STATUS : OVERRIDE")
        log("REASON : Unsafe action detected")
        log("ACTION : STOP")
        log("============================")

        execute_robot(safe_action, world)

    else:
        log()
        log("========== SAFETY ==========")
        log("STATUS : APPROVED")
        log("============================")

        execute_robot(action, world)

    display_world_state(world)


def autonomous_decision(world):
    log("\n========== AUTONOMOUS DECISION ==========")

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

    log("\nQWEN RESPONSE:")
    log(response)

    return response

# ============================================================
# AUTONOMOUS FORWARD MOVEMENT
# ============================================================

def autonomous_move_forward(world, max_cycles=20):
    log()
    log("========================================")
    log("       AUTONOMOUS FORWARD MODE")
    log("========================================")
    log()

    for cycle in range(1, max_cycles + 1):

        log()
        log("----------------------------------------")
        log("AUTONOMOUS CYCLE :", cycle)
        log("----------------------------------------")

        state = world.get_state()

        log()
        log("Front distance :", state["front_distance"], "cm")
        log("Battery        :", state["battery"], "%")

        if state["front_distance"] <= 20:
            log()
            log("[AUTONOMOUS SAFETY]")
            log("Obstacle too close.")
            log("Stopping robot.")

            stop_action = {"action": "STOP", "reason": "OBSTACLE_TOO_CLOSE"}
            execute_robot(stop_action, world)
            break

        command = "Move forward safely"

        log()
        log("[AUTONOMOUS -> QWEN]")
        log("Requesting next decision...")

        raw_response = ask_robot_ai(command, world)

        if raw_response is None:
            print("[AUTONOMOUS] Qwen failed.")
            execute_robot({"action": "STOP", "reason": "LLM_FAILURE"}, world)
            break

        log()
        log("Qwen:", raw_response)

        action, message = parse_response(raw_response)

        if action is None:
            log()
            log("[AUTONOMOUS] Invalid Qwen response.")
            log("Reason:", message)

            execute_robot({"action": "STOP", "reason": "INVALID_AI_RESPONSE"}, world)
            break

        log()
        log("[AUTONOMOUS] Parsed action:")
        log(json.dumps(action, indent=4))

        sensor_data = world.get_state()
        safe, safe_action = safety_check(action, sensor_data)

        if not safe:
            log()
            log("[AUTONOMOUS] Safety override.")
            log("Executing STOP.")
            execute_robot(safe_action, world)
            break

        log()
        log("[AUTONOMOUS] Action approved.")
        execute_robot(action, world)

        display_world_state(world)

        if action.get("action") == "STOP":
            log("[AUTONOMOUS] Qwen selected STOP.")
            break

    log()
    log("========================================")
    log("       AUTONOMOUS MODE ENDED")
    log("========================================")
    log()


# ============================================================
# MAIN PROGRAM
# ============================================================

def run_dev_command(command, world):
    """Handle a resolved dev command ('state' / 'autonomous' / 'exit').
    Returns True if the caller's loop should break (exit requested)."""
    if command == "exit":
        print()
        print("RobotAI shutting down...")
        return True

    if command == "state":
        display_world_state(world)
        return False

    if command == "autonomous":
        autonomous_move_forward(world)
        return False

    return False


def main():

    world = WorldState()

    print()
    print("==============================================")
    print("              RobotAI Controller")
    print("==============================================")
    print("Model :", MODEL)
    print("Server:", LLAMA_SERVER)
    print("Name  :", BOT_NAME)
    print("Mode  : Simulation")
    print("----------------------------------------------")
    print("Dev commands (no wake word needed):")
    print("  state")
    print("  autonomous")
    print("  exit")
    print("----------------------------------------------")
    print(f"Say 'hey {BOT_NAME}' before every robot command.")
    print("Examples:")
    print(f"  hey {BOT_NAME}, move forward")
    print(f"  hey {BOT_NAME}, turn left 90 degrees")
    print(f"  hey {BOT_NAME}, stop")
    print(f"  hey {BOT_NAME}, how are you")
    print(f"  hey {BOT_NAME}, call you Hulk")
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

        if not user_input:
            continue

        # Check dev commands against the raw input first (typo-tolerant).
        dev_command = match_dev_command(user_input)

        if dev_command is not None:
            if run_dev_command(dev_command, world):
                break
            continue

        wake_match = _wake_pattern.match(user_input)

        if not wake_match:
            log(f"[IGNORED] No wake word ('hey {BOT_NAME}') detected")
            continue

        command_text = wake_match.group(1).strip()

        if not command_text:
            print(f"{BOT_NAME} > Yes?")
            continue

        # Also check dev commands AFTER stripping the wake word, so
        # "hey RobotAI, autonomous" (or a typo of it) resolves as a
        # dev command instead of being sent to Qwen.
        dev_command = match_dev_command(command_text)

        if dev_command is not None:
            if run_dev_command(dev_command, world):
                break
            continue

        process_command(command_text, world)


if __name__ == "__main__":
    main()
