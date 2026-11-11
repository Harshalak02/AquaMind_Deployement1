"""Run the real AquaMind crew on ONE benchmark case and write the row + trace as JSON.

usage (from repo root): python -I demo_agent/run_one.py <case> <spread_k3|spread_k5|spread_k10> <out.json>
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
case, layout, out = sys.argv[1:4]
bench = "data/benchmark/agentix_master"
print("loading the town and the benchmark...", flush=True)
from aquamind.eval.runner import World, run_case      # noqa: E402
from aquamind.methods import registry                  # noqa: E402

world = World(bench)
methods = registry(None, "rules")
print("running the four-agent crew (this calls the LLM)...", flush=True)
row = run_case(world, methods["agentix_crew"], case, layout)
json.dump(row, open(out, "w"), default=str)
print("done", row.get("outcome"), flush=True)
