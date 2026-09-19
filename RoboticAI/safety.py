MAX_SPEED = 60
MIN_SPEED = 0

MAX_TURN_ANGLE = 360
MIN_TURN_ANGLE = 0

MAX_WAIT_SECONDS = 10

OBSTACLE_LIMIT_CM = 20

# Actions that need no physical safety check (informational / no motion)
PASSIVE_ACTIONS = {"LOOK", "GET_DISTANCE", "GET_BATTERY", "SPEAK"}


def _stop(reason):
    return False, {"action": "STOP", "reason": reason}


def safety_check(action, sensor_data=None):

    if not isinstance(action, dict):
        return _stop("INVALID_ACTION_FORMAT")

    action_type = action.get("action")
    sensor_data = sensor_data or {}

    # STOP is always safe
    if action_type == "STOP":
        return True, action

    # ---------------- MOVE ----------------
    if action_type == "MOVE":

        speed = action.get("speed", 0)
        direction = action.get("direction", "FORWARD")

        if not isinstance(speed, (int, float)):
            return _stop("INVALID_SPEED")

        if speed < MIN_SPEED or speed > MAX_SPEED:
            return _stop("SPEED_LIMIT_EXCEEDED")

        if direction == "FORWARD":
            front_distance = sensor_data.get("front_distance")

            # Unknown surroundings = unsafe to move forward.
            if front_distance is None:
                return _stop("MISSING_SENSOR_DATA")

            if not isinstance(front_distance, (int, float)):
                return _stop("INVALID_SENSOR_DATA")

            if front_distance <= OBSTACLE_LIMIT_CM:
                return _stop("OBSTACLE_TOO_CLOSE")

        return True, action

    # ---------------- TURN ----------------
    if action_type == "TURN":

        angle = action.get("angle", 90)

        if not isinstance(angle, (int, float)):
            return _stop("INVALID_TURN_ANGLE")

        if angle < MIN_TURN_ANGLE or angle > MAX_TURN_ANGLE:
            return _stop("TURN_ANGLE_LIMIT")

        return True, action

    # ---------------- WAIT ----------------
    if action_type == "WAIT":

        duration = action.get("duration", 1)

        if not isinstance(duration, (int, float)):
            return _stop("INVALID_WAIT_DURATION")

        if duration < 0 or duration > MAX_WAIT_SECONDS:
            return _stop("WAIT_LIMIT_EXCEEDED")

        return True, action

    # ---------------- Passive / informational actions ----------------
    if action_type in PASSIVE_ACTIONS:
        return True, action

    # ---------------- Anything else: fail closed ----------------
    return _stop("UNKNOWN_OR_UNSAFE_ACTION")
