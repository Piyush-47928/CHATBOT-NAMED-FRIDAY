import json
import math


# ============================================================
# Simulation Constants
# ============================================================

# Heading convention: compass degrees, clockwise from North.
#   0   = North  (+Y)
#   90  = East   (+X)
#   180 = South  (-Y)
#   270 = West   (-X)

SENSOR_MAX_RANGE = 100      # cm -- matches the old "no obstacle" default
ROBOT_RADIUS = 5            # cm -- robot's own physical footprint
COLLISION_BUFFER = 1        # cm -- gap kept from an obstacle's surface
                             # once movement is clamped, so the robot
                             # doesn't end up touching it exactly
OBSTACLE_LIMIT_CM = 20      # cm -- matches safety.py's threshold, used
                             # only for the informational *_obstacle flags


class WorldState:

    def __init__(self):
        # -----------------------------
        # Robot physical state
        # -----------------------------
        self.battery = 100

        self.x = 0.0
        self.y = 0.0
        self.heading = 0.0

        self.front_distance = SENSOR_MAX_RANGE
        self.left_distance = SENSOR_MAX_RANGE
        self.right_distance = SENSOR_MAX_RANGE

        self.robot_speed = 0
        self.robot_direction = "STOPPED"

        # -----------------------------
        # Environment
        # -----------------------------
        self.obstacles = []

        # -----------------------------
        # Derived status
        # -----------------------------
        self.obstacle_detected = False
        self.front_obstacle = False
        self.left_obstacle = False
        self.right_obstacle = False
        self.is_moving = False

        self.last_move_collided = False

        # True while sensor readings were set manually via
        # update_sensors() and haven't been invalidated by a real
        # movement/turn yet. See update_sensors() and update().
        self._sensor_override = False

    # ========================================================
    # ENVIRONMENT SETUP
    # ========================================================

    def add_obstacle(self, x, y, radius=10):
        self.obstacles.append({"x": float(x), "y": float(y), "radius": float(radius)})

    def clear_obstacles(self):
        self.obstacles = []

    # ========================================================
    # GEOMETRY
    # ========================================================

    @staticmethod
    def _direction_vector(heading_deg):
        theta = math.radians(heading_deg)
        return math.sin(theta), math.cos(theta)

    def _raycast(self, origin_x, origin_y, heading_deg, max_range, margin=0.0):
        """Distance to the nearest obstacle surface along a ray, or
        max_range if nothing is hit within that distance."""
        dx, dy = self._direction_vector(heading_deg)
        closest = max_range

        for obstacle in self.obstacles:
            ocx = obstacle["x"] - origin_x
            ocy = obstacle["y"] - origin_y
            effective_radius = obstacle["radius"] + margin

            b = ocx * dx + ocy * dy
            oc_len_sq = ocx * ocx + ocy * ocy
            perp_sq = oc_len_sq - b * b

            if perp_sq > effective_radius * effective_radius:
                continue

            thc = math.sqrt(max(0.0, effective_radius * effective_radius - perp_sq))
            t_near = b - thc
            t_far = b + thc

            t = t_near if t_near >= 0 else (t_far if t_far >= 0 else None)

            if t is not None and t < closest:
                closest = t

        return closest

    def _update_sensors_from_environment(self):
        self.front_distance = self._raycast(self.x, self.y, self.heading, SENSOR_MAX_RANGE)
        self.left_distance = self._raycast(self.x, self.y, (self.heading - 90) % 360, SENSOR_MAX_RANGE)
        self.right_distance = self._raycast(self.x, self.y, (self.heading + 90) % 360, SENSOR_MAX_RANGE)

    # ========================================================
    # UPDATE DERIVED STATE
    # ========================================================

    def update(self):
        """
        Recompute sensor readings from the environment (unless a
        manual override via update_sensors() is still active), then
        derive obstacle flags and is_moving from the current readings.
        """
        if not self._sensor_override:
            self._update_sensors_from_environment()

        # Directional flags -- these are what anything making a
        # movement decision should use, never the combined flag below.
        self.front_obstacle = self.front_distance <= OBSTACLE_LIMIT_CM
        self.left_obstacle = self.left_distance <= OBSTACLE_LIMIT_CM
        self.right_obstacle = self.right_distance <= OBSTACLE_LIMIT_CM

        # Informational only: "is something nearby in any direction".
        # NOT safe to use for deciding whether a specific move is
        # clear -- e.g. this can be True from a left-side obstacle
        # while the front is completely open. Use front_obstacle /
        # front_distance for forward-movement decisions.
        self.obstacle_detected = self.front_obstacle or self.left_obstacle or self.right_obstacle

        self.is_moving = self.robot_speed > 0

    # ========================================================
    # MOVE ROBOT
    # ========================================================

    def simulate_movement(self, direction, speed):
        direction = str(direction).upper()

        if direction == "FORWARD":
            movement_heading = self.heading
        elif direction == "BACKWARD":
            movement_heading = (self.heading + 180) % 360
        else:
            self.update()
            return

        # A real movement command always invalidates any manual sensor
        # override -- the world has genuinely changed, so go back to
        # geometry-driven sensing.
        self._sensor_override = False

        self.robot_direction = direction
        self.robot_speed = speed

        if speed > 0:
            self.battery -= 1
        self.battery = max(0, self.battery)

        requested_distance = max(1, int(speed // 10))

        hit_distance = self._raycast(
            self.x, self.y, movement_heading,
            max_range=requested_distance,
            margin=ROBOT_RADIUS,
        )

        if hit_distance < requested_distance:
            actual_distance = max(0.0, hit_distance - COLLISION_BUFFER)
            self.last_move_collided = True
        else:
            actual_distance = requested_distance
            self.last_move_collided = False

        dx, dy = self._direction_vector(movement_heading)
        self.x += dx * actual_distance
        self.y += dy * actual_distance

        # Fully blocked: the robot didn't move at all. Both speed AND
        # direction must reflect that it's genuinely stopped, not just
        # "FORWARD at 0 speed" -- a state that misleads anything
        # reading robot_direction, including the LLM prompt.
        if self.last_move_collided and actual_distance == 0:
            self.robot_speed = 0
            self.robot_direction = "STOPPED"

        self.update()

    # ========================================================
    # TURN ROBOT
    # ========================================================

    def simulate_turn(self, direction, angle):
        direction = str(direction).upper()

        # Turning also invalidates a manual sensor override, same
        # reasoning as movement.
        self._sensor_override = False

        if direction == "LEFT":
            self.heading = (self.heading - angle) % 360
        elif direction == "RIGHT":
            self.heading = (self.heading + angle) % 360

        self.robot_direction = f"TURN_{direction}"
        self.robot_speed = 0

        self.update()

    # ========================================================
    # STOP ROBOT
    # ========================================================

    def stop_robot(self):
        self.robot_speed = 0
        self.robot_direction = "STOPPED"
        self.update()

    # ========================================================
    # SENSOR OVERRIDE (manual / hardware injection)
    # ========================================================

    def update_sensors(self, front=None, left=None, right=None):
        """
        Manually override sensor readings. Unlike before, these values
        now actually persist -- through get_state(), update(), print_state(),
        anything -- until the robot's next simulate_movement() or
        simulate_turn() call, at which point the physical state has
        genuinely changed and auto-sensing resumes.

        Intended for: quick manual testing without setting up obstacles,
        and (later) a real-hardware mode where readings come from
        physical sensors instead of the geometry engine.
        """
        if front is not None:
            self.front_distance = max(0, front)
        if left is not None:
            self.left_distance = max(0, left)
        if right is not None:
            self.right_distance = max(0, right)

        self._sensor_override = True
        self.update()

    def resume_auto_sensors(self):
        """Explicitly cancel a manual override without needing to
        move/turn first."""
        self._sensor_override = False
        self.update()

    # ========================================================
    # BATTERY UPDATE
    # ========================================================

    def set_battery(self, battery):
        self.battery = max(0, min(100, battery))

    # ========================================================
    # GET WORLD STATE
    # ========================================================

    def get_state(self):
        self.update()

        return {
            "battery": self.battery,

            "front_distance": round(self.front_distance, 1),
            "left_distance": round(self.left_distance, 1),
            "right_distance": round(self.right_distance, 1),

            "robot_speed": self.robot_speed,
            "robot_direction": self.robot_direction,

            "obstacle_detected": self.obstacle_detected,
            "front_obstacle": self.front_obstacle,
            "left_obstacle": self.left_obstacle,
            "right_obstacle": self.right_obstacle,

            "is_moving": self.is_moving,

            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "heading": round(self.heading, 1),
        }

    # ========================================================
    # PRINT STATE
    # ========================================================

    def print_state(self):
        state = self.get_state()
        print()
        print("========== WORLD STATE ==========")
        print(json.dumps(state, indent=4))
        print("=================================")
        print()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    world = WorldState()

    print("TEST 1: manual sensor override persists across get_state()")
    world.update_sensors(front=7, left=50, right=50)
    world.get_state()          # previously this would have wiped front=7
    state = world.get_state()  # calling it twice on purpose
    assert state["front_distance"] == 7, "override did not persist!"
    print("  PASS -- front_distance still", state["front_distance"])

    print("\nTEST 2: directional obstacle flags, not just the combined one")
    world.update_sensors(front=100, left=10, right=100)
    state = world.get_state()
    assert state["front_obstacle"] is False
    assert state["left_obstacle"] is True
    assert state["obstacle_detected"] is True  # combined flag is still True
    print("  PASS -- front_obstacle:", state["front_obstacle"],
          "left_obstacle:", state["left_obstacle"],
          "(obstacle_detected:", state["obstacle_detected"], "but front is clear)")

    print("\nTEST 3: fully blocked movement resets BOTH speed and direction")
    world2 = WorldState()
    world2.add_obstacle(x=0, y=7, radius=2)  # right up against the robot
    world2.simulate_movement("FORWARD", 40)
    state = world2.get_state()
    assert state["robot_speed"] == 0
    assert state["robot_direction"] == "STOPPED"
    print("  PASS -- robot_speed:", state["robot_speed"],
          "robot_direction:", state["robot_direction"])

    print("\nTEST 4: a real movement clears a stale manual override")
    world3 = WorldState()
    world3.update_sensors(front=999, left=999, right=999)  # obviously fake
    world3.simulate_movement("FORWARD", 40)  # empty world, should move freely
    state = world3.get_state()
    assert state["front_distance"] == SENSOR_MAX_RANGE
    print("  PASS -- front_distance back to real value:", state["front_distance"])

    print("\nAll tests passed.")
