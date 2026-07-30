"""Versioned scenario coverage contract for the CHẮN detection stack."""

from __future__ import annotations

from dataclasses import dataclass


SCENARIO_CATALOG_VERSION = "vn-scam-catalog-2026.07"
SCENARIO_CATALOG_REVIEWED_AT = "2026-07-30"

ADVISORY_SOURCES: dict[str, str] = {
    "bca_24_forms": (
        "https://hvannd.bocongan.gov.vn/bv/ct/10060/"
        "24-hinh-thuc-lua-dao-dien-ra-tren-khong-gian-mang-viet-nam"
    ),
    "bca_ecommerce_2025": (
        "https://bocongan.gov.vn/bai-viet/chong-lua-dao-truc-tuyen-2025-"
        "lan-toa-thong-diep-nhan-dien-bay-lua-an-tam-vui-sam-1764245385"
    ),
    "bca_online_kidnapping_2025": (
        "https://bocongan.gov.vn/bai-viet/"
        "canh-bao-bien-tuong-thu-doan-bat-coc-online-1757302259"
    ),
    "bca_traffic_2025": (
        "https://www.bocongan.gov.vn/bai-viet/huong-dan-nop-phat-nguoi-va-"
        "tham-gia-giao-thong-khi-dang-trong-thoi-gian-cho-cap-doi-"
        "giay-phep-lai-xe-d2-t43826"
    ),
    "bca_sim_2026": (
        "https://bocongan.gov.vn/bai-viet/cong-an-tinh-quang-ninh-tuyen-truyen-"
        "phuong-thuc-thu-doan-lua-dao-moi-tren-mang-xa-hoi-tai-dia-diem-"
        "tiep-cong-dan-cua-cong-an-tinh-1778493752"
    ),
    "bca_sextortion_2025": (
        "https://bocongan.gov.vn/bai-viet/canh-giac-voi-thu-doan-cat-ghep-"
        "hinh-anh-video-nhay-cam-nham-lua-dao-chiem-doat-tai-san-cua-"
        "can-bo-cong-chuc-doanh-nhan-d22-t44736"
    ),
    "bca_recovery_2025": (
        "https://bocongan.gov.vn/bai-viet/"
        "canh-giac-voi-thu-doan-ho-tro-lay-lai-tien-bi-lua-dao-1758700973"
    ),
    "bca_investment_2025": (
        "https://www.bocongan.gov.vn/bai-viet/canh-bao-thu-doan-du-do-tham-gia-"
        "dau-tu-tai-chinh-san-chung-khoan-tien-ao-tren-khong-gian-mang-"
        "d22-t44828"
    ),
    "bca_trafficking_2026": (
        "https://www.bocongan.gov.vn/bai-viet/xu-ly-nghiem-cac-duong-day-"
        "toi-pham-loi-dung-cong-nghe-cao-de-lua-dao-mua-ban-nguoi-1782696133"
    ),
    "sbv_biometrics": "https://sbv.gov.vn/w/sbv605424",
}


@dataclass(frozen=True)
class ScenarioDefinition:
    title_vi: str
    source_refs: tuple[str, ...]
    detector_layers: tuple[str, ...] = ("l3_text", "l4_policy")


SCENARIO_CATALOG: dict[str, ScenarioDefinition] = {
    "fake_investigation": ScenarioDefinition(
        "Giả danh công an, viện kiểm sát, tòa án",
        ("bca_24_forms",),
    ),
    "fake_bank_otp": ScenarioDefinition(
        "Giả danh ngân hàng để lấy OTP",
        ("bca_24_forms", "sbv_biometrics"),
    ),
    "fake_public_service_app": ScenarioDefinition(
        "Giả dịch vụ công và phát tán APK",
        ("bca_24_forms", "bca_traffic_2025"),
        ("l3_text", "url_lookup", "l4_policy"),
    ),
    "fake_prize": ScenarioDefinition(
        "Trúng thưởng và phí nhận quà giả",
        ("bca_24_forms",),
    ),
    "fake_job": ScenarioDefinition(
        "Tuyển cộng tác viên, làm nhiệm vụ nhận hoa hồng",
        ("bca_24_forms",),
    ),
    "fake_school": ScenarioDefinition(
        "Giả danh nhà trường, giáo viên",
        ("bca_24_forms",),
    ),
    "fake_utility": ScenarioDefinition(
        "Giả điện lực, nước, viễn thông",
        ("bca_24_forms",),
    ),
    "family_emergency": ScenarioDefinition(
        "Giả người thân gặp tai nạn hoặc cấp cứu",
        ("bca_24_forms",),
    ),
    "fake_vneid_biometric": ScenarioDefinition(
        "Giả cập nhật VNeID hoặc sinh trắc học",
        ("bca_sim_2026", "sbv_biometrics"),
        ("l3_text", "url_lookup", "l4_policy"),
    ),
    "fake_sim_update_call_forwarding": ScenarioDefinition(
        "Giả chuẩn hóa SIM và chiếm OTP bằng chuyển tiếp cuộc gọi",
        ("bca_sim_2026",),
        ("l1_device", "l3_text", "l4_policy"),
    ),
    "fake_traffic_fine": ScenarioDefinition(
        "Giả phạt nguội hoặc đổi giấy phép lái xe",
        ("bca_traffic_2025",),
        ("l3_text", "url_lookup", "account_lookup", "l4_policy"),
    ),
    "online_kidnapping": ScenarioDefinition(
        "Bắt cóc online, cách ly và ép chứng minh vô tội",
        ("bca_online_kidnapping_2025",),
    ),
    "deepfake_relative": ScenarioDefinition(
        "Deepfake người thân hoặc lãnh đạo để chuyển tiền",
        ("bca_ecommerce_2025",),
        ("l3_text", "media_verification", "l4_policy"),
    ),
    "deepfake_sextortion": ScenarioDefinition(
        "Tống tiền bằng ảnh hoặc video nhạy cảm cắt ghép",
        ("bca_sextortion_2025",),
        ("l3_text", "media_verification", "l4_policy"),
    ),
    "ecommerce_refund": ScenarioDefinition(
        "Giả nhân viên sàn và hoàn tiền ảo",
        ("bca_ecommerce_2025",),
    ),
    "fake_shipper": ScenarioDefinition(
        "Giả shipper, phí đơn hàng hoặc đăng ký hội viên",
        ("bca_ecommerce_2025",),
    ),
    "fake_marketplace_deposit": ScenarioDefinition(
        "Mua bán ngoài sàn và yêu cầu đặt cọc",
        ("bca_24_forms", "bca_ecommerce_2025"),
    ),
    "fake_travel_ticket": ScenarioDefinition(
        "Combo du lịch, phòng và vé giá rẻ giả",
        ("bca_24_forms",),
    ),
    "investment_crypto": ScenarioDefinition(
        "Đầu tư chứng khoán, tiền ảo hoặc sàn giả",
        ("bca_24_forms", "bca_investment_2025"),
    ),
    "romance_investment": ScenarioDefinition(
        "Lừa tình cảm kết hợp đầu tư hoặc bưu kiện",
        ("bca_24_forms", "bca_investment_2025"),
    ),
    "fake_loan_finance": ScenarioDefinition(
        "Khoản vay giả, phí giải ngân và app tín dụng",
        ("bca_24_forms",),
        ("l3_text", "url_lookup", "account_lookup", "l4_policy"),
    ),
    "account_recovery": ScenarioDefinition(
        "Dịch vụ lấy lại tài khoản mạng xã hội",
        ("bca_24_forms",),
    ),
    "recovery_refund": ScenarioDefinition(
        "Dịch vụ lấy lại tiền đã bị lừa",
        ("bca_24_forms", "bca_recovery_2025"),
    ),
    "fake_charity_hospital": ScenarioDefinition(
        "Kêu gọi từ thiện hoặc viện phí giả",
        ("bca_24_forms",),
    ),
    "fake_health_insurance": ScenarioDefinition(
        "Giả bảo hiểm xã hội, bảo hiểm y tế",
        ("bca_24_forms",),
        ("l3_text", "url_lookup", "l4_policy"),
    ),
    "fake_customs_parcel": ScenarioDefinition(
        "Bưu kiện, hải quan hoặc quà từ nước ngoài giả",
        ("bca_24_forms",),
    ),
    "social_account_takeover": ScenarioDefinition(
        "Chiếm tài khoản mạng xã hội rồi vay tiền hoặc lấy OTP",
        ("bca_24_forms",),
    ),
    "fake_transfer_receipt": ScenarioDefinition(
        "Biên lai chuyển khoản giả hoặc hoàn tiền chuyển nhầm",
        ("bca_24_forms",),
        ("l3_text", "receipt_verification", "l4_policy"),
    ),
    "malicious_qr_payment": ScenarioDefinition(
        "Mã QR thanh toán hoặc đăng nhập độc hại",
        ("bca_ecommerce_2025",),
        ("l3_text", "qr_url_lookup", "account_lookup", "l4_policy"),
    ),
    "business_invoice_change": ScenarioDefinition(
        "Giả lãnh đạo hoặc nhà cung cấp đổi tài khoản hóa đơn",
        ("bca_ecommerce_2025",),
    ),
    "fake_child_model": ScenarioDefinition(
        "Tuyển người mẫu nhí và thu phí giả",
        ("bca_24_forms",),
    ),
    "gambling_tip": ScenarioDefinition(
        "Bán số đề hoặc kèo chắc thắng",
        ("bca_24_forms",),
    ),
    "overseas_job_trafficking": ScenarioDefinition(
        "Việc làm nước ngoài giả gắn với nguy cơ mua bán người",
        ("bca_trafficking_2026",),
    ),
    "fake_rental_deposit": ScenarioDefinition(
        "Cho thuê nhà giá rẻ và yêu cầu cọc trước",
        ("bca_ecommerce_2025",),
    ),
    "fake_event_ticket": ScenarioDefinition(
        "Vé sự kiện giả và chuyển khoản ngoài nền tảng",
        ("bca_ecommerce_2025",),
    ),
    "tech_support_screen_share": ScenarioDefinition(
        "Giả hỗ trợ kỹ thuật, chia sẻ màn hình và điều khiển thiết bị",
        ("bca_sim_2026", "bca_online_kidnapping_2025"),
        ("l1_device", "l3_text", "url_lookup", "l4_policy"),
    ),
}
