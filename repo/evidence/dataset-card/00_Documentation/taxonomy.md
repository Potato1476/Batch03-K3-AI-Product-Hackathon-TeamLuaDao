# CHẮN Dataset Taxonomy Specification

## 1. Overview
The CHẮN Dataset provides structured multi-turn Vietnamese conversation data for cyber scam detection and classification.

## 2. Emotion Groups & Scenarios (9 Groups, 32 Explicit Scenarios)
- **Fear**: Police (#1), Tax (#3), Electricity (#4), Court (#1), Bank (#2), Customs (#5)
- **Greed**: Crypto (#12), Forex (#13), Stock (#14), MLM (#12), AI_Bot (#12), Task (#18)
- **Compassion**: Charity (#19), Sick_Urgent (#20)
- **Romance**: Facebook (#8), Tinder (#10), Telegram (#24), DatingApp (#10)
- **Lust**: Sextortion (#22), Sugar (#11)
- **Curiosity**: Prize (#16), Refund (#15), Package_Foreign (#21)
- **Authority**: Police (#1), Bank (#2)
- **Social**: Hacked_FB (#8), Hacked_Zalo (#9), Relative_Borrow (#7), School (#6)
- **Hybrid**: Telegram_Redirect (#24), VideoCall (#23), Deepfake (#25)

## 3. Negative Dataset Categories (10 Categories)
Family, Bank, School, Hospital, Shopping, Work, OTP_Real, Government, Delivery, Utilities.

## 4. Multi-turn Stage Evolution
1. `contact`: Initial greeting / reach out
2. `building_trust`: Credibility / authority / intimacy establishing
3. `solicitation`: Scam hook introduction
4. `demanding_money`: Financial / credentials request
5. `conclusion`: Victim reaction & conversation outcome
