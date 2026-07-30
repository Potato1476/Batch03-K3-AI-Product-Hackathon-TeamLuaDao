from chan_ml.augmentation import augment_text, augmented_variants


def test_augmentation_is_deterministic_and_changes_text():
    text = "Công an yêu cầu cập nhật hồ sơ ngay hôm nay."
    first = augment_text(text, seed=42, variant=0)
    assert first == augment_text(text, seed=42, variant=0)
    assert first != text


def test_augmentation_preserves_placeholders_urls_and_numbers():
    text = (
        "Chuyển <AMOUNT:trieu> vào <ACCOUNT>, mở "
        "https://example.invalid/a và nhập 839201."
    )
    variants = augmented_variants(text, count=8, seed=42)
    assert variants
    for variant in variants:
        assert "<AMOUNT:trieu>" in variant
        assert "<ACCOUNT>" in variant
        assert "https://example.invalid/a" in variant
        assert "839201" in variant
