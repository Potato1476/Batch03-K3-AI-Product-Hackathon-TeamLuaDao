import {
  analyzeMessage,
  deepAnalyzeMessage,
  resetRuleBundleForTests,
} from "./engine";

const { analyzeOnServerMock, fetchRuleBundleMock } = vi.hoisted(() => ({
  analyzeOnServerMock: vi.fn(),
  fetchRuleBundleMock: vi.fn(),
}));

vi.mock("./api", async (importOriginal) => {
  const original = await importOriginal<typeof import("./api")>();
  return {
    ...original,
    analyzeOnServer: analyzeOnServerMock,
    fetchRuleBundle: fetchRuleBundleMock,
  };
});

const bundle = {
  bundle_version: "rb-test",
  l0: {
    unicode_form: "NFKC",
    lowercase: true,
    collapse_whitespace: true,
    strip_invisible: [],
    strip_diacritics_for_matching: true,
    separator_characters: [".", "-", "_", "*", "/", "|", " "],
    typo_aliases: {},
    teencode: {},
  },
  l1: {
    gate: {
      min_score_to_call_server: 0.12,
      min_length_to_call_server: 12,
      always_call_when_local_signal: ["apk_link"],
    },
    otp_block: {
      patterns: [
        "(?i)(?:doc|gui)\\s+ma\\s+otp",
        "(?i)\\b(?:ma\\s*)?otp\\b[^\\n]{0,80}\\b(?:la|:|=|-)\\s*\\d(?:[\\s.\\-]?\\d){3,7}",
      ],
    },
    local_signals: {
      authority_claim: {
        patterns: ["(?i)can\\s+bo"],
        boost_signal: "mao_danh_tham_quyen",
        boost: 0.2,
      },
      delivery_payment_request: {
        patterns: [
          "(?i)(?=.*\\b(?:don hang|giao hang|shipper|buu pham|goi hang)\\b)(?=.*\\b(?:chuyen (?:tien|khoan)|gui tien|thanh toan (?:ho|truoc)|dong phi|tra tien giup)\\b)(?=.*\\b(?:ngoai cua|nha hang xom|nhan sau|lay sau|giu don)\\b)",
        ],
        boost_signal: "tk_ca_nhan",
        boost: 0.2,
      },
      truncation_marker: {
        patterns: ["\\.\\.\\.$"],
        boost_signal: null,
        boost: 0,
      },
    },
  },
};

describe("on-device L0/L1 gate", () => {
  beforeEach(() => {
    resetRuleBundleForTests();
    fetchRuleBundleMock.mockReset();
    analyzeOnServerMock.mockReset();
    fetchRuleBundleMock.mockResolvedValue(bundle);
  });

  it("blocks an OTP request without sending message content", async () => {
    const result = await analyzeMessage("Đọc mã OTP cho tôi");
    expect(result.risk).toBe("high");
    expect(result.engine_version).toBe("l1-local");
    expect(analyzeOnServerMock).not.toHaveBeenCalled();
  });

  it("applies reviewed typo aliases before the OTP rule", async () => {
    const typoBundle = structuredClone(bundle);
    typoBundle.l0.typo_aliases = { "guima otp": "gui ma otp" };
    fetchRuleBundleMock.mockResolvedValue(typoBundle);
    const result = await analyzeMessage("Guima OTP 6 số vừa nhận");
    expect(result.risk).toBe("high");
    expect(result.engine_version).toBe("l1-local");
    expect(analyzeOnServerMock).not.toHaveBeenCalled();
  });

  it("sends suspicious content with the L1 signal vocabulary", async () => {
    analyzeOnServerMock.mockResolvedValue({
      analysis_id: "an_test",
      risk: "medium",
    });
    await analyzeMessage("Tôi là cán bộ, làm theo ngay.");
    expect(analyzeOnServerMock).toHaveBeenCalledWith({
      text: "Tôi là cán bộ, làm theo ngay.",
      localSignals: ["authority_claim"],
      truncated: false,
    });
  });

  it("keeps a benign below-gate message on the device", async () => {
    const result = await analyzeMessage("Hẹn gặp bác tại cửa hàng ngày mai.");
    expect(result.risk).toBe("unknown");
    expect(result.engine_version).toBe("l1-local");
    expect(result.questions).toHaveLength(1);
    expect(analyzeOnServerMock).not.toHaveBeenCalled();
  });

  it("normalizes diacritics in rules after stripping input diacritics", async () => {
    const accentedBundle = structuredClone(bundle);
    accentedBundle.l1.local_signals.authority_claim.patterns = [
      "(?i)cán\\s+bộ",
    ];
    fetchRuleBundleMock.mockResolvedValue(accentedBundle);
    analyzeOnServerMock.mockResolvedValue({
      analysis_id: "an_accent",
      risk: "medium",
    });
    await analyzeMessage("Tôi là cán bộ, cần trao đổi hồ sơ.");
    expect(analyzeOnServerMock).toHaveBeenCalled();
  });

  it("joins dot-obfuscated words before applying rules", async () => {
    analyzeOnServerMock.mockResolvedValue({
      analysis_id: "an_obfuscated",
      risk: "high",
    });
    await analyzeMessage("Tôi là c.a.n b.o thuế, cần làm việc.");
    expect(analyzeOnServerMock).toHaveBeenCalledWith({
      text: "Tôi là c.a.n b.o thuế, cần làm việc.",
      localSignals: ["authority_claim"],
      truncated: false,
    });
  });

  it("blocks an OTP notice when context separates the label and code", async () => {
    const result = await analyzeMessage(
      "Mã OTP chuyển khoản của bạn là 839201. Không chia sẻ mã này.",
    );
    expect(result.risk).toBe("high");
    expect(result.engine_version).toBe("l1-local");
    expect(analyzeOnServerMock).not.toHaveBeenCalled();
  });

  it("marks a below-gate message as decided on the device, not as a verdict", async () => {
    const result = await analyzeMessage("Hẹn gặp bác tại cửa hàng ngày mai.");
    expect(result.engine_version).toBe("l1-local");
    expect(result.explanation).toMatch(/chưa được gửi đi chấm sâu/i);
    expect(result.explanation).not.toMatch(/an toàn/i);
  });

  it("escalates a below-gate message to the model when the user asks", async () => {
    analyzeOnServerMock.mockResolvedValue({
      analysis_id: "an_deep",
      risk: "medium",
    });
    const text = "Hẹn gặp bác tại cửa hàng ngày mai.";
    const result = await deepAnalyzeMessage(text);
    expect(analyzeOnServerMock).toHaveBeenCalledWith({
      text,
      localSignals: [],
      truncated: false,
    });
    expect(result.risk).toBe("medium");
  });

  it("keeps OTP content on the device even on an explicit deep check", async () => {
    const result = await deepAnalyzeMessage("Đọc mã OTP cho tôi");
    expect(result.risk).toBe("high");
    expect(result.engine_version).toBe("l1-local");
    expect(analyzeOnServerMock).not.toHaveBeenCalled();
  });

  it("sends a soft fake-shipper payment request to the server", async () => {
    analyzeOnServerMock.mockResolvedValue({
      analysis_id: "an_shipper",
      risk: "medium",
    });
    const text =
      "Chào bác Lý, bác có đơn hàng ở ngoài cửa, cháu gửi hàng ở nhà hàng xóm, " +
      "bác chuyển tiền giúp cháu rồi về nhận sau nhé";
    await analyzeMessage(text);
    expect(analyzeOnServerMock).toHaveBeenCalledWith({
      text,
      localSignals: ["delivery_payment_request"],
      truncated: false,
    });
  });
});
