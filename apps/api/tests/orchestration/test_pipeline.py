"""V0 skeleton test: a request flows through every stage with typed objects."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.audit import write_to_disk
from src.core.schemas import (
    AuditEntry,
    CalculationRequest,
    FinalAnswer,
    OptionsPricingRequest,
    OptionType,
    VerificationStatus,
)
from src.orchestration.pipeline import run_pipeline


def test_skeleton_flow_produces_typed_objects_and_audit_log(tmp_path: Path) -> None:
    payload = OptionsPricingRequest(
        spot=100.0, strike=100.0, time_to_expiry_years=1.0,
        volatility=0.20, risk_free_rate=0.05,
        option_type=OptionType.CALL,
    )
    req = CalculationRequest(raw_input="textbook ATM call")
    answer, log = run_pipeline(req, parsed_payload=payload)

    # 1. The result is a real FinalAnswer (typed).
    assert isinstance(answer, FinalAnswer)
    assert answer.request_id == req.request_id

    # 2. Verification reached `verified` for textbook inputs.
    assert answer.verification_status == VerificationStatus.VERIFIED

    # 3. Audit log contains every stage in order.
    expected_stages = ["request", "parse", "calculate", "verify", "explain", "respond"]
    assert [e.stage for e in log.entries] == expected_stages
    for entry in log.entries:
        assert isinstance(entry, AuditEntry)

    # 4. Persisted JSON round-trips and matches the in-memory log.
    path = write_to_disk(log, tmp_path)
    on_disk = json.loads(path.read_text())
    assert on_disk["request_id"] == str(req.request_id)
    assert [e["stage"] for e in on_disk["entries"]] == expected_stages
