"""Small command dispatcher; no automatic training, refresh or account writes."""
import argparse
import runpy
import sys
from runtime import initialise, install_approved_model

COMMANDS = {"refresh": "refresh", "download-history": "download_history",
            "build-features": "build_features", "train": "train", "forecast": "forecast",
            "score": "score_forecast", "decision-trial": "decision_trial",
            "search-improvements": "search_improvements", "search-quality": "search_quality_targets",
            "search-lightweight": "search_lightweight", "benchmark": "external_benchmark", "benchmark-preflight": "benchmark_readiness", "run-experiment": "experiment_runner", "reference-pilot": "reference_pilot", "audit-deadlines": "deadline_provenance", "native-reference": "native_reference", "native-development": "native_development", "audit-availability": "availability_history", "conditional-reference": "conditional_reference", "historical-references": "historical_references", "archived-reference": "archived_reference", "selection-benchmark": "selection_benchmark", "participation-audit": "participation_audit", "news-probe": "news_availability_probe", "incumbent-availability": "incumbent_availability", "availability-points": "incumbent_availability_points", "availability-benchmark": "availability_rebenchmark"}

def main():
    parser = argparse.ArgumentParser(description="Local leakage-aware FPL prediction engine")
    parser.add_argument("command", choices=["init", "install-model", *COMMANDS])
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        parser.parse_args(argv)
        return
    args = parser.parse_args(argv[:1])
    rest = argv[1:]
    if args.command == "init":
        if rest: parser.error("init accepts no extra arguments")
        print(initialise()); return
    if args.command == "install-model":
        if len(rest) != 1: parser.error("install-model requires one trusted artifact path")
        print(install_approved_model(rest[0])); return
    read_only_trial = args.command == "decision-trial" and bool(rest) and rest[0] == "review"
    if not read_only_trial and args.command not in ("benchmark", "benchmark-preflight", "run-experiment", "reference-pilot", "audit-deadlines", "native-reference", "native-development", "audit-availability", "conditional-reference", "historical-references", "archived-reference", "selection-benchmark", "participation-audit", "news-probe", "incumbent-availability", "availability-points", "availability-benchmark") and not any(flag in rest for flag in ("-h", "--help")):
        initialise()
    sys.argv = [COMMANDS[args.command], *rest]
    runpy.run_module(COMMANDS[args.command], run_name="__main__")

if __name__ == "__main__": main()
