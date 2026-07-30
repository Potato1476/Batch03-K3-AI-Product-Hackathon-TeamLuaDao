"""Deterministic, scalable Vietnamese synthetic-data generator.

The generator creates L2-redacted messages only. It deliberately includes
hard negatives containing words such as "OTP", deadlines, banks, and schools
without labeling those messages as malicious behavior.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TextIO

from .constants import GENERATOR_VERSION
from .emerging_scenarios import (
    EMERGING_LEGITIMATE_SPECS,
    EMERGING_SCAM_SPECS,
    ScenarioTemplateSpec,
)
from .policy import aggregate_risk
from .schema import DatasetRecord


@dataclass(frozen=True)
class Template:
    id: str
    split: str
    scenario: str
    text: str
    signals: tuple[str, ...]
    is_phishing: bool


def _expand_specs(
    specs: tuple[ScenarioTemplateSpec, ...],
) -> tuple[Template, ...]:
    templates: list[Template] = []
    for spec in specs:
        split_texts = (
            ("train", (spec.train, *spec.train_extra)),
            ("validation", (spec.validation,)),
            ("test", (spec.test,)),
        )
        for split, texts in split_texts:
            for variant, text in enumerate(texts, start=1):
                templates.append(
                    Template(
                        id=f"{spec.key}_{split}_{variant:02d}",
                        split=split,
                        scenario=spec.scenario,
                        text=text,
                        signals=spec.signals,
                        is_phishing=spec.is_phishing,
                    )
                )
    return tuple(templates)


SCAM_TEMPLATES: tuple[Template, ...] = (
    Template(
        "inv_train_01",
        "train",
        "fake_investigation",
        "{greeting}, tôi là cán bộ {authority}. Hồ sơ của {honorific} liên quan vụ án. Không được nói với gia đình, phải chuyển <AMOUNT:trieu> vào <ACCOUNT> trước {deadline}.",
        ("mao_danh_tham_quyen", "yeu_cau_bi_mat", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "inv_train_02",
        "train",
        "fake_investigation",
        "{authority} thông báo tài khoản của {honorific} đang bị điều tra. Giữ kín nội dung này và nộp tiền xác minh vào <ACCOUNT> trong {duration}.",
        ("mao_danh_tham_quyen", "yeu_cau_bi_mat", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "inv_train_03",
        "train",
        "fake_investigation",
        "Tôi gọi từ {authority} về một hồ sơ khẩn. Tuyệt đối không kể cho người thân; gửi <AMOUNT:trieu> đến <ACCOUNT> ngay hôm nay.",
        ("mao_danh_tham_quyen", "yeu_cau_bi_mat", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "inv_val_01",
        "validation",
        "fake_investigation",
        "Tôi gọi từ {authority}. Đây là chuyên án bí mật, tuyệt đối không kể cho ai. Chuyển <AMOUNT:trieu> vào <ACCOUNT> ngay hôm nay để chứng minh vô tội.",
        ("mao_danh_tham_quyen", "yeu_cau_bi_mat", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "inv_test_01",
        "test",
        "fake_investigation",
        "Cán bộ {authority} yêu cầu hợp tác kín. Nếu tiết lộ với người thân hồ sơ sẽ bị xử lý. Trong {duration} hãy nộp tiền vào tài khoản cá nhân <ACCOUNT>.",
        ("mao_danh_tham_quyen", "yeu_cau_bi_mat", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "otp_train_01",
        "train",
        "fake_bank_otp",
        "{bank} cần xác minh giao dịch. Đọc mã <OTP> vừa gửi cho nhân viên ngay để tránh khóa tài khoản.",
        ("mao_danh_tham_quyen", "ap_luc_thoi_gian", "yeu_cau_otp"),
        True,
    ),
    Template(
        "otp_train_02",
        "train",
        "fake_bank_otp",
        "Nhân viên {bank}: vui lòng gửi lại mã xác nhận <OTP> trong {duration}, nếu chậm thẻ sẽ bị vô hiệu hóa.",
        ("mao_danh_tham_quyen", "ap_luc_thoi_gian", "yeu_cau_otp"),
        True,
    ),
    Template(
        "otp_train_03",
        "train",
        "fake_bank_otp",
        "Bộ phận {bank} yêu cầu cung cấp mã <OTP> cho nhân viên để hủy giao dịch lạ.",
        ("mao_danh_tham_quyen", "yeu_cau_otp"),
        True,
    ),
    Template(
        "otp_train_04",
        "train",
        "fake_bank_otp",
        "Cho tổng đài viên {bank} biết dãy <OTP> trên màn hình trong {duration} để mở lại tài khoản.",
        ("mao_danh_tham_quyen", "ap_luc_thoi_gian", "yeu_cau_otp"),
        True,
    ),
    Template(
        "otp_val_01",
        "validation",
        "fake_bank_otp",
        "Bộ phận chống gian lận {bank} yêu cầu {honorific} cung cấp mã <OTP> để hủy lệnh chuyển tiền đang chờ.",
        ("mao_danh_tham_quyen", "yeu_cau_otp"),
        True,
    ),
    Template(
        "otp_test_01",
        "test",
        "fake_bank_otp",
        "Muốn nhận lại tiền, hãy đọc dãy <OTP> trên điện thoại cho tổng đài viên {bank}.",
        ("mao_danh_tham_quyen", "yeu_cau_otp"),
        True,
    ),
    Template(
        "apk_train_01",
        "train",
        "fake_public_service_app",
        "{authority} yêu cầu cài ứng dụng từ {fake_url}, bật quyền trợ năng và hoàn tất trước {deadline}. Liên hệ riêng qua {channel}.",
        ("mao_danh_tham_quyen", "ap_luc_thoi_gian", "cai_app_ngoai", "chuyen_kenh"),
        True,
    ),
    Template(
        "apk_train_02",
        "train",
        "fake_public_service_app",
        "Cập nhật định danh theo yêu cầu {authority}: tải file APK tại {fake_url}. Không có trên cửa hàng. Làm ngay trong {duration}.",
        ("mao_danh_tham_quyen", "ap_luc_thoi_gian", "cai_app_ngoai"),
        True,
    ),
    Template(
        "apk_val_01",
        "validation",
        "fake_public_service_app",
        "Thông báo từ {authority}: mở link {fake_url} cài phần mềm điều khiển hỗ trợ, sau đó nhắn {channel} cho cán bộ.",
        ("mao_danh_tham_quyen", "cai_app_ngoai", "chuyen_kenh"),
        True,
    ),
    Template(
        "apk_test_01",
        "test",
        "fake_public_service_app",
        "Hồ sơ sắp hết hạn. {authority} gửi ứng dụng ngoài kho tại {fake_url}; hãy cho phép truy cập màn hình trước {deadline}.",
        ("mao_danh_tham_quyen", "ap_luc_thoi_gian", "cai_app_ngoai"),
        True,
    ),
    Template(
        "prize_train_01",
        "train",
        "fake_prize",
        "Chúc mừng {honorific} trúng {prize}. Chuyển phí nhận quà <AMOUNT:trieu> vào <ACCOUNT> trước {deadline}, rồi nhắn {channel}.",
        ("loi_ich_bat_thuong", "ap_luc_thoi_gian", "tk_ca_nhan", "chuyen_kenh"),
        True,
    ),
    Template(
        "prize_train_02",
        "train",
        "fake_prize",
        "Số điện thoại của {honorific} nhận giải {prize}. Suất chỉ giữ {duration}; đóng phí cá nhân qua <ACCOUNT> để nhận.",
        ("loi_ich_bat_thuong", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "prize_val_01",
        "validation",
        "fake_prize",
        "Bạn được chọn nhận {prize} dù chưa đăng ký. Kết bạn {channel} và chuyển phí hồ sơ vào <ACCOUNT> hôm nay.",
        ("loi_ich_bat_thuong", "ap_luc_thoi_gian", "tk_ca_nhan", "chuyen_kenh"),
        True,
    ),
    Template(
        "prize_test_01",
        "test",
        "fake_prize",
        "Quà tri ân đặc biệt trị giá <AMOUNT:trieu> đang chờ. Xác nhận gấp bằng khoản phí vào <ACCOUNT> và trao đổi qua {channel}.",
        ("loi_ich_bat_thuong", "ap_luc_thoi_gian", "tk_ca_nhan", "chuyen_kenh"),
        True,
    ),
    Template(
        "job_train_01",
        "train",
        "fake_job",
        "Việc online lương <AMOUNT:trieu> mỗi tuần, không cần kinh nghiệm. Giữ kín nhóm nhiệm vụ và chuyển sang {channel} để nhận đơn.",
        ("loi_ich_bat_thuong", "yeu_cau_bi_mat", "chuyen_kenh"),
        True,
    ),
    Template(
        "job_train_02",
        "train",
        "fake_job",
        "Tuyển cộng tác viên tại nhà, thu nhập cao bất thường. Đóng cọc vào <ACCOUNT> trong {duration} và chỉ trao đổi ở {channel}.",
        ("loi_ich_bat_thuong", "ap_luc_thoi_gian", "tk_ca_nhan", "chuyen_kenh"),
        True,
    ),
    Template(
        "job_train_03",
        "train",
        "fake_job",
        "Không phỏng vấn vẫn có lương <AMOUNT:trieu>. Đừng cho người khác biết nhiệm vụ, vào nhóm riêng {channel} để ứng tiền.",
        ("loi_ich_bat_thuong", "yeu_cau_bi_mat", "chuyen_kenh"),
        True,
    ),
    Template(
        "job_train_04",
        "train",
        "fake_job",
        "Công việc bấm đơn nhận hoa hồng lớn. Chuyển phí kích hoạt vào <ACCOUNT> trước {deadline} và chỉ nhắn qua {channel}.",
        ("loi_ich_bat_thuong", "ap_luc_thoi_gian", "tk_ca_nhan", "chuyen_kenh"),
        True,
    ),
    Template(
        "job_val_01",
        "validation",
        "fake_job",
        "Không phỏng vấn vẫn nhận lương <AMOUNT:trieu>. Đừng cho người khác biết nhiệm vụ; nhắn riêng {channel} để ứng tiền.",
        ("loi_ich_bat_thuong", "yeu_cau_bi_mat", "chuyen_kenh"),
        True,
    ),
    Template(
        "job_test_01",
        "test",
        "fake_job",
        "Công việc bấm đơn nhận hoa hồng lớn. Chuyển tiền kích hoạt <ACCOUNT> ngay và vào nhóm kín {channel}.",
        (
            "loi_ich_bat_thuong",
            "yeu_cau_bi_mat",
            "ap_luc_thoi_gian",
            "tk_ca_nhan",
            "chuyen_kenh",
        ),
        True,
    ),
    Template(
        "school_train_01",
        "train",
        "fake_school",
        "Phòng tài vụ {school} yêu cầu phụ huynh giữ kín đợt thu này và chuyển học phí vào tài khoản cá nhân <ACCOUNT> trước {deadline}.",
        ("mao_danh_tham_quyen", "yeu_cau_bi_mat", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "school_val_01",
        "validation",
        "fake_school",
        "Giáo vụ {school}: con anh/chị chưa đóng khoản bắt buộc. Chuyển <AMOUNT:trieu> vào <ACCOUNT> trong {duration}, không gọi lại nhà trường.",
        ("mao_danh_tham_quyen", "yeu_cau_bi_mat", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "school_test_01",
        "test",
        "fake_school",
        "{school} thông báo đóng gấp tiền ngoại khóa qua tài khoản cá nhân <ACCOUNT>. Xin không trao đổi trong nhóm phụ huynh.",
        ("mao_danh_tham_quyen", "yeu_cau_bi_mat", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "utility_train_01",
        "train",
        "fake_utility",
        "{utility} báo sẽ cắt dịch vụ sau {duration}. Chuyển <AMOUNT:trieu> vào tài khoản nhân viên <ACCOUNT> để mở lại.",
        ("mao_danh_tham_quyen", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "utility_val_01",
        "validation",
        "fake_utility",
        "Nhân viên {utility}: hóa đơn quá hạn, thanh toán gấp vào <ACCOUNT> trước {deadline} nếu không sẽ ngừng cấp.",
        ("mao_danh_tham_quyen", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "utility_test_01",
        "test",
        "fake_utility",
        "Thông báo khẩn từ {utility}. Dịch vụ bị khóa hôm nay; nộp tiền qua tài khoản cá nhân <ACCOUNT>.",
        ("mao_danh_tham_quyen", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "relative_train_01",
        "train",
        "family_emergency",
        "Con đang gặp việc gấp. Bố mẹ đừng gọi cho ai, chuyển <AMOUNT:trieu> vào <ACCOUNT> trong {duration}, con sẽ giải thích sau.",
        ("yeu_cau_bi_mat", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "relative_val_01",
        "validation",
        "family_emergency",
        "Cháu đổi số mới và đang cấp cứu. Cô giữ kín giúp cháu, gửi tiền ngay vào <ACCOUNT>.",
        ("yeu_cau_bi_mat", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    Template(
        "relative_test_01",
        "test",
        "family_emergency",
        "Máy con hỏng nên mượn số này. Đừng hỏi người nhà, trong {duration} chuyển tiền viện phí vào <ACCOUNT>.",
        ("yeu_cau_bi_mat", "ap_luc_thoi_gian", "tk_ca_nhan"),
        True,
    ),
    # Training-only contrastive probes reduce shortcut learning between signals.
    Template(
        "probe_authority_01",
        "train",
        "contrast_authority",
        "Tôi tự nhận là cán bộ {authority} đang liên hệ với {honorific}.",
        ("mao_danh_tham_quyen",),
        True,
    ),
    Template(
        "probe_authority_02",
        "train",
        "contrast_authority",
        "Đây là nhân viên của {bank}, tôi liên hệ về hồ sơ của quý khách.",
        ("mao_danh_tham_quyen",),
        True,
    ),
    Template(
        "probe_secret_01",
        "train",
        "contrast_secrecy",
        "Việc này phải giữ bí mật, không được kể với gia đình.",
        ("yeu_cau_bi_mat",),
        True,
    ),
    Template(
        "probe_secret_02",
        "train",
        "contrast_secrecy",
        "Đừng cho bất kỳ người thân nào biết nội dung chúng ta đang nói.",
        ("yeu_cau_bi_mat",),
        True,
    ),
    Template(
        "probe_secret_03",
        "train",
        "contrast_secrecy",
        "Không trao đổi việc này trong nhóm và không hỏi lại người quen.",
        ("yeu_cau_bi_mat",),
        True,
    ),
    Template(
        "probe_time_01",
        "train",
        "contrast_time_pressure",
        "Phải hoàn tất ngay trong {duration}, nếu chậm sẽ mất quyền xử lý.",
        ("ap_luc_thoi_gian",),
        True,
    ),
    Template(
        "probe_time_02",
        "train",
        "contrast_time_pressure",
        "Làm gấp trước {deadline}, không được trì hoãn.",
        ("ap_luc_thoi_gian",),
        True,
    ),
    Template(
        "probe_time_03",
        "train",
        "contrast_time_pressure",
        "Khoản này phải đóng gấp trong hôm nay.",
        ("ap_luc_thoi_gian",),
        True,
    ),
    Template(
        "probe_account_01",
        "train",
        "contrast_personal_account",
        "Hãy chuyển khoản vào tài khoản cá nhân <ACCOUNT>.",
        ("tk_ca_nhan",),
        True,
    ),
    Template(
        "probe_account_02",
        "train",
        "contrast_personal_account",
        "Khoản tiền này nộp cho tài khoản đứng tên cá nhân <ACCOUNT>.",
        ("tk_ca_nhan",),
        True,
    ),
    Template(
        "probe_app_01",
        "train",
        "contrast_outside_app",
        "Tải file APK ngoài cửa hàng tại {fake_url} và bật quyền trợ năng.",
        ("cai_app_ngoai",),
        True,
    ),
    Template(
        "probe_app_02",
        "train",
        "contrast_outside_app",
        "Ứng dụng này không có trên kho chính thức, hãy cài trực tiếp từ {fake_url}.",
        ("cai_app_ngoai",),
        True,
    ),
    Template(
        "probe_benefit_01",
        "train",
        "contrast_unusual_benefit",
        "Bạn bất ngờ trúng {prize} dù chưa từng đăng ký.",
        ("loi_ich_bat_thuong",),
        True,
    ),
    Template(
        "probe_benefit_02",
        "train",
        "contrast_unusual_benefit",
        "Không cần kinh nghiệm vẫn nhận thu nhập <AMOUNT:trieu> mỗi tuần.",
        ("loi_ich_bat_thuong",),
        True,
    ),
    Template(
        "probe_channel_01",
        "train",
        "contrast_channel",
        "Hãy rời kênh này và chuyển sang nhóm {channel} riêng để nói tiếp.",
        ("chuyen_kenh",),
        True,
    ),
    Template(
        "probe_channel_02",
        "train",
        "contrast_channel",
        "Chỉ liên lạc với tôi qua {channel}, không dùng kênh chính thức.",
        ("chuyen_kenh",),
        True,
    ),
    Template(
        "probe_otp_01",
        "train",
        "contrast_otp_request",
        "Đọc mã xác nhận <OTP> cho tôi.",
        ("yeu_cau_otp",),
        True,
    ),
    Template(
        "probe_otp_02",
        "train",
        "contrast_otp_request",
        "Gửi lại dãy <OTP> vừa xuất hiện trên điện thoại.",
        ("yeu_cau_otp",),
        True,
    ),
)
SCAM_TEMPLATES += _expand_specs(EMERGING_SCAM_SPECS)


LEGITIMATE_TEMPLATES: tuple[Template, ...] = (
    Template(
        "legit_otp_train_01",
        "train",
        "legitimate_otp_warning",
        "{bank}: mã <OTP> dùng để xác nhận giao dịch. Tuyệt đối không cung cấp mã này cho bất kỳ ai, kể cả nhân viên ngân hàng.",
        (),
        False,
    ),
    Template(
        "legit_otp_train_02",
        "train",
        "legitimate_otp_warning",
        "Mã xác nhận của quý khách là <OTP>. {bank} không bao giờ gọi điện yêu cầu đọc mã.",
        (),
        False,
    ),
    Template(
        "legit_otp_val_01",
        "validation",
        "legitimate_otp_warning",
        "Cảnh báo bảo mật {bank}: không chia sẻ <OTP>; nhân viên thật sẽ không hỏi mã xác nhận.",
        (),
        False,
    ),
    Template(
        "legit_otp_test_01",
        "test",
        "legitimate_otp_warning",
        "<OTP> là mã dùng một lần của bạn. Nếu không thực hiện giao dịch, hãy tự gọi số ở mặt sau thẻ.",
        (),
        False,
    ),
    Template(
        "legit_bank_train_01",
        "train",
        "legitimate_bank_notice",
        "{bank} thông báo giao dịch <AMOUNT:trieu> đã hoàn tất. Nếu không phải bạn, vui lòng tự mở ứng dụng chính thức để kiểm tra.",
        (),
        False,
    ),
    Template(
        "legit_bank_val_01",
        "validation",
        "legitimate_bank_notice",
        "Thẻ {bank} sắp đến ngày thanh toán. Quý khách xem số tiền và hướng dẫn trong ứng dụng đã cài từ cửa hàng.",
        (),
        False,
    ),
    Template(
        "legit_bank_test_01",
        "test",
        "legitimate_bank_notice",
        "{bank} ghi nhận đăng nhập mới. Không bấm liên kết trong tin nhắn; hãy gọi hotline in trên thẻ nếu cần.",
        (),
        False,
    ),
    Template(
        "legit_school_train_01",
        "train",
        "legitimate_school_notice",
        "{school} nhắc lịch họp phụ huynh lúc {meeting_time}. Thông tin chi tiết đã đăng trên cổng chính thức của trường.",
        (),
        False,
    ),
    Template(
        "legit_school_train_02",
        "train",
        "legitimate_school_notice",
        "Phòng tài vụ {school} đã phát hành thông báo học phí. Phụ huynh kiểm tra tài khoản định danh trên ứng dụng nhà trường.",
        (),
        False,
    ),
    Template(
        "legit_school_train_03",
        "train",
        "legitimate_school_notice",
        "{school} thông báo hạn hoàn thành hồ sơ. Nhà trường không yêu cầu chuyển tiền vào tài khoản cá nhân hoặc giữ bí mật.",
        (),
        False,
    ),
    Template(
        "legit_school_train_04",
        "train",
        "legitimate_school_notice",
        "Giáo viên nhắc lịch học trên nhóm phụ huynh; mọi khoản thu phải xác minh qua văn phòng trước khi thanh toán.",
        (),
        False,
    ),
    Template(
        "legit_school_val_01",
        "validation",
        "legitimate_school_notice",
        "{school}: hạn đăng ký học kỳ là {deadline}. Nhà trường không thu tiền qua tài khoản cá nhân.",
        (),
        False,
    ),
    Template(
        "legit_school_test_01",
        "test",
        "legitimate_school_notice",
        "Giáo viên nhắc lớp nộp phiếu trước {deadline}. Đây không phải yêu cầu chuyển tiền.",
        (),
        False,
    ),
    Template(
        "legit_utility_train_01",
        "train",
        "legitimate_utility_notice",
        "{utility} đã phát hành hóa đơn tháng này. Khách hàng thanh toán trên ứng dụng hoặc điểm thu chính thức.",
        (),
        False,
    ),
    Template(
        "legit_utility_val_01",
        "validation",
        "legitimate_utility_notice",
        "Lịch bảo trì của {utility} từ {meeting_time}. Không có nhân viên nào yêu cầu chuyển tiền qua tin nhắn.",
        (),
        False,
    ),
    Template(
        "legit_utility_test_01",
        "test",
        "legitimate_utility_notice",
        "{utility} xác nhận đã nhận thanh toán. Tra cứu hóa đơn bằng ứng dụng chính thức, không cần gửi mã cho ai.",
        (),
        False,
    ),
    Template(
        "legit_app_train_01",
        "train",
        "legitimate_app_notice",
        "Ứng dụng {bank} có bản cập nhật trên cửa hàng chính thức. Bạn có thể cập nhật khi thuận tiện.",
        (),
        False,
    ),
    Template(
        "legit_app_val_01",
        "validation",
        "legitimate_app_notice",
        "Để bảo vệ thiết bị, chỉ cài ứng dụng từ Google Play hoặc App Store; không mở file APK lạ.",
        (),
        False,
    ),
    Template(
        "legit_app_test_01",
        "test",
        "legitimate_app_notice",
        "Bản cập nhật đã sẵn sàng trong kho ứng dụng. Không cần bật quyền điều khiển màn hình.",
        (),
        False,
    ),
    Template(
        "legit_family_train_01",
        "train",
        "legitimate_family_chat",
        "Cả nhà giữ bí mật món quà sinh nhật cho mẹ nhé, tối nay gặp nhau như kế hoạch.",
        (),
        False,
    ),
    Template(
        "legit_family_train_02",
        "train",
        "legitimate_family_chat",
        "Nếu có việc cần tiền thì gọi lại số cũ hoặc video xác nhận, đừng chỉ tin tin nhắn.",
        (),
        False,
    ),
    Template(
        "legit_family_train_03",
        "train",
        "legitimate_family_chat",
        "Anh đang bận nên nhắn trước, nhưng em không chuyển khoản cho đến khi hai người nói chuyện trực tiếp.",
        (),
        False,
    ),
    Template(
        "legit_family_val_01",
        "validation",
        "legitimate_family_chat",
        "Đừng kể cho bố chuyện cả nhà chuẩn bị tiệc bất ngờ. Không cần chuyển khoản gì cả.",
        (),
        False,
    ),
    Template(
        "legit_family_test_01",
        "test",
        "legitimate_family_chat",
        "Anh đang họp nên chưa gọi được. Em cứ xác nhận lại qua số cũ trước khi gửi bất kỳ khoản tiền nào.",
        (),
        False,
    ),
    Template(
        "legit_job_train_01",
        "train",
        "legitimate_job",
        "Công ty mời bạn phỏng vấn vị trí bán hàng. Mức lương theo thỏa thuận, không thu phí ứng tuyển.",
        (),
        False,
    ),
    Template(
        "legit_job_val_01",
        "validation",
        "legitimate_job",
        "Hồ sơ của bạn đã được nhận. Bộ phận tuyển dụng sẽ gửi lịch qua email tên miền công ty và không yêu cầu đặt cọc.",
        (),
        False,
    ),
    Template(
        "legit_job_test_01",
        "test",
        "legitimate_job",
        "Lịch phỏng vấn lúc {meeting_time} tại văn phòng. Ứng viên không phải nạp tiền hay làm nhiệm vụ online.",
        (),
        False,
    ),
    Template(
        "legit_channel_train_01",
        "train",
        "legitimate_channel_change",
        "Nhóm lớp chuyển sang {channel} để dễ gửi tài liệu. Mọi khoản thu vẫn xác nhận qua văn phòng.",
        (),
        False,
    ),
    Template(
        "legit_channel_train_02",
        "train",
        "legitimate_channel_change",
        "Gia đình dùng nhóm {channel} mới, nhưng việc tiền bạc phải gọi video xác nhận trước.",
        (),
        False,
    ),
    Template(
        "legit_channel_train_03",
        "train",
        "legitimate_channel_change",
        "Ban tổ chức đổi kênh cập nhật lịch và nhắc không cung cấp OTP hoặc chuyển tiền cho quản trị viên.",
        (),
        False,
    ),
    Template(
        "legit_channel_train_04",
        "train",
        "legitimate_channel_change",
        "Người thân gửi lại địa chỉ {channel} của nhóm gia đình; nếu có việc tiền bạc thì gọi video xác nhận.",
        (),
        False,
    ),
    Template(
        "legit_channel_val_01",
        "validation",
        "legitimate_channel_change",
        "Tôi gửi lại địa chỉ {channel} của nhóm gia đình. Có việc tiền bạc thì gọi video xác nhận trước.",
        (),
        False,
    ),
    Template(
        "legit_channel_test_01",
        "test",
        "legitimate_channel_change",
        "Ban tổ chức dùng {channel} để cập nhật lịch. Không yêu cầu cung cấp mã hoặc chuyển khoản.",
        (),
        False,
    ),
    Template(
        "neutral_train_01",
        "train",
        "ordinary_message",
        "Chiều nay {honorific} nhớ mua giúp rau và thuốc nhé.",
        (),
        False,
    ),
    Template(
        "neutral_train_02",
        "train",
        "ordinary_message",
        "Cuộc hẹn đã đổi sang {meeting_time}. Khi đến nơi gọi cho tôi.",
        (),
        False,
    ),
    Template(
        "neutral_val_01",
        "validation",
        "ordinary_message",
        "Cảm ơn {honorific}, tôi đã nhận được tài liệu.",
        (),
        False,
    ),
    Template(
        "neutral_test_01",
        "test",
        "ordinary_message",
        "Ngày mai trời có thể mưa, cả nhà nhớ mang áo.",
        (),
        False,
    ),
)
LEGITIMATE_TEMPLATES += _expand_specs(EMERGING_LEGITIMATE_SPECS)

ALL_TEMPLATES = SCAM_TEMPLATES + LEGITIMATE_TEMPLATES
SPLIT_WEIGHTS = (("train", 0.80), ("validation", 0.10), ("test", 0.10))

VALUES: dict[str, tuple[str, ...]] = {
    "greeting": ("Chào anh/chị", "Xin chào", "Thông báo khẩn"),
    "authority": ("công an", "cơ quan thuế", "tòa án", "bảo hiểm xã hội"),
    "honorific": ("anh/chị", "quý khách", "cô/chú"),
    "deadline": ("17 giờ hôm nay", "12 giờ trưa", "cuối ngày hôm nay"),
    "duration": ("30 phút", "2 giờ", "một giờ"),
    "bank": ("Ngân hàng An Tâm", "Ngân hàng Thịnh Vượng", "Ngân hàng Thành Công"),
    "channel": ("Zalo", "Telegram", "một nhóm chat riêng"),
    "fake_url": (
        "https://dichvu-cong.invalid/ho-so.apk",
        "https://hotro-khachhang.invalid/capnhat.apk",
        "https://xac-minh.invalid/trogiup.apk",
    ),
    "prize": ("một xe máy", "phiếu quà tặng lớn", "giải thưởng tiền mặt"),
    "school": ("Trường Bình Minh", "Trường Hòa Bình", "Trung tâm Ánh Dương"),
    "utility": ("Công ty Điện lực", "Công ty Cấp nước", "Nhà mạng Di Động"),
    "meeting_time": ("8 giờ sáng mai", "14 giờ thứ sáu", "19 giờ tối nay"),
}

_PLACEHOLDER = re.compile(r"(<[^>]+>)")


def _render(template: Template, rng: random.Random) -> str:
    values = {key: rng.choice(items) for key, items in VALUES.items()}
    return template.text.format(**values)


def _without_diacritics(text: str) -> str:
    return (
        "".join(
            char
            for char in unicodedata.normalize("NFD", text)
            if unicodedata.category(char) != "Mn"
        )
        .replace("đ", "d")
        .replace("Đ", "D")
    )


def _teencode(text: str) -> str:
    replacements = {
        r"\bkhông\b": "ko",
        r"\bđược\b": "dc",
        r"\btrước\b": "truoc",
        r"\bchuyển\b": "chuyen",
        r"\bnhắn\b": "nhan",
        r"\bngay\b": "ngay",
    }
    result = text
    for pattern, replacement in replacements.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def _insert_separators(text: str, rng: random.Random) -> str:
    words = list(re.finditer(r"\b[\wÀ-ỹ]{6,}\b", text))
    if not words:
        return text
    match = rng.choice(words)
    word = match.group(0)
    separated = ".".join(word)
    return text[: match.start()] + separated + text[match.end() :]


def _duplicate_whitespace(text: str, rng: random.Random) -> str:
    spaces = [match.start() for match in re.finditer(" ", text)]
    if not spaces:
        return text
    position = rng.choice(spaces)
    return text[:position] + rng.choice(("  ", "   ", "\n")) + text[position + 1 :]


def _protect_placeholders(text: str, transform) -> str:
    parts = _PLACEHOLDER.split(text)
    return "".join(
        part if _PLACEHOLDER.fullmatch(part) else transform(part) for part in parts
    )


def _augment(text: str, rng: random.Random, is_phishing: bool) -> tuple[str, bool]:
    # Most examples stay natural; multiple perturbations may be composed.
    if rng.random() < 0.20:
        text = _protect_placeholders(text, _without_diacritics)
    if rng.random() < 0.12:
        text = _protect_placeholders(text, _teencode)
    if is_phishing and rng.random() < 0.10:
        text = _protect_placeholders(text, lambda value: _insert_separators(value, rng))
    if rng.random() < 0.08:
        text = _protect_placeholders(
            text, lambda value: _duplicate_whitespace(value, rng)
        )
    if rng.random() < 0.05:
        text = text.upper()

    truncated = rng.random() < 0.08
    if truncated and len(text) > 80:
        keep = rng.randint(max(60, int(len(text) * 0.78)), len(text) - 1)
        text = text[:keep].rstrip(" ,.;:-") + "…"
    return text, truncated


def _choose_split(rng: random.Random) -> str:
    value = rng.random()
    cumulative = 0.0
    for split, weight in SPLIT_WEIGHTS:
        cumulative += weight
        if value < cumulative:
            return split
    return "test"


def generate_records(
    size: int,
    *,
    seed: int = 20260730,
    phishing_ratio: float = 0.55,
) -> Iterable[DatasetRecord]:
    if size <= 0:
        raise ValueError("size must be positive")
    if not 0.05 <= phishing_ratio <= 0.95:
        raise ValueError("phishing_ratio must be between 0.05 and 0.95")
    rng = random.Random(seed)
    pools: dict[tuple[str, bool], dict[str, list[Template]]] = {}
    for split, _ in SPLIT_WEIGHTS:
        for is_phishing, templates in (
            (True, SCAM_TEMPLATES),
            (False, LEGITIMATE_TEMPLATES),
        ):
            grouped: defaultdict[str, list[Template]] = defaultdict(list)
            for template in templates:
                if template.split == split:
                    grouped[template.scenario].append(template)
            pools[(split, is_phishing)] = dict(grouped)

    for index in range(size):
        split = _choose_split(rng)
        is_phishing = rng.random() < phishing_ratio
        pool = pools[(split, is_phishing)]
        scenarios = sorted(pool)
        scenario = rng.choices(
            scenarios,
            weights=[
                0.20 if item.startswith("contrast_") else 1.0 for item in scenarios
            ],
            k=1,
        )[0]
        template = rng.choice(pool[scenario])
        text, truncated = _augment(_render(template, rng), rng, is_phishing)
        signal_scores = {code: 1.0 for code in template.signals}
        policy = aggregate_risk(signal_scores)
        source = rng.choices(("android", "web", "zalo_oa"), (0.60, 0.30, 0.10))[0]
        if source == "android":
            input_mode = rng.choices(
                ("notification", "sms_scan", "share", "manual"),
                (0.60, 0.20, 0.12, 0.08),
            )[0]
        elif source == "web":
            input_mode = rng.choice(("manual", "share"))
        else:
            input_mode = "share"
        yield DatasetRecord(
            id=f"syn_{seed}_{index:09d}",
            text=text,
            risk=policy.risk,
            signals=signal_scores,
            is_phishing=is_phishing,
            scenario=template.scenario,
            template_id=template.id,
            source=source,
            input_mode=input_mode,
            truncated=truncated,
            split=split,
        )


def _open_output(path: Path) -> TextIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".gz":
        return gzip.open(path, "wt", encoding="utf-8")
    return path.open("w", encoding="utf-8")


def write_dataset(
    records: Iterable[DatasetRecord],
    output: Path,
    *,
    seed: int,
    requested_size: int,
    phishing_ratio: float,
) -> dict[str, object]:
    digest = hashlib.sha256()
    split_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    scenario_counts: Counter[str] = Counter()
    phishing_counts: Counter[str] = Counter()
    count = 0

    with _open_output(output) as handle:
        for record in records:
            line = json.dumps(
                record.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            handle.write(line + "\n")
            digest.update((line + "\n").encode("utf-8"))
            count += 1
            split_counts[record.split] += 1
            risk_counts[record.risk] += 1
            scenario_counts[record.scenario] += 1
            phishing_counts[str(record.is_phishing).lower()] += 1

    manifest = {
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "requested_size": requested_size,
        "record_count": count,
        "phishing_ratio": phishing_ratio,
        "content_sha256_uncompressed_jsonl": digest.hexdigest(),
        "split_counts": dict(split_counts),
        "risk_counts": dict(risk_counts),
        "phishing_counts": dict(phishing_counts),
        "scenario_counts": dict(scenario_counts),
        "contains_real_person_data": False,
        "redaction_state": "L2 placeholders only",
    }
    manifest_path = Path(str(output) + ".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic Vietnamese CHAN training dataset."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/chan-synthetic.jsonl.gz"),
    )
    parser.add_argument("--size", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=20260730)
    parser.add_argument("--phishing-ratio", type=float, default=0.55)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    records = generate_records(
        args.size, seed=args.seed, phishing_ratio=args.phishing_ratio
    )
    manifest = write_dataset(
        records,
        args.output,
        seed=args.seed,
        requested_size=args.size,
        phishing_ratio=args.phishing_ratio,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
