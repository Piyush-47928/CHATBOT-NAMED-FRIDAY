MAX_SPEED = 60
MIN_SPEED = 0

MAX_TURN_ANGLE = 360
MIN_TURN_ANGLE = 0

MAX_WAIT_SECONDS = 10

OBSTACLE_LIMIT_CM = 20


def safety_check(action, sensor_data=None):

    if sensor_data is None:
        sensor_data = {}

    action_type = action.get("action")

    # STOP is always allowed
    if action_type == "STOP":
        return True, action

    # -------------------------
    # MOVE SAFETY
    # -------------------------
    if action_type == "MOVE":

        speed = action.get("speed", 0)
        direction = action.get("direction", "FORWARD")

        if not isinstance(speed, (int, float)):
            return False, {
                "action": "STOP",
                "reason": "INVALID_SPEED"
            }

        if speed < MIN_SPEED or speed > MAX_SPEED:
            return False, {
                "action": "STOP",
                "reason": "SPEED_LIMIT_EXCEEDED"
            }

        front_distance = sensor_data.get("front_distance")

        if direction == "FORWARD" and front_distance is not None:

            if front_distance <= OBSTACLE_LIMIT_CM:
                return False, {
                    "action": "STOP",
                    "reason": "OBSTACLE_TOO_CLOSE"
                }

    # -------------------------
    # TURN SAFETY
    # -------------------------
    elif action_type == "TURN":

        angle = action.get("angle", 90)

        if not isinstance(angle, (int, float)):
            return False, {
                "action": "STOP",
                "reason": "INVALID_TURN_ANGLE"
            }

        if angle < MIN_TURN_ANGLE or angle > MAX_TURN_ANGLE:
            return False, {
                "action": "STOP",
                "reason": "TURN_ANGLE_LIMIT"
            }

    # -------------------------
    # WAIT SAFETY
    # -------------------------
    elif action_type == "WAIT":

        duration = action.get("duration", 1)

        if not isinstance(duration, (int, float)):
            return False, {
                "action": "STOP",
                "reason": "INVALID_WAIT_DURATION"
            }

        if duration < 0 or duration > MAX_WAIT_SECONDS:
            return False, {
                "action": "STOP",
                "reason": "WAIT_LIMIT_EXCEEDED"
            }

    return True, action