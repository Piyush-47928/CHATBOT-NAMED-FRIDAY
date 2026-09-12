import json


# ============================================================
# Allowed Robot Actions
# ============================================================

ALLOWED_ACTIONS = {
    "MOVE",
    "TURN",
    "STOP",
    "LOOK",
    "GET_DISTANCE",
    "GET_BATTERY",
    "SPEAK",
    "WAIT"
}


# ============================================================
# Extract JSON from LLM Response
# ============================================================

def extract_json(text):

    if not text:
        return None

    # Remove markdown code fences
    text = text.replace("```json", "")
    text = text.replace("```", "")

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    json_text = text[start:end + 1]

    try:
        return json.loads(json_text)

    except json.JSONDecodeError:
        return None


# ============================================================
# Normalize Robot Action
# ============================================================

def normalize_action(action):

    if not isinstance(action, dict):
        return action

    # Normalize action name
    if "action" in action:
        action["action"] = str(action["action"]).upper()

    # Normalize direction
    if "direction" in action:
        action["direction"] = str(action["direction"]).upper()

    return action


# ============================================================
# Validate Robot Action
# ============================================================

def validate_action(action):

    if not isinstance(action, dict):
        return False, "Action is not a JSON object"

    if "action" not in action:
        return False, "Missing action field"

    action = normalize_action(action)

    action_type = action["action"]

    if action_type not in ALLOWED_ACTIONS:
        return False, f"Unknown action: {action_type}"

    # --------------------------------------------------------
    # MOVE validation
    # --------------------------------------------------------

    if action_type == "MOVE":

        if action.get("direction") not in {
            "FORWARD",
            "BACKWARD"
        }:
            return False, "Invalid MOVE direction"

        speed = action.get("speed", 40)

        if not isinstance(speed, (int, float)):
            return False, "Invalid speed"

        if speed < 0 or speed > 60:
            return False, "Speed must be between 0 and 60"

        action["speed"] = speed

    # --------------------------------------------------------
    # TURN validation
    # --------------------------------------------------------

    elif action_type == "TURN":

        if action.get("direction") not in {
            "LEFT",
            "RIGHT"
        }:
            return False, "Invalid TURN direction"

        angle = action.get("angle", 90)

        if not isinstance(angle, (int, float)):
            return False, "Invalid turn angle"

        if angle < 0 or angle > 360:
            return False, "Turn angle must be between 0 and 360"

        action["angle"] = angle

    # --------------------------------------------------------
    # SPEAK validation
    # --------------------------------------------------------

    elif action_type == "SPEAK":

        if "text" not in action:
            return False, "Missing speech text"

        action["text"] = str(action["text"])


    elif action_type == "WAIT":
        duration = action.get("duration", 1)

        if not isinstance(duration, (int, float)):
            return False, "Invalid wait duration"

        if duration < 0 or duration > 10:
            return False, "Wait duration must be between 0 and 10 seconds"

        action["duration"] = duration

    elif action_type == "GET_DISTANCE":
        direction = action.get("direction", "FRONT")
        direction = str(direction).upper()

        if direction not in {"FRONT", "LEFT", "RIGHT"}:
            return False, "Invalid distance direction"

        action["direction"] = direction

# ============================================================
# Main Parser
# ============================================================

def parse_response(text):

    action = extract_json(text)

    if action is None:
        return None, "No valid JSON found"

    action = normalize_action(action)

    valid, message = validate_action(action)

    if not valid:
        return None, message

    return action, "OK"


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":

    tests = [

        '{"action":"MOVE","direction":"FORWARD","speed":40}',

        '{"action":"move","direction":"forward"}',

        '{"action":"TURN","direction":"left","angle":90}',

        '{"action":"STOP"}'

    ]

    for test in tests:

        print("\nInput:")
        print(test)

        action, message = parse_response(test)

        print("Result:")
        print(action)

        print("Status:")
        print(message)
