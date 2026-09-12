import subprocess
import json

MODEL = "Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M"

SYSTEM_PROMPT = """
You are RobotAI, the artificial intelligence brain of a mobile robot.

Your responsibilities are:
1. Understand the user's commands.
2. Reason about the robot's environment.
3. Decide safe actions.
4. Never move the robot when an obstacle makes movement unsafe.
5. Eventually communicate with sensors, motors, camera and other robot systems.

Available robot actions:

MOVE
TURN
STOP
LOOK
GET_DISTANCE
GET_BATTERY
SPEAK
WAIT

For now, do not directly control hardware.

When a robot action is required, respond using JSON.

Example:

{
  "action": "MOVE",
  "direction": "FORWARD",
  "speed": 40
}

For an obstacle:

{
  "action": "STOP",
  "reason": "OBSTACLE_TOO_CLOSE"
}

For normal conversation, you may respond naturally.
"""

def ask_robotai(user_input):

    prompt = f"""
{SYSTEM_PROMPT}

USER:
{user_input}

ROBOTAI:
"""

    command = [
        "llama",
        "cli",
        "-hf",
        MODEL,
        "-p",
        prompt,
        "-n",
        "256"
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    return result.stdout


def main():

    print("=" * 50)
    print("              ROBOTAI")
    print("        Qwen2.5-1.5B Brain")
    print("=" * 50)
    print("Type 'exit' to quit.\n")

    while True:

        user_input = input("You: ")

        if user_input.lower() == "exit":
            print("RobotAI shutting down.")
            break

        response = ask_robotai(user_input)

        print("\nRobotAI:")
        print(response)
        print()


if __name__ == "__main__":
    main()
