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
  pattern = stripDiacritics(pattern);
  try {
    return new RegExp(pattern, flags);
  } catch {
    return null;
  }
}

function stripDiacritics(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/[đĐ]/g, (character) => (character === "Đ" ? "D" : "d"));
}

function escapeCharacterClass(value: string): string {
  return value.replace(/[\\\]\-^]/g, "\\$&");
}

function escapePattern(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function joinSeparatedRuns(text: string, separators: string[]): string {
  const compact = separators.filter((character) => character !== " ");
  if (!compact.length) return text;
  const characters = compact.map(escapeCharacterClass).join("");
  const runs = new RegExp(
    `(?<![\\p{L}\\p{N}])(?:[\\p{L}\\p{N}][${characters}])+[\\p{L}\\p{N}](?![\\p{L}\\p{N}])`,
    "gu",
  );
  const separatorPattern = new RegExp(`[${characters}]`, "gu");
  return text.replace(runs, (run) => run.replace(separatorPattern, ""));
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
  normalized = joinSeparatedRuns(
    normalized,
    bundle.l0.separator_characters ?? [],
  );
  if (bundle.l0.strip_diacritics_for_matching) {
    normalized = stripDiacritics(normalized);
  }
  const typoAliases = Object.entries(bundle.l0.typo_aliases ?? {}).sort(
    ([left], [right]) => right.length - left.length,
  );
  for (const [source, target] of typoAliases) {
    const phrase = escapePattern(source).replace(/ /g, "\\s+");
    normalized = normalized.replace(
      new RegExp(`\\b${phrase}\\b`, "gu"),
      target,
    );
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

/** Engine tag of a verdict decided entirely on the device by L0/L1. */
export const LOCAL_ENGINE_VERSION = "l1-local";

type LocalEvaluation = {
  otpBlocked: boolean;
  localSignals: string[];
  truncated: boolean;
  gated: boolean;
};

function evaluateLocally(text: string, bundle: RuleBundle): LocalEvaluation {
  const normalized = matchingText(text, bundle);
  if (matchesAny(normalized, bundle.l1.otp_block.patterns)) {
    return {
      otpBlocked: true,
      localSignals: [],
      truncated: false,
      gated: false,
    };
  }
  const localSignals = Object.entries(bundle.l1.local_signals)
    .filter(([, rule]) => matchesAny(normalized, rule.patterns))
    .map(([name]) => name);
  const gate = bundle.l1.gate;
  const score = localSignals.reduce(
    (total, name) =>
      total + Math.max(0, bundle.l1.local_signals[name]?.boost ?? 0),
    0,
  );
  const shouldAlwaysCall = localSignals.some((name) =>
    gate.always_call_when_local_signal.includes(name),
  );
  return {
    otpBlocked: false,
    localSignals,
    truncated: localSignals.includes("truncation_marker"),
    gated:
      normalized.length < gate.min_length_to_call_server ||
      (!shouldAlwaysCall && score < gate.min_score_to_call_server),
  };
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
    engine_version: LOCAL_ENGINE_VERSION,
    rule_bundle_version: bundle.bundle_version,
  };
}

function localUnknown(bundle: RuleBundle): AnalyzeResponse {
  return {
    analysis_id: `local_${crypto.randomUUID()}`,
    risk: "unknown",
    score: 0,
    signals: [],
    // The gate decided not to spend the message's privacy, not that the
    // message is fine. The client must not present this as a finished check.
    explanation:
      "Các quy tắc trên máy không thấy dấu hiệu nào, nên tin nhắn chưa được gửi đi chấm sâu. Đây chưa phải kết luận.",
    questions: [
      "Tin nhắn đến từ đâu và có yêu cầu bấm link, chuyển tiền hoặc cung cấp mã xác nhận không?",
    ],
    verified_hotline: null,
    actions: [],
    engine_version: LOCAL_ENGINE_VERSION,
    rule_bundle_version: bundle.bundle_version,
  };
}

export async function analyzeMessage(text: string): Promise<AnalyzeResponse> {
  const bundle = await ruleBundle();
  const local = evaluateLocally(text, bundle);

  // I1: a value or request for OTP is decided entirely on-device.
  if (local.otpBlocked) return localHigh(bundle);
  if (local.gated) return localUnknown(bundle);
  return analyzeOnServer({
    text,
    localSignals: local.localSignals,
    truncated: local.truncated,
  });
}

/**
 * Escalate past the L1 gate on an explicit user request. The gate trades recall
 * for privacy, so a message it kept on the device must stay one tap away from
 * the model instead of ending as a silent "no signals found".
 */
export async function deepAnalyzeMessage(
  text: string,
): Promise<AnalyzeResponse> {
  const bundle = await ruleBundle();
  const local = evaluateLocally(text, bundle);

  // I1 outranks the user's request: OTP content never leaves the device.
  if (local.otpBlocked) return localHigh(bundle);
  return analyzeOnServer({
    text,
    localSignals: local.localSignals,
    truncated: local.truncated,
  });
}

export function resetRuleBundleForTests(): void {
  bundlePromise = null;
}
