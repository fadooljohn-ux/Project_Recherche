from pulsar_pilot.pilot2_failure_analysis import analyze_statistics


def test_failure_analysis_is_deterministic_and_reproduces_nearest_rank() -> None:
    calibration = [float(index) for index in range(1000)]
    sealed = [float(index) for index in range(500)]
    result = analyze_statistics(calibration, sealed, 989.0)
    assert result["locked_threshold_reproduced"] is True
    assert result["calibration_nearest_rank"] == 990
    assert result["calibration_strict_exceedances"] == 10
    assert result["sealed_strict_exceedances"] == 0


def test_analysis_source_contains_no_random_generation_or_science_runtime() -> None:
    import inspect

    import pulsar_pilot.pilot2_failure_analysis as module

    source = inspect.getsource(module)
    assert "np.random" not in source
    assert "fit_toas" not in source
    assert ".scan(" not in source
