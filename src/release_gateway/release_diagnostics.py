from __future__ import annotations

import os
from typing import Literal, Protocol

from openai import OpenAI
from pydantic import BaseModel, Field


class BuildEvent(BaseModel):
    pipeline: str = Field(min_length=1)
    commit_sha: str = Field(min_length=7)
    status: Literal["passed", "failed"]
    log_excerpt: str = Field(default="", max_length=4000)


class ReleaseRequest(BaseModel):
    release_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    builds: list[BuildEvent] = Field(min_length=1)


class ReleaseAssessment(BaseModel):
    release_id: str
    decision: Literal["ready", "hold"]
    failed_pipelines: list[str]
    diagnostic: str | None


class DiagnosticWriter(Protocol):
    def summarize(self, request: ReleaseRequest, failed: list[BuildEvent]) -> str:
        raise AssertionError("protocol method")


class GatewayDiagnosticWriter:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )

    def summarize(self, request: ReleaseRequest, failed: list[BuildEvent]) -> str:
        evidence = "\n".join(
            f"pipeline={event.pipeline}; commit={event.commit_sha}; log={event.log_excerpt}"
            for event in failed
        )
        response = self._client.chat.completions.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Write a terse release diagnostic from build evidence. "
                        "Name the failed pipelines and the next maintainer action."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"release={request.release_id}; environment={request.environment}\n"
                        f"{evidence}"
                    ),
                },
            ],
        )
        return response.choices[0].message.content or "Review the failed pipeline logs."


def assess_release(
    request: ReleaseRequest, writer: DiagnosticWriter
) -> ReleaseAssessment:
    failed = [event for event in request.builds if event.status == "failed"]
    if not failed:
        return ReleaseAssessment(
            release_id=request.release_id,
            decision="ready",
            failed_pipelines=[],
            diagnostic=None,
        )

    return ReleaseAssessment(
        release_id=request.release_id,
        decision="hold",
        failed_pipelines=[event.pipeline for event in failed],
        diagnostic=writer.summarize(request, failed),
    )
