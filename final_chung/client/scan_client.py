import cv2
import threading
import time
import json
import requests
import socket
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
import tkinter as tk
from tkinter import messagebox, simpledialog
from queue import Queue

# ==== Cấu hình chung ====
TOTAL_PEOPLE = 500
scan_delay = 1
last_scan_time = 0
scanned_qrs = set()
info_text = ""
info_expire_time = 0
running = False
cap = None
server_url = ""
qr_queue = Queue()
latest_frame = None

CAM_CAPTURE_WIDTH = 1920
CAM_CAPTURE_HEIGHT = 1080
CAM_DISPLAY_WIDTH = 960
CAM_DISPLAY_HEIGHT = 540

# ==== Tìm IP máy chủ tự động qua UDP broadcast ====
def discover_server_ip():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_socket.settimeout(3)
    try:
        udp_socket.sendto(b"DISCOVER_SERVER", ("<broadcast>", 9999))
        data, addr = udp_socket.recvfrom(1024)
        if data.decode() == "SERVER_IP_RESPONSE":
            print(f"[\u2713] \u0110\u00e3 t\u00ecm th\u1ea5y server t\u1ea1i {addr[0]}")
            return addr[0]
    except:
        return None
    return None

# ==== Gửi dữ liệu QR lên server ====
def process_qr_data(qr_data):
    global info_text, info_expire_time
    try:
        qr_info = json.loads(qr_data)
        ma_qr = qr_data.strip()
        if ma_qr in scanned_qrs:
            info_text = " QR \u0111\u00e3 \u0111\u01b0\u1ee3c qu\u00e9t tr\u01b0\u1edbc \u0111\u00f3!!!!"
            info_expire_time = time.time() + 3
            return

        payload = {
            "Ten": qr_info["Ten"],
            "Gioi_Tinh": qr_info["Gioi_Tinh"],
            "Chuc_Vu": qr_info["Chuc_Vu"],
            "Don_Vi": qr_info["Don_Vi"],
            "Loai_Dai_Bieu": qr_info["Loai_Dai_Bieu"],
            "Ma_QR": ma_qr,
            "video_path": qr_info.get("video_path", "")
        }

        response = requests.post(server_url, json=payload)
        if response.status_code == 200:
            res = response.json()
            if res["status"] == "success":
                scanned_qrs.add(ma_qr)
                stt = res["stt"]
                ten = qr_info["Ten"]
                info_text = f"✅ STT {stt}: {ten} – Người thứ {stt}/{TOTAL_PEOPLE}"
            elif res["status"] == "duplicate":
                info_text = " Mã đã điểm danh trước đó"
            else:
                info_text = " " + res["message"]
        else:
            info_text = " Lỗi kết nối tới server"
    except Exception as e:
        print("[Lỗi QR]:", e)
        info_text = " Lỗi dữ liệu QR"
    info_expire_time = time.time() + 3

# ==== Kiểm tra máy chủ từ chối hoặc ngắt kết nối ====
def check_if_disconnected():
    try:
        res = requests.get(server_url.replace("/scan", "/get_clients"))
        if res.status_code == 200:
            ip = socket.gethostbyname(socket.gethostname())
            data = res.json()
            if ip not in data.get("allowed", []):
                raise Exception("Bị từ chối kết nối từ máy chủ")
    except:
        global info_text, info_expire_time, running
        info_text = " Mất kết nối hoặc bị từ chối bởi máy chủ"
        info_expire_time = time.time() + 5
        running = False

# ==== Luồng 1: Đọc camera và phát hiện QR ====
def camera_reader():
    global last_scan_time, running, latest_frame
    detector = cv2.QRCodeDetector()
    while running:
        ret, frame = cap.read()
        if not ret:
            continue

        latest_frame = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.equalizeHist(gray)
        qr_data, bbox, _ = detector.detectAndDecode(enhanced)
        if qr_data:
            current_time = time.time()
            if current_time - last_scan_time >= scan_delay:
                if qr_data not in scanned_qrs:
                    qr_queue.put((qr_data, frame.copy()))
                last_scan_time = current_time
        time.sleep(0.01)

# ==== Luồng 2: Gửi dữ liệu QR lên server ====
def api_worker():
    global running
    while running:
        try:
            qr_data, _ = qr_queue.get(timeout=1)
            process_qr_data(qr_data)
            check_if_disconnected()
        except:
            pass

# ==== Luồng 3: Hiển thị video + overlay ====
def update_display_loop():
    global info_text, info_expire_time
    if not running:
        return

    if latest_frame is None:
        root.after(10, update_display_loop)
        return

    frame = latest_frame.copy()
    display_frame = cv2.resize(frame, (CAM_DISPLAY_WIDTH, CAM_DISPLAY_HEIGHT))
    black_bg = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)
    x_offset = (screen_width - CAM_DISPLAY_WIDTH) // 2
    y_offset = (screen_height - CAM_DISPLAY_HEIGHT) // 2
    black_bg[y_offset:y_offset+CAM_DISPLAY_HEIGHT, x_offset:x_offset+CAM_DISPLAY_WIDTH] = display_frame

    cv2_im_rgb = cv2.cvtColor(black_bg, cv2.COLOR_BGR2RGB)
    pil_im = Image.fromarray(cv2_im_rgb)
    draw = ImageDraw.Draw(pil_im)

    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    if info_text and time.time() < info_expire_time:
        w, h = pil_im.size
        text_bbox = draw.textbbox((0, 0), info_text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        draw.text((w - text_w - 30, h - text_h - 30), info_text, fill=(255, 0, 0), font=font)

    imgtk = ImageTk.PhotoImage(image=pil_im)
    video_label.imgtk = imgtk
    video_label.configure(image=imgtk)
    root.after(10, update_display_loop)

# ==== Bắt đầu quét ====
def start_scanning():
    global cap, running, server_url, latest_frame
    latest_frame = None

    ip = discover_server_ip()
    if not ip:
        ip = simpledialog.askstring("Không tìm thấy server", "Nhập IP server:")
        if not ip:
            return

    server_url = f"http://{ip}:8000/scan"
    try:
        res = requests.post(f"http://{ip}:8000/request_access")
        status = res.json().get("status")
        if status == "denied":
            print(" Máy chủ đã từ chối kết nối.")
            return
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không gửi được yêu cầu truy cập: {e}")
        return

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_CAPTURE_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_CAPTURE_HEIGHT)
    running = True

    threading.Thread(target=camera_reader, daemon=True).start()
    threading.Thread(target=api_worker, daemon=True).start()
    update_display_loop()

    messagebox.showinfo("Kết nối", f" Đã tìm thấy máy chủ tại {ip}")

# ==== Dừng quét ====
def stop_scanning():
    global running, cap
    running = False
    if cap:
        cap.release()
        cap = None
    video_label.configure(image=None)

# ==== Giao diện GUI ====
root = tk.Tk()
root.attributes('-fullscreen', True)
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

video_label = tk.Label(root)
video_label.pack(fill=tk.BOTH, expand=True)

root.bind("<Escape>", lambda e: (stop_scanning(), root.destroy()))
root.after(100, start_scanning)
root.mainloop()
