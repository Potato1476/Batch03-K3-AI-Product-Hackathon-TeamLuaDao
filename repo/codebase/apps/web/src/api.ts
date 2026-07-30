export type Risk = "high" | "medium" | "unknown";
export type LookupKind = "account" | "phone" | "url";

export type SignalResult = {
  code: string;
  confidence: number;
  evidence: string;
};

export type AnalyzeResponse = {
  analysis_id: string;
  risk: Risk;
  score: number;
  signals: SignalResult[];
  explanation: string;
  questions: string[];
  verified_hotline: { name: string; number: string } | null;
  actions: Array<"report" | "share_to_guardian" | "lookup_account">;
  engine_version: string;
  rule_bundle_version: string;
};

export type RuleBundle = {
  bundle_version: string;
  l0: {
    unicode_form: "NFKC";
    lowercase: boolean;
    collapse_whitespace: boolean;
    strip_invisible: string[];
    strip_diacritics_for_matching: boolean;
    separator_characters: string[];
    teencode: Record<string, string>;
  };
  l1: {
    gate: {
      min_score_to_call_server: number;
      min_length_to_call_server: number;
      always_call_when_local_signal: string[];
    };
    otp_block: { patterns: string[] };
    local_signals: Record<
      string,
      {
        patterns: string[];
        boost_signal: string | null;
        boost: number;
      }
    >;
  };
};

export type LookupMatch = {
  hash: string;
  report_cnt: number;
  first_seen: string;
  last_seen: string;
  origin: string;
};

export type LookupResult = {
  kind: LookupKind;
  displayValue: string;
  matched: boolean;
  match: LookupMatch | null;
  noMatchMessage: string;
  bundleVersion: string;
};

export type OcrResponse = {
  text: string;
  provider: string;
  next_step: "POST /v1/analyze";
};

type DeviceTokenResponse = {
  token: string;
};

type LookupResponse = {
  hashes: LookupMatch[];
  no_match_message: string;
  bundle_version: string;
};

const API_BASE_URL = (
  import.meta.env.VITE_CHAN_API_BASE_URL || "/api"
).replace(/\/+$/, "");
const TOKEN_STORAGE_KEY = "chan.device-token.v1";
let tokenRequest: Promise<string> | null = null;

export class ChanApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
  ) {
    super(code);
    this.name = "ChanApiError";
  }
}

async function errorFrom(response: Response): Promise<ChanApiError> {
  let code = `http_${response.status}`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") code = body.detail;
  } catch {
    // The status code remains enough for a user-safe error.
  }
  return new ChanApiError(response.status, code);
}

async function issueDeviceToken(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/v1/devices/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ platform: "web", push_token: null }),
    cache: "no-store",
  });
  if (!response.ok) throw await errorFrom(response);
  const payload = (await response.json()) as DeviceTokenResponse;
  if (!payload.token) throw new ChanApiError(502, "invalid_token_response");
  window.localStorage.setItem(TOKEN_STORAGE_KEY, payload.token);
  return payload.token;
}

async function deviceToken(): Promise<string> {
  const stored = window.localStorage.getItem(TOKEN_STORAGE_KEY);
  if (stored) return stored;
  tokenRequest ??= issueDeviceToken().finally(() => {
    tokenRequest = null;
  });
  return tokenRequest;
}

async function authenticatedFetch(
  path: string,
  init: RequestInit,
  retry = true,
): Promise<Response> {
  const token = await deviceToken();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (response.status === 401 && retry) {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    return authenticatedFetch(path, init, false);
  }
  return response;
}

export async function fetchRuleBundle(): Promise<RuleBundle> {
  const response = await fetch(`${API_BASE_URL}/v1/rules/bundle`, {
    cache: "no-store",
  });
  if (!response.ok) throw await errorFrom(response);
  return (await response.json()) as RuleBundle;
}

export async function analyzeOnServer(input: {
  text: string;
  localSignals: string[];
  truncated: boolean;
}): Promise<AnalyzeResponse> {
  const response = await authenticatedFetch("/v1/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: input.text,
      source: "web",
      input_mode: "manual",
      app_package: null,
      local_signals: input.localSignals,
      truncated: input.truncated,
      locale: "vi-VN",
    }),
  });
  if (!response.ok) throw await errorFrom(response);
  return (await response.json()) as AnalyzeResponse;
}

const OCR_MAX_BYTES = 6 * 1024 * 1024;
const OCR_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);

export async function extractTextFromImage(image: File): Promise<OcrResponse> {
  if (!OCR_IMAGE_TYPES.has(image.type)) {
    throw new ChanApiError(415, "unsupported_image_type");
  }
  if (image.size === 0) throw new ChanApiError(422, "empty_image");
  if (image.size > OCR_MAX_BYTES) {
    throw new ChanApiError(413, "image_too_large");
  }
  const form = new FormData();
  form.set("image", image, image.name);
  const response = await authenticatedFetch("/v1/ocr", {
    method: "POST",
    body: form,
  });
  if (!response.ok) throw await errorFrom(response);
  const payload = (await response.json()) as OcrResponse;
  if (!payload.text.trim()) throw new ChanApiError(502, "ocr_no_text_detected");
  return payload;
}

function normalizePhone(value: string): string {
  let normalized = value.normalize("NFKC").trim();
  if (normalized.startsWith("+")) normalized = normalized.slice(1);
  let digits = normalized.replace(/[\s().-]/g, "");
  if (digits.startsWith("0084")) {
    digits = digits.slice(2);
  } else if (digits.startsWith("0") && digits.length === 10) {
    digits = `84${digits.slice(1)}`;
  }
  if (!/^\d{8,15}$/.test(digits)) throw new Error("invalid_phone");
  return digits;
}

function normalizeAccount(value: string): string {
  const normalized = value
    .normalize("NFKC")
    .trim()
    .toUpperCase()
    .replace(/[\s.-]/g, "");
  if (!/^[A-Z0-9]{6,34}$/.test(normalized)) {
    throw new Error("invalid_account");
  }
  return normalized;
}

function normalizeUrl(value: string): string {
  const raw = value.trim().includes("://") ? value.trim() : `https://${value.trim()}`;
  const parsed = new URL(raw);
  if (
    !["http:", "https:"].includes(parsed.protocol) ||
    !parsed.hostname.includes(".")
  ) {
    throw new Error("invalid_http_url");
  }
  const port =
    (parsed.protocol === "http:" && parsed.port === "80") ||
    (parsed.protocol === "https:" && parsed.port === "443")
      ? ""
      : parsed.port;
  const authority = port ? `${parsed.hostname.toLowerCase()}:${port}` : parsed.hostname.toLowerCase();
  return `${parsed.protocol}//${authority}${parsed.pathname || "/"}${parsed.search}`;
}

export function normalizeIndicator(kind: LookupKind, value: string): string {
  if (kind === "phone") return normalizePhone(value);
  if (kind === "account") return normalizeAccount(value);
  return normalizeUrl(value);
}

export async function indicatorHash(
  kind: LookupKind,
  value: string,
): Promise<string> {
  const normalized = normalizeIndicator(kind, value);
  const bytes = new TextEncoder().encode(`chan:${kind}:v1:${normalized}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

export async function lookupIndicator(
  kind: LookupKind,
  value: string,
): Promise<LookupResult> {
  const digest = await indicatorHash(kind, value);
  const prefix = digest.slice(0, 5);
  const response = await authenticatedFetch(
    `/v1/lookup/${kind}?prefix=${encodeURIComponent(prefix)}`,
    { method: "GET" },
  );
  if (!response.ok) throw await errorFrom(response);
  const payload = (await response.json()) as LookupResponse;
  const match = payload.hashes.find((item) => item.hash === digest) ?? null;
  return {
    kind,
    displayValue: value.trim(),
    matched: match !== null,
    match,
    noMatchMessage: payload.no_match_message,
    bundleVersion: payload.bundle_version,
  };
}

export function resetApiStateForTests(): void {
  tokenRequest = null;
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}
