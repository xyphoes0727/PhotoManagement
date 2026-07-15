from __future__ import annotations

import argparse
import json
from pathlib import Path

from datasets import load_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate benchmark query and ground-truth JSON from the train split.")
    parser.add_argument("--dataset-path", required=True, help="Path to the dataset directory containing the parquet data.")
    parser.add_argument("--count", type=int, default=20, help="Number of examples to generate.")
    parser.add_argument("--output-queries", required=True, help="Output path for the query JSON file.")
    parser.add_argument("--output-ground-truth", required=True, help="Output path for the ground-truth JSON file.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    dataset = load_dataset(args.dataset_path)["train"]

    query_records: list[str] = []
    ground_truth_records: list[dict[str, object]] = []

    sample_count = min(args.count, len(dataset))
    for index in range(sample_count):
        row = dict(dataset[index])
        query = str(row["caption"][0]).strip()
        img_id = str(row["img_id"])
        if not query:
            continue
        query_records.append(query)
        ground_truth_records.append({"query": query, "relevant_images": [img_id]})

    queries_path = Path(args.output_queries)
    ground_truth_path = Path(args.output_ground_truth)
    queries_path.parent.mkdir(parents=True, exist_ok=True)
    ground_truth_path.parent.mkdir(parents=True, exist_ok=True)

    queries_path.write_text(json.dumps(query_records, indent=2), encoding="utf-8")
    ground_truth_path.write_text(json.dumps(ground_truth_records, indent=2), encoding="utf-8")
    print(f"Wrote {len(query_records)} queries to {queries_path}")
    print(f"Wrote {len(ground_truth_records)} ground-truth rows to {ground_truth_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())