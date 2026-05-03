from __future__ import annotations

from microct_analysis.domain.confidence import AcceptanceCheckResult, ConfidenceLevel, assess_confidence


def check(name: str, passed: bool, violated: ConfidenceLevel) -> AcceptanceCheckResult:
    return AcceptanceCheckResult(
        check_name=name,
        rule="rule",
        passed=passed,
        confidence_if_violated=violated,
        detail=f"{name} detail",
    )


def test_all_checks_pass_high() -> None:
    result = assess_confidence([check("roi", True, ConfidenceLevel.LOW)])
    assert result.level is ConfidenceLevel.HIGH


def test_one_medium_violation_medium() -> None:
    result = assess_confidence([check("threshold", False, ConfidenceLevel.MEDIUM)])
    assert result.level is ConfidenceLevel.MEDIUM


def test_one_low_violation_low() -> None:
    result = assess_confidence([check("identity", False, ConfidenceLevel.LOW)])
    assert result.level is ConfidenceLevel.LOW


def test_multiple_violations_lowest_confidence_wins() -> None:
    result = assess_confidence(
        [
            check("threshold", False, ConfidenceLevel.MEDIUM),
            check("identity", False, ConfidenceLevel.LOW),
        ]
    )
    assert result.level is ConfidenceLevel.LOW


def test_visual_observations_without_check_violations_stay_high() -> None:
    result = assess_confidence([], visual_observations=["scene matches reference"])
    assert result.level is ConfidenceLevel.HIGH
    assert result.observations == ["scene matches reference"]
