import {
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
  onresult: ((event: never) => void) | null = null;
  onerror: ((event: never) => void) | null = null;
  onend: (() => void) | null = null;
  started = false;

  constructor() {
    FakeRecognition.instance = this;
  }

  start() {
    this.started = true;
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
});
