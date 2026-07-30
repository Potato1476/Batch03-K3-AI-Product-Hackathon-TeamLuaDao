import {
  isLocalSpeechSupported,
  SpeechInputError,
  startLocalSpeechRecognition,
} from "./speech";

class FakeRecognition {
  static availability = "available";
  static installed = false;
  static instance: FakeRecognition | null = null;

  static async available() {
    return FakeRecognition.availability;
  }

  static async install() {
    FakeRecognition.installed = true;
    return true;
  }

  lang = "";
  continuous = false;
  interimResults = false;
  maxAlternatives = 0;
  processLocally = false;
  onaudiostart: (() => void) | null = null;
  onstart: (() => void) | null = null;
  onresult: ((event: never) => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  started = false;
  startCount = 0;

  constructor() {
    FakeRecognition.instance = this;
  }

  start() {
    this.started = true;
    this.startCount += 1;
  }

  stop() {
    this.onend?.();
  }

  abort() {
    this.onend?.();
  }
}

describe("local speech recognition", () => {
  beforeEach(() => {
    FakeRecognition.availability = "available";
    FakeRecognition.installed = false;
    FakeRecognition.instance = null;
    window.SpeechRecognition = FakeRecognition as never;
    delete window.webkitSpeechRecognition;
  });

  it("forces Vietnamese recognition to stay on the device", async () => {
    const onEnd = vi.fn();
    const controller = await startLocalSpeechRecognition({
      onTranscript: vi.fn(),
      onError: vi.fn(),
      onEnd,
    });
    const recognition = FakeRecognition.instance;

    expect(recognition?.started).toBe(true);
    expect(recognition?.lang).toBe("vi-VN");
    expect(recognition?.processLocally).toBe(true);
    controller.stop();
    expect(onEnd).toHaveBeenCalled();
  });

  it("installs a downloadable Vietnamese language pack", async () => {
    FakeRecognition.availability = "downloadable";
    await startLocalSpeechRecognition({
      onTranscript: vi.fn(),
      onError: vi.fn(),
      onEnd: vi.fn(),
    });
    expect(FakeRecognition.installed).toBe(true);
  });

  it("refuses a browser that cannot guarantee local processing", async () => {
    class RemoteOnlyRecognition extends FakeRecognition {
      declare processLocally: never;

      constructor() {
        super();
        delete (this as Partial<FakeRecognition>).processLocally;
      }
    }
    window.SpeechRecognition = RemoteOnlyRecognition as never;

    await expect(
      startLocalSpeechRecognition({
        onTranscript: vi.fn(),
        onError: vi.fn(),
        onEnd: vi.fn(),
      }),
    ).rejects.toEqual(
      new SpeechInputError("speech_local_not_supported"),
    );
  });

  it("keeps runs single-utterance, which on-device Vietnamese requires", async () => {
    // Chrome's on-device vi-VN engine emits sound and speech events but never a
    // result when `continuous` is on. Continuity comes from restarting instead.
    await startLocalSpeechRecognition({
      onTranscript: vi.fn(),
      onError: vi.fn(),
      onEnd: vi.fn(),
    });

    expect(FakeRecognition.instance?.continuous).toBe(false);
    expect(FakeRecognition.instance?.interimResults).toBe(true);
  });

  it("gives up when runs end instantly instead of spinning forever", async () => {
    const onEnd = vi.fn();
    await startLocalSpeechRecognition({
      onTranscript: vi.fn(),
      onError: vi.fn(),
      onEnd,
    });
    const recognition = FakeRecognition.instance;

    for (let attempt = 0; attempt < 30; attempt += 1) recognition?.onend?.();

    expect(onEnd).toHaveBeenCalledOnce();
    expect(recognition?.startCount).toBeLessThan(15);
  });

  it("reports on-device support before the user presses the mic", () => {
    expect(isLocalSpeechSupported()).toBe(true);
    delete window.SpeechRecognition;
    expect(isLocalSpeechSupported()).toBe(false);
  });

  it("signals the caller only once the microphone is really open", async () => {
    const onStart = vi.fn();
    await startLocalSpeechRecognition({
      onTranscript: vi.fn(),
      onError: vi.fn(),
      onEnd: vi.fn(),
      onStart,
    });

    expect(onStart).not.toHaveBeenCalled();
    FakeRecognition.instance?.onaudiostart?.();
    FakeRecognition.instance?.onstart?.();
    expect(onStart).toHaveBeenCalledOnce();
  });

  it("keeps listening when the engine stops itself on a pause", async () => {
    const onEnd = vi.fn();
    await startLocalSpeechRecognition({
      onTranscript: vi.fn(),
      onError: vi.fn(),
      onEnd,
    });
    const recognition = FakeRecognition.instance;

    recognition?.onerror?.({ error: "no-speech" });
    recognition?.onend?.();

    expect(recognition?.startCount).toBe(2);
    expect(onEnd).not.toHaveBeenCalled();
  });

  it("keeps words from earlier runs when the engine restarts", async () => {
    const onTranscript = vi.fn();
    await startLocalSpeechRecognition({
      onTranscript,
      onError: vi.fn(),
      onEnd: vi.fn(),
    });
    const recognition = FakeRecognition.instance;
    const say = (transcript: string, isFinal: boolean) =>
      recognition?.onresult?.({
        resultIndex: 0,
        results: [{ isFinal, 0: { transcript } }],
      } as never);

    say("Bác chuyển tiền ngay", true);
    recognition?.onend?.();
    say("không nói với ai", true);

    expect(onTranscript).toHaveBeenLastCalledWith(
      "Bác chuyển tiền ngay không nói với ai",
      true,
    );
  });

  it("starts a fresh transcript after the user stops and records again", async () => {
    const say = (transcript: string) =>
      FakeRecognition.instance?.onresult?.({
        resultIndex: 0,
        results: [{ isFinal: true, 0: { transcript } }],
      } as never);

    const first = await startLocalSpeechRecognition({
      onTranscript: vi.fn(),
      onError: vi.fn(),
      onEnd: vi.fn(),
    });
    say("Câu thứ nhất");
    first.stop();

    const onTranscript = vi.fn();
    await startLocalSpeechRecognition({
      onTranscript,
      onError: vi.fn(),
      onEnd: vi.fn(),
    });
    say("Câu thứ hai");

    // The earlier run's words belong to the text box now, not to this run.
    expect(onTranscript).toHaveBeenCalledWith("Câu thứ hai", true);
  });

  it("does not restart after the user stops it", async () => {
    const onEnd = vi.fn();
    const controller = await startLocalSpeechRecognition({
      onTranscript: vi.fn(),
      onError: vi.fn(),
      onEnd,
    });

    controller.stop();

    expect(FakeRecognition.instance?.startCount).toBe(1);
    expect(onEnd).toHaveBeenCalledOnce();
  });

  it("ends the session on a real failure instead of restarting", async () => {
    const onError = vi.fn();
    await startLocalSpeechRecognition({
      onTranscript: vi.fn(),
      onError,
      onEnd: vi.fn(),
    });
    const recognition = FakeRecognition.instance;

    recognition?.onerror?.({ error: "not-allowed" });
    recognition?.onend?.();

    expect(onError).toHaveBeenCalledWith("speech_permission_denied");
    expect(recognition?.startCount).toBe(1);
  });
});
