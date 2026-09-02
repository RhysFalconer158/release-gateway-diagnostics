from release_gateway.release_diagnostics import (
    BuildEvent,
    ReleaseRequest,
    assess_release,
)


class RecordedWriter:
    def __init__(self) -> None:
        self.failed_pipelines: list[str] = []

    def summarize(self, request: ReleaseRequest, failed: list[BuildEvent]) -> str:
        self.failed_pipelines = [event.pipeline for event in failed]
        return "Re-run warehouse-load after checking the rejected rows."


def test_failed_pipeline_holds_release_and_gets_diagnostic() -> None:
    writer = RecordedWriter()
    request = ReleaseRequest(
        release_id="etl-2026-08-31.1",
        environment="production",
        builds=[
            BuildEvent(
                pipeline="schema-check",
                commit_sha="a1b2c3d4",
                status="passed",
            ),
            BuildEvent(
                pipeline="warehouse-load",
                commit_sha="a1b2c3d4",
                status="failed",
                log_excerpt="12 rows rejected by the target schema",
            ),
        ],
    )

    result = assess_release(request, writer)

    assert result.decision == "hold"
    assert result.failed_pipelines == ["warehouse-load"]
    assert writer.failed_pipelines == ["warehouse-load"]
    assert result.diagnostic == "Re-run warehouse-load after checking the rejected rows."


def test_all_passed_pipelines_are_ready_without_diagnostic_call() -> None:
    writer = RecordedWriter()
    request = ReleaseRequest(
        release_id="etl-2026-08-31.2",
        environment="production",
        builds=[
            BuildEvent(
                pipeline="warehouse-load",
                commit_sha="d4c3b2a1",
                status="passed",
            )
        ],
    )

    result = assess_release(request, writer)

    assert result.decision == "ready"
    assert result.diagnostic is None
    assert writer.failed_pipelines == []
