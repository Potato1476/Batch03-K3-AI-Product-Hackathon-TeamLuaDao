import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";

const {
  analyzeMessageMock,
  analyzeThreadMock,
  deepAnalyzeMessageMock,
  extractTextFromImageMock,
  extractThreadFromImageMock,
  lookupIndicatorMock,
  startLocalSpeechRecognitionMock,
  isLocalSpeechSupportedMock,
} = vi.hoisted(() => ({
  analyzeMessageMock: vi.fn(),
  analyzeThreadMock: vi.fn(),
  deepAnalyzeMessageMock: vi.fn(),
  extractTextFromImageMock: vi.fn(),
  extractThreadFromImageMock: vi.fn(),
  lookupIndicatorMock: vi.fn(),
  startLocalSpeechRecognitionMock: vi.fn(),
  isLocalSpeechSupportedMock: vi.fn(),
}));

vi.mock("./engine", async (importOriginal) => {
  const original = await importOriginal<typeof import("./engine")>();
  return {
    ...original,
    analyzeMessage: analyzeMessageMock,
    analyzeThread: analyzeThreadMock,
    deepAnalyzeMessage: deepAnalyzeMessageMock,
  };
});
vi.mock("./api", async (importOriginal) => {
  const original = await importOriginal<typeof import("./api")>();
  return {
    ...original,
    extractTextFromImage: extractTextFromImageMock,
    extractThreadFromImage: extractThreadFromImageMock,
    lookupIndicator: lookupIndicatorMock,
  };
});
vi.mock("./speech", async (importOriginal) => {
  const original = await importOriginal<typeof import("./speech")>();
  return {
    ...original,
    startLocalSpeechRecognition: startLocalSpeechRecognitionMock,
    isLocalSpeechSupported: isLocalSpeechSupportedMock,
  };
});

const highResult = {
  analysis_id: "an_test",
  risk: "high",
  score: 0.91,
  signals: [
    { code: "mao_danh_tham_quyen", confidence: 0.9, evidence: "cán bộ" },
    { code: "yeu_cau_bi_mat", confidence: 0.88, evidence: "không nói với ai" },
    { code: "ap_luc_thoi_gian", confidence: 0.8, evidence: "ngay" },
    { code: "tk_ca_nhan", confidence: 0.78, evidence: "chuyển tiền" },
  ],
  explanation: "Tin nhắn có nhiều dấu hiệu thao túng.",
  questions: ["Tại sao tôi phải chuyển tiền ngay?"],
  verified_hotline: null,
  actions: ["report", "share_to_guardian"],
  engine_version: "ml-test",
  rule_bundle_version: "rb-test",
};

const localOnlyResult = {
  analysis_id: "local_test",
  risk: "unknown",
  score: 0,
  signals: [],
  explanation:
    "Các quy tắc trên máy không thấy dấu hiệu nào, nên tin nhắn chưa được gửi đi chấm sâu. Đây chưa phải kết luận.",
  questions: ["Tin nhắn đến từ đâu?"],
  verified_hotline: null,
  actions: [],
  engine_version: "l1-local",
  rule_bundle_version: "rb-test",
};

describe("CHAN web flow", () => {
  beforeEach(() => {
    analyzeMessageMock.mockReset();
    analyzeThreadMock.mockReset();
    deepAnalyzeMessageMock.mockReset();
    extractThreadFromImageMock.mockReset();
    extractTextFromImageMock.mockReset();
    lookupIndicatorMock.mockReset();
    startLocalSpeechRecognitionMock.mockReset();
    analyzeMessageMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          window.setTimeout(() => resolve(highResult), 10);
        }),
    );
    lookupIndicatorMock.mockResolvedValue({
      kind: "phone",
      displayValue: "0982558619",
      matched: false,
      match: null,
      noMatchMessage: "Chưa có báo cáo về số điện thoại này.",
      bundleVersion: "rb-test",
    });
    extractTextFromImageMock.mockResolvedValue({
      text: "Công an yêu cầu chuyển tiền ngay.",
      provider: "tesseract",
      next_step: "POST /v1/analyze",
    });
    isLocalSpeechSupportedMock.mockReset();
    isLocalSpeechSupportedMock.mockReturnValue(true);
    startLocalSpeechRecognitionMock.mockImplementation(
      async ({ onTranscript, onStart, onSound }) => {
        onStart?.();
        onSound?.(true);
        onTranscript("Không nói với ai và chuyển tiền ngay.", true);
        return { stop: vi.fn(), abort: vi.fn() };
      },
    );
  });

  it("keeps analysis disabled until the user enters a message", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tin nhắn đáng ngờ/i }));
    const analyze = screen.getByRole("button", { name: "Kiểm tra ngay" });
    expect(analyze).toBeDisabled();

    await user.type(screen.getByLabelText("Nội dung tin nhắn"), "Chuyển tiền ngay.");
    expect(analyze).toBeEnabled();
  });

  it("shows the high-risk guidance after analysis", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tin nhắn đáng ngờ/i }));
    await user.type(screen.getByLabelText("Nội dung tin nhắn"), "Đọc mã OTP cho tôi.");
    await user.click(screen.getByRole("button", { name: "Kiểm tra ngay" }));

    expect(screen.getByText("Đang đọc tin nhắn…")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Nhiều dấu hiệu lừa đảo")).toBeInTheDocument());
    expect(screen.getByText("Đừng chuyển tiền. Đừng đọc mã OTP.")).toBeInTheDocument();
    expect(screen.getByText("Trúng 4/8 dấu hiệu thao túng")).toBeInTheDocument();
    expect(analyzeMessageMock).toHaveBeenCalledWith("Đọc mã OTP cho tôi.");
  });

  it("keeps the checked message visible above the signal checklist", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tin nhắn đáng ngờ/i }));
    await user.type(screen.getByLabelText("Nội dung tin nhắn"), "Chuyển tiền ngay.");
    await user.click(screen.getByRole("button", { name: "Kiểm tra ngay" }));

    await waitFor(() =>
      expect(screen.getByText("TIN NHẮN BÁC VỪA KIỂM TRA")).toBeInTheDocument(),
    );
    expect(screen.getByText("Chuyển tiền ngay.")).toBeInTheDocument();
    expect(screen.getByText("Trúng 4/8 dấu hiệu thao túng")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Mạo danh cơ quan chức năng" }),
    ).toBeInTheDocument();
  });

  it("offers a deep check instead of passing an on-device result off as a verdict", async () => {
    analyzeMessageMock.mockResolvedValue(localOnlyResult);
    deepAnalyzeMessageMock.mockResolvedValue(highResult);
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tin nhắn đáng ngờ/i }));
    await user.type(screen.getByLabelText("Nội dung tin nhắn"), "Bác xem giúp cháu.");
    await user.click(screen.getByRole("button", { name: "Kiểm tra ngay" }));

    await waitFor(() =>
      expect(screen.getByText("Máy chưa thấy dấu hiệu nào")).toBeInTheDocument(),
    );
    expect(screen.queryByText("Chưa phát hiện dấu hiệu")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Kiểm tra kỹ hơn" }));

    await waitFor(() =>
      expect(screen.getByText("Nhiều dấu hiệu lừa đảo")).toBeInTheDocument(),
    );
    expect(deepAnalyzeMessageMock).toHaveBeenCalledWith("Bác xem giúp cháu.");
    expect(screen.getByText("Bác xem giúp cháu.")).toBeInTheDocument();
  });

  it("extracts text from an uploaded screenshot", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tin nhắn đáng ngờ/i }));
    await user.click(screen.getByRole("button", { name: "Gửi ảnh chụp" }));
    const image = new File(["png"], "message.png", { type: "image/png" });
    await user.upload(screen.getByLabelText("Ảnh chụp tin nhắn"), image);

    await waitFor(() =>
      expect(screen.getByLabelText("Nội dung tin nhắn")).toHaveValue(
        "Công an yêu cầu chuyển tiền ngay.",
      ),
    );
    expect(extractTextFromImageMock).toHaveBeenCalledWith(image);
    expect(screen.getByText(/Đã đọc ảnh bằng tesseract/i)).toBeInTheDocument();
  });

  it("fills the message using local speech recognition", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tin nhắn đáng ngờ/i }));
    await user.click(
      screen.getByRole("button", { name: "Đọc nội dung bằng giọng nói" }),
    );

    await waitFor(() =>
      expect(screen.getByLabelText("Nội dung tin nhắn")).toHaveValue(
        "Không nói với ai và chuyển tiền ngay.",
      ),
    );
    expect(startLocalSpeechRecognitionMock).toHaveBeenCalledOnce();
  });

  it("shows a recording panel driven by the recogniser's own sound events", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tin nhắn đáng ngờ/i }));
    await user.click(
      screen.getByRole("button", { name: "Đọc nội dung bằng giọng nói" }),
    );

    await waitFor(() =>
      expect(screen.getByText("Đang thu âm — bác cứ nói")).toBeInTheDocument(),
    );
    expect(screen.getByRole("img", { name: "Đang nghe thấy tiếng" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Dừng thu âm/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("keeps saying it hears nothing until the recogniser reports sound", async () => {
    const user = userEvent.setup();
    startLocalSpeechRecognitionMock.mockImplementation(async ({ onStart }) => {
      onStart?.();
      return { stop: vi.fn(), abort: vi.fn() };
    });
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tin nhắn đáng ngờ/i }));
    await user.click(
      screen.getByRole("button", { name: "Đọc nội dung bằng giọng nói" }),
    );

    await waitFor(() =>
      expect(screen.getByRole("img", { name: "Chưa nghe thấy tiếng" })).toBeInTheDocument(),
    );
    expect(screen.getByText(/Bác nói to hơn hoặc lại gần micro/)).toBeInTheDocument();
  });

  it("adds to the box on a second recording instead of replacing it", async () => {
    const user = userEvent.setup();
    const say = vi.fn();
    startLocalSpeechRecognitionMock.mockImplementation(
      async ({ onTranscript, onStart }) => {
        onStart?.();
        say.mockImplementation(onTranscript);
        return { stop: vi.fn(), abort: vi.fn() };
      },
    );
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tin nhắn đáng ngờ/i }));
    const record = () =>
      user.click(
        screen.getByRole("button", {
          name: /Đọc nội dung bằng giọng nói|Dừng thu âm/,
        }),
      );

    await record();
    say("Câu thứ nhất.", true);
    await waitFor(() =>
      expect(screen.getByLabelText("Nội dung tin nhắn")).toHaveValue(
        "Câu thứ nhất.",
      ),
    );

    await record(); // stop
    await record(); // start again
    say("Câu thứ hai.", true);

    await waitFor(() =>
      expect(screen.getByLabelText("Nội dung tin nhắn")).toHaveValue(
        "Câu thứ nhất. Câu thứ hai.",
      ),
    );
  });

  it("stops recording when the user says stop", async () => {
    const user = userEvent.setup();
    const stop = vi.fn();
    startLocalSpeechRecognitionMock.mockImplementation(async ({ onStart }) => {
      onStart?.();
      return { stop, abort: vi.fn() };
    });
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tin nhắn đáng ngờ/i }));
    await user.click(
      screen.getByRole("button", { name: "Đọc nội dung bằng giọng nói" }),
    );
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Dừng thu âm/ })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: /Dừng thu âm/ }));

    expect(stop).toHaveBeenCalled();
    expect(screen.queryByText("Đang thu âm — bác cứ nói")).not.toBeInTheDocument();
  });

  it("disables the mic button when the browser cannot transcribe on the device", async () => {
    const user = userEvent.setup();
    isLocalSpeechSupportedMock.mockReturnValue(false);
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tin nhắn đáng ngờ/i }));

    expect(
      screen.getByRole("button", { name: "Đọc nội dung bằng giọng nói" }),
    ).toBeDisabled();
    expect(screen.getByText(/tạm khoá nút nói/i)).toBeInTheDocument();
    expect(startLocalSpeechRecognitionMock).not.toHaveBeenCalled();
  });

  it("explains the privacy-preserving lookup before searching", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tài khoản, số điện thoại/i }));
    expect(screen.getByText(/chỉ gửi 5 ký tự đầu/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tra cứu báo cáo" })).toBeDisabled();
  });

  it("supports dark mode and prototype error simulation from settings", async () => {
    const user = userEvent.setup();
    const { container } = render(<App />);

    await user.click(screen.getByRole("button", { name: "Cài đặt" }));
    await user.click(screen.getByRole("switch", { name: "Chế độ tối" }));
    expect(container.querySelector("[data-theme='dark']")).toBeInTheDocument();

    await user.click(screen.getByRole("switch", { name: "Mất mạng" }));
    expect(screen.getByText(/Mất mạng · kiểm tra trên máy vẫn hoạt động/i)).toBeInTheDocument();
  });

  it("shows a neutral no-report page for the authentic demo number", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tài khoản, số điện thoại/i }));
    await user.click(screen.getByRole("button", { name: "Điện thoại" }));
    await user.type(screen.getByLabelText("Điện thoại cần tra"), "0982558619");
    await user.click(screen.getByRole("button", { name: "Tra cứu báo cáo" }));

    expect(screen.getByRole("heading", { name: "Chưa có báo cáo về số điện thoại này." })).toBeInTheDocument();
    expect(screen.getByText("0982558619")).toBeInTheDocument();
    expect(screen.getByText(/Thông tin đúng định dạng/i)).toBeInTheDocument();
    expect(screen.getByText(/không có nghĩa là an toàn tuyệt đối/i)).toBeInTheDocument();
  });

  it("shows a community report returned by the backend", async () => {
    lookupIndicatorMock.mockResolvedValue({
      kind: "phone",
      displayValue: "0393066063",
      matched: true,
      match: {
        hash: "a".repeat(64),
        report_cnt: 12,
        first_seen: "2026-07-20T00:00:00Z",
        last_seen: "2026-07-30T00:00:00Z",
        origin: "community",
      },
      noMatchMessage: "Chưa có báo cáo về số điện thoại này.",
      bundleVersion: "rb-test",
    });
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tài khoản, số điện thoại/i }));
    await user.click(screen.getByRole("button", { name: "Điện thoại" }));
    await user.type(screen.getByLabelText("Điện thoại cần tra"), "0393066063");
    await user.click(screen.getByRole("button", { name: "Tra cứu báo cáo" }));

    expect(screen.getByRole("heading", { name: "Đã có người báo cáo" })).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(lookupIndicatorMock).toHaveBeenCalledWith("phone", "0393066063");
  });
});

describe("CHAN conversation flow", () => {
  const hijacked = {
    analysis_id: "th_test",
    risk: "high",
    thread_signals: [
      {
        code: "doi_giong_van",
        label: "Cách nhắn tin đổi khác so với trước",
        confidence: 0.8,
        evidence: "ck giup a 15 trieu",
      },
      {
        code: "ne_goi_thoai",
        label: "Né gọi điện hoặc gọi video",
        confidence: 0.9,
        evidence: "dang hop k goi dc",
      },
    ],
    explanation: "Cách nhắn tin của người này đã đổi khác so với trước.",
    questions: ["Gọi video cho Minh bằng số cũ để nghe giọng."],
    actions: ["report"],
    baseline_messages: 3,
    style_distance: 0.52,
    insufficient_history: false,
    ask_message_index: 5,
    ask_message_risk: "medium",
    ask_message_signals: [],
    engine_version: "ml-test",
    rule_bundle_version: "rb-test",
  };

  beforeEach(() => {
    analyzeThreadMock.mockReset();
    extractThreadFromImageMock.mockReset();
    analyzeThreadMock.mockResolvedValue(hijacked);
    extractThreadFromImageMock.mockResolvedValue({
      messages: [
        { sender: "contact", text: "Chào cậu, dạo này thế nào? 😊" },
        { sender: "user", text: "Tớ vẫn ổn" },
        { sender: "contact", text: "ck giup a 15 trieu vao stk 0912345678" },
      ],
      provider: "tesseract",
      inferred_senders: true,
      next_step: "POST /v1/analyze-thread",
    });
  });

  it("reads a conversation screenshot and lets the user fix who said what", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Cả đoạn trò chuyện/i }));
    const image = new File(["png"], "chat.png", { type: "image/png" });
    await user.upload(screen.getByLabelText("Ảnh chụp đoạn trò chuyện"), image);

    await waitFor(() =>
      expect(screen.getByLabelText("Nội dung tin nhắn 1")).toHaveValue(
        "Chào cậu, dạo này thế nào? 😊",
      ),
    );
    expect(screen.getByText(/Máy đoán ai nhắn dựa vào vị trí bong bóng chat/i)).toBeInTheDocument();

    // The attribution is a guess, so it has to be correctable.
    const toggles = screen.getAllByRole("button", { name: /bấm để đổi/i });
    await user.click(toggles[0]);
    expect(toggles[0]).toHaveTextContent("Bác");
  });

  it("warns about a hijacked account using thread-level signals", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Cả đoạn trò chuyện/i }));
    await user.type(screen.getByLabelText("Bác lưu tên người này là gì?"), "Minh");
    await user.click(screen.getByRole("button", { name: "Dùng đoạn ví dụ" }));
    await user.click(screen.getByRole("button", { name: "Kiểm tra đoạn trò chuyện" }));

    await waitFor(() =>
      expect(screen.getByText("Có thể tài khoản đã bị chiếm")).toBeInTheDocument(),
    );
    expect(screen.getByText("Cách nhắn tin đổi khác so với trước")).toBeInTheDocument();
    expect(screen.getByText("Né gọi điện hoặc gọi video")).toBeInTheDocument();
    expect(screen.getByText(/độ lệch cách nhắn tin 52%/)).toBeInTheDocument();
    expect(analyzeThreadMock).toHaveBeenCalledWith(expect.any(Array), "Minh");
  });
});
