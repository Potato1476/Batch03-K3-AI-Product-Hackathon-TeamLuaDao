export type SpeechErrorCode =
  | "speech_not_supported"
  | "speech_local_not_supported"
  | "speech_language_unavailable"
  | "speech_language_downloading"
  | "speech_permission_denied"
  | "speech_failed";

export class SpeechInputError extends Error {
  constructor(readonly code: SpeechErrorCode) {
    super(code);
    this.name = "SpeechInputError";
  }
}

type SpeechResult = {
  isFinal: boolean;
  0: { transcript: string };
};

type SpeechResultEvent = Event & {
  resultIndex: number;
  results: ArrayLike<SpeechResult>;
};

type SpeechRecognitionErrorEvent = Event & {
  error: string;
};

type SpeechRecognitionInstance = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  processLocally?: boolean;
  onaudiostart?: (() => void) | null;
  onstart?: (() => void) | null;
  onsoundstart?: (() => void) | null;
  onsoundend?: (() => void) | null;
  onspeechstart?: (() => void) | null;
  onspeechend?: (() => void) | null;
  onresult: ((event: SpeechResultEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
};

type LocalSpeechAvailability =
  | "available"
  | "downloadable"
  | "downloading"
  | "unavailable";

type SpeechRecognitionConstructor = {
  new (): SpeechRecognitionInstance;
  available?: (options: {
    langs: string[];
    processLocally: boolean;
  }) => Promise<LocalSpeechAvailability>;
  install?: (options: {
    langs: string[];
    processLocally: boolean;
  }) => Promise<boolean>;
};

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

export type SpeechController = {
  stop(): void;
  abort(): void;
};

/**
 * A recognition run ends after each utterance, so we restart it to keep the
 * button listening until the user says stop. Long dictation legitimately needs
 * many restarts, so instead of a flat cap we only bail when runs start ending
 * instantly — the signature of an engine that cannot start at all.
 */
const RAPID_RESTART_MS = 300;
const MAX_RAPID_RESTARTS = 10;

function speechConstructor(): SpeechRecognitionConstructor | null {
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

/**
 * Whether this browser can transcribe without shipping audio off the device.
 * Checked before rendering the mic button so the user is never invited to
 * press a control that can only fail.
 */
export function isLocalSpeechSupported(): boolean {
  const constructor = speechConstructor();
  if (!constructor) return false;
  try {
    return "processLocally" in new constructor();
  } catch {
    return false;
  }
}

async function ensureVietnameseLanguage(
  constructor: SpeechRecognitionConstructor,
  language: string,
): Promise<void> {
  if (!constructor.available) return;
  let availability: LocalSpeechAvailability;
  try {
    availability = await constructor.available({
      langs: [language],
      processLocally: true,
    });
  } catch {
    throw new SpeechInputError("speech_language_unavailable");
  }
  if (availability === "available") return;
  if (availability === "downloading") {
    throw new SpeechInputError("speech_language_downloading");
  }
  if (availability === "downloadable" && constructor.install) {
    const installed = await constructor.install({
      langs: [language],
      processLocally: true,
    });
    if (installed) return;
  }
  throw new SpeechInputError("speech_language_unavailable");
}

export async function startLocalSpeechRecognition(options: {
  onTranscript: (transcript: string, isFinal: boolean) => void;
  onStart?: () => void;
  onEnd: () => void;
  onError: (code: SpeechErrorCode) => void;
  /** True while the recogniser itself reports incoming sound. */
  onSound?: (active: boolean) => void;
  language?: string;
}): Promise<SpeechController> {
  const constructor = speechConstructor();
  if (!constructor) throw new SpeechInputError("speech_not_supported");

  const recognition = new constructor();
  if (!("processLocally" in recognition)) {
    throw new SpeechInputError("speech_local_not_supported");
  }
  const language = options.language ?? "vi-VN";
  await ensureVietnameseLanguage(constructor, language);

  let stopped = false;
  let rapidRestarts = 0;
  let runStartedAt = Date.now();
  let capturing = false;
  // Each restart gives us a fresh `results` list, so text from earlier runs
  // has to be kept here or it disappears from the box mid-sentence.
  let committed = "";
  let sessionText = "";

  const finish = () => {
    if (stopped) return;
    stopped = true;
    options.onEnd();
  };

  const markCapturing = () => {
    if (stopped || capturing) return;
    capturing = true;
    options.onStart?.();
  };

  recognition.lang = language;
  // Chrome's on-device engine silently transcribes nothing for Vietnamese when
  // `continuous` is on: it reports sound and speech, then never emits a result.
  // (Verified against the same engine with continuous off, with the cloud path,
  // and with en-US — all three transcribe fine.) We keep single-utterance runs
  // and stitch them together across restarts instead.
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  recognition.processLocally = true;
  // Not every engine fires both, and the pair tells us the mic is actually
  // open — `start()` returning only means the request was accepted.
  recognition.onaudiostart = markCapturing;
  recognition.onstart = markCapturing;
  // These are the only honest "we hear you" signals: they come from the
  // recogniser's own capture, not from a second microphone stream.
  recognition.onsoundstart = () => options.onSound?.(true);
  recognition.onsoundend = () => options.onSound?.(false);
  recognition.onresult = (event) => {
    markCapturing();
    let transcript = "";
    let isFinal = true;
    for (let index = 0; index < event.results.length; index += 1) {
      const result = event.results[index];
      transcript += result?.[0]?.transcript ?? "";
      isFinal = isFinal && Boolean(result?.isFinal);
    }
    sessionText = transcript.trim();
    const full = [committed, sessionText].filter(Boolean).join(" ").trim();
    if (full) options.onTranscript(full, isFinal);
  };
  recognition.onerror = (event) => {
    // Silence is normal while the user gathers their thoughts; `onend` will
    // restart us. Everything else ends the session.
    if (event.error === "no-speech" || event.error === "aborted") return;
    const code =
      event.error === "not-allowed" || event.error === "service-not-allowed"
        ? "speech_permission_denied"
        : event.error === "language-not-supported"
          ? "speech_language_unavailable"
          : "speech_failed";
    stopped = true;
    options.onError(code);
  };
  recognition.onend = () => {
    if (stopped) return;
    rapidRestarts =
      Date.now() - runStartedAt < RAPID_RESTART_MS ? rapidRestarts + 1 : 0;
    if (rapidRestarts >= MAX_RAPID_RESTARTS) {
      finish();
      return;
    }
    // Carry this run's words over; the next run starts with an empty list.
    committed = [committed, sessionText].filter(Boolean).join(" ").trim();
    sessionText = "";
    try {
      runStartedAt = Date.now();
      recognition.start();
    } catch {
      finish();
    }
  };
  try {
    runStartedAt = Date.now();
    recognition.start();
  } catch {
    throw new SpeechInputError("speech_failed");
  }
  return {
    stop: () => {
      stopped = true;
      recognition.stop();
      options.onEnd();
    },
    abort: () => {
      stopped = true;
      recognition.abort();
    },
  };
}
