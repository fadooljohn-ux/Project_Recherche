from pulsar_pilot.acquire import ARCHIVE_PREFIX, is_selected_member


def test_selects_only_target_and_support_files() -> None:
    assert is_selected_member(f"{ARCHIVE_PREFIX}README")
    assert is_selected_member(f"{ARCHIVE_PREFIX}clock/gbt2gps.clk")
    assert is_selected_member(
        f"{ARCHIVE_PREFIX}wideband/par/J1744-1134_PINT_20230131.wb.par"
    )
    assert is_selected_member(
        f"{ARCHIVE_PREFIX}wideband/tim/J1744-1134_PINT_20230131.wb.tim"
    )


def test_rejects_other_targets_and_bulk_products() -> None:
    assert not is_selected_member(
        f"{ARCHIVE_PREFIX}wideband/par/J1909-3744_PINT_20230131.wb.par"
    )
    assert not is_selected_member(
        f"{ARCHIVE_PREFIX}wideband/noise/J1744-1134.wb.chain_1.txt"
    )
    assert not is_selected_member(
        f"{ARCHIVE_PREFIX}correlations/wideband/J1744-1134_PINT_20230131.wb.correlation.hdf5"
    )
