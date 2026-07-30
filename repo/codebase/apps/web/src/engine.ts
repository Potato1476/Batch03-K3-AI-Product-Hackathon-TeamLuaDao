import {
  analyzeOnServer,
  fetchRuleBundle,
  type AnalyzeResponse,
  type RuleBundle,
} from "./api";

let bundlePromise: Promise<RuleBundle> | null = null;

function ruleBundle(): Promise<RuleBundle> {
  bundlePromise ??= fetchRuleBundle().catch((error: unknown) => {
    bundlePromise = null;
    throw error;
  });
  return bundlePromise;
}

function compilePattern(source: string): RegExp | null {
  if (!source || source === "__see_otp_block__") return null;
  let flags = "u";
  let pattern = source;
  if (pattern.startsWith("(?i)")) {
    flags = "iu";
    pattern = pattern.slice(4);
  }
  try {
    return new RegExp(pattern, flags);
  } catch {
    return null;
  }
}

function matchingText(text: string, bundle: RuleBundle): string {
  let normalized = text.normalize(bundle.l0.unicode_form);
  for (const character of bundle.l0.strip_invisible) {
    normalized = normalized.split(character).join("");
  }
  if (bundle.l0.lowercase) normalized = normalized.toLocaleLowerCase("vi");
  if (bundle.l0.collapse_whitespace) {
    normalized = normalized.replace(/\s+/g, " ").trim();
  }
  if (bundle.l0.strip_diacritics_for_matching) {
    normalized = normalized
      .normalize("NFD")
      .replace(/\p{M}/gu, "")
      .replace(/đ/g, "d");
  }
  const words = normalized.split(" ");
  normalized = words
    .map((word) => bundle.l0.teencode[word] ?? word)
    .join(" ");
  return normalized;
}

function matchesAny(text: string, patterns: string[]): boolean {
  return patterns.some((pattern) => compilePattern(pattern)?.test(text) ?? false);
}

function localHigh(bundle: RuleBundle): AnalyzeResponse {
  return {
    analysis_id: `local_${crypto.randomUUID()}`,
    risk: "high",
    score: 1,
    signals: [{ code: "yeu_cau_otp", confidence: 1, evidence: "" }],
    explanation:
      "Tin nhắn này đang hỏi mã xác nhận của bác. Đừng đọc mã cho bất kỳ ai.",
    questions: ["Tại sao họ cần mã xác nhận của tôi?"],
    verified_hotline: null,
    actions: ["report", "share_to_guardian"],
    engine_version: "l1-local",
    rule_bundle_version: bundle.bundle_version,
  };
}

function localUnknown(bundle: RuleBundle): AnalyzeResponse {
  return {
    analysis_id: `local_${crypto.randomUUID()}`,
    risk: "unknown",
    score: 0,
    signals: [],
    explanation: "Chưa phát hiện dấu hiệu.",
    questions: [],
    verified_hotline: null,
    actions: [],
    engine_version: "l1-local",
    rule_bundle_version: bundle.bundle_version,
  };
}

export async function analyzeMessage(text: string): Promise<AnalyzeResponse> {
  const bundle = await ruleBundle();
  const normalized = matchingText(text, bundle);

  // I1: a value or request for OTP is decided entirely on-device.
  if (matchesAny(normalized, bundle.l1.otp_block.patterns)) {
    return localHigh(bundle);
  }

  const localSignals = Object.entries(bundle.l1.local_signals)
    .filter(([, rule]) => matchesAny(normalized, rule.patterns))
    .map(([name]) => name);
  const truncated = localSignals.includes("truncation_marker");
  const gate = bundle.l1.gate;
  const score = localSignals.reduce(
    (total, name) =>
      total + Math.max(0, bundle.l1.local_signals[name]?.boost ?? 0),
    0,
  );
  const shouldAlwaysCall = localSignals.some((name) =>
    gate.always_call_when_local_signal.includes(name),
  );
  if (
    normalized.length < gate.min_length_to_call_server ||
    (!shouldAlwaysCall && score < gate.min_score_to_call_server)
  ) {
    return localUnknown(bundle);
  }
  return analyzeOnServer({ text, localSignals, truncated });
}

export function resetRuleBundleForTests(): void {
  bundlePromise = null;
}
