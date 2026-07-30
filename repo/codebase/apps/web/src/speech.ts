export type SpeechErrorCode =
  | "speech_not_supported"
  | "speech_local_not_supported"
  | "speech_language_unavailable"
  | "speech_language_downloading"
  | "speech_permission_denied"
  | "speech_no_speech"
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

function speechConstructor(): SpeechRecognitionConstructor | null {
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
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
  onEnd: () => void;
  onError: (code: SpeechErrorCode) => void;
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

  recognition.lang = language;
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  recognition.processLocally = true;
  recognition.onresult = (event) => {
    let transcript = "";
    let isFinal = true;
    for (let index = 0; index < event.results.length; index += 1) {
      const result = event.results[index];
      transcript += result?.[0]?.transcript ?? "";
      isFinal = isFinal && Boolean(result?.isFinal);
    }
    if (transcript.trim()) options.onTranscript(transcript.trim(), isFinal);
  };
  recognition.onerror = (event) => {
    const code =
      event.error === "not-allowed" || event.error === "service-not-allowed"
        ? "speech_permission_denied"
        : event.error === "language-not-supported"
          ? "speech_language_unavailable"
          : event.error === "no-speech"
            ? "speech_no_speech"
            : "speech_failed";
    options.onError(code);
  };
  recognition.onend = options.onEnd;
  try {
    recognition.start();
  } catch {
    throw new SpeechInputError("speech_failed");
  }
  return {
    stop: () => recognition.stop(),
    abort: () => recognition.abort(),
  };
}
