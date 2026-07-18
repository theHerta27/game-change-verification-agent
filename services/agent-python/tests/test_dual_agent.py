from pathlib import Path

from agent_service.agents.dual_agent import run_dual_agent
from agent_service.agents.single_agent import run_single_agent
from agent_service.schemas import ReviewRequest
from agent_service.summary import SAMPLES


PROJECT = Path(__file__).resolve().parents[1]


def _request(sample, mode):
    return ReviewRequest(
        diff=(PROJECT / sample.path).read_text(encoding="utf-8"),
        language=sample.language,
        mode="mock",
    )


def test_dual_agent_runs_same_examples_as_single_agent():
    for sample in SAMPLES:
        single = run_single_agent(_request(sample, "single_agent"))
        dual = run_dual_agent(_request(sample, "dual_agent"))

        assert not single.validation_errors
        assert not dual.validation_errors
        assert len(single.findings) == len(dual.findings)
        assert len(single.test_suggestions) == len(dual.test_suggestions)
        assert all(0 <= suggestion.finding_index < len(dual.findings) for suggestion in dual.test_suggestions)


def test_dual_agent_uses_separate_agent_runs():
    sample = SAMPLES[0]
    dual = run_dual_agent(_request(sample, "dual_agent"))
    agent_names = [run.agent_name for run in dual.agent_runs]

    assert agent_names == ["review_agent", "test_agent"]
