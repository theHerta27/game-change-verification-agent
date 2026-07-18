from gameconfig_agent.agents.test_scenario import TestScenarioAgent
from gameconfig_agent.cli import run_phase0_demo, run_phase1_demo
from gameconfig_agent.data.evaluation_dataset import EVALUATION_DATASET
from gameconfig_agent.tools.evaluator import EvaluationTool


REQUIREMENT = "设计一个新手武器 Training Sword，基础攻击力 50，可升级 3 次，每级攻击力 +5。升级消耗金币和强化石。该武器作为新手任务奖励发放，只能领取一次。"


def test_test_scenario_agent_generates_expected_coverage(tmp_path):
    input_path = tmp_path / "requirement.txt"
    input_path.write_text(REQUIREMENT, encoding="utf-8")
    phase0 = run_phase0_demo(input_path, tmp_path / "phase0")

    scenarios = TestScenarioAgent().generate(phase0["repaired_configs"])
    evaluation = EvaluationTool().evaluate(scenarios, EVALUATION_DATASET)

    assert len(scenarios) == 7
    assert evaluation["coverage"] == 1.0
    assert evaluation["missing_tags"] == []
    assert all(scenario["source_agent"] == "Test Scenario Agent" for scenario in scenarios)


def test_phase1_cli_function_generates_outputs(tmp_path):
    input_path = tmp_path / "requirement.txt"
    input_path.write_text(REQUIREMENT, encoding="utf-8")

    result = run_phase1_demo(input_path, tmp_path / "phase0", tmp_path / "phase1")

    assert result["evaluation"]["coverage_percent"] == 100.0
    assert len(result["test_scenarios"]) == 7
    expected_files = {
        "test_scenarios.json",
        "test_scenario_report.md",
        "evaluation_report.md",
    }
    assert expected_files == {path.name for path in (tmp_path / "phase1").iterdir()}
