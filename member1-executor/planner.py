class Planner:
    def __init__(self):
        pass

    def create_plan(self, task: str):
        """Generates steps for the given task."""
        print(f"[Planner] Generating plan for: {task}")
        return [
            {"step_id": 1, "action": "Gather requirements", "details": task},
            {"step_id": 2, "action": "Execute core logic", "details": "Processing steps"},
            {"step_id": 3, "action": "Output result", "details": "Finished"}
        ]