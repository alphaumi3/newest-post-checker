# Theo dõi bài đăng mới trang tuyển sinh sau đại học

Script Python chạy tự động trên GitHub Actions, kiểm tra định kỳ các trang thông báo tuyển sinh. Khi có bài mới sẽ gửi email.

Hiện đang theo dõi:

| Mã | Trường | Trang |
|----|--------|-------|
| `ump` | ĐH Y Dược TP.HCM | https://ump.edu.vn/tuyen-sinh-dao-tao/sau-dai-hoc/tuyen-sinh |
| `pnt` | ĐH Y khoa Phạm Ngọc Thạch | https://psdh.pnt.edu.vn/vi/tuyen-sinh-sau-dai-hoc |

## Cấu trúc repo

```
.
├── ump_watch.py                  # script chính
├── ump_seen.json                 # danh sách bài đã thấy (tự cập nhật)
├── README.md
└── .github/workflows/ump-watch.yml   # lịch chạy trên GitHub Actions
```

## Cài đặt ban đầu (chỉ làm một lần)

1. Tạo App Password cho Gmail (bật xác minh 2 bước, rồi vào Google Account > Security > App passwords).
2. Vào repo: **Settings > Secrets and variables > Actions > New repository secret**, thêm 3 secret:
   - `SMTP_USER`: Gmail dùng để gửi
   - `SMTP_PASS`: App Password (16 ký tự)
   - `MAIL_TO`: email nhận thông báo
3. Vào tab **Actions**, chọn **UMP watch**, bấm **Run workflow** để chạy thử.

Lần chạy đầu của mỗi trang chỉ lưu mốc các bài hiện có, không gửi mail. Mail chỉ được gửi khi có bài mới sau đó.

## Thêm một trang theo dõi mới

Mở `ump_watch.py`, tìm biến `SITES` ở đầu file và thêm một mục:

```python
{
    "key": "abc",                      # mã ngắn, không trùng mã khác
    "label": "ABC",                    # hiện trong tiêu đề mail: [ABC] ...
    "url": "https://example.edu.vn/thong-bao",
    "item": "ul.news > li",            # selector của MỖI bài trong danh sách
    "link": "h4 a",                    # selector thẻ <a> chứa tiêu đề và link (nằm trong item)
    "date": ".date",                   # selector ngày đăng (nằm trong item)
},
```

### Cách tìm các selector

1. Mở trang cần theo dõi bằng Chrome, nhấn **F12**.
2. Bấm biểu tượng mũi tên chọn phần tử (góc trái công cụ dev), rồi bấm vào **một bài trong danh sách**.
3. Nhìn cây HTML để tìm:
   - **item**: thẻ bao quanh toàn bộ một bài (thường là `li`, hoặc `div` có class như `widget`, `news-item`). Viết dạng `tên-thẻ.tên-class`, ví dụ `li.hightlight` hoặc `div.widget`.
   - **link**: thẻ `a` chứa tiêu đề bài, ví dụ `h4 a` hoặc `a.txt-title`.
   - **date**: thẻ chứa ngày đăng, ví dụ `.txt-date`.
4. Kiểm tra selector: ở tab **Console** gõ `document.querySelectorAll("ul.news > li").length`. Số trả về phải bằng số bài hiển thị trên trang.

Nếu chưa chắc, bạn có thể copy phần HTML của khu vực danh sách bài đăng gửi cho Claude để được viết giúp mục cấu hình.

### Sau khi thêm

1. Commit `ump_watch.py`.
2. Vào **Actions > UMP watch > Run workflow**.
3. Mở log bước **Kiểm tra bài mới**, phải thấy dòng `[ABC] Lần đầu: đã lưu N bài làm mốc.` với N đúng bằng số bài trên trang. Nếu thấy `Không đọc được bài nào` thì selector chưa đúng.

### Xóa một trang khỏi danh sách theo dõi

Xóa mục tương ứng trong `SITES` và commit. Có thể để nguyên phần dữ liệu cũ trong `ump_seen.json`, không ảnh hưởng gì.

## Chỉnh số phút giữa các lần kiểm tra

> Nếu bạn dùng cron-job.org để kích hoạt workflow (xem mục "Tùy chọn: dùng cron-job.org" bên dưới), hãy đổi chu kỳ trực tiếp trên cron-job.org. Phần dưới đây áp dụng cho lịch `schedule` của GitHub.

Mở `.github/workflows/ump-watch.yml`, sửa dòng `cron`:

```yaml
on:
  schedule:
    - cron: "7,22,37,52 * * * *"
```

Năm trường của cron là: `phút giờ ngày tháng thứ`. Một số mẫu dùng thường:

| Muốn chạy | Giá trị `cron` |
|-----------|----------------|
| Mỗi 15 phút | `7,22,37,52 * * * *` |
| Mỗi 30 phút | `7,37 * * * *` |
| Mỗi giờ | `7 * * * *` |
| Mỗi 2 giờ | `7 */2 * * *` |
| Mỗi 5 phút (mức tối thiểu) | `2,7,12,17,22,27,32,37,42,47,52,57 * * * *` |
| 8h sáng mỗi ngày (giờ Việt Nam) | `0 1 * * *` |

Lưu ý:

- **GitHub dùng giờ UTC**, giờ Việt Nam (UTC+7) sớm hơn 7 tiếng. Ví dụ 8h sáng Việt Nam là 1h UTC.
- **Khoảng cách tối thiểu là 5 phút.**
- **Tránh phút 00** (và các mốc tròn như 15, 30, 45). Đó là lúc GitHub quá tải nên lịch chạy hay bị trễ hoặc bỏ lượt. Vì vậy các mẫu trên dùng phút 7, 22, 37, 52.
- Lịch chạy của GitHub không chính xác tuyệt đối, có thể trễ vài phút.
- Sửa xong phải commit lên nhánh mặc định (thường là `main`), lịch mới mới có hiệu lực.

### Hạn mức miễn phí

- **Repo public**: chạy không giới hạn phút.
- **Repo private**: 2.000 phút/tháng. Chạy mỗi 15 phút sẽ vượt hạn mức, nên dùng mỗi 30 phút trở lên.

## Tùy chọn: dùng cron-job.org để kích hoạt workflow

Lịch `schedule` của GitHub chạy theo kiểu "cố gắng hết sức": có thể trễ, bỏ lượt, hoặc với repo mới đôi khi nhiều giờ không chạy lần nào. Nếu tab Actions không thấy các lần chạy "Scheduled", hoặc bạn muốn lịch đều đặn hơn, dùng [cron-job.org](https://cron-job.org) (miễn phí) để gọi GitHub bấm "Run workflow" thay bạn theo chu kỳ.

### Bước 1: tạo token trên GitHub

1. Vào GitHub > ảnh đại diện > **Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token**.
2. Đặt tên tùy ý, chọn thời hạn (tối đa 1 năm).
3. **Repository access**: *Only select repositories*, chọn repo `newest-post-checker`.
4. **Permissions > Repository permissions**: đặt **Actions** thành **Read and write**.
5. Bấm **Generate token** và **copy token ngay** (chỉ hiện một lần).

Không dán token vào code, README hay bất kỳ file nào trong repo.

### Bước 2: tạo job trên cron-job.org

1. Đăng ký tài khoản miễn phí, bấm **Create cronjob**.
2. **URL**:

   ```
   https://api.github.com/repos/alphaumi3/newest-post-checker/actions/workflows/ump-watch.yml/dispatches
   ```

3. **Schedule**: chọn chu kỳ mong muốn (ví dụ *Every 15 minutes*).
4. Mở phần **Advanced**:
   - **Request method**: `POST`
   - **Headers**, thêm 3 dòng:

     | Header | Giá trị |
     |--------|---------|
     | `Authorization` | `Bearer <token vừa copy>` |
     | `Accept` | `application/vnd.github+json` |
     | `X-GitHub-Api-Version` | `2022-11-28` |

   - **Request body**: `{"ref":"main"}`
5. Lưu, rồi bấm **Test run**. Kết quả đúng là mã **HTTP 204** (không có nội dung trả về). Vài giây sau, tab **Actions** sẽ có thêm một lần chạy mới.

Nếu đổi tên user/repo hoặc tên file workflow, sửa lại URL cho khớp.

### Lưu ý khi dùng cron-job.org

- Các lần chạy do cron-job.org kích hoạt hiển thị là "Manually run" (vì dùng `workflow_dispatch`), không phải "Scheduled". Hiệu quả giống nhau.
- **Đổi số phút**: sửa chu kỳ ngay trong job trên cron-job.org, không cần sửa file `.yml`.
- Có thể giữ nguyên khối `schedule` trong file `.yml`. Nếu cả hai cùng chạy, mục `concurrency` trong workflow sẽ xếp hàng chứ không chạy chồng, và script chỉ gửi mail cho bài chưa thấy nên không bị gửi trùng. Muốn gọn thì xóa khối `schedule`, chỉ giữ `workflow_dispatch`.
- **Token có hạn**: khi token hết hạn, job sẽ báo lỗi 401. Tạo token mới (Bước 1) rồi cập nhật lại header `Authorization` trên cron-job.org. Nên ghi chú ngày hết hạn để nhớ gia hạn.
- Repo private vẫn bị giới hạn 2.000 phút Actions mỗi tháng, dù kích hoạt bằng cách nào. Chạy mỗi 15 phút nên dùng repo public.
- Nếu Test run không trả về 204: `401` là token sai hoặc hết hạn; `403` là token thiếu quyền Actions (Read and write); `404` là sai URL hoặc token chưa được cấp cho repo này; `422` là sai nội dung body (kiểm tra `{"ref":"main"}` và tên nhánh).

## Xử lý sự cố

| Hiện tượng | Cách xử lý |
|------------|-----------|
| Không thấy mail | Kiểm tra thư mục spam; kiểm tra 3 secret; `SMTP_PASS` phải là App Password chứ không phải mật khẩu Gmail. Log sẽ ghi `Gửi email lỗi: ...` nếu gửi thất bại. |
| Log ghi `Không đọc được bài nào` | Trang có thể đã đổi giao diện hoặc chặn IP của GitHub. Kiểm tra lại selector bằng F12. |
| Log ghi `[XXX] Lỗi: ...` | Trang tạm thời lỗi hoặc chặn truy cập. Lần chạy sau thường tự ổn lại; các trang khác vẫn chạy bình thường. |
| Mail ngừng về nhiều ngày | Vào tab Actions xem workflow có bị GitHub tắt do repo lâu không hoạt động không, nếu có thì bấm **Enable workflow**. |
| Tab Actions không có lần chạy "Scheduled" nào | Lịch của GitHub có thể chưa kích hoạt hoặc bị trễ. Kiểm tra file `.yml` có khối `schedule` đúng, commit lại file một lần để đăng ký lại lịch, hoặc chuyển sang dùng cron-job.org (xem mục ở trên). |
| Muốn thử gửi mail | Mở `ump_seen.json`, xóa một khối bài trong mục của trang cần thử, commit, rồi chạy **Run workflow**. Bài bị xóa sẽ được coi là bài mới. |
| Lỗi `No file matched requirements.txt` | Xóa dòng `cache: pip` trong bước `setup-python` của file workflow. |

## Chạy thử trên máy

```bash
pip install requests beautifulsoup4
export SMTP_USER="you@gmail.com" SMTP_PASS="app-password" MAIL_TO="you@gmail.com"
python ump_watch.py            # chạy 1 lần
python ump_watch.py --loop 900 # chạy lặp mỗi 15 phút
```

Trên Windows PowerShell dùng `$env:SMTP_USER="..."` thay cho `export`.

## Bảo mật

Không ghi mật khẩu hoặc email vào code. Chỉ lưu trong GitHub Secrets. Nếu lỡ commit mật khẩu lên repo, hãy thu hồi App Password và tạo cái mới.
