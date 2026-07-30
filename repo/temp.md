Trợ lý chống lừa đảo cho người lớn tuổi / người ít kinh nghiệm số tôi thấy cái này hay, nhưng mô hình truy cập dữ liệu của người dùng kiểu gì mà chống
Câu hỏi này chính là chỗ ý tưởng sống hay chết. Mình tách ra 4 mức truy cập dữ liệu, từ dễ đến khó, kèm giới hạn thật.

Mức 0 — Người dùng chủ động gửi (pull)

Không cần quyền gì cả. Người dùng forward tin nhắn/ảnh chụp màn hình vào một Zalo Official Account hoặc dùng share sheet của Android/iOS.

Nghe có vẻ "yếu" nhưng thực ra rất mạnh, vì hành vi này đã tồn tại: người lớn tuổi vốn hay chụp màn hình gửi vào nhóm gia đình hỏi "cái này có thật không con?". Bạn chỉ đang thay người con bằng một bot trả lời trong 5 giây, 11h đêm. Zalo OA còn bỏ luôn rào cản cài app — thứ giết chết 90% sản phẩm nhắm vào người 55+.

Nhược điểm: chỉ bắt được khi người dùng đã nghi ngờ. Bỏ lọt đúng nhóm nguy hiểm nhất — người tin ngay.

Mức 1 — NotificationListenerService (Android)

Đọc nội dung thông báo từ SMS, Zalo, Messenger mà không cần quyền READ_SMS. Người dùng bật một lần trong Settings → Special app access. Đây là đường thực tế nhất để có real-time, và nó bắt được Zalo — nơi phần lớn lừa đảo ở VN thực sự diễn ra, còn SMS thì không.

Đánh đổi: Play scrutinize khá nặng phần disclosure & consent, và bạn phải cam kết không exfiltrate dữ liệu ngoài mục đích khai báo.

Mức 2 — READ_SMS / RECEIVE_SMS: gần như là cửa đóng

Mình vừa kiểm tra chính sách Play. Có đúng một exception tên "Anti-SMS phishing (smishing)", nhưng điều kiện là: bạn phải có thành tích đã bảo vệ người dùng ở quy mô đáng kể, được chứng minh qua báo cáo của analyst, kết quả benchmark test, ấn phẩm ngành hoặc nguồn tin cậy tương đương. Nghĩa là Kaspersky đủ điều kiện, team hackathon thì không. 
google

Có một cửa dễ hơn một chút: exception cho "Caller ID, spam detection và/hoặc spam blocking" không kèm yêu cầu track record đó. Nếu định thương mại hóa thật thì đóng gói sản phẩm theo hướng này khả thi hơn nhiều. 
google

Cho hackathon: cứ demo bằng debug build/sideload, nhưng phải nói rõ trong slide rằng bạn biết giới hạn này — đó là điểm cộng lớn, vì hầu hết team khác sẽ vẽ kiến trúc đọc hết SMS mà không biết Play cấm.

Mức 3 — AccessibilityService: đừng
Đọc được toàn bộ nội dung màn hình, nghe rất hấp dẫn. Nhưng đây đúng là vector mà malware banking thật đang dùng, Play có policy riêng rất chặt, và về mặt pitch nó phá hỏng câu chuyện của bạn: bạn đang xin quyền y hệt cái mà bạn nói là mình chống.

iOS thì sao

Gần như không có đường nào ngoài Mức 0. ILMessageFilterExtension chỉ lọc được tin từ người gửi lạ, chạy trong sandbox, và không chạm được Zalo. Nên định vị: Android = real-time, iOS = forward thủ công.

Hai thiết kế làm ý tưởng này khác hẳn phần còn lại

1. Mô hình người bảo hộ (guardian). Đừng bắt bà cài app. Người con cài và cấu hình, cảnh báo bay về điện thoại của người con: "Mẹ vừa nhận tin nhắn có dấu hiệu mạo danh công an, 21:40". Điều này giải quyết đúng thất bại lớn nhất của mọi sản phẩm nhắm người cao tuổi — người thụ hưởng không phải người có động lực cài đặt. Và nó có ràng buộc đạo đức rõ ràng bạn nên nói thẳng trong pitch: người được bảo vệ phải biết và đồng ý, không thì bạn vừa xây một app giám sát gia đình.

2. Đổi điểm chặn: kiểm tra số tài khoản thụ hưởng thay vì đọc tin nhắn. Đây là chỗ hay nhất. NHNN đã có hệ thống SIMO — đến tháng 4/2026 ghi nhận hơn 688 nghìn tài khoản nghi ngờ gian lận, và các tổ chức tín dụng dựa trên dữ liệu này để chặn giao dịch hoặc yêu cầu xác thực thêm. Về phía công khai, tinnhiemmang.vn (NCSC) và checkscam.vn cho tra cứu số tài khoản theo danh sách báo cáo từ người dùng. Người dùng chỉ nhập một số tài khoản — không giao dữ liệu cá nhân nào cho bạn cả, mà vẫn chặn được đúng khoảnh khắc mất tiền. 
An Ninh Thủ đô

Kết hợp cả hai mới là sản phẩm: AI đọc kịch bản để phát hiện biến thể mới, danh sách tài khoản chặn hành vi cuối cùng.