from __future__ import annotations

import argparse
import os

from executors import execute_task
from judge import process_result
from planner import build_initial_state
from tracker import fail_task, load_state, log_event, next_task, save_state


def run_loop(goal: str | None = None, *, max_iterations: int = 50, resume: bool = False) -> str:
    if resume:
        state = load_state()
        if state is None:
            raise SystemExit("No existing tracker_state.json found to resume.")
    else:
        if not goal:
            raise SystemExit("A goal is required unless --resume is used.")
        for artifact in ("tracker.md", "tracker_state.json"):
            if os.path.exists(artifact):
                os.remove(artifact)
        state = build_initial_state(goal)
        save_state(state)

    for step in range(max_iterations):
        if state.status == "DONE":
            break

        task = next_task(state)
        if task is None:
            log_event(state, "No runnable task remained.")
            save_state(state)
            break

        log_event(state, f"Executing task {step + 1}: {task.title}")
        save_state(state)

        try:
            result = execute_task(state, task)
            process_result(state, task, result)
        except Exception as exc:
            fail_task(state, task.id, str(exc))
            log_event(state, f"Unhandled exception while executing {task.title}: {exc}")

        save_state(state)

    print(save_state_and_render(state))
    return state.final_result


def save_state_and_render(state) -> str:
    save_state(state)
    return open("tracker.md", "r").read()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DEW planner/worker/judge loop.")
    parser.add_argument("goal", nargs="?", help="Goal to solve")
    parser.add_argument("--max-iterations", type=int, default=50)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    run_loop(args.goal, max_iterations=args.max_iterations, resume=args.resume)


if __name__ == "__main__":
    main()
