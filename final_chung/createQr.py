import tkinter as tk
from tkinter import filedialog, messagebox
import qrcode
import json
from PIL import ImageTk, Image
import os
import sys

# ===== Xử lý icon an toàn khi đóng gói .exe =====
def get_icon_path():
    try:
        if getattr(sys, 'frozen', False):  # Nếu chạy từ .exe
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        icon_file = os.path.join(base_path, "your_icon.ico")
        if os.path.exists(icon_file):
            return icon_file
    except:
        pass
    return None  # Không có icon

# ===== Hàm chọn video =====
def choose_video():
    video_path = filedialog.askopenfilename(
        title="Chọn tệp",
        filetypes=(("Video files", "*.mp4"), ("GIF files", "*.gif"), ("All files", "*.*"))
    )
    if video_path:
        video_entry.delete(0, tk.END)
        video_entry.insert(0, video_path)

# ===== Hàm tạo mã QR =====
def generate_qr():
    name = name_entry.get()
    gender = gender_var.get()
    position = position_entry.get()
    department = department_entry.get()
    delegate_type = delegate_type_entry.get()
    video_path = video_entry.get()

    if not name or not position or not department or not video_path or not delegate_type:
        messagebox.showwarning("Lỗi", "Vui lòng điền đầy đủ thông tin!")
        return

    data = {
    "Ten": name,
    "Gioi_Tinh": gender,
    "Chuc_Vu": position,
    "Don_Vi": department,
    "Loai_Dai_Bieu": delegate_type,
    "video_path": video_path
    }
    json_data = json.dumps(data, ensure_ascii=True)


    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(json_data)
    qr.make(fit=True)

    file_name = f"{name}.png"
    img = qr.make_image(fill='black', back_color='white')
    img.save(file_name)

    img_pil = Image.open(file_name).resize((200, 200))
    img_tk = ImageTk.PhotoImage(img_pil)
    qr_label.config(image=img_tk)
    qr_label.image = img_tk
    messagebox.showinfo("Thành công", f"Mã QR đã được tạo và lưu vào {file_name}!")

# ===== Giao diện =====
root = tk.Tk()
root.title("Ứng dụng tạo mã QR")

# Set icon an toàn (không lỗi nếu thiếu)
icon_path = get_icon_path()
if icon_path:
    try:
        root.iconbitmap(icon_path)
    except Exception as e:
        print(f"[!] Không thể dùng icon: {e}")

# ===== Các trường nhập liệu =====
tk.Label(root, text="Tên:").grid(row=0, column=0, padx=10, pady=5)
name_entry = tk.Entry(root, width=30)
name_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Giới tính:").grid(row=1, column=0, padx=10, pady=5)
gender_var = tk.StringVar(value="Nam")
tk.Radiobutton(root, text="Nam", variable=gender_var, value="Nam").grid(row=1, column=1, padx=10, pady=5, sticky="w")
tk.Radiobutton(root, text="Nữ", variable=gender_var, value="Nữ").grid(row=1, column=1, padx=10, pady=5, sticky="e")

tk.Label(root, text="Chức vụ:").grid(row=2, column=0, padx=10, pady=5)
position_entry = tk.Entry(root, width=30)
position_entry.grid(row=2, column=1, padx=10, pady=5)

tk.Label(root, text="Đơn vị:").grid(row=3, column=0, padx=10, pady=5)
department_entry = tk.Entry(root, width=30)
department_entry.grid(row=3, column=1, padx=10, pady=5)

tk.Label(root, text="Loại đại biểu:").grid(row=4, column=0, padx=10, pady=5)
delegate_type_entry = tk.Entry(root, width=30)
delegate_type_entry.grid(row=4, column=1, padx=10, pady=5)

tk.Label(root, text="Chọn video:").grid(row=5, column=0, padx=10, pady=5)
video_entry = tk.Entry(root, width=30)
video_entry.grid(row=5, column=1, padx=10, pady=5)
tk.Button(root, text="Chọn video", command=choose_video).grid(row=5, column=2, padx=10, pady=5)

# Nút tạo mã QR
generate_button = tk.Button(root, text="Tạo mã QR", command=generate_qr)
generate_button.grid(row=6, column=0, columnspan=3, padx=10, pady=20)

# Label hiển thị mã QR
qr_label = tk.Label(root)
qr_label.grid(row=7, column=0, columnspan=3, padx=10, pady=5)

# Chạy ứng dụng
root.mainloop()
