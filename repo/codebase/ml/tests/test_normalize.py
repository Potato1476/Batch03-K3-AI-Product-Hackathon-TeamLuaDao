from chan_ml.normalize import normalize_for_model


def test_model_normalization_joins_single_character_obfuscation():
    assert normalize_for_model("c.a.n b.o t.h.u.e") == "can bo thue"


def test_model_normalization_does_not_destroy_shortened_domains():
    assert normalize_for_model("bit.ly/abc") == "bit.ly/abc"
