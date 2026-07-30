import { useEffect, useState } from "react";
import { Icon } from "./components/Icon";

type Screen = "home" | "input" | "loading" | "result" | "check" | "checkResult" | "checkClear" | "checkVerified" | "shield" | "settings";
type LookupKind = "account" | "phone" | "url";
type ErrorKey = "mic" | "micMissing" | "ocr" | "offline";
type Simulations = Record<ErrorKey, boolean>;

const sampleMessage =
  "Tôi là cán bộ công an. Bác phải chuyển tiền xác minh trước 17h hôm nay và không được nói với người nhà.";

const signals = [
  { label: "Mạo danh cơ quan chức năng", hit: true, evidence: "Tôi là cán bộ công an" },
  { label: "Doạ hậu quả pháp lý", hit: false },
  { label: "Ép gấp về thời gian", hit: true, evidence: "trước 17h hôm nay" },
  { label: "Yêu cầu giữ bí mật", hit: true, evidence: "không được nói với người nhà" },
  { label: "Đòi mã OTP", hit: false },
  { label: "Yêu cầu chuyển tiền", hit: true, evidence: "chuyển tiền xác minh" },
  { label: "Đường link giả mạo", hit: false },
  { label: "Hứa lợi ích bất thường", hit: false },
] as const;

export function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [message, setMessage] = useState("");
  const [lookupKind, setLookupKind] = useState<LookupKind>("account");
  const [lookupValue, setLookupValue] = useState("");
  const [shareOpen, setShareOpen] = useState(window.location.pathname === "/share");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [error, setError] = useState<ErrorKey | null>(null);
  const [simulations, setSimulations] = useState<Simulations>({
    mic: false,
    micMissing: false,
    ocr: false,
    offline: false,
  });

  useEffect(() => {
    if (screen !== "loading") return;
    const timer = window.setTimeout(() => setScreen("result"), 700);
    return () => window.clearTimeout(timer);
  }, [screen]);

  const go = (next: Screen) => {
    setScreen(next);
    const main = document.querySelector("main");
    if (main && "scrollTo" in main) {
      main.scrollTo({ top: 0 });
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
              onAnalyze={() => go("loading")}
              error={error}
              onError={setError}
              simulations={simulations}
            />
          )}
          {screen === "loading" && <Loading />}
          {screen === "result" && <Result onBack={() => go("input")} />}
          {screen === "check" && (
            <Lookup
              kind={lookupKind}
              value={lookupValue}
              onKind={setLookupKind}
              onValue={setLookupValue}
              onBack={() => go("home")}
              onLookup={() => {
                if (simulations.offline) {
                  setError("offline");
                  return;
                }
                const normalized = lookupValue.replace(/\D/g, "");
                if (lookupKind === "phone" && normalized === "0393066063") {
                  go("checkVerified");
                  return;
                }
                go(lookupKind === "phone" && normalized === "0982558619" ? "checkClear" : "checkResult");
              }}
              error={error}
              onDismissError={() => setError(null)}
            />
          )}
          {screen === "checkResult" && <LookupResult onBack={() => go("check")} />}
          {screen === "checkClear" && <ClearLookupResult onBack={() => go("check")} />}
          {screen === "checkVerified" && <VerifiedLookupResult onBack={() => go("check")} />}
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

function Result({ onBack }: { onBack: () => void }) {
  return (
    <section>
      <div className="risk-hero danger-hero">
        <BackButton onClick={onBack} label="Quay lại" />
        <span className="hero-pill">NGUY CƠ CAO</span>
        <h1>Nhiều dấu hiệu lừa đảo</h1>
        <p><strong>Đừng chuyển tiền. Đừng đọc mã OTP.</strong></p>
      </div>
      <div className="page result-body">
        <div className="source-card"><span>ZALO</span><p>Tin nhắn bác vừa gửi để kiểm tra</p></div>
        <h2>Trúng 4/8 dấu hiệu thao túng</h2>
        <div className="signal-list">
          {signals.map((signal) => (
            <article className={signal.hit ? "signal hit" : "signal miss"} key={signal.label}>
              <span className="signal-mark">{signal.hit ? "!" : "–"}</span>
              <div><h3>{signal.label}</h3>{signal.hit && <blockquote>“{signal.evidence}”</blockquote>}</div>
            </article>
          ))}
        </div>
        <div className="recommendation">
          <h2>Bác hãy hỏi lại họ</h2>
          <p>Tại sao tiền lại chuyển vào tài khoản cá nhân?</p>
          <p>Cho tôi số cơ quan để tôi tự gọi lại.</p>
          <small>Họ né trả lời và hối thúc — lúc đó nên cúp máy.</small>
        </div>
        <a className="hotline" href="tel:156"><Icon name="phone" /><span><strong>Tổng đài chống lừa đảo</strong><small>Gọi miễn phí</small></span><b>156</b></a>
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
      {error === "offline" && <ErrorBox error="offline" onClose={onDismissError} onAction={onDismissError} />}
      <div className="pills">
        {(Object.keys(labels) as LookupKind[]).map((item) => <button key={item} className={kind === item ? "pill active" : "pill"} onClick={() => onKind(item)}>{labels[item]}</button>)}
      </div>
      <label className="field-label" htmlFor="lookup">{labels[kind]} cần tra</label>
      <input id="lookup" value={value} onChange={(event) => onValue(event.target.value)} placeholder={kind === "account" ? "Nhập số tài khoản" : "Nhập thông tin"} />
      <button className="cta" disabled={!value.trim()} onClick={onLookup}>Tra cứu báo cáo</button>
      <InfoBox>Máy biến thông tin thành mã rút gọn và chỉ gửi 2 ký tự đầu. Hệ thống không biết bác đang tra cứu gì.</InfoBox>
    </section>
  );
}

function LookupResult({ onBack }: { onBack: () => void }) {
  return (
    <section>
      <div className="risk-hero warning-hero">
        <BackButton onClick={onBack} label="Tra cứu lại" />
        <span className="hero-pill">CẦN CẨN TRỌNG</span>
        <h1>Đã có người báo cáo</h1>
        <p>Hãy dừng lại và gọi người thân trước khi chuyển tiền.</p>
      </div>
      <div className="page result-body">
        <div className="stats"><div><b>12</b><span>lượt báo cáo</span></div><div><b>3 ngày</b><span>lần gần nhất</span></div></div>
        <div className="recommendation"><h2>Bác nên làm gì?</h2><p>Dừng giao dịch và gọi ngân hàng bằng số trên thẻ.</p><p>Hỏi người thân trước khi làm tiếp.</p></div>
        <div className="disclaimer">Đây là báo cáo của người dùng, không phải kết luận chính thức. Không có báo cáo <strong>không có nghĩa là an toàn</strong>.</div>
        <button className="secondary-button" onClick={onBack}>Tra cứu thông tin khác</button>
      </div>
    </section>
  );
}

function ClearLookupResult({ onBack }: { onBack: () => void }) {
  return (
    <section className="page clear-result">
      <BackButton onClick={onBack} label="Tra cứu lại" />
      <div className="neutral-status" aria-hidden="true">–</div>
      <p className="eyebrow">KẾT QUẢ TRA CỨU SỐ ĐIỆN THOẠI</p>
      <h1>Chưa có báo cáo về số này</h1>
      <p className="clear-number">0982 558 619</p>
      <div className="validity-card">
        <span className="validity-mark">✓</span>
        <div>
          <h2>Đúng định dạng số điện thoại</h2>
          <p>CHAN chưa tìm thấy báo cáo lừa đảo nào gắn với số này trong dữ liệu demo.</p>
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

function VerifiedLookupResult({ onBack }: { onBack: () => void }) {
  return (
    <section className="page verified-result">
      <BackButton onClick={onBack} label="Tra cứu lại" />
      <div className="verified-status" aria-label="Đã xác thực">✓</div>
      <p className="eyebrow">KẾT QUẢ TRA CỨU SỐ ĐIỆN THOẠI</p>
      <h1>Số điện thoại đã xác thực</h1>
      <p className="verified-number">0393 066 063</p>
      <div className="verified-card">
        <span className="verified-mark">✓</span>
        <div>
          <h2>Không phát hiện vấn đề</h2>
          <p>Số này được đánh dấu xác thực và chưa có báo cáo lừa đảo trong dữ liệu demo.</p>
        </div>
      </div>
      <div className="info-box verified-note">
        <Icon name="shield" />
        <p>Dấu tích xác nhận thông tin của số điện thoại. Nếu nội dung cuộc gọi đòi tiền hoặc mã OTP, bác vẫn nên dừng lại để kiểm tra.</p>
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
  onSimulation: (key: ErrorKey, enabled: boolean) => void;
}) {
  const labels: Record<ErrorKey, string> = {
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
        {(Object.keys(labels) as ErrorKey[]).map((key) => (
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
