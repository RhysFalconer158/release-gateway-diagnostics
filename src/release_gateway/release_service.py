from fastapi import FastAPI

from .release_diagnostics import (
    GatewayDiagnosticWriter,
    ReleaseAssessment,
    ReleaseRequest,
    assess_release,
)

app = FastAPI(title="Release gateway diagnostics")


@app.post("/releases/assess", response_model=ReleaseAssessment)
def assess(request: ReleaseRequest) -> ReleaseAssessment:
    return assess_release(request, GatewayDiagnosticWriter())


def run() -> None:
    import uvicorn

    uvicorn.run("release_gateway.release_service:app", host="127.0.0.1", port=8000)
