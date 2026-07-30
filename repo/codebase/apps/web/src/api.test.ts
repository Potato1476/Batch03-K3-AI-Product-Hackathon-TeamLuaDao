import {
  analyzeOnServer,
  ChanApiError,
  extractTextFromImage,
  indicatorHash,
  resetApiStateForTests,
} from "./api";

const analysis = {
  analysis_id: "an_test",
  risk: "unknown",
  score: 0.01,
  signals: [],
  explanation: "Chưa phát hiện dấu hiệu.",
  questions: [],
  verified_hotline: null,
  actions: [],
  engine_version: "ml-test",
  rule_bundle_version: "rb-test",
};

describe("Gateway API client", () => {
  beforeEach(() => {
    resetApiStateForTests();
    vi.restoreAllMocks();
  });

  it("bootstraps a device token before authenticated analysis", async () => {
    const request = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ token: "device-token" }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(analysis), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", request);

    await analyzeOnServer({
      text: "Cán bộ yêu cầu chuyển tiền ngay.",
      localSignals: ["authority_claim"],
      truncated: false,
    });

    expect(request).toHaveBeenCalledTimes(2);
    expect(request.mock.calls[0][0]).toBe("/api/v1/devices/token");
    const headers = new Headers(request.mock.calls[1][1]?.headers);
    expect(headers.get("Authorization")).toBe("Bearer device-token");
  });

  it("renews an invalid token once and retries the request", async () => {
    window.localStorage.setItem("chan.device-token.v1", "expired-token");
    const request = vi
      .fn()
      .mockResolvedValueOnce(new Response("", { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ token: "fresh-token" }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(analysis), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", request);

    await analyzeOnServer({
      text: "Cán bộ yêu cầu chuyển tiền ngay.",
      localSignals: ["authority_claim"],
      truncated: false,
    });

    expect(request).toHaveBeenCalledTimes(3);
    const headers = new Headers(request.mock.calls[2][1]?.headers);
    expect(headers.get("Authorization")).toBe("Bearer fresh-token");
  });

  it("matches the canonical phone hash vector used by Python", async () => {
    expect(await indicatorHash("phone", "090 123 4567")).toBe(
      "28e50e599fe468498bc0b7dbb7f100aa2d55317ec4f544eed745f6e6da4cfdad",
    );
  });

  it("uploads an image with device authentication", async () => {
    window.localStorage.setItem("chan.device-token.v1", "device-token");
    const request = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          text: "Chuyển tiền ngay.",
          provider: "tesseract",
          next_step: "POST /v1/analyze",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", request);
    const image = new File(["png"], "message.png", { type: "image/png" });

    const result = await extractTextFromImage(image);

    expect(result.text).toBe("Chuyển tiền ngay.");
    expect(request.mock.calls[0][0]).toBe("/api/v1/ocr");
    const init = request.mock.calls[0][1];
    expect(init.body).toBeInstanceOf(FormData);
    expect(new Headers(init.headers).get("Authorization")).toBe(
      "Bearer device-token",
    );
  });

  it("rejects an unsupported image before making a request", async () => {
    const request = vi.fn();
    vi.stubGlobal("fetch", request);
    const image = new File(["text"], "message.txt", { type: "text/plain" });

    await expect(extractTextFromImage(image)).rejects.toEqual(
      new ChanApiError(415, "unsupported_image_type"),
    );
    expect(request).not.toHaveBeenCalled();
  });
});
