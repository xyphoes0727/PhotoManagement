from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Any, Optional
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from pinecone import Pinecone

from benchmarks.cache import BenchmarkCache


logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def percentile(values: list[float], percentile_rank: float) -> float:
    if not values:
        return 0.0
    if percentile_rank <= 0:
        return min(values)
    if percentile_rank >= 100:
        return max(values)

    ordered = sorted(values)
    position = (len(ordered) - 1) * (percentile_rank / 100.0)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    if lower_index == upper_index:
        return lower_value
    return lower_value + (upper_value - lower_value) * (position - lower_index)


def sanitize_segment(segment: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", segment).strip("._-")
    return cleaned or "image"


def load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_image_files(dataset_dir: Path) -> list[Path]:
    files = [path for path in dataset_dir.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES]
    return sorted(files)


def make_image_id(dataset_dir: Path, image_path: Path) -> str:
    relative_path = image_path.relative_to(dataset_dir)
    relative_no_suffix = relative_path.with_suffix("")
    return "__".join(sanitize_segment(part) for part in relative_no_suffix.parts)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class BenchmarkConfig:
    dataset_dir: Path
    queries_file: Path
    ground_truth_file: Optional[Path]
    output_json: Path
    output_csv: Path
    cache_dir: Path
    number_of_images: Optional[int] = None
    number_of_queries: Optional[int] = None
    warmup_iterations: int = 2
    repeated_runs: int = 5
    top_k: int = 10
    ml_base_url: str = "http://127.0.0.1:8000/ml"
    pinecone_api_key: Optional[str] = None
    pinecone_image_index_host: Optional[str] = None
    sample_seed: Optional[int] = None


@dataclass
class QueryTimingSample:
    query: str
    query_index: int
    run_index: int
    phase: str
    latency_sec: float
    cache_hit: bool
    top1_id: str = ""
    top1_score: float = 0.0
    error: str = ""


@dataclass
class QuerySummary:
    query: str
    index: int
    latencies_sec: list[float] = field(default_factory=list)
    cache_hits: int = 0
    failures: int = 0
    top_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        if self.latencies_sec:
            summary = {
                "mean_latency_sec": mean(self.latencies_sec),
                "median_latency_sec": median(self.latencies_sec),
                "p95_latency_sec": percentile(self.latencies_sec, 95),
                "p99_latency_sec": percentile(self.latencies_sec, 99),
                "fastest_latency_sec": min(self.latencies_sec),
                "slowest_latency_sec": max(self.latencies_sec),
            }
        else:
            summary = {
                "mean_latency_sec": 0.0,
                "median_latency_sec": 0.0,
                "p95_latency_sec": 0.0,
                "p99_latency_sec": 0.0,
                "fastest_latency_sec": 0.0,
                "slowest_latency_sec": 0.0,
            }

        return {
            "query": self.query,
            "index": self.index,
            "latencies_sec": self.latencies_sec,
            "cache_hits": self.cache_hits,
            "failures": self.failures,
            "top_results": self.top_results,
            **summary,
        }


@dataclass
class RetrievalQualityResult:
    query: str
    relevant_images: list[str]
    retrieved_images: list[str]
    recall_at_1: float
    recall_at_5: float
    recall_at_10: float
    mrr: float


class BenchmarkClient:
    def __init__(self, config: BenchmarkConfig, cache: BenchmarkCache) -> None:
        self.config = config
        self.cache = cache
        self.session = requests.Session()
        self.ml_base_url = config.ml_base_url.rstrip("/")

        pinecone_api_key = config.pinecone_api_key or os.getenv("PINECONE_API_KEY")
        pinecone_image_index_host = config.pinecone_image_index_host or os.getenv("PINECONE_IMAGE_INDEX_HOST")
        if not pinecone_api_key:
            raise RuntimeError("PINECONE_API_KEY is required for the benchmark runner")
        if not pinecone_image_index_host:
            raise RuntimeError("PINECONE_IMAGE_INDEX_HOST is required for the benchmark runner")

        self.pinecone = Pinecone(api_key=pinecone_api_key)
        self.image_index = self.pinecone.Index(host=pinecone_image_index_host)

    def close(self) -> None:
        self.session.close()

    def caption_image(self, image_bytes: bytes, image_id: str) -> tuple[Optional[str], float, bool, str]:
        cache_key = sha256_bytes(image_bytes)
        cached = self.cache.get_caption(cache_key)
        if cached is not None:
            return cached, 0.0, True, ""

        encoded = base64.b64encode(image_bytes).decode("ascii")
        started = perf_counter()
        try:
            response = self.session.post(
                f"{self.ml_base_url}/image-caption/",
                json={"image_id": image_id, "image": encoded},
                timeout=300,
            )
            response.raise_for_status()
            payload = response.json()
            caption = str(payload.get("caption", "")).strip()
            self.cache.set_caption(cache_key, caption)
            return caption, perf_counter() - started, False, ""
        except Exception as exc:
            return None, perf_counter() - started, False, str(exc)

    def embed_text(self, text: str) -> tuple[Optional[list[float]], float, bool, str]:
        cache_key = sha256_text(text)
        cached = self.cache.get_embedding(cache_key)
        if cached is not None:
            return cached, 0.0, True, ""

        started = perf_counter()
        try:
            encoded_text = quote(text, safe="")
            response = self.session.post(
                f"{self.ml_base_url}/text-embed/{encoded_text}",
                timeout=300,
            )
            response.raise_for_status()
            payload = response.json()
            embedding = payload.get("embed")
            if not isinstance(embedding, list):
                raise ValueError("Embedding response did not contain a vector")
            embedding_list = [float(value) for value in embedding]
            self.cache.set_embedding(cache_key, embedding_list)
            return embedding_list, perf_counter() - started, False, ""
        except Exception as exc:
            return None, perf_counter() - started, False, str(exc)

    def upsert_image(self, image_id: str, vector: list[float], metadata: dict[str, Any]) -> tuple[float, str]:
        started = perf_counter()
        try:
            self.image_index.upsert(vectors=[{"id": image_id, "values": vector, "metadata": metadata}])
            return perf_counter() - started, ""
        except Exception as exc:
            return perf_counter() - started, str(exc)

    def query_image_index(self, vector: list[float], top_k: int) -> tuple[list[dict[str, Any]], float, str]:
        started = perf_counter()
        try:
            response = self.image_index.query(vector=vector, top_k=top_k)
            matches = extract_matches(response)
            return matches, perf_counter() - started, ""
        except Exception as exc:
            return [], perf_counter() - started, str(exc)


def extract_matches(response: Any) -> list[dict[str, Any]]:
    matches = getattr(response, "matches", None)
    if matches is None and isinstance(response, dict):
        matches = response.get("matches", [])
    if matches is None:
        return []

    normalized: list[dict[str, Any]] = []
    for match in matches:
        if isinstance(match, dict):
            normalized.append({"id": match.get("id", ""), "score": float(match.get("score", 0.0))})
            continue
        normalized.append({"id": getattr(match, "id", ""), "score": float(getattr(match, "score", 0.0))})
    return normalized


def load_queries(path: Path, limit: Optional[int]) -> list[str]:
    raw = load_json_file(path)
    queries: list[str] = []
    for item in raw:
        if isinstance(item, str):
            query = item.strip()
        elif isinstance(item, dict):
            query = str(item.get("query", "")).strip()
        else:
            query = ""
        if query:
            queries.append(query)
    if limit is not None:
        return queries[:limit]
    return queries


def load_ground_truth(path: Path) -> dict[str, list[str]]:
    raw = load_json_file(path)
    mapping: dict[str, list[str]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        query = str(item.get("query", "")).strip()
        relevant = item.get("relevant_images", [])
        if query and isinstance(relevant, list):
            mapping[query] = [str(image_id) for image_id in relevant]
    return mapping


def summarize_numbers(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "mean": 0.0,
            "median": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "fastest": 0.0,
            "slowest": 0.0,
        }
    return {
        "mean": mean(values),
        "median": median(values),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "fastest": min(values),
        "slowest": max(values),
    }


def compute_retrieval_quality(query: str, retrieved_ids: list[str], relevant_images: list[str]) -> RetrievalQualityResult:
    relevant_set = [image_id for image_id in relevant_images if image_id]
    if not relevant_set:
        return RetrievalQualityResult(query, relevant_images, retrieved_ids, 0.0, 0.0, 0.0, 0.0)

    relevant_lookup = set(relevant_set)
    hits_at_1 = len([image_id for image_id in retrieved_ids[:1] if image_id in relevant_lookup])
    hits_at_5 = len([image_id for image_id in retrieved_ids[:5] if image_id in relevant_lookup])
    hits_at_10 = len([image_id for image_id in retrieved_ids[:10] if image_id in relevant_lookup])

    recall_at_1 = hits_at_1 / len(relevant_set)
    recall_at_5 = hits_at_5 / len(relevant_set)
    recall_at_10 = hits_at_10 / len(relevant_set)

    reciprocal_rank = 0.0
    for rank, image_id in enumerate(retrieved_ids, start=1):
        if image_id in relevant_lookup:
            reciprocal_rank = 1.0 / rank
            break

    return RetrievalQualityResult(
        query=query,
        relevant_images=relevant_set,
        retrieved_images=retrieved_ids,
        recall_at_1=recall_at_1,
        recall_at_5=recall_at_5,
        recall_at_10=recall_at_10,
        mrr=reciprocal_rank,
    )


def format_seconds(value: float) -> str:
    return f"{value:,.4f} s"


def print_console_summary(report: dict[str, Any]) -> None:
    dataset = report["dataset"]
    retrieval = report["retrieval"]
    quality = report.get("quality")

    print("\n" + "=" * 84)
    print("PHOTO MANAGEMENT BENCHMARK")
    print("=" * 84)
    print("DATASET")
    print(f"  Indexed images:                   {dataset['indexed_images']}")
    print(f"  Total indexing time:              {format_seconds(dataset['total_indexing_time_sec'])}")
    print(f"  Average indexing throughput:      {dataset['average_indexing_throughput_images_per_sec']:.2f} images/sec")
    print(f"  Avg. metadata gen time/image:     {format_seconds(dataset['average_metadata_generation_time_per_image_sec'])}")
    print(f"  Total embedding generation time:  {format_seconds(dataset['total_embedding_generation_time_sec'])}")
    print(f"  Total Pinecone upsert time:       {format_seconds(dataset['total_pinecone_upsert_time_sec'])}")
    print(f"  Failed images:                    {dataset['failed_images']}")

    print("\nRETRIEVAL PERFORMANCE")
    overall = retrieval["overall"]
    print(f"  Mean latency:                     {format_seconds(overall['mean_latency_sec'])}")
    print(f"  Median latency:                   {format_seconds(overall['median_latency_sec'])}")
    print(f"  P95 latency:                      {format_seconds(overall['p95_latency_sec'])}")
    print(f"  P99 latency:                      {format_seconds(overall['p99_latency_sec'])}")
    print(f"  Fastest query:                    {overall['fastest_query']} ({format_seconds(overall['fastest_latency_sec'])})")
    print(f"  Slowest query:                    {overall['slowest_query']} ({format_seconds(overall['slowest_latency_sec'])})")

    if quality:
        quality_overall = quality["overall"]
        print("\nRETRIEVAL QUALITY")
        print(f"  Recall@1:                         {quality_overall['recall_at_1']:.4f}")
        print(f"  Recall@5:                         {quality_overall['recall_at_5']:.4f}")
        print(f"  Recall@10:                        {quality_overall['recall_at_10']:.4f}")
        print(f"  MRR:                              {quality_overall['mrr']:.4f}")
    print("=" * 84 + "\n")


def write_csv(path: Path, rows: list[QueryTimingSample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "query",
                "query_index",
                "run_index",
                "phase",
                "latency_sec",
                "cache_hit",
                "top1_id",
                "top1_score",
                "error",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the PhotoManagement benchmarking suite.")
    parser.add_argument("--dataset-dir", required=True, help="Directory containing images to benchmark.")
    parser.add_argument("--queries-file", required=True, help="JSON file with benchmark queries.")
    parser.add_argument("--ground-truth-file", default=None, help="Optional JSON file with retrieval ground truth.")
    parser.add_argument("--number-of-images", type=int, default=None, help="Limit the number of images to benchmark.")
    parser.add_argument("--number-of-queries", type=int, default=None, help="Limit the number of queries to benchmark.")
    parser.add_argument("--warmup-iterations", type=int, default=2, help="Number of warmup runs to ignore.")
    parser.add_argument("--repeated-runs", type=int, default=5, help="Number of measured runs per query.")
    parser.add_argument("--output-json", default="benchmark_results.json", help="Path to the JSON results file.")
    parser.add_argument("--output-csv", default="benchmark_query_timings.csv", help="Path to the per-query timings CSV file.")
    parser.add_argument("--cache-dir", default=".benchmark_cache", help="Directory for persistent caption/embedding caches.")
    parser.add_argument("--top-k", type=int, default=10, help="Number of retrieval results to request per query.")
    parser.add_argument("--ml-base-url", default=None, help="Override the ML service base URL.")
    parser.add_argument("--pinecone-api-key", default=None, help="Override the Pinecone API key.")
    parser.add_argument("--pinecone-image-index-host", default=None, help="Override the Pinecone image index host.")
    parser.add_argument("--sample-seed", type=int, default=None, help="Reserved for future sampling strategies.")
    return parser


def run_benchmark(config: BenchmarkConfig) -> tuple[dict[str, Any], list[QueryTimingSample]]:
    cache = BenchmarkCache(config.cache_dir)
    client = BenchmarkClient(config, cache)
    timing_samples: list[QueryTimingSample] = []

    try:
        dataset_images = read_image_files(config.dataset_dir)
        if config.number_of_images is not None:
            dataset_images = dataset_images[: config.number_of_images]

        indexed_images = 0
        failed_images = 0
        metadata_generation_times: list[float] = []
        embedding_generation_times: list[float] = []
        upsert_times: list[float] = []
        cached_caption_count = 0
        cached_embedding_count = 0

        indexing_started = perf_counter()
        for image_path in dataset_images:
            image_id = make_image_id(config.dataset_dir, image_path)
            try:
                image_bytes = image_path.read_bytes()
            except Exception as exc:
                logger.warning("Failed to read %s: %s", image_path, exc)
                failed_images += 1
                continue

            caption, caption_time, caption_cached, caption_error = client.caption_image(image_bytes, image_id)
            metadata_generation_times.append(caption_time)
            cached_caption_count += int(caption_cached)
            if caption_error or not caption:
                logger.warning("Captioning failed for %s: %s", image_path, caption_error)
                failed_images += 1
                continue

            embedding, embedding_time, embedding_cached, embedding_error = client.embed_text(caption)
            embedding_generation_times.append(embedding_time)
            cached_embedding_count += int(embedding_cached)
            if embedding_error or not embedding:
                logger.warning("Embedding failed for %s: %s", image_path, embedding_error)
                failed_images += 1
                continue

            upsert_time, upsert_error = client.upsert_image(
                image_id=image_id,
                vector=embedding,
                metadata={
                    "source_path": str(image_path.relative_to(config.dataset_dir)),
                    "caption": caption,
                },
            )
            upsert_times.append(upsert_time)
            if upsert_error:
                logger.warning("Pinecone upsert failed for %s: %s", image_path, upsert_error)
                failed_images += 1
                continue

            indexed_images += 1

        total_indexing_time = perf_counter() - indexing_started

        query_list = load_queries(config.queries_file, config.number_of_queries)
        ground_truth = load_ground_truth(config.ground_truth_file) if config.ground_truth_file else {}

        all_query_latencies: list[float] = []
        query_summaries: list[QuerySummary] = []
        quality_results: list[RetrievalQualityResult] = []

        for query_index, query in enumerate(query_list):
            summary = QuerySummary(query=query, index=query_index)
            query_embedding, _, embedding_cached, embedding_error = client.embed_text(query)
            if embedding_error or query_embedding is None:
                summary.failures += 1
                timing_samples.append(
                    QueryTimingSample(
                        query=query,
                        query_index=query_index,
                        run_index=0,
                        phase="query",
                        latency_sec=0.0,
                        cache_hit=embedding_cached,
                        error=embedding_error,
                    )
                )
                query_summaries.append(summary)
                continue

            for run_index in range(config.warmup_iterations + config.repeated_runs):
                phase = "warmup" if run_index < config.warmup_iterations else "measurement"
                retrieved, latency, query_error = client.query_image_index(query_embedding, config.top_k)
                top1_id = retrieved[0]["id"] if retrieved else ""
                top1_score = float(retrieved[0]["score"] if retrieved else 0.0)
                timing_samples.append(
                    QueryTimingSample(
                        query=query,
                        query_index=query_index,
                        run_index=run_index,
                        phase=phase,
                        latency_sec=latency,
                        cache_hit=embedding_cached,
                        top1_id=top1_id,
                        top1_score=top1_score,
                        error=query_error,
                    )
                )

                if query_error:
                    summary.failures += 1
                    continue

                if phase == "measurement":
                    summary.latencies_sec.append(latency)
                    summary.cache_hits += int(embedding_cached)
                    all_query_latencies.append(latency)
                    if not summary.top_results:
                        summary.top_results = retrieved

            query_summaries.append(summary)

            relevant_images = ground_truth.get(query)
            if relevant_images is not None:
                retrieved_ids = [match["id"] for match in (summary.top_results or [])]
                quality_results.append(compute_retrieval_quality(query, retrieved_ids, relevant_images))

        query_summaries_dict = [summary.to_dict() for summary in query_summaries]
        overall_latency = summarize_numbers(all_query_latencies)

        fastest_query = ""
        slowest_query = ""
        if query_summaries_dict:
            measured_queries = [item for item in query_summaries_dict if item["latencies_sec"]]
            if measured_queries:
                fastest_query = min(measured_queries, key=lambda item: min(item["latencies_sec"]))["query"]
                slowest_query = max(measured_queries, key=lambda item: max(item["latencies_sec"]))["query"]

        quality_report: Optional[dict[str, Any]] = None
        if quality_results:
            recall_at_1 = mean(result.recall_at_1 for result in quality_results)
            recall_at_5 = mean(result.recall_at_5 for result in quality_results)
            recall_at_10 = mean(result.recall_at_10 for result in quality_results)
            mrr = mean(result.mrr for result in quality_results)
            quality_report = {
                "overall": {
                    "recall_at_1": recall_at_1,
                    "recall_at_5": recall_at_5,
                    "recall_at_10": recall_at_10,
                    "mrr": mrr,
                    "evaluated_queries": len(quality_results),
                },
                "per_query": [asdict(result) for result in quality_results],
            }

        report = {
            "config": {
                **asdict(config),
                "dataset_dir": str(config.dataset_dir),
                "queries_file": str(config.queries_file),
                "ground_truth_file": str(config.ground_truth_file) if config.ground_truth_file else None,
                "output_json": str(config.output_json),
                "output_csv": str(config.output_csv),
                "cache_dir": str(config.cache_dir),
            },
            "dataset": {
                "indexed_images": indexed_images,
                "failed_images": failed_images,
                "total_indexing_time_sec": total_indexing_time,
                "average_indexing_throughput_images_per_sec": indexed_images / total_indexing_time if total_indexing_time > 0 else 0.0,
                "average_metadata_generation_time_per_image_sec": mean(metadata_generation_times) if metadata_generation_times else 0.0,
                "total_embedding_generation_time_sec": sum(embedding_generation_times),
                "total_pinecone_upsert_time_sec": sum(upsert_times),
                "cached_caption_count": cached_caption_count,
                "cached_embedding_count": cached_embedding_count,
            },
            "retrieval": {
                "queries": query_summaries_dict,
                "overall": {
                    "mean_latency_sec": overall_latency["mean"],
                    "median_latency_sec": overall_latency["median"],
                    "p95_latency_sec": overall_latency["p95"],
                    "p99_latency_sec": overall_latency["p99"],
                    "fastest_latency_sec": overall_latency["fastest"],
                    "slowest_latency_sec": overall_latency["slowest"],
                    "fastest_query": fastest_query,
                    "slowest_query": slowest_query,
                },
            },
        }
        if quality_report is not None:
            report["quality"] = quality_report

        return report, timing_samples
    finally:
        client.close()


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    load_dotenv()
    dataset_dir = Path(args.dataset_dir).expanduser().resolve()
    queries_file = Path(args.queries_file).expanduser().resolve()
    ground_truth_file = Path(args.ground_truth_file).expanduser().resolve() if args.ground_truth_file else None
    output_json = Path(args.output_json).expanduser().resolve()
    output_csv = Path(args.output_csv).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()

    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    if not queries_file.exists():
        raise FileNotFoundError(f"Queries file not found: {queries_file}")
    if ground_truth_file and not ground_truth_file.exists():
        raise FileNotFoundError(f"Ground truth file not found: {ground_truth_file}")

    config = BenchmarkConfig(
        dataset_dir=dataset_dir,
        queries_file=queries_file,
        ground_truth_file=ground_truth_file,
        output_json=output_json,
        output_csv=output_csv,
        cache_dir=cache_dir,
        number_of_images=args.number_of_images,
        number_of_queries=args.number_of_queries,
        warmup_iterations=max(0, args.warmup_iterations),
        repeated_runs=max(1, args.repeated_runs),
        top_k=max(1, args.top_k),
        ml_base_url=args.ml_base_url or os.getenv("ML_BASE_URL", "http://127.0.0.1:8000/ml"),
        pinecone_api_key=args.pinecone_api_key or os.getenv("PINECONE_API_KEY"),
        pinecone_image_index_host=args.pinecone_image_index_host or os.getenv("PINECONE_IMAGE_INDEX_HOST"),
        sample_seed=args.sample_seed,
    )

    report, timing_samples = run_benchmark(config)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    write_csv(output_csv, timing_samples)
    print_console_summary(report)
    logger.info("Wrote benchmark JSON to %s", output_json)
    logger.info("Wrote benchmark CSV to %s", output_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
