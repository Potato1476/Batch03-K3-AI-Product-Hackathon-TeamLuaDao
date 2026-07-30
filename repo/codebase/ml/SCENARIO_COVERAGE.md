# CHẮN Vietnamese scam scenario coverage

Catalog version: `vn-scam-catalog-2026.07`
Reviewed: 2026-07-30

This is a coverage contract, not a claim that the model knows every future
scam. The executable catalog is
[`src/chan_ml/scenario_catalog.py`](src/chan_ml/scenario_catalog.py). CI checks
that every catalogued phishing family has separate train, validation, and test
templates.

## Official advisory basis

The catalog was built from public safety descriptions, not copied victim
messages:

- The People's Security Academy's 24-form taxonomy covers travel, deepfake,
  SIM locking, fake receipts, medical/school impersonation, fake finance,
  investment, account takeover, recovery, romance, phishing links, and
  gambling-tip scams:
  <https://hvannd.bocongan.gov.vn/bv/ct/10060/24-hinh-thuc-lua-dao-dien-ra-tren-khong-gian-mang-viet-nam>
- The Ministry of Public Security's 2025 e-commerce campaign highlights fake
  brands, marketplace staff, fake refunds, wallet payments, malicious QR,
  deposits, and deepfake impersonation:
  <https://bocongan.gov.vn/bai-viet/chong-lua-dao-truc-tuyen-2025-lan-toa-thong-diep-nhan-dien-bay-lua-an-tam-vui-sam-1764245385>
- The online-kidnapping advisory documents fake police, Zoom/screen sharing,
  isolation, secrecy, and "proof of innocence" transfers:
  <https://bocongan.gov.vn/bai-viet/canh-bao-bien-tuong-thu-doan-bat-coc-online-1757302259>
- The 2026 SIM advisory covers fake subscriber verification and call
  forwarding used to intercept OTP:
  <https://bocongan.gov.vn/bai-viet/cong-an-tinh-quang-ninh-tuyen-truyen-phuong-thuc-thu-doan-lua-dao-moi-tren-mang-xa-hoi-tai-dia-diem-tiep-cong-dan-cua-cong-an-tinh-1778493752>
- The traffic advisory covers fake traffic fines and driving-licence services:
  <https://www.bocongan.gov.vn/bai-viet/huong-dan-nop-phat-nguoi-va-tham-gia-giao-thong-khi-dang-trong-thoi-gian-cho-cap-doi-giay-phep-lai-xe-d2-t43826>
- The deepfake-extortion advisory covers fabricated sensitive media and
  payment threats:
  <https://bocongan.gov.vn/bai-viet/canh-giac-voi-thu-doan-cat-ghep-hinh-anh-video-nhay-cam-nham-lua-dao-chiem-doat-tai-san-cua-can-bo-cong-chuc-doanh-nhan-d22-t44736>
- The recovery advisory covers secondary scams promising to recover stolen
  funds:
  <https://bocongan.gov.vn/bai-viet/canh-giac-voi-thu-doan-ho-tro-lay-lai-tien-bi-lua-dao-1758700973>
- The investment advisory covers relationship-building followed by fake
  securities and crypto platforms:
  <https://www.bocongan.gov.vn/bai-viet/canh-bao-thu-doan-du-do-tham-gia-dau-tu-tai-chinh-san-chung-khoan-tien-ao-tren-khong-gian-mang-d22-t44828>
- The 2026 anti-trafficking plan specifically warns about fraudulent online
  recruitment:
  <https://www.bocongan.gov.vn/bai-viet/xu-ly-nghiem-cac-duong-day-toi-pham-loi-dung-cong-nghe-cao-de-lua-dao-mua-ban-nguoi-1782696133>

## Coverage

The text model has 36 phishing families. They cover government/bank
impersonation, OTP theft, malicious APK and screen sharing, VNeID and SIM
updates, traffic fines, online kidnapping, deepfake family requests,
sextortion, e-commerce refunds and shipper scams, marketplace/travel/rental/
ticket deposits, investment and romance scams, fake loans, account and
money-recovery services, charity/insurance/customs impersonation, social
account takeover, fake receipts, QR payments, invoice redirection, child-model
casting, gambling tips, and overseas-job trafficking.

Fifteen emerging legitimate families plus the original hard negatives teach
the model that warnings such as "do not share OTP", official app updates,
school deadlines, verified refunds, and legitimate channel changes are not
themselves scams.

Some families require more than text:

- Deepfake requires media/provenance verification.
- Fake receipts require bank-side transaction or image verification.
- QR requires decoding followed by URL/account lookup.
- Known URL, phone, and account indicators require the Intel/Lookup service.
- Call forwarding, accessibility permission, and screen sharing require
  on-device L0/L1 protection.

The text model detects the manipulation surrounding those attacks; it does not
claim to authenticate a face, receipt, QR, caller, or bank transaction.

## Update rule

New public advisories enter the catalog as a new version. A new family must
have:

1. at least one official or licensed source reference;
2. L2-redacted train/validation/test paraphrases with no copied personal data;
3. hard negatives for legitimate messages using similar vocabulary;
4. per-scenario recall and false-positive evaluation;
5. human review before the candidate can enter the daily training database.

Synthetic coverage is a pipeline and regression test. Production release still
requires a frozen, permitted, human-labelled corpus of real Vietnamese scam
and legitimate messages.
