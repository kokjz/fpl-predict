"""Small command dispatcher; no automatic training, refresh or account writes."""
import argparse
import runpy
import sys
from runtime import initialise, install_approved_model

COMMANDS = {"refresh": "refresh", "download-history": "download_history",
            "build-features": "build_features", "train": "train", "forecast": "forecast",
            "score": "score_forecast", "decision-trial": "decision_trial",
            "search-improvements": "search_improvements", "search-quality": "search_quality_targets"}

def main():
    parser = argparse.ArgumentParser(description="Local leakage-aware FPL prediction engine")
    parser.add_argument("command", choices=["init", "install-model", *COMMANDS])
    args, rest = parser.parse_known_args()
    if args.command == "init":
        if rest: parser.error("init accepts no extra arguments")
        print(initialise()); return
    if args.command == "install-model":
        if len(rest) != 1: parser.error("install-model requires one trusted artifact path")
        print(install_approved_model(rest[0])); return
    initialise()
    sys.argv = [COMMANDS[args.command], *rest]
    runpy.run_module(COMMANDS[args.command], run_name="__main__")

if __name__ == "__main__": main()
