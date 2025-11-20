# OPERATIONS.md

## 1. Mục đích
Tài liệu hướng dẫn quy trình **cập nhật giá – tồn kho**, **thêm sách mới**.

---

## 2. Cấu trúc dữ liệu liên quan
### Bảng `books`
- `id`: mã sách
- `title`: tiêu đề
- `authors`: danh sách tác giả
- `genres_primary`: thể loại chính
- `pages`: số trang
- `year`: năm xuất bản
- `publisher`: nhà xuất bản
- `short_summary`: tóm tắt
- `introduction`: giới thiệu dài
- `rating_avg`: điểm đánh giá trung bình
- `price_vnd`: giá bán
- `stocks`: lượng tồn trong kho
- `created_at`, `updated_at`: các mốc thời gian quản lý dữ liệu

---

## 3. Quy trình cập nhật giá & tồn kho

### 3.1 Nguồn dữ liệu
- File đầu vào: `price_stock.csv`
  - Gồm cột: `book_id`, `price_vnd`, `stock`.

### 3.2 Phạm vi ảnh hưởng
- Chỉ cập nhật **price_vnd** và **stock**.
- Không thay đổi các trường nội dung (title, authors, summary,...).

### 3.3 Các bước thực hiện
1. **Đọc file CSV** và kiểm tra dữ liệu:
   - Kiểm tra `book_id` có tồn tại trong hệ thống.
   - Kiểm tra giá trị phải là số hợp lệ (`price_vnd > 0`, `stock >= 0`).
2. **Đối chiếu dữ liệu**:
   - Nếu trùng `book_id` => cập nhật giá và tồn.
   - Nếu không tìm thấy => ghi vào file log `missing_books.log`.
3. **Cập nhật dữ liệu**:
   - Cập nhật lại `updated_at = NOW()`.
4. **Lưu kết quả**:
   - Xuất file `update_result.json` gồm:
     ```json
     {
       "success": [...],
       "fail": [...]
     }
     ```

---

## 4. Quy trình thêm sách mới

### 4.1 Nguồn dữ liệu
- File đầu vào: `new_books.csv` hoặc JSON kết quả từ crawler.
- Các trường bắt buộc:
  - `id`, `title`, `authors`, `genres_primary`, `pages`,
  - `year`, `publisher`, `short_summary`, `price_vnd`, `stocks`.

### 4.2 Các bước thực hiện
1. **Kiểm tra tính đầy đủ của trường dữ liệu**:
   - Thiếu trường => ghi log vào `invalid_books.log`.
2. **Kiểm tra trùng ID**:
   - Nếu ID đã tồn tại => **không thêm** => ghi log `duplicated_id.log`.
3. **Chuẩn hóa dữ liệu**:
   - Xóa khoảng trắng, UTF-8, chuẩn hóa newline.
4. **Thêm vào hệ thống**:
   - Ghi `created_at` và `updated_at`.
5. **Xuất báo cáo**:
   - File: `insert_result.json`.

---

## 5. Kiểm thử (QA Checklist)

### 5.1 Trước khi chạy batch update
- Kiểm tra định dạng CSV hợp lệ.
- Đảm bảo không có giá trị rỗng ở trường bắt buộc.
- File không chứa ký tự BOM.

### 5.2 Sau khi chạy
- Số lượng record cập nhật khớp với số lượng đầu vào.
- Kiểm tra ngẫu nhiên vài record xem `price_vnd` và `stock` đã cập nhật đúng chưa.
- Kiểm tra timestamp `updated_at` tăng đúng chưa.

---

## 6. Lịch trình vận hành
- **Cập nhật giá & tồn**: 1 lần/ngày.
- **Đồng bộ sách mới**: 1 lần/tuần hoặc theo yêu cầu sản phẩm.

---

## 7. Xử lý lỗi thường gặp

| Lỗi | Nguyên nhân | Cách xử lý |
|-----|-------------|------------|
| Missing book_id | Thu thập thiếu hoặc file đầu vào lỗi | Ghi log, bổ sung dữ liệu |
| Dữ liệu trùng ID | Nhập trùng sách | Kiểm tra pipeline nhập liệu |
| Giá hoặc tồn không hợp lệ | Dữ liệu đầu vào lỗi | Validate lại file CSV |



