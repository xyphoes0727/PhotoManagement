from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from datasets import load_dataset


DATASET_PATH = Path("photo_management/PhotoManagement/data")
FINAL_PATH = Path("photo_management/PhotoManagement/data_processed")
IMAGE_OUTPUT_DIR = FINAL_PATH / "images"
MANIFEST_PATH = FINAL_PATH / "manifest.json"


def normalize_captions(captions: list[str]) -> list[str]:
    return [str(caption).strip() for caption in captions if str(caption).strip()]


def main() -> None:
    dataset = load_dataset(str(DATASET_PATH))
    split = dataset["train"]

    IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, object]] = []

    for row in split:
        row = dict(row)
        image = row["image"]
        captions = normalize_captions(row["caption"])
        img_id = str(row["img_id"])
        filename = str(row["filename"])

        image_path = IMAGE_OUTPUT_DIR / filename
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        image_path.write_bytes(buffer.getvalue())

        manifest.append(
            {
                "image": str(image_path),
                "caption": captions,
                "img_id": img_id,
                "filename": filename,
            }
        )

    FINAL_PATH.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {len(manifest)} records to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
