import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";

describe("CHAN web flow", () => {
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
  });

  it("explains the privacy-preserving lookup before searching", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tài khoản, số điện thoại/i }));
    expect(screen.getByText(/chỉ gửi 2 ký tự đầu/i)).toBeInTheDocument();
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

    expect(screen.getByRole("heading", { name: "Chưa có báo cáo về số này" })).toBeInTheDocument();
    expect(screen.getByText("0982 558 619")).toBeInTheDocument();
    expect(screen.getByText(/Đúng định dạng số điện thoại/i)).toBeInTheDocument();
    expect(screen.getByText(/không có nghĩa là an toàn tuyệt đối/i)).toBeInTheDocument();
  });

  it("shows a green verified result for 0393066063", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /Tài khoản, số điện thoại/i }));
    await user.click(screen.getByRole("button", { name: "Điện thoại" }));
    await user.type(screen.getByLabelText("Điện thoại cần tra"), "0393066063");
    await user.click(screen.getByRole("button", { name: "Tra cứu báo cáo" }));

    expect(screen.getByRole("heading", { name: "Số điện thoại đã xác thực" })).toBeInTheDocument();
    expect(screen.getByText("0393 066 063")).toBeInTheDocument();
    expect(screen.getByText("Không phát hiện vấn đề")).toBeInTheDocument();
    expect(screen.getByLabelText("Đã xác thực")).toHaveTextContent("✓");
  });
});
