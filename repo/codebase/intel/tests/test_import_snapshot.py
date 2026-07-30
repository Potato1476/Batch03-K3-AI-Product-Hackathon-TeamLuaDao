from __future__ import annotations

from chan_intel.import_snapshot import parse_phishvn_csv
from chan_intel.normalization import hash_url


def test_phishvn_import_keeps_only_positive_rows_and_hashes_urls(tmp_path):
    path = tmp_path / "phishvn.csv"
    path.write_text(
        "record_id,url,label,first_seen\n"
        "a,https://bad.example/login,phishing,2026-07-01\n"
        "b,https://good.example/,legitimate,2026-07-01\n",
        encoding="utf-8",
    )
    result = parse_phishvn_csv(
        path,
        url_column="url",
        label_column="label",
        id_column="record_id",
        first_seen_column="first_seen",
    )
    expected, _ = hash_url("https://bad.example/login")
    assert result.source == "phishvn"
    assert len(result.indicators) == 1
    assert result.indicators[0].digest == expected
