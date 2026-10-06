"""Status endpoint tests — verifies no fabricated metrics are returned."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.core.config import get_settings, project_root


def test_status_returns_200(client: TestClient) -> None:
    response = client.get("/api/status")
    assert response.status_code == 200


def test_status_matches_baseline_file(client: TestClient) -> None:
    """Baseline values must equal the audited file — not invented numbers."""
    baseline_path = project_root() / get_settings().paths.baseline_file
    expected = json.loads(baseline_path.read_text(encoding="utf-8"))
    body = client.get("/api/status").json()

    baseline = body["stage0_baseline"]
    assert baseline is not None
    assert baseline["total_images"] == expected["total_images"]
    assert baseline["class_counts"] == expected["class_counts"]
    assert baseline["source"] == expected["source"]


def test_pipeline_values_are_null_until_produced(client: TestClient) -> None:
    pipeline = client.get("/api/status").json()["pipeline"]
    assert pipeline["dataset_version"] is None
    assert pipeline["annotated_images"] is None
    assert pipeline["train_images"] is None
    assert pipeline["validation_images"] is None
    assert pipeline["test_images"] is None
    assert pipeline["model_version"] is None


def test_evaluation_is_not_faked(client: TestClient) -> None:
    evaluation = client.get("/api/status").json()["pipeline"]["evaluation"]
    assert evaluation["status"] == "not_evaluated_yet"
    for metric in ("precision", "recall", "f1", "map"):
        assert evaluation[metric] is None, metric


def test_public_config_returns_real_settings(client: TestClient) -> None:
    body = client.get("/api/config").json()
    assert body["num_classes"] == 2
    assert [c["name"] for c in body["classes"]] == ["bell", "oillamp"]
    assert body["split"]["seed"] == get_settings().split.seed
    # Targets are goals, clearly separated from results.
    assert body["evaluation"]["target_map"] is not None
