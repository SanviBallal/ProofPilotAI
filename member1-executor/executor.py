from .planner import Planner

class Executor:
    def __init__(self):
        self.planner = Planner()

    def run(self, task: str):
        plan = self.planner.create_plan(task)
        print("[Executor] Running plan...")
        for step in plan:
            print(f" -> Step {step['step_id']}: {step['action']}")
        print("[Executor] Execution complete!")

if __name__ == "__main__":
    executor = Executor()
    executor.run("Test Task")