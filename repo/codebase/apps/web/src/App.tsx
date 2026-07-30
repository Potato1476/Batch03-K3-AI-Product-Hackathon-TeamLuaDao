import { useState } from "react";
import { Icon } from "./components/Icon";
import {
  lookupIndicator,
  type AnalyzeResponse,
  type LookupKind,
  type LookupResult as LookupApiResult,
} from "./api";
import { analyzeMessage } from "./engine";

type Screen = "home" | "input" | "loading" | "result" | "check" | "checkResult" | "checkClear" | "shield" | "settings";
type SimulationKey = "mic" | "micMissing" | "ocr" | "offline";
type ErrorKey = SimulationKey | "backend" | "lookupInvalid";
type Simulations = Record<SimulationKey, boolean>;

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

  const runAnalysis = async () => {
    if (simulations.offline) {
      setError("offline");
      return;
    }
    setError(null);
    go("loading");
    try {
      const result = await analyzeMessage(message);
      setAnalysis(result);
      go("result");
    } catch {
      setError("backend");
      go("input");
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
          {screen === "home" && <Home onInput={() => go("input")} onLookup={() => go("check")} />}
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
          {screen === "result" && analysis && <Result analysis={analysis} onBack={() => go("input")} />}
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

function Home({ onInput, onLookup }: { onInput: () => void; onLookup: () => void }) {
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
  return (
    <section className="page">
      <BackButton onClick={onBack} />
      <h1>Dán tin nhắn cần kiểm tra</h1>
      <p className="page-lead">CHAN sẽ chỉ ra những câu đang thúc ép hoặc thao túng bác.</p>
      {error && error !== "offline" && <ErrorBox error={error} onClose={() => onError(null)} onAction={() => onError(null)} />}
      <div className="mode-grid">
        <button className={mode === "text" ? "mode active" : "mode"} onClick={() => {
          setMode("text");
          if (simulations.micMissing) onError("micMissing");
          else if (simulations.mic) onError("mic");
        }}><Icon name="mic" /> Đọc hoặc dán chữ</button>
        <button className={mode === "image" ? "mode active" : "mode"} onClick={() => setMode("image")}><Icon name="camera" /> Gửi ảnh chụp</button>
      </div>
      {mode === "image" && <button className="upload-zone" onClick={() => simulations.ocr && onError("ocr")}><Icon name="camera" size={40} /><strong>Chọn ảnh chụp tin nhắn</strong><span>Máy sẽ đọc chữ ngay trên thiết bị.</span></button>}
      <label className="field-label" htmlFor="message">Nội dung tin nhắn</label>
      <textarea id="message" value={message} onChange={(event) => onMessage(event.target.value)} placeholder="Bác dán tin nhắn vào đây…" />
      <button className="cta danger" disabled={!message.trim()} onClick={onAnalyze}>Kiểm tra ngay</button>
      <InfoBox>CHAN không lưu nội dung bác nhập. Mã OTP sẽ không bao giờ rời khỏi máy.</InfoBox>
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
  tk_ca_nhan: "Yêu cầu chuyển vào tài khoản cá nhân",
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

function Result({ analysis, onBack }: { analysis: AnalyzeResponse; onBack: () => void }) {
  const copy = riskCopy[analysis.risk];
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
        <div className="source-card"><span>WEB</span><p>Kết quả từ CHAN · {analysis.engine_version}</p></div>
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

function LookupResult({ result, onBack }: { result: LookupApiResult; onBack: () => void }) {
  const reportCount = result.match?.report_cnt ?? 0;
  const lastSeen = result.match?.last_seen
    ? new Date(result.match.last_seen).toLocaleDateString("vi-VN")
    : "Chưa rõ";
  return (
    <section>
      <div className="risk-hero warning-hero">
        <BackButton onClick={onBack} label="Tra cứu lại" />
        <span className="hero-pill">CẦN CẨN TRỌNG</span>
        <h1>Đã có người báo cáo</h1>
        <p>Hãy dừng lại và gọi người thân trước khi chuyển tiền.</p>
      </div>
      <div className="page result-body">
        <div className="stats"><div><b>{reportCount}</b><span>lượt báo cáo</span></div><div><b>{lastSeen}</b><span>lần gần nhất</span></div></div>
        <div className="recommendation"><h2>Bác nên làm gì?</h2><p>Dừng giao dịch và gọi ngân hàng bằng số trên thẻ.</p><p>Hỏi người thân trước khi làm tiếp.</p></div>
        <div className="disclaimer">Đây là báo cáo của người dùng, không phải kết luận chính thức. Không có báo cáo <strong>không có nghĩa là an toàn</strong>.</div>
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
  offline: { title: "Mất mạng", body: "CHAN vẫn quét được quy tắc trên máy, nhưng chưa tra được danh sách tài khoản.", action: "Thử lại" },
  backend: { title: "Chưa kết nối được hệ thống", body: "Máy chủ CHAN chưa sẵn sàng. Bác thử lại sau ít phút.", action: "Thử lại" },
  lookupInvalid: { title: "Thông tin chưa đúng định dạng", body: "Bác kiểm tra lại số tài khoản, số điện thoại hoặc đường link.", action: "Sửa lại" },
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
