# Threat-intelligence source decision register

Research date: 2026-07-30. Re-check terms before changing a source from
`disabled` to `enabled`; terms and feeds can change without notice.

| Source | Data | Decision | Reason / control |
|---|---|---|---|
| [PhishTank](https://phishtank.org/developer_info.php) | verified online phishing URLs | **implemented + enabled** | hourly bulk database, ETag, commercial API Data permitted by [terms](https://phishtank.org/terms.php) |
| [PhishVN v2](https://data.mendeley.com/datasets/b97hxbxtpd/2) | Vietnamese phishing/legitimate URLs | **implemented local import** | CC BY 4.0; static bootstrap, attribution required |
| [OpenPhish Community](https://www.openphish.com/phishing_feeds.html) | phishing URLs | **implemented + disabled** | public [terms](https://www.openphish.com/terms.html) restrict service to personal use without written consent |
| [Chống Lừa Đảo](https://chongluadao.vn/database/denylist) | malicious URLs | **partnership pending** | public page is a random sample; full list is offered by contact to authorities/businesses |
| [CheckScam](https://checkscam.vn/cam-ket-du-lieu-thong-tin/) | accounts, phones, community reports | **not crawled** | no public contracted API; `robots.txt` reserves AI-training use |
| Ngân hàng/NAPAS/SBV SIMO | suspicious payment accounts/wallets | **partnership pending** | high-quality restricted ecosystem data, not a public feed |
| Hiya | phone reputation | **coverage/licence evaluation pending** | commercial partner access; Vietnam coverage must be measured before use |
| Product community report | URL, phone, account hashes | **implemented + enabled** | explicit consent, quarantine, independent review, two-reporter activation |
| Product scenario contribution | redacted message text | **already implemented in `codebase/api`** | explicit consent, L2 check, quarantine, separate reviewer, guarded promotion |
| Ministry of Public Security/NCSC warnings | new scam narratives | **reference only** | use to update taxonomy and commission reviewed examples; do not copy article text into training without confirmed rights |

## Static text datasets

The following can bootstrap evaluation or a human annotation queue, but are
not automatically imported into the eight-signal model:

- [SMS Phishing Dataset](https://data.mendeley.com/datasets/f45bkkt8pr/1),
  5,971 messages, CC BY 4.0.
- [UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection),
  5,574 messages, CC BY 4.0.

They provide coarse ham/spam/smishing labels, not CHẮN's eight signal labels.
Automatically assigning those labels with the current model and then
retraining on them would create self-training feedback and false confidence.
Route selected, L2-redacted rows through the existing scenario quarantine and
human review API instead.

Sting9 is not onboarded because its dataset page currently says CC0 in the
body while its footer says ODC-BY-NC. Resolve the licence conflict in writing
before use.

## Refresh policy

| Data plane | Schedule | Promotion rule |
|---|---:|---|
| PhishTank URL snapshot | hourly | atomic snapshot after schema/size validation |
| PhishVN | when a signed new version is published | manual manifest and attribution review |
| Community indicators | real time into quarantine | two independent approved reporters |
| L1 rule/taxonomy update | daily if reviewed changes exist | parity tests across clients |
| Message model candidate | weekly or after enough reviewed scenarios | frozen golden-set and regression gates |

Daily full-model retraining is intentionally avoided. Fresh blocklists and
rules handle rapidly rotating indicators immediately; the classifier changes
only after enough reviewed language examples exist.
