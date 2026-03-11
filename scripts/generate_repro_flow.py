#!/usr/bin/env python3

import argparse
import copy
import gzip
import json
import uuid
from pathlib import Path


PROCESSOR_TYPES = [
    "ReproProcessorAlpha",
    "ReproProcessorBeta",
    "ReproProcessorGamma",
]
NAMESPACE = uuid.UUID("6b9a9a7a-5aa9-4b7c-96d4-2f5a4b1bb10d")


def load_gzip_json(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def dump_gzip_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False)


def stable_uuid(name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, name))


def make_process_group(root_group_id: str, group_index: int) -> dict:
    group_id = stable_uuid(f"group:{group_index}")
    return {
        "identifier": group_id,
        "instanceIdentifier": stable_uuid(f"instance:group:{group_index}"),
        "name": f"Python Repro Group {group_index + 1:02d}",
        "comments": "Synthetic group for reproducing Python bridge startup deadlocks.",
        "position": {
            "x": float((group_index % 2) * 720),
            "y": float((group_index // 2) * 640),
        },
        "processGroups": [],
        "remoteProcessGroups": [],
        "processors": [],
        "inputPorts": [],
        "outputPorts": [],
        "connections": [],
        "labels": [],
        "funnels": [],
        "controllerServices": [],
        "defaultFlowFileExpiration": "0 sec",
        "defaultBackPressureObjectThreshold": 10000,
        "defaultBackPressureDataSizeThreshold": "1 GB",
        "scheduledState": "ENABLED",
        "executionEngine": "INHERITED",
        "maxConcurrentTasks": 1,
        "statelessFlowTimeout": "1 min",
        "flowFileConcurrency": "UNBOUNDED",
        "flowFileOutboundPolicy": "STREAM_WHEN_AVAILABLE",
        "componentType": "PROCESS_GROUP",
        "groupIdentifier": root_group_id,
    }


def make_processor(group_id: str, global_index: int, local_index: int, processor_type: str) -> dict:
    return {
        "identifier": stable_uuid(f"processor:{group_id}:{global_index}"),
        "instanceIdentifier": stable_uuid(f"instance:processor:{group_id}:{global_index}"),
        "name": f"{processor_type} {global_index + 1:03d}",
        "comments": "Synthetic processor for reproducing Python bridge startup deadlocks.",
        "position": {
            "x": float((local_index % 6) * 280),
            "y": float((local_index // 6) * 160),
        },
        "type": processor_type,
        "bundle": {
            "group": "org.apache.nifi",
            "artifact": "python-extensions",
            "version": "1.0.0",
        },
        "properties": {},
        "propertyDescriptors": {},
        "style": {},
        "schedulingPeriod": "0 sec",
        "schedulingStrategy": "TIMER_DRIVEN",
        "executionNode": "ALL",
        "penaltyDuration": "30 sec",
        "yieldDuration": "1 sec",
        "bulletinLevel": "WARN",
        "runDurationMillis": 0,
        "concurrentlySchedulableTaskCount": 1,
        "autoTerminatedRelationships": ["success", "failure"],
        "scheduledState": "ENABLED",
        "retryCount": 10,
        "retriedRelationships": [],
        "backoffMechanism": "PENALIZE_FLOWFILE",
        "maxBackoffPeriod": "10 mins",
        "componentType": "PROCESSOR",
        "groupIdentifier": group_id,
    }


def reset_root_group(root: dict) -> None:
    for key in [
        "processGroups",
        "remoteProcessGroups",
        "processors",
        "inputPorts",
        "outputPorts",
        "connections",
        "labels",
        "funnels",
        "controllerServices",
    ]:
        root[key] = []


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic persisted flow.json.gz for the NiFi Python bridge reproducer."
    )
    parser.add_argument("--base-flow", type=Path, required=True, help="Existing clean flow.json.gz")
    parser.add_argument("--output", type=Path, required=True, help="Output persisted flow.json.gz")
    parser.add_argument("--group-count", type=int, default=4, help="Number of process groups")
    parser.add_argument(
        "--instances-per-group",
        type=int,
        default=36,
        help="Number of processor instances per process group",
    )
    parser.add_argument(
        "--processor-types",
        default=",".join(PROCESSOR_TYPES),
        help="Comma-separated processor type names",
    )
    args = parser.parse_args()

    if args.group_count <= 0:
        raise SystemExit("--group-count must be positive")
    if args.instances_per_group <= 0:
        raise SystemExit("--instances-per-group must be positive")

    processor_types = [item.strip() for item in args.processor_types.split(",") if item.strip()]
    if not processor_types:
        raise SystemExit("At least one processor type is required")

    persisted = load_gzip_json(args.base_flow)
    flow = copy.deepcopy(persisted)
    root = flow["rootGroup"]

    reset_root_group(root)
    for top_level_key in [
        "parameterContexts",
        "parameterProviders",
        "controllerServices",
        "reportingTasks",
        "flowAnalysisRules",
        "registries",
    ]:
        if top_level_key in flow and isinstance(flow[top_level_key], list):
            flow[top_level_key] = []

    total_processors = 0
    for group_index in range(args.group_count):
        group = make_process_group(root["identifier"], group_index)
        for local_index in range(args.instances_per_group):
            processor_type = processor_types[(group_index + local_index) % len(processor_types)]
            processor = make_processor(
                group["identifier"],
                total_processors,
                local_index,
                processor_type,
            )
            group["processors"].append(processor)
            total_processors += 1
        root["processGroups"].append(group)

    dump_gzip_json(args.output, flow)

    print(f"Built {args.output}")
    print(f"Process groups: {args.group_count}")
    print(f"Processors per group: {args.instances_per_group}")
    print(f"Total processors: {total_processors}")
    print("Processor types:")
    for processor_type in processor_types:
        print(f"  {processor_type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
