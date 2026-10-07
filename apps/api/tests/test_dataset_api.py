"""Stage 2 API tests: real scan, queries, filters, thumbnails, error envelope."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.services import dataset_service


def sha_map(raw_dir: Path) -> dict[str, str]:
    return {
        p.relative_to(raw_dir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(raw_dir.rglob("*"))
        if p.is_file()
    }


def test_summary_before_scan_returns_not_scanned(client, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(dataset_service, "_manifest_json_path", lambda: tmp_path / "missing.json")
    response = client.get("/api/dataset/summary")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "DATASET_NOT_SCANNED"


def test_images_before_scan_returns_not_scanned(client, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(dataset_service, "_manifest_json_path", lambda: tmp_path / "missing.json")
    response = client.get("/api/dataset/images")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DATASET_NOT_SCANNED"


def test_quality_before_scan_returns_not_scanned(client, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(dataset_service, "_quality_json_path", lambda: tmp_path / "missing.json")
    response = client.get("/api/dataset/quality")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DATASET_NOT_SCANNED"


def test_scan_then_full_query_flow(client, raw_dir: Path, stage0_baseline: dict) -> None:
    before = sha_map(raw_dir)

    scan = client.post("/api/dataset/scan")
    assert scan.status_code == 200, scan.text
    body = scan.json()
    assert body["success"] is True
    assert body["image_count"] == stage0_baseline["total_images"]
    assert body["summary"]["class_counts"] == stage0_baseline["class_counts"]
    assert body["outputs"]["manifest_json"].endswith("dataset_manifest.json")

    assert sha_map(raw_dir) == before, "scan must never modify the raw dataset"

    summary = client.get("/api/dataset/summary").json()
    assert summary["summary"]["total_images"] == stage0_baseline["total_images"]
    assert summary["summary"]["class_counts"] == stage0_baseline["class_counts"]
    assert summary["summary"]["unreadable"] == stage0_baseline["unreadable_files"]

    page = client.get("/api/dataset/images", params={"page": 1, "page_size": 10}).json()
    assert page["total"] == stage0_baseline["total_images"]
    assert len(page["items"]) == 10
    assert page["page"] == 1

    bell = client.get("/api/dataset/images", params={"class_name": "bell", "page_size": 200}).json()
    assert bell["total"] == stage0_baseline["class_counts"]["bell"]

    quality = client.get("/api/dataset/quality").json()
    qsummary = quality["summary"]
    assert qsummary["total"] == stage0_baseline["total_images"]
    assert (
        qsummary["pass_count"] + qsummary["review_count"] + qsummary["fail_count"]
        == qsummary["total"]
    )
    assert quality["thresholds"]["blur_review_threshold"] > 0
    assert len(quality["flagged_records"]) == qsummary["flagged_count"]

    failed = client.get(
        "/api/dataset/images",
        params={"quality_status": "FAIL", "page_size": 200},
    ).json()
    assert failed["total"] == qsummary["fail_count"]
    assert all(item["quality_status"] == "FAIL" for item in failed["items"])

    flagged = client.get("/api/dataset/images", params={"page_size": 200}).json()
    assert sum(1 for i in flagged["items"] if i["quality_status"]) == qsummary["total"]


def test_image_detail_hides_absolute_paths(client) -> None:
    page = client.get("/api/dataset/images", params={"page_size": 1}).json()
    image_id = page["items"][0]["image_id"]

    detail = client.get(f"/api/dataset/images/{image_id}").json()
    assert detail["record"]["image_id"] == image_id
    assert "source_path" not in detail["record"], "absolute raw paths must not be exposed"
    assert detail["quality"] is not None
    assert detail["quality"]["image_id"] == image_id


def test_thumbnail_is_real_jpeg(client) -> None:
    page = client.get("/api/dataset/images", params={"page_size": 1}).json()
    image_id = page["items"][0]["image_id"]

    response = client.get(f"/api/dataset/images/{image_id}/thumbnail", params={"size": 64})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content[:2] == b"\xff\xd8", "expected JPEG SOI marker"

    import io

    from PIL import Image

    with Image.open(io.BytesIO(response.content)) as img:
        assert max(img.size) <= 64


def test_unknown_image_returns_404(client) -> None:
    response = client.get("/api/dataset/images/img_" + "f" * 64)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "IMAGE_NOT_FOUND"

    malformed = client.get("/api/dataset/images/not-an-id")
    assert malformed.status_code == 404
    assert malformed.json()["error"]["code"] == "IMAGE_NOT_FOUND"


def test_invalid_quality_status_returns_400(client) -> None:
    response = client.get("/api/dataset/images", params={"quality_status": "EXCELLENT"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PARAMETER"


def test_pagination_boundaries(client, stage0_baseline: dict) -> None:
    total = stage0_baseline["total_images"]
    last_page = client.get(
        "/api/dataset/images",
        params={"page": (total // 10) + 1, "page_size": 10},
    ).json()
    assert 0 < len(last_page["items"]) <= 10
    assert last_page["total"] == total

    beyond = client.get("/api/dataset/images", params={"page": 99, "page_size": 10}).json()
    assert beyond["items"] == []


def test_cors_allows_configured_frontend_origin(client, settings) -> None:
    origin = settings.api.cors_origins[0]
    response = client.get("/api/dataset/summary", headers={"Origin": origin})
    assert response.headers.get("access-control-allow-origin") == origin

    forbidden = client.get("/api/dataset/summary", headers={"Origin": "https://evil.example"})
    assert forbidden.headers.get("access-control-allow-origin") is None
