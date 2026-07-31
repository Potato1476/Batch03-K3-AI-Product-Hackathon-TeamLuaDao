import { useEffect, useRef, useState } from "react";
import { Icon } from "./components/Icon";
import {
  ChanApiError,
  extractTextFromImage,
  extractThreadFromImage,
  lookupIndicator,
  type AnalyzeResponse,
  type AnalyzeThreadResponse,
  type LookupKind,
  type LookupResult as LookupApiResult,
  type ThreadMessage,
} from "./api";
import {
  analyzeMessage,
  analyzeThread,
  deepAnalyzeMessage,
  LOCAL_ENGINE_VERSION,
  parseThread,
} from "./engine";
import {
  isLocalSpeechSupported,
  SpeechInputError,
  startLocalSpeechRecognition,
  type SpeechController,
  type SpeechErrorCode,
} from "./speech";

type Screen =
  | "home"
  | "input"
  | "loading"
  | "result"
  | "thread"
  | "threadResult"
  | "check"
  | "checkResult"
  | "checkClear"
  | "shield"
  | "settings";
type SimulationKey = "mic" | "micMissing" | "ocr" | "offline";
type ErrorKey =
  | SimulationKey
  | "backend"
  | "lookupInvalid"
  | "imageTooLarge"
  | "imageType"
  | "ocrUnavailable"
  | "speechLocal"
  | "speechLanguage"
  | "threadTooShort";
type Simulations = Record<SimulationKey, boolean>;

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

const sampleMessage =
  "Tôi là cán bộ công an. Bác phải chuyển tiền xác minh trước 17h hôm nay và không được nói với người nhà.";

export function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [message, setMessage] = useState("");
  const [lookupKind, setLookupKind] = useState<LookupKind>("account");
  const [lookupValue, setLookupValue] = useState("");
  const [shareOpen, setShareOpen] = useState(window.location.pathname === "/share");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [error, setError] = useState<ErrorKey | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  // The result screen quotes what was actually checked, which may differ from
  // the textarea once the user starts editing the next message.
  const [analyzedMessage, setAnalyzedMessage] = useState("");
  const [threadMessages, setThreadMessages] = useState<ThreadMessage[]>([]);
  const [contactName, setContactName] = useState("");
  const [threadAnalysis, setThreadAnalysis] = useState<AnalyzeThreadResponse | null>(null);
  const [lookupResult, setLookupResult] = useState<LookupApiResult | null>(null);
  const [simulations, setSimulations] = useState<Simulations>({
    mic: false,
    micMissing: false,
    ocr: false,
    offline: false,
  });

  const go = (next: Screen) => {
    setScreen(next);
    const main = document.querySelector("main");
    if (main && "scrollTo" in main) {
      main.scrollTo({ top: 0 });
    }
  };

  const runCheck = async (
    text: string,
    check: (text: string) => Promise<AnalyzeResponse>,
  ) => {
    if (simulations.offline) {
      setError("offline");
      return;
    }
    setError(null);
    go("loading");
    try {
      const result = await check(text);
      setAnalyzedMessage(text);
      setAnalysis(result);
      go("result");
    } catch {
      setError("backend");
      go("input");
    }
  };

  const runAnalysis = () => runCheck(message, analyzeMessage);
  const runDeepAnalysis = () => runCheck(analyzedMessage, deepAnalyzeMessage);

  const runThreadAnalysis = async () => {
    if (simulations.offline) {
      setError("offline");
      return;
    }
    const messages = threadMessages.filter((message) => message.text.trim());
    if (messages.length < 2) {
      setError("threadTooShort");
      return;
    }
    setError(null);
    go("loading");
    try {
      const result = await analyzeThread(messages, contactName.trim());
      setThreadAnalysis(result);
      go("threadResult");
    } catch {
      setError("backend");
      go("thread");
    }
  };

  const runLookup = async () => {
    if (simulations.offline) {
      setError("offline");
      return;
    }
    setError(null);
    try {
      const result = await lookupIndicator(lookupKind, lookupValue);
      setLookupResult(result);
      go(result.matched ? "checkResult" : "checkClear");
    } catch (lookupError) {
      setError(
        lookupError instanceof Error &&
          lookupError.message.startsWith("invalid_")
          ? "lookupInvalid"
          : "backend",
      );
    }
  };

  return (
    <div className="app-shell" data-theme={theme}>
      <header className="site-header">
        <a className="site-brand" href="/" aria-label="CHAN — Trang chủ">
          <img src="/chan-logo-horizontal.svg" alt="CHAN" />
        </a>
        <p>Trợ lý chống lừa đảo</p>
      </header>

      <div className="app-layout">
        {simulations.offline && <div className="offline-banner"><Icon name="alert" size={20} /> Mất mạng · kiểm tra trên máy vẫn hoạt động</div>}

        <main className={`screen screen-${screen}`} key={screen}>
          {screen === "home" && (
            <Home
              onInput={() => go("input")}
              onThread={() => go("thread")}
              onLookup={() => go("check")}
            />
          )}
          {screen === "input" && (
            <InputScreen
              message={message}
              onMessage={setMessage}
              onBack={() => go("home")}
              onAnalyze={() => void runAnalysis()}
              error={error}
              onError={setError}
              simulations={simulations}
            />
          )}
          {screen === "loading" && <Loading />}
          {screen === "result" && analysis && (
            <Result
              analysis={analysis}
              message={analyzedMessage}
              onBack={() => go("input")}
              onDeepCheck={() => void runDeepAnalysis()}
            />
          )}
          {screen === "thread" && (
            <ThreadScreen
              messages={threadMessages}
              onMessages={setThreadMessages}
              contactName={contactName}
              onContactName={setContactName}
              onBack={() => go("home")}
              onAnalyze={() => void runThreadAnalysis()}
              error={error}
              onError={setError}
              simulations={simulations}
            />
          )}
          {screen === "threadResult" && threadAnalysis && (
            <ThreadResult analysis={threadAnalysis} onBack={() => go("thread")} />
          )}
          {screen === "check" && (
            <Lookup
              kind={lookupKind}
              value={lookupValue}
              onKind={setLookupKind}
              onValue={setLookupValue}
              onBack={() => go("home")}
              onLookup={() => void runLookup()}
              error={error}
              onDismissError={() => setError(null)}
            />
          )}
          {screen === "checkResult" && lookupResult && <LookupResult result={lookupResult} onBack={() => go("check")} />}
          {screen === "checkClear" && lookupResult && <ClearLookupResult result={lookupResult} onBack={() => go("check")} />}
          {screen === "shield" && <Shield />}
          {screen === "settings" && (
            <Settings
              theme={theme}
              onTheme={setTheme}
              simulations={simulations}
              onSimulation={(key, enabled) => {
                setSimulations((current) => ({ ...current, [key]: enabled }));
                if (!enabled && error === key) setError(null);
              }}
            />
          )}
        </main>

        <Navigation screen={screen} onGo={go} />

        {shareOpen && (
          <ShareSheet
            onCancel={() => setShareOpen(false)}
            onAccept={() => {
              setMessage(sampleMessage);
              setShareOpen(false);
              go("input");
            }}
          />
        )}
      </div>
    </div>
  );
}

function Home({
  onInput,
  onThread,
  onLookup,
}: {
  onInput: () => void;
  onThread: () => void;
  onLookup: () => void;
}) {
  return (
    <section className="page home-page">
      <header className="brand-header">
        <img className="project-logo" src="/chan-logo-horizontal.svg" alt="CHAN" />
        <p>Chào bác Lý, mình cùng kiểm tra nhé.</p>
      </header>
      <div className="protection-card">
        <span className="status-dot" />
        <div><h2>Đang bảo vệ bác</h2><p>Tin nhắn được kiểm tra riêng tư trên máy.</p></div>
      </div>
      <div>
        <p className="eyebrow">BÁC MUỐN KIỂM TRA GÌ?</p>
        <button className="action-card primary" onClick={onInput}>
          <span className="action-icon"><Icon name="message" /></span>
          <span><strong>Tin nhắn đáng ngờ</strong><small>Dán tin nhắn hoặc gửi ảnh chụp</small></span>
        </button>
        <button className="action-card secondary" onClick={onThread}>
          <span className="action-icon"><Icon name="message" /></span>
          <span><strong>Cả đoạn trò chuyện</strong><small>Nghi người quen bị chiếm tài khoản</small></span>
        </button>
        <button className="action-card secondary" onClick={onLookup}>
          <span className="action-icon"><Icon name="account" /></span>
          <span><strong>Tài khoản, số điện thoại</strong><small>Tra cứu báo cáo từ cộng đồng</small></span>
        </button>
      </div>
      <div className="recent">
        <h2>Gần đây</h2>
        <div className="recent-card"><span className="risk-badge">CẦN CẨN TRỌNG</span><p>Tin nhắn tự nhận là nhân viên ngân hàng</p><small>Hôm qua · không lưu nội dung</small></div>
      </div>
    </section>
  );
}

function BackButton({ onClick, label = "Trang chủ" }: { onClick: () => void; label?: string }) {
  return <button className="back-button" onClick={onClick}><Icon name="back" /> {label}</button>;
}

function InputScreen({
  message,
  onMessage,
  onBack,
  onAnalyze,
  error,
  onError,
  simulations,
}: {
  message: string;
  onMessage: (value: string) => void;
  onBack: () => void;
  onAnalyze: () => void;
  error: ErrorKey | null;
  onError: (error: ErrorKey | null) => void;
  simulations: Simulations;
}) {
  const [mode, setMode] = useState<"text" | "image">("text");
  const [ocrBusy, setOcrBusy] = useState(false);
  const [ocrProvider, setOcrProvider] = useState("");
  const [speechState, setSpeechState] = useState<
    "idle" | "preparing" | "listening"
  >("idle");
  const [soundActive, setSoundActive] = useState(false);
  const [heardSeconds, setHeardSeconds] = useState(0);
  const [heardSomething, setHeardSomething] = useState(false);
  const imageInput = useRef<HTMLInputElement>(null);
  const speechController = useRef<SpeechController | null>(null);
  const speechBase = useRef("");
  const speechRun = useRef(0);
  const [speechSupported] = useState(isLocalSpeechSupported);

  const releaseMic = () => {
    speechController.current = null;
    setSoundActive(false);
  };

  useEffect(
    () => () => {
      speechController.current?.abort();
    },
    [],
  );

  useEffect(() => {
    if (speechState !== "listening") return;
    const startedAt = Date.now();
    const timer = setInterval(
      () => setHeardSeconds(Math.floor((Date.now() - startedAt) / 1000)),
      1000,
    );
    return () => clearInterval(timer);
  }, [speechState]);

  // Some engines never fire a start event. Rather than leave the user staring
  // at "đang chuẩn bị" forever, show the listening panel once the mic is live.
  useEffect(() => {
    if (speechState !== "preparing") return;
    const timer = setTimeout(() => {
      if (speechController.current) setSpeechState("listening");
    }, 3000);
    return () => clearTimeout(timer);
  }, [speechState]);

  const mapSpeechError = (code: SpeechErrorCode): ErrorKey => {
    if (code === "speech_permission_denied") return "mic";
    if (code === "speech_not_supported") return "micMissing";
    if (code === "speech_local_not_supported") return "speechLocal";
    if (
      code === "speech_language_unavailable" ||
      code === "speech_language_downloading"
    ) {
      return "speechLanguage";
    }
    return "mic";
  };

  const handleVoice = async () => {
    // Also cancels while still waiting for permission, so the button is never
    // a dead control.
    if (speechState !== "idle") {
      // Only retire the run when nothing is listening yet — a live recogniser
      // still owes us the last words, which arrive just after stop().
      if (!speechController.current) speechRun.current += 1;
      speechController.current?.stop();
      releaseMic();
      setSpeechState("idle");
      return;
    }
    if (!speechSupported) {
      onError("speechLocal");
      return;
    }
    if (simulations.micMissing) {
      onError("micMissing");
      return;
    }
    if (simulations.mic) {
      onError("mic");
      return;
    }
    onError(null);
    speechBase.current = message.trim();
    speechRun.current += 1;
    const run = speechRun.current;
    const isCurrent = () => speechRun.current === run;
    setHeardSomething(false);
    setHeardSeconds(0);
    setSpeechState("preparing");
    try {
      const controller = await startLocalSpeechRecognition({
        onTranscript: (transcript) => {
          if (!isCurrent()) return;
          setHeardSomething(true);
          // `speechBase` is whatever was in the box when this run began, so a
          // second run adds to the text instead of replacing it.
          onMessage(
            [speechBase.current, transcript].filter(Boolean).join(" ").trim(),
          );
        },
        // Only now is the microphone truly open — before this the browser is
        // still asking for permission, so claiming "đang nghe" would be a lie.
        onStart: () => {
          if (isCurrent()) setSpeechState("listening");
        },
        onSound: (active) => {
          if (isCurrent()) setSoundActive(active);
        },
        onError: (code) => {
          if (!isCurrent()) return;
          releaseMic();
          setSpeechState("idle");
          onError(mapSpeechError(code));
        },
        onEnd: () => {
          if (!isCurrent()) return;
          releaseMic();
          setSpeechState("idle");
        },
      });
      // The user cancelled while the permission prompt was still open.
      if (!isCurrent()) {
        controller.abort();
        return;
      }
      speechController.current = controller;
    } catch (speechError) {
      if (!isCurrent()) return;
      releaseMic();
      setSpeechState("idle");
      onError(
        speechError instanceof SpeechInputError
          ? mapSpeechError(speechError.code)
          : "mic",
      );
    }
  };

  const handleImage = async (file: File | undefined) => {
    if (!file) return;
    if (simulations.offline) {
      onError("offline");
      return;
    }
    if (simulations.ocr) {
      onError("ocr");
      return;
    }
    onError(null);
    setOcrProvider("");
    setOcrBusy(true);
    try {
      const result = await extractTextFromImage(file);
      onMessage(result.text);
      setOcrProvider(result.provider);
      setMode("text");
    } catch (ocrError) {
      if (ocrError instanceof ChanApiError) {
        if (ocrError.code === "image_too_large") onError("imageTooLarge");
        else if (ocrError.code === "unsupported_image_type") onError("imageType");
        else if (
          ocrError.code === "ocr_provider_not_configured" ||
          ocrError.code === "ocr_provider_not_installed"
        ) {
          onError("ocrUnavailable");
        } else {
          onError("ocr");
        }
      } else {
        onError("ocr");
      }
    } finally {
      setOcrBusy(false);
      if (imageInput.current) imageInput.current.value = "";
    }
  };

  return (
    <section className="page">
      <BackButton onClick={onBack} />
      <h1>Dán tin nhắn cần kiểm tra</h1>
      <p className="page-lead">CHAN sẽ chỉ ra những câu đang thúc ép hoặc thao túng bác.</p>
      {error && error !== "offline" && <ErrorBox error={error} onClose={() => onError(null)} onAction={() => onError(null)} />}
      <div className="mode-grid">
        <button className={mode === "text" ? "mode active" : "mode"} onClick={() => setMode("text")}><Icon name="mic" /> Nhập hoặc đọc chữ</button>
        <button className={mode === "image" ? "mode active" : "mode"} onClick={() => setMode("image")}><Icon name="camera" /> Gửi ảnh chụp</button>
      </div>
      {mode === "image" && (
        <>
          <input
            ref={imageInput}
            className="visually-hidden"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            aria-label="Ảnh chụp tin nhắn"
            onChange={(event) => void handleImage(event.target.files?.[0])}
          />
          <button
            type="button"
            className={`upload-zone${ocrBusy ? " busy" : ""}`}
            disabled={ocrBusy}
            onClick={() => imageInput.current?.click()}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              void handleImage(event.dataTransfer.files[0]);
            }}
          >
            <Icon name="camera" size={40} />
            <strong>{ocrBusy ? "Đang đọc chữ trong ảnh…" : "Chọn ảnh chụp tin nhắn"}</strong>
            <span>PNG, JPG hoặc WebP · tối đa 6 MB</span>
          </button>
        </>
      )}
      <label className="field-label" htmlFor="message">Nội dung tin nhắn</label>
      <textarea id="message" value={message} onChange={(event) => onMessage(event.target.value)} placeholder="Bác dán tin nhắn vào đây…" />
      {speechState !== "idle" && (
        <div
          className={`recording-panel${speechState === "listening" ? " live" : ""}`}
          role="status"
          aria-live="polite"
        >
          <div className="recording-head">
            <span className="recording-dot" aria-hidden="true" />
            <strong>
              {speechState === "preparing"
                ? "Đang xin quyền dùng micro…"
                : "Đang thu âm — bác cứ nói"}
            </strong>
            {speechState === "listening" && (
              <span className="recording-time">{formatDuration(heardSeconds)}</span>
            )}
          </div>
          {speechState === "listening" && (
            <>
              <div
                className={`sound-bars${soundActive ? " active" : ""}`}
                role="img"
                aria-label={
                  soundActive ? "Đang nghe thấy tiếng" : "Chưa nghe thấy tiếng"
                }
              >
                <span />
                <span />
                <span />
                <span />
                <span />
              </div>
              <p>
                {heardSomething
                  ? "CHAN đang ghi chữ vào ô “Nội dung tin nhắn” ngay phía trên. Bấm nút đỏ để dừng."
                  : soundActive
                    ? "Nghe thấy tiếng rồi, đang chuyển thành chữ…"
                    : "Chưa nghe thấy tiếng. Bác nói to hơn hoặc lại gần micro."}
              </p>
            </>
          )}
        </div>
      )}
      <button
        type="button"
        className={`voice-button${speechState === "listening" ? " listening" : ""}`}
        disabled={!speechSupported}
        aria-pressed={speechState === "listening"}
        onClick={() => void handleVoice()}
      >
        <Icon name="mic" />
        {speechState === "preparing"
          ? "Huỷ, không dùng giọng nói nữa"
          : speechState === "listening"
            ? "Dừng thu âm"
            : "Đọc nội dung bằng giọng nói"}
      </button>
      {!speechSupported && (
        <p className="input-status muted" role="status">
          Trình duyệt này chưa đọc được giọng nói ngay trên máy, nên CHAN tạm khoá
          nút nói. Bác dùng Chrome hoặc Edge bản mới trên máy tính, hoặc gõ và gửi
          ảnh như bình thường.
        </p>
      )}
      {ocrProvider && (
        <p className="input-status" role="status">
          Đã đọc ảnh bằng {ocrProvider}. Bác xem lại chữ trước khi kiểm tra.
        </p>
      )}
      <button className="cta danger" disabled={!message.trim()} onClick={onAnalyze}>Kiểm tra ngay</button>
      <InfoBox>Ảnh được OCR tự host và xoá ngay sau khi đọc. Giọng nói chỉ bật khi trình duyệt hỗ trợ xử lý cục bộ. Mã OTP không được gửi sang bước phân tích.</InfoBox>
    </section>
  );
}

function Loading() {
  return <section className="loading-page" aria-live="polite"><span className="loading-dot">!</span><h1>Đang đọc tin nhắn…</h1><p>Máy đang tìm các câu thúc ép bác.</p></section>;
}

const signalLabels: Record<string, string> = {
  mao_danh_tham_quyen: "Mạo danh cơ quan chức năng",
  yeu_cau_bi_mat: "Yêu cầu giữ bí mật",
  ap_luc_thoi_gian: "Ép gấp về thời gian",
  tk_ca_nhan: "Yêu cầu chuyển tiền cho người chưa xác minh",
  cai_app_ngoai: "Yêu cầu cài ứng dụng ngoài cửa hàng",
  loi_ich_bat_thuong: "Hứa lợi ích bất thường",
  chuyen_kenh: "Yêu cầu chuyển kênh liên lạc",
  yeu_cau_otp: "Đòi mã OTP hoặc mã xác nhận",
};

const riskCopy = {
  high: {
    hero: "danger-hero",
    pill: "NGUY CƠ CAO",
    title: "Nhiều dấu hiệu lừa đảo",
    guidance: "Đừng chuyển tiền. Đừng đọc mã OTP.",
  },
  medium: {
    hero: "warning-hero",
    pill: "CẦN KIỂM TRA",
    title: "Cần kiểm tra thêm",
    guidance: "Hãy dừng lại và tự gọi kênh chính thức.",
  },
  unknown: {
    hero: "neutral-hero",
    pill: "CHƯA ĐỦ DẤU HIỆU",
    title: "Chưa phát hiện dấu hiệu",
    guidance: "Kết quả này không có nghĩa là an toàn.",
  },
} as const;

const localOnlyCopy = {
  hero: "neutral-hero",
  pill: "CHƯA CHẤM SÂU",
  title: "Máy chưa thấy dấu hiệu nào",
  guidance: "Tin nhắn chưa được gửi đi chấm sâu. Đây chưa phải kết luận.",
} as const;

function CheckedMessage({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = text.length > 240;
  const shown = expanded || !isLong ? text : `${text.slice(0, 240).trimEnd()}…`;
  return (
    <div className="checked-message">
      <p className="eyebrow">TIN NHẮN BÁC VỪA KIỂM TRA</p>
      <p className="checked-message-text">{shown}</p>
      {isLong && (
        <button type="button" className="link-button" onClick={() => setExpanded(!expanded)}>
          {expanded ? "Thu gọn tin nhắn" : "Xem đầy đủ tin nhắn"}
        </button>
      )}
    </div>
  );
}

function Result({
  analysis,
  message,
  onBack,
  onDeepCheck,
}: {
  analysis: AnalyzeResponse;
  message: string;
  onBack: () => void;
  onDeepCheck: () => void;
}) {
  // A gate decision is not a verdict: say so instead of borrowing the copy of
  // a real "no signals found" answer from the model.
  const localOnly =
    analysis.engine_version === LOCAL_ENGINE_VERSION && analysis.risk === "unknown";
  const copy = localOnly ? localOnlyCopy : riskCopy[analysis.risk];
  const hits = new Map(analysis.signals.map((signal) => [signal.code, signal]));
  return (
    <section>
      <div className={`risk-hero ${copy.hero}`}>
        <BackButton onClick={onBack} label="Quay lại" />
        <span className="hero-pill">{copy.pill}</span>
        <h1>{copy.title}</h1>
        <p><strong>{copy.guidance}</strong></p>
      </div>
      <div className="page result-body">
        {message && <CheckedMessage text={message} />}
        {localOnly && (
          <div className="deep-check">
            <h2>Bác muốn kiểm tra kỹ hơn?</h2>
            <p>
              CHAN mới chỉ đối chiếu quy tắc ngay trên máy để giữ riêng tư. Bấm nút
              dưới đây để gửi tin nhắn cho máy chủ chấm đầy đủ 8 dấu hiệu.
            </p>
            <button type="button" className="cta" onClick={onDeepCheck}>
              Kiểm tra kỹ hơn
            </button>
          </div>
        )}
        <div className="source-card">
          <span>{localOnly ? "MÁY" : "WEB"}</span>
          <p>Kết quả từ CHAN · {analysis.engine_version}</p>
        </div>
        <h2>Trúng {analysis.signals.length}/8 dấu hiệu thao túng</h2>
        <div className="signal-list">
          {Object.entries(signalLabels).map(([code, label]) => {
            const signal = hits.get(code);
            return (
            <article className={signal ? "signal hit" : "signal miss"} key={code}>
              <span className="signal-mark">{signal ? "!" : "–"}</span>
              <div><h3>{label}</h3>{signal?.evidence && <blockquote>“{signal.evidence}”</blockquote>}</div>
            </article>
            );
          })}
        </div>
        <div className="recommendation">
          <h2>{analysis.questions.length ? "Bác hãy hỏi lại họ" : "Kết luận"}</h2>
          {analysis.questions.map((question) => <p key={question}>{question}</p>)}
          {!analysis.questions.length && <p>{analysis.explanation}</p>}
          <small>{analysis.explanation}</small>
        </div>
        {analysis.verified_hotline && (
          <a className="hotline" href={`tel:${analysis.verified_hotline.number}`}>
            <Icon name="phone" />
            <span><strong>{analysis.verified_hotline.name}</strong><small>Tự gọi số chính thức để kiểm tra</small></span>
            <b>{analysis.verified_hotline.number}</b>
          </a>
        )}
        <button className="secondary-button" onClick={onBack}>Kiểm tra tin khác</button>
      </div>
    </section>
  );
}

const sampleThread: ThreadMessage[] = [
  { sender: "contact", text: "Chào cậu, dạo này công việc thế nào rồi? 😊" },
  { sender: "user", text: "Tớ vẫn ổn, cậu sao rồi" },
  { sender: "contact", text: "Mình cũng bình thường thôi. Cuối tuần này rảnh không? ☕" },
  { sender: "user", text: "Chắc rảnh, sao thế" },
  { sender: "contact", text: "Đi cà phê nhé, lâu lắm không gặp rồi. 🙂" },
  { sender: "contact", text: "e dang ket tien qua, ck giup a 15 trieu vao stk 0912345678 duoc k" },
  { sender: "user", text: "Ơ sao gấp thế, gọi video cho tớ cái" },
  { sender: "contact", text: "dang hop k goi dc, nhan tin thoi, chuyen gap giup a" },
];

function ThreadScreen({
  messages,
  onMessages,
  contactName,
  onContactName,
  onBack,
  onAnalyze,
  error,
  onError,
  simulations,
}: {
  messages: ThreadMessage[];
  onMessages: (messages: ThreadMessage[]) => void;
  contactName: string;
  onContactName: (value: string) => void;
  onBack: () => void;
  onAnalyze: () => void;
  error: ErrorKey | null;
  onError: (error: ErrorKey | null) => void;
  simulations: Simulations;
}) {
  const [busy, setBusy] = useState(false);
  const [provider, setProvider] = useState("");
  const [pasting, setPasting] = useState(false);
  const [pasted, setPasted] = useState("");
  const imageInput = useRef<HTMLInputElement>(null);

  const handleImage = async (file: File | undefined) => {
    if (!file) return;
    if (simulations.offline) {
      onError("offline");
      return;
    }
    if (simulations.ocr) {
      onError("ocr");
      return;
    }
    onError(null);
    setProvider("");
    setBusy(true);
    try {
      const result = await extractThreadFromImage(file);
      onMessages(result.messages);
      setProvider(result.provider);
    } catch (ocrError) {
      if (ocrError instanceof ChanApiError) {
        if (ocrError.code === "image_too_large") onError("imageTooLarge");
        else if (ocrError.code === "unsupported_image_type") onError("imageType");
        else if (ocrError.code === "ocr_thread_too_short") onError("threadTooShort");
        else if (
          ocrError.code === "ocr_provider_not_configured" ||
          ocrError.code === "ocr_provider_not_installed" ||
          ocrError.code === "ocr_provider_without_layout"
        ) {
          onError("ocrUnavailable");
        } else onError("ocr");
      } else onError("ocr");
    } finally {
      setBusy(false);
      if (imageInput.current) imageInput.current.value = "";
    }
  };

  const update = (index: number, next: Partial<ThreadMessage>) => {
    onMessages(messages.map((m, i) => (i === index ? { ...m, ...next } : m)));
  };

  return (
    <section className="page">
      <BackButton onClick={onBack} />
      <h1>Kiểm tra cả đoạn trò chuyện</h1>
      <p className="page-lead">
        Khi tài khoản của người quen bị chiếm, kẻ xấu nhắn từ đúng tài khoản đó. Một
        tin nhắn nhìn không ra — nhưng cách nhắn tin của họ thì đổi khác.
      </p>
      {error && error !== "offline" && (
        <ErrorBox error={error} onClose={() => onError(null)} onAction={() => onError(null)} />
      )}
      <label className="field-label" htmlFor="contact">Bác lưu tên người này là gì?</label>
      <input
        id="contact"
        value={contactName}
        onChange={(event) => onContactName(event.target.value)}
        placeholder="Ví dụ: Minh"
      />
      <input
        ref={imageInput}
        className="visually-hidden"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        aria-label="Ảnh chụp đoạn trò chuyện"
        onChange={(event) => void handleImage(event.target.files?.[0])}
      />
      <button
        type="button"
        className={`upload-zone${busy ? " busy" : ""}`}
        disabled={busy}
        onClick={() => imageInput.current?.click()}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          void handleImage(event.dataTransfer.files[0]);
        }}
      >
        <Icon name="camera" size={40} />
        <strong>{busy ? "Đang đọc đoạn trò chuyện…" : "Chụp màn hình đoạn trò chuyện"}</strong>
        <span>Chụp cả những tin cũ trước đó thì máy mới so được</span>
      </button>
      {!messages.length && (
        <button type="button" className="link-button" onClick={() => setPasting(!pasting)}>
          {pasting ? "Ẩn ô gõ tay" : "Hoặc gõ tay đoạn trò chuyện"}
        </button>
      )}
      {pasting && !messages.length && (
        <>
          <p className="input-hint">
            Mỗi dòng một tin nhắn, bắt đầu bằng <strong>Họ:</strong> hoặc <strong>Tôi:</strong>
          </p>
          <textarea
            className="thread-input"
            aria-label="Gõ đoạn trò chuyện"
            value={pasted}
            onChange={(event) => setPasted(event.target.value)}
            placeholder={"Họ: Chào cậu, dạo này thế nào?\nTôi: Tớ vẫn ổn\nHọ: cho a muon 5 trieu voi"}
          />
          <button
            type="button"
            className="secondary-button"
            disabled={parseThread(pasted).length < 2}
            onClick={() => onMessages(parseThread(pasted))}
          >
            Dùng đoạn vừa gõ
          </button>
        </>
      )}
      {messages.length > 0 && (
        <>
          <h2>Đoạn trò chuyện đọc được</h2>
          {provider && (
            <p className="input-status" role="status">
              Đã đọc ảnh bằng {provider}. Máy đoán ai nhắn dựa vào vị trí bong bóng chat —
              bác bấm để sửa nếu sai.
            </p>
          )}
          <div className="thread-rows">
            {messages.map((message, index) => (
              <div className={`thread-row ${message.sender}`} key={index}>
                <button
                  type="button"
                  className="sender-toggle"
                  aria-label={`Tin này của ${message.sender === "contact" ? "họ" : "bác"} — bấm để đổi`}
                  onClick={() =>
                    update(index, {
                      sender: message.sender === "contact" ? "user" : "contact",
                    })
                  }
                >
                  {message.sender === "contact" ? "Họ" : "Bác"}
                </button>
                <input
                  aria-label={`Nội dung tin nhắn ${index + 1}`}
                  value={message.text}
                  onChange={(event) => update(index, { text: event.target.value })}
                />
              </div>
            ))}
          </div>
          <button
            type="button"
            className="link-button"
            onClick={() => {
              onMessages([]);
              setProvider("");
            }}
          >
            Xoá và chụp lại
          </button>
        </>
      )}
      <div className="thread-meta">
        <span>
          {messages.length} tin nhắn · {messages.filter((m) => m.sender === "contact").length} tin của họ
        </span>
        <button type="button" className="link-button" onClick={() => onMessages(sampleThread)}>
          Dùng đoạn ví dụ
        </button>
      </div>
      <button className="cta danger" disabled={messages.length < 2} onClick={onAnalyze}>
        Kiểm tra đoạn trò chuyện
      </button>
      <InfoBox>
        Mã OTP xuất hiện ở bất kỳ tin nào đều được chặn ngay trên máy, không gửi đi đâu.
        Ảnh chỉ đi qua bộ nhớ rồi xoá. Tên người quen chỉ dùng để so với tên chủ tài khoản
        trong tin nhắn, không được lưu.
      </InfoBox>
    </section>
  );
}

const threadRiskCopy = {
  high: {
    hero: "danger-hero",
    pill: "NGUY CƠ CAO",
    title: "Có thể tài khoản đã bị chiếm",
    guidance: "Đừng chuyển tiền cho tới khi nghe được giọng họ.",
  },
  medium: {
    hero: "warning-hero",
    pill: "CẦN KIỂM TRA",
    title: "Nên xác minh trước khi chuyển",
    guidance: "Gọi trực tiếp cho người đó bằng số cũ.",
  },
  unknown: {
    hero: "neutral-hero",
    pill: "CHƯA ĐỦ DẤU HIỆU",
    title: "Chưa thấy dấu hiệu bất thường",
    guidance: "Kết quả này không có nghĩa là an toàn.",
  },
} as const;

function ThreadResult({
  analysis,
  onBack,
}: {
  analysis: AnalyzeThreadResponse;
  onBack: () => void;
}) {
  const copy = threadRiskCopy[analysis.risk];
  return (
    <section>
      <div className={`risk-hero ${copy.hero}`}>
        <BackButton onClick={onBack} label="Quay lại" />
        <span className="hero-pill">{copy.pill}</span>
        <h1>{copy.title}</h1>
        <p><strong>{copy.guidance}</strong></p>
      </div>
      <div className="page result-body">
        <div className="source-card">
          <span>LUỒNG</span>
          <p>
            So trên {analysis.baseline_messages} tin nhắn cũ của người này
            {analysis.style_distance !== null &&
              ` · độ lệch cách nhắn tin ${(analysis.style_distance * 100).toFixed(0)}%`}
          </p>
        </div>
        {analysis.insufficient_history && (
          <div className="deep-check">
            <h2>Chưa đủ tin nhắn cũ để so</h2>
            <p>
              Máy cần ít nhất 3 tin nhắn cũ của người này trước lúc họ hỏi tiền thì mới
              so được cách nhắn tin. Bác dán thêm đoạn cũ hơn rồi kiểm tra lại.
            </p>
          </div>
        )}
        <h2>Dấu hiệu tìm thấy trong cả đoạn</h2>
        {analysis.thread_signals.length ? (
          <div className="signal-list">
            {analysis.thread_signals.map((signal) => (
              <article className="signal hit" key={signal.code}>
                <span className="signal-mark">!</span>
                <div>
                  <h3>{signal.label}</h3>
                  {signal.evidence && <blockquote>“{signal.evidence}”</blockquote>}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="input-status">Không tìm thấy dấu hiệu bất thường nào trong đoạn này.</p>
        )}
        <div className="recommendation">
          <h2>{analysis.questions.length ? "Bác hãy làm thế này" : "Kết luận"}</h2>
          {analysis.questions.map((question) => <p key={question}>{question}</p>)}
          {!analysis.questions.length && <p>{analysis.explanation}</p>}
          <small>{analysis.explanation}</small>
        </div>
        <div className="disclaimer">
          CHẮN so cách nhắn tin, không đọc được suy nghĩ. Cách chắc chắn nhất vẫn là
          <strong> nghe được giọng người đó</strong> trước khi chuyển tiền.
        </div>
        <button className="secondary-button" onClick={onBack}>Kiểm tra đoạn khác</button>
      </div>
    </section>
  );
}

function Lookup({
  kind,
  value,
  onKind,
  onValue,
  onBack,
  onLookup,
  error,
  onDismissError,
}: {
  kind: LookupKind;
  value: string;
  onKind: (kind: LookupKind) => void;
  onValue: (value: string) => void;
  onBack: () => void;
  onLookup: () => void;
  error: ErrorKey | null;
  onDismissError: () => void;
}) {
  const labels: Record<LookupKind, string> = { account: "Tài khoản", phone: "Điện thoại", url: "Đường link" };
  return (
    <section className="page">
      <BackButton onClick={onBack} />
      <h1>Tra cứu trước khi chuyển</h1>
      <p className="page-lead">Xem cộng đồng đã từng báo cáo thông tin này chưa.</p>
      {(error === "offline" || error === "backend" || error === "lookupInvalid") && (
        <ErrorBox error={error} onClose={onDismissError} onAction={onDismissError} />
      )}
      <div className="pills">
        {(Object.keys(labels) as LookupKind[]).map((item) => <button key={item} className={kind === item ? "pill active" : "pill"} onClick={() => onKind(item)}>{labels[item]}</button>)}
      </div>
      <label className="field-label" htmlFor="lookup">{labels[kind]} cần tra</label>
      <input id="lookup" value={value} onChange={(event) => onValue(event.target.value)} placeholder={kind === "account" ? "Nhập số tài khoản" : "Nhập thông tin"} />
      <button className="cta" disabled={!value.trim()} onClick={onLookup}>Tra cứu báo cáo</button>
      <InfoBox>Máy biến thông tin thành mã băm và chỉ gửi 5 ký tự đầu. Hệ thống không biết bác đang tra cứu gì.</InfoBox>
    </section>
  );
}

/**
 * Where a hit came from decides what the screen is allowed to claim. A row that
 * arrived from a data feed has not been "reported by people", and saying so
 * would put words in the mouths of users who never spoke.
 */
const lookupOrigin: Record<string, { title: string; unit: string; source: string }> = {
  community_reviewed: {
    title: "Đã có người báo cáo",
    unit: "lượt báo cáo",
    source: "Đây là báo cáo của người dùng khác, đã qua rà soát.",
  },
  verified: {
    title: "Đã được xác minh là lừa đảo",
    unit: "lượt ghi nhận",
    source: "Thông tin này đã được xác minh, không chỉ do người dùng báo.",
  },
  partner_verified: {
    title: "Đơn vị hợp tác đã xác nhận",
    unit: "lượt ghi nhận",
    source: "Thông tin do đơn vị hợp tác của CHAN xác nhận.",
  },
  feed_listed: {
    title: "Có trong danh sách cảnh báo",
    unit: "lượt ghi nhận",
    source:
      "Thông tin này nằm trong danh sách dữ liệu CHAN đang dùng — **không phải** báo cáo của người dùng.",
  },
};

function LookupResult({ result, onBack }: { result: LookupApiResult; onBack: () => void }) {
  const reportCount = result.match?.report_cnt ?? 0;
  const lastSeen = result.match?.last_seen
    ? new Date(result.match.last_seen).toLocaleDateString("vi-VN")
    : "Chưa rõ";
  const copy = lookupOrigin[result.match?.origin ?? ""] ?? lookupOrigin.feed_listed;
  return (
    <section>
      <div className="risk-hero warning-hero">
        <BackButton onClick={onBack} label="Tra cứu lại" />
        <span className="hero-pill">CẦN CẨN TRỌNG</span>
        <h1>{copy.title}</h1>
        <p>Hãy dừng lại và gọi người thân trước khi chuyển tiền.</p>
      </div>
      <div className="page result-body">
        <div className="stats"><div><b>{reportCount}</b><span>{copy.unit}</span></div><div><b>{lastSeen}</b><span>lần gần nhất</span></div></div>
        <div className="recommendation"><h2>Bác nên làm gì?</h2><p>Dừng giao dịch và gọi ngân hàng bằng số trên thẻ.</p><p>Hỏi người thân trước khi làm tiếp.</p></div>
        <div className="disclaimer">
          {copy.source.replace(/\*\*/g, "")} Đây không phải kết luận chính thức.
          Không có báo cáo <strong>không có nghĩa là an toàn</strong>.
        </div>
        <button className="secondary-button" onClick={onBack}>Tra cứu thông tin khác</button>
      </div>
    </section>
  );
}

function ClearLookupResult({ result, onBack }: { result: LookupApiResult; onBack: () => void }) {
  const kindLabel = result.kind === "phone" ? "SỐ ĐIỆN THOẠI" : result.kind === "account" ? "TÀI KHOẢN" : "ĐƯỜNG LINK";
  return (
    <section className="page clear-result">
      <BackButton onClick={onBack} label="Tra cứu lại" />
      <div className="neutral-status" aria-hidden="true">–</div>
      <p className="eyebrow">KẾT QUẢ TRA CỨU {kindLabel}</p>
      <h1>{result.noMatchMessage}</h1>
      <p className="clear-number">{result.displayValue}</p>
      <div className="validity-card">
        <span className="validity-mark">✓</span>
        <div>
          <h2>Thông tin đúng định dạng</h2>
          <p>CHAN chưa tìm thấy báo cáo nào khớp trong dữ liệu hiện có.</p>
        </div>
      </div>
      <div className="recommendation">
        <h2>Bác vẫn nên kiểm tra nội dung</h2>
        <p>Nghe xem họ có thúc ép chuyển tiền hoặc hỏi mã OTP không.</p>
        <p>Nếu họ tự nhận là tổ chức, hãy gọi lại số trên trang chính thức.</p>
      </div>
      <div className="disclaimer">
        Không có báo cáo <strong>không có nghĩa là an toàn tuyệt đối</strong>.
        Kẻ xấu có thể dùng một số điện thoại chưa từng bị báo cáo.
      </div>
      <button className="secondary-button" onClick={onBack}>Tra cứu số khác</button>
    </section>
  );
}

function Shield() {
  return (
    <section className="page">
      <h1>Bảo vệ & riêng tư</h1>
      <div className="shield-card"><Icon name="shield" size={40} /><div><h2>Hai lớp chạy trên máy</h2><p>Phần lớn tin nhắn được kiểm tra mà không gửi đi đâu.</p></div></div>
      <h2>Cam kết của CHAN</h2>
      <ul className="promise-list">
        <li>Không lưu nội dung tin nhắn.</li>
        <li>Không gửi mã OTP khỏi thiết bị.</li>
        <li>Không âm thầm báo cho người khác.</li>
        <li>Bác luôn có thể dừng chia sẻ.</li>
      </ul>
      <div className="guardian-card"><span className="avatar">L</span><div><strong>Độ · Con Trai</strong><small>Chỉ nhận cảnh báo mức cao, không thấy nội dung</small></div><button>Ngừng chia sẻ</button></div>
    </section>
  );
}

function Settings({
  theme,
  onTheme,
  simulations,
  onSimulation,
}: {
  theme: "light" | "dark";
  onTheme: (theme: "light" | "dark") => void;
  simulations: Simulations;
  onSimulation: (key: SimulationKey, enabled: boolean) => void;
}) {
  const labels: Record<SimulationKey, string> = {
    offline: "Mất mạng",
    mic: "Chặn quyền micro",
    micMissing: "Máy không có micro",
    ocr: "Ảnh không đọc được",
  };
  return (
    <section className="page">
      <h1>Cài đặt</h1>
      <div className="setting-row">
        <div><strong>Chế độ tối</strong><small>Dịu mắt hơn khi dùng vào ban đêm</small></div>
        <Switch checked={theme === "dark"} label="Chế độ tối" onChange={(checked) => onTheme(checked ? "dark" : "light")} />
      </div>
      <h2>Quyền truy cập</h2>
      <div className="permission-list">
        <p><Icon name="mic" /><span><strong>Micro</strong><small>Chỉ bật khi bác chủ động đọc tin nhắn</small></span></p>
        <p><Icon name="camera" /><span><strong>Ảnh</strong><small>Chỉ đọc ảnh bác tự chọn</small></span></p>
      </div>
      <h2>Thử tình huống lỗi</h2>
      <p className="settings-note">Các công tắc này chỉ dùng trong prototype để demo.</p>
      <div className="simulation-list">
        {(Object.keys(labels) as SimulationKey[]).map((key) => (
          <div className="setting-row compact" key={key}>
            <strong>{labels[key]}</strong>
            <Switch checked={simulations[key]} label={labels[key]} onChange={(checked) => onSimulation(key, checked)} />
          </div>
        ))}
      </div>
      <InfoBox>CHAN không giám sát bí mật. Mọi quyền đều cần bác chủ động đồng ý.</InfoBox>
    </section>
  );
}

function Switch({ checked, label, onChange }: { checked: boolean; label: string; onChange: (checked: boolean) => void }) {
  return <button type="button" role="switch" aria-checked={checked} aria-label={label} className="switch" onClick={() => onChange(!checked)}><span /></button>;
}

const errorCopy: Record<ErrorKey, { title: string; body: string; action: string }> = {
  mic: { title: "Không dùng được micro", body: "Bác có thể mở quyền micro, hoặc dán chữ thay vì nói.", action: "Mở quyền micro" },
  micMissing: { title: "Không tìm thấy micro", body: "Bác vẫn có thể gửi ảnh chụp hoặc dán nội dung tin nhắn.", action: "Gửi ảnh thay" },
  ocr: { title: "Không đọc được chữ trong ảnh", body: "Bác thử chụp lại cho rõ, hoặc dán chữ vào ô bên dưới.", action: "Chụp lại" },
  imageTooLarge: { title: "Ảnh lớn hơn 6 MB", body: "Bác hãy cắt bớt ảnh hoặc chọn ảnh có dung lượng nhỏ hơn.", action: "Chọn ảnh khác" },
  imageType: { title: "Định dạng ảnh chưa hỗ trợ", body: "Bác hãy chọn ảnh PNG, JPG hoặc WebP.", action: "Chọn ảnh khác" },
  ocrUnavailable: { title: "OCR chưa sẵn sàng", body: "Dịch vụ đọc ảnh chưa được cài trên máy chủ. Bác có thể dán chữ để kiểm tra.", action: "Dán chữ" },
  speechLocal: { title: "Trình duyệt chưa hỗ trợ đọc riêng tư", body: "CHAN chỉ bật giọng nói khi âm thanh được xử lý ngay trên máy. Bác hãy dùng Chrome mới hoặc gửi ảnh.", action: "Gửi ảnh thay" },
  speechLanguage: { title: "Chưa có gói giọng nói tiếng Việt", body: "Trình duyệt chưa tải xong dữ liệu tiếng Việt. Bác thử lại sau hoặc dán chữ.", action: "Thử lại" },
  offline: { title: "Mất mạng", body: "CHAN vẫn quét được quy tắc trên máy, nhưng chưa tra được danh sách tài khoản.", action: "Thử lại" },
  backend: { title: "Chưa kết nối được hệ thống", body: "Máy chủ CHAN chưa sẵn sàng. Bác thử lại sau ít phút.", action: "Thử lại" },
  lookupInvalid: { title: "Thông tin chưa đúng định dạng", body: "Bác kiểm tra lại số tài khoản, số điện thoại hoặc đường link.", action: "Sửa lại" },
  threadTooShort: { title: "Cần ít nhất hai tin nhắn", body: "Để so được cách nhắn tin trước và sau, bác dán thêm vài tin nhắn cũ của người đó.", action: "Dán thêm" },
};

function ErrorBox({ error, onAction, onClose }: { error: ErrorKey; onAction: () => void; onClose: () => void }) {
  const copy = errorCopy[error];
  return (
    <div className="error-box" role="alert">
      <div className="error-copy"><span><Icon name="alert" size={20} /></span><div><h2>{copy.title}</h2><p>{copy.body}</p></div></div>
      <div className="error-actions"><button onClick={onAction}>{copy.action}</button><button onClick={onClose}>Đóng</button></div>
    </div>
  );
}

function InfoBox({ children }: { children: React.ReactNode }) {
  return <div className="info-box"><Icon name="lock" /><p>{children}</p></div>;
}

function Navigation({ screen, onGo }: { screen: Screen; onGo: (screen: Screen) => void }) {
  const active = screen === "settings" ? "settings" : screen === "shield" ? "shield" : screen === "home" ? "home" : "check";
  return (
    <nav className="bottom-nav" aria-label="Điều hướng chính">
      <button className={active === "home" ? "active" : ""} onClick={() => onGo("home")}><Icon name="home" /><span>Trang chủ</span></button>
      <button className={active === "check" ? "active" : ""} onClick={() => onGo("input")}><Icon name="search" /><span>Kiểm tra</span></button>
      <button className={active === "shield" ? "active" : ""} onClick={() => onGo("shield")}><Icon name="shield" /><span>Bảo vệ</span></button>
      <button className={active === "settings" ? "active" : ""} onClick={() => onGo("settings")}><Icon name="settings" /><span>Cài đặt</span></button>
    </nav>
  );
}

function ShareSheet({ onCancel, onAccept }: { onCancel: () => void; onAccept: () => void }) {
  return (
    <div className="share-overlay" role="dialog" aria-modal="true" aria-labelledby="share-title">
      <div className="share-sheet"><span className="sheet-handle" /><div className="share-heading"><div className="brand-mark"><Icon name="shield" /></div><div><p className="eyebrow">CHIA SẺ TỪ ZALO</p><h2 id="share-title">Kiểm tra tin nhắn này?</h2></div></div><p>CHAN sẽ tìm dấu hiệu thúc ép. Nội dung không được lưu.</p><div className="sheet-actions"><button onClick={onCancel}>Huỷ</button><button className="confirm" onClick={onAccept}>Mở trong CHAN</button></div></div>
    </div>
  );
}
