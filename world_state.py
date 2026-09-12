import json


class WorldState:

    def __init__(self):
        # -----------------------------
        # Robot physical state
        # -----------------------------
        self.battery = 100

        self.front_distance = 100
        self.left_distance = 100
        self.right_distance = 100

        self.robot_speed = 0
        self.robot_direction = "STOPPED"

        # -----------------------------
        # Environment state
        # -----------------------------
        self.obstacle_detected = False

        # -----------------------------
        # Robot status
        # -----------------------------
        self.is_moving = False

    # ========================================================
    # UPDATE ENVIRONMENT
    # ========================================================

    def update(self):
        """
        Update derived robot/environment information.
        """

        self.obstacle_detected = (
            self.front_distance <= 20
            or self.left_distance <= 20
            or self.right_distance <= 20
        )

        self.is_moving = self.robot_speed > 0

    # ========================================================
    # MOVE ROBOT
    # ========================================================

    def simulate_movement(self, direction, speed):
        """
        Simulate robot movement.

        This function represents the future hardware
        abstraction layer. Real motor control can later
        replace this simulation.
        """

        self.robot_direction = direction
        self.robot_speed = speed

        # Battery consumption
        if speed > 0:
            self.battery -= 1

        # Prevent negative battery
        self.battery = max(0, self.battery)

        # -----------------------------
        # Forward movement
        # -----------------------------

        if direction == "FORWARD":

            distance_change = max(1, int(speed // 10))

            self.front_distance -= distance_change

            self.front_distance = max(
                0,
                self.front_distance
            )

        # -----------------------------
        # Backward movement
        # -----------------------------

        elif direction == "BACKWARD":

            # In the current simulation,
            # backward movement does not change
            # the front obstacle distance.
            pass

        self.update()

    # ========================================================
    # STOP ROBOT
    # ========================================================

    def stop_robot(self):
        """
        Stop the robot immediately.
        """

        self.robot_speed = 0
        self.robot_direction = "STOPPED"

        self.update()

    # ========================================================
    # SENSOR UPDATE
    # ========================================================

    def update_sensors(
        self,
        front=None,
        left=None,
        right=None
    ):
        """
        Update simulated sensor readings.

        Later these values will come from real
        ultrasonic/IR/LiDAR sensors.
        """

        if front is not None:
            self.front_distance = max(0, front)

        if left is not None:
            self.left_distance = max(0, left)

        if right is not None:
            self.right_distance = max(0, right)

        self.update()

    # ========================================================
    # BATTERY UPDATE
    # ========================================================

    def set_battery(self, battery):
        """
        Set battery percentage.
        """

        self.battery = max(
            0,
            min(100, battery)
        )

    # ========================================================
    # GET WORLD STATE
    # ========================================================

    def get_state(self):
        """
        Return the complete robot state.

        This dictionary is what RobotAI sends to Qwen.
        """

        self.update()

        return {
            "battery": self.battery,

            "front_distance": self.front_distance,
            "left_distance": self.left_distance,
            "right_distance": self.right_distance,

            "robot_speed": self.robot_speed,
            "robot_direction": self.robot_direction,

            "obstacle_detected": self.obstacle_detected,
            "is_moving": self.is_moving
        }

    # ========================================================
    # PRINT STATE
    # ========================================================

    def print_state(self):

        state = self.get_state()

        print()
        print("========== WORLD STATE ==========")

        print(
            json.dumps(
                state,
                indent=4
            )
        )

        print("=================================")
        print()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    world = WorldState()

    print("INITIAL STATE")
    world.print_state()

    print("MOVING FORWARD")
    world.simulate_movement(
        "FORWARD",
        40
    )

    world.print_state()

    print("UPDATING SENSOR")

    world.update_sensors(
        front=15,
        left=50,
        right=50
    )

    world.print_state()

    print("STOPPING ROBOT")

    world.stop_robot()

    world.print_state()