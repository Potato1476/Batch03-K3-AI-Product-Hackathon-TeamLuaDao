import { analyzeMessage, resetRuleBundleForTests } from "./engine";

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
    teencode: {},
  },
  l1: {
    gate: {
      min_score_to_call_server: 0.12,
      min_length_to_call_server: 12,
      always_call_when_local_signal: ["apk_link"],
    },
    otp_block: {
      patterns: ["(?i)(?:doc|gui)\\s+ma\\s+otp"],
    },
    local_signals: {
      authority_claim: {
        patterns: ["(?i)can\\s+bo"],
        boost_signal: "mao_danh_tham_quyen",
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
    expect(analyzeOnServerMock).not.toHaveBeenCalled();
  });
});
