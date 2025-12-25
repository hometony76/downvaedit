import streamlit as st
import yt_dlp
import os
import time
import shutil
import random
import glob
import subprocess
import concurrent.futures
import extra_streamlit_components as stx
from datetime import datetime, timedelta

# --- CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Tool Download Đa Năng - Thắng Nguyễn",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🛑 BẢO MẬT GIAO DIỆN (CHỐNG LỘ CODE)
# ==========================================
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# ==========================================
# 🔐 HỆ THỐNG QUẢN LÝ KEY (COOKIES)
# ==========================================
VALID_KEYS = [
    "NCTHANG01",
    "NCTHANG002",
    "NCTHANG0003",
    "NCTHANG00004",
    "NCTHANG000005",
]

# Khởi tạo Cookie Manager
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# Lấy cookie hiện tại (nếu có)
cookie_val = cookie_manager.get(cookie="user_key")

if 'da_dang_nhap' not in st.session_state:
    st.session_state.da_dang_nhap = False

# Logic Kiểm tra Đăng nhập
if cookie_val in VALID_KEYS:
    st.session_state.da_dang_nhap = True
    st.session_state.user_key = cookie_val
elif cookie_val is not None:
    cookie_manager.delete("user_key")
    st.session_state.da_dang_nhap = False

# Giao diện Đăng nhập
if not st.session_state.da_dang_nhap:
    st.title("🔒 HỆ THỐNG GIỚI HẠN TRUY CẬP")
    st.markdown("---")
    st.info("👋 Chào mừng! Vui lòng nhập Mã Kích Hoạt để tiếp tục.")
    
    col_log1, col_log2 = st.columns([2, 1])
    with col_log1:
        input_key = st.text_input("🔑 Nhập Key:", type="password")
    
    if st.button("🚀 Đăng Nhập"):
        if input_key in VALID_KEYS:
            expires_at = datetime.now() + timedelta(days=30)
            cookie_manager.set("user_key", input_key, expires_at=expires_at)
            
            st.session_state.da_dang_nhap = True
            st.session_state.user_key = input_key
            st.success(f"✅ Mã hợp lệ! Đang chuyển hướng...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("⛔ Mã không đúng hoặc đã bị Admin khóa!")
    
    st.stop() 

# ==========================================
# PHẦN TOOL CHÍNH
# ==========================================

with st.sidebar:
    st.success(f"👤 User: **{st.session_state.user_key}**")
    if st.button("Đăng xuất (Xóa Cookie)"):
        cookie_manager.delete("user_key")
        st.session_state.da_dang_nhap = False
        st.rerun()
    st.markdown("---")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: white; }
    [data-testid="stSidebar"] { background-color: rgba(0, 0, 0, 0.4); border-right: 1px solid rgba(255, 255, 255, 0.1); }
    .stButton > button { background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%); border: none; color: white; font-weight: bold; border-radius: 8px; transition: all 0.3s ease; }
    .stButton > button:hover { transform: scale(1.02); box-shadow: 0 4px 15px rgba(0, 210, 255, 0.4); }
    div[data-testid="stButton"] > button:active { border-color: white; }
    .log-box { background-color: rgba(0,0,0,0.6); padding: 10px; border-radius: 5px; font-family: monospace; color: #00ff00; height: 250px; overflow-y: scroll; border: 1px solid #444; font-size: 0.9em; }
    .stProgress > div > div > div > div { background-color: #00d2ff; }
</style>
""", unsafe_allow_html=True)

if 'log_messages' not in st.session_state: st.session_state.log_messages = []
if 'is_running' not in st.session_state: st.session_state.is_running = False

def log(message):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.log_messages.append(f"[{timestamp}] {message}")

def get_ffmpeg_path():
    if os.path.exists('ffmpeg.exe'): return os.path.abspath('ffmpeg.exe') 
    return 'ffmpeg'

def get_ffprobe_path():
    if os.path.exists('ffprobe.exe'): return os.path.abspath('ffprobe.exe')
    return 'ffprobe'

def clear_downloads(folder="downloads"):
    if os.path.exists(folder): shutil.rmtree(folder)
    os.makedirs(folder)

with st.sidebar:
    st.header("⚙️ CẤU HÌNH DOWNLOAD")
    st.subheader("🍪 Cookies (Bắt buộc)")
    uploaded_cookie = st.file_uploader("Upload cookies.txt", type=['txt'])
    
    cookie_path = None
    if uploaded_cookie:
        with open("cookies_temp.txt", "wb") as f: f.write(uploaded_cookie.getbuffer())
        cookie_path = "cookies_temp.txt"
        st.success("Đã nạp Cookies từ Upload!", icon="✅")
    elif os.path.exists("cookies.txt"):
        cookie_path = "cookies.txt"
        st.info("Đang dùng file 'cookies.txt' có sẵn.", icon="ℹ️")
    else:
        st.warning("Chưa có Cookies! Vui lòng Upload hoặc copy file vào thư mục.", icon="⚠️")
    
    st.markdown("---")
    st.subheader("🔢 Số lượng & Lọc")
    qty_option = st.selectbox("Số lượng tải:", ["50", "100", "150", "Full Kênh", "Tùy chỉnh"])
    max_videos = st.number_input("Nhập số:", min_value=1, value=5) if qty_option == "Tùy chỉnh" else (None if qty_option == "Full Kênh" else int(qty_option))
    
    dur_option = st.selectbox("Thời lượng <:", ["60 giây", "90 giây", "120 giây", "Full thời lượng"])
    match_filter_func = None
    if dur_option != "Full thời lượng":
        sec = int(dur_option.split(" ")[0])
        match_filter_func = yt_dlp.utils.match_filter_func(f"duration < {sec}")

st.title("Công cụ Download & Edit Hàng Loạt (Made by Thắng Nguyễn) 🚀")
st.markdown("Hệ thống tải video đa nền tảng & Edit tự động tối ưu hóa.")

tab1, tab2 = st.tabs(["📥 TẢI VIDEO (CONTROL MODE)", "✂️ EDIT HÀNG LOẠT (PRO)"])

# ================= TAB 1: DOWNLOAD (GIỮ NGUYÊN) =================
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1: url_input = st.text_input("🔗 Link Kênh/Video (TikTok/YouTube):", placeholder="https://www.tiktok.com/@username...")
    with col2:
        c1, c2 = st.columns(2)
        with c1: start_btn = st.button("▶️ BẮT ĐẦU", use_container_width=True)
        with c2: 
            if st.button("⏹️ STOP", key="stop_dl", use_container_width=True):
                st.session_state.is_running = False
                st.warning("Đang dừng và đóng gói dữ liệu...")

    st.markdown("### 📊 Log Hoạt Động")
    progress_bar = st.progress(0)
    status_text = st.empty()
    log_container = st.empty()
    
    def render_log():
        logs_html = "<br>".join(st.session_state.log_messages[-15:])
        log_container.markdown(f'<div class="log-box">{logs_html}</div>', unsafe_allow_html=True)

    if start_btn:
        if not url_input: st.error("Vui lòng nhập Link!")
        elif not cookie_path: st.error("Thiếu Cookie! Vui lòng nạp cookie để tránh lỗi.")
        else:
            st.session_state.is_running = True
            st.session_state.log_messages = []
            clear_downloads("downloads")
            
            std_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Referer': 'https://www.tiktok.com/',
            }

            try:
                log("🚀 Đang quét danh sách video...")
                render_log()
                
                ydl_scan_opts = {
                    'quiet': True, 'ignoreerrors': True, 'extract_flat': True,
                    'cookiefile': cookie_path,
                    'http_headers': std_headers,
                }
                if max_videos: ydl_scan_opts['playlistend'] = max_videos

                video_list = []
                with yt_dlp.YoutubeDL(ydl_scan_opts) as ydl:
                    info = ydl.extract_info(url_input, download=False)
                    if 'entries' in info: video_list = list(info['entries'])
                    else: video_list = [info]
                
                total_vids = len(video_list)
                log(f"✅ Tìm thấy {total_vids} video. Bắt đầu tải...")
                render_log()

                ydl_run_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'outtmpl': 'downloads/%(autonumber)s_%(title)s.%(ext)s',
                    'cookiefile': cookie_path,
                    'ffmpeg_location': get_ffmpeg_path(),
                    'quiet': True, 'no_warnings': True,
                    'http_headers': std_headers,
                    'socket_timeout': 30,
                }
                if match_filter_func: ydl_run_opts['match_filter'] = match_filter_func

                success_count = 0
                for i, entry in enumerate(video_list):
                    if not st.session_state.is_running: 
                        log("🛑 Đã dừng quy trình.")
                        break
                    
                    if i > 0 and i % 5 == 0:
                        log(f"💤 Nghỉ 15s bảo vệ Cookie...")
                        render_log()
                        time.sleep(15)
                    elif i > 0:
                        time.sleep(random.randint(2, 5))

                    title = entry.get('title', f'Video {i+1}')
                    status_text.text(f"Đang xử lý ({i+1}/{total_vids}): {title}")
                    
                    max_retries = 2
                    for attempt in range(max_retries):
                        try:
                            with yt_dlp.YoutubeDL(ydl_run_opts) as ydl:
                                ydl.download([entry['url']])
                            log(f"✅ Xong: {title}")
                            render_log()
                            success_count += 1
                            progress_bar.progress((i+1)/total_vids)
                            break
                        except Exception as e:
                            if attempt < max_retries - 1: time.sleep(5)
                            else: log(f"❌ Lỗi: {title}")

                log(f"🎉 Kết thúc phiên tải!")
                render_log()

            except Exception as e:
                st.error(f"Lỗi hệ thống: {e}")
            finally:
                st.session_state.is_running = False

    if os.path.exists("downloads") and len(os.listdir("downloads")) > 0:
        st.markdown("---")
        part_files = glob.glob("downloads/*.part")
        if part_files:
            for pf in part_files:
                try: os.remove(pf)
                except: pass
        
        files_ok = [f for f in os.listdir("downloads") if not f.endswith('.part')]
        if len(files_ok) > 0:
            st.success(f"✅ Đã sẵn sàng {len(files_ok)} video! (Kể cả khi bạn đã bấm Stop)")
            shutil.make_archive("Video_Download_ThanhPham", 'zip', "downloads")
            with open("Video_Download_ThanhPham.zip", "rb") as fp:
                st.download_button("📥 TẢI FILE ZIP NGAY", fp, "Video_Download_StopPoint.zip", "application/zip", use_container_width=True)
        else:
            st.info("Chưa có video nào hoàn chỉnh.")

# ================= TAB 2: EDIT (ĐÃ FIX LỖI WORKER + SYNTAX) =================
with tab2:
    st.header("✂️ STUDIO EDIT HÀNG LOẠT")
    st.info("💡 Lưu ý trên Cloud: Nên edit lần lượt 5-10 video để tránh sập Web.")
    
    c_in1, c_in2 = st.columns([1, 1])
    with c_in1: uploaded_videos = st.file_uploader("1️⃣ Chọn Video:", type=['mp4','mov','avi'], accept_multiple_files=True)
    with c_in2: uploaded_audios = st.file_uploader("2️⃣ Chọn Nhạc (Tùy chọn):", type=['mp3','wav'], accept_multiple_files=True)

    font_path = "fonts/font_mac_dinh.ttf"
    has_font = os.path.exists(font_path)
    if not has_font: st.warning("⚠️ Thiếu font! Vui lòng kiểm tra thư mục fonts/.")

    if uploaded_videos:
        st.markdown("---")
        st.subheader("⚙️ Cấu hình Chi tiết")
        
        c_row1_1, c_row1_2, c_row1_3 = st.columns(3)
        with c_row1_1: render_720 = st.checkbox("⚡ Render 720p (Nhanh)", value=True)
        with c_row1_2: enable_mirror = st.checkbox("Lật gương (Mirror)", True)
        with c_row1_3: enable_blur = st.checkbox("Blur Background", False)
        
        c_row2_1, c_row2_2, c_row2_3 = st.columns(3)
        with c_row2_1:
            speed_val = st.select_slider("Tốc độ", options=[0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.25, 1.3, 1.4, 1.5], value=1.0)
        with c_row2_2:
            brightness_val = st.select_slider("Độ sáng (+)", options=[0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5], value=0.0)
        with c_row2_3:
            mute_original = st.checkbox("Tắt âm gốc", True)
            audio_vol = 1.0
            if uploaded_audios: audio_vol = st.slider("Volume Nhạc nền", 0.1, 2.0, 1.0)

        st.markdown("---")
        c_row3_1, c_row3_2 = st.columns(2)
        with c_row3_1:
            st.markdown("**✂️ Cắt Video (Trimming)**")
            cut_start = st.number_input("Cắt đầu (giây):", min_value=0, value=0, step=1)
            cut_end = st.number_input("Cắt cuối (giây):", min_value=0, value=0, step=1)
            
        with c_row3_2:
            st.markdown("**🖼️ Chèn Logo**")
            uploaded_logo = st.file_uploader("Upload Logo", type=['png'])
            if uploaded_logo: st.caption("⚠️ LƯU Ý: Dùng ảnh PNG (Nền Trong Suốt) để đẹp nhất.")
            logo_pos = st.selectbox("Vị trí Logo:", ["Góc dưới phải", "Góc dưới trái", "Góc trên phải", "Góc trên trái"])

        st.markdown("---")
        st.markdown("**✍️ Chèn Text**")
        enable_text = st.checkbox("Kích hoạt Text", False, disabled=not has_font)
        txt_content = ""
        if enable_text:
            c_txt1, c_txt2, c_txt3 = st.columns([2, 1, 1])
            with c_txt1: txt_content = st.text_input("Nội dung:", "Follow Me")
            with c_txt2: txt_color = st.selectbox("Màu:", ["white", "yellow", "red", "black", "lime"])
            with c_txt3: txt_sz = st.selectbox("Size:", ["Vừa", "To", "Nhỏ"])
            txt_pos = st.selectbox("Vị trí Text:", ["Góc dưới", "Góc trên", "Giữa"])

        st.markdown("---")
        
        def process_single_video(file_idx, video_file, list_audios, logo_bytes):
            temp_in = None
            bg_music_path = None
            logo_path = None
            try:
                safe_name = "".join([c for c in video_file.name if c.isalnum() or c in (' ', '.', '_')]).strip()
                temp_in = f"temp_in_{file_idx}_{int(time.time())}_{safe_name}"
                with open(temp_in, "wb") as f: f.write(video_file.getvalue())
                
                out_name = f"Edit_{safe_name}"
                out_path = os.path.join("processed_videos", out_name)
                
                if list_audios:
                    music_file = random.choice(list_audios)
                    bg_music_path = f"temp_music_{file_idx}_{int(time.time())}.mp3"
                    with open(bg_music_path, "wb") as f: f.write(music_file.getvalue())
                
                if logo_bytes:
                    logo_path = f"temp_logo_{file_idx}_{int(time.time())}.png"
                    with open(logo_path, "wb") as f: f.write(logo_bytes)

                trim_args = ""
                if cut_start > 0 or cut_end > 0:
                    try:
                        cmd_prob = f'"{get_ffprobe_path()}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{temp_in}"'
                        res_prob = subprocess.run(cmd_prob, capture_output=True, text=True, shell=True)
                        total_dur = float(res_prob.stdout.strip())
                        new_dur = total_dur - cut_start - cut_end
                        if new_dur > 0: trim_args = f"-ss {cut_start} -t {new_dur}"
                    except: pass

                filters = []
                curr_v = "0:v"
                t_w, t_h = (720, 1280) if render_720 else (1080, 1920)
                
                if speed_val != 1.0:
                    filters.append(f"[{curr_v}]setpts={1/speed_val}*PTS[v_spd]")
                    curr_v = "v_spd"
                if enable_mirror:
                    filters.append(f"[{curr_v}]hflip[v_flip]")
                    curr_v = "v_flip"
                if brightness_val > 0:
                    filters.append(f"[{curr_v}]eq=brightness={brightness_val}[v_br]")
                    curr_v = "v_br"
                
                if enable_blur:
                    filters.append(f"[{curr_v}]split[bg][fg]")
                    filters.append(f"[bg]scale={t_w}:{t_h}:force_original_aspect_ratio=increase,crop={t_w}:{t_h},boxblur=20:10[bg_bl]")
                    filters.append(f"[fg]scale={t_w}:{t_h}:force_original_aspect_ratio=decrease[fg_sc]")
                    filters.append(f"[bg_bl][fg_sc]overlay=(W-w)/2:(H-h)/2[v_base]")
                    curr_v = "v_base"
                else:
                    if render_720:
                        filters.append(f"[{curr_v}]scale={t_w}:{t_h}:force_original_aspect_ratio=decrease,pad={t_w}:{t_h}:(ow-iw)/2:(oh-ih)/2[v_base]")
                        curr_v = "v_base"
                
                if logo_path:
                    logo_idx = 1 if not bg_music_path else 2
                    logo_w = int(t_w * 0.15)
                    filters.append(f"[{logo_idx}:v]scale={logo_w}:-1[logo_sc]")
                    pad = 20
                    if logo_pos == "Góc trên trái": overlay_c = f"{pad}:{pad}"
                    elif logo_pos == "Góc trên phải": overlay_c = f"W-w-{pad}:{pad}"
                    elif logo_pos == "Góc dưới trái": overlay_c = f"{pad}:H-h-{pad}"
                    else: overlay_c = f"W-w-{pad}:H-h-{pad}"
                    filters.append(f"[{curr_v}][logo_sc]overlay={overlay_c}[v_logo]")
                    curr_v = "v_logo"

                if enable_text and has_font:
                    fs = "h/20" if txt_sz=="Vừa" else ("h/10" if txt_sz=="To" else "h/30")
                    y = "h-th-100" if txt_pos=="Góc dưới" else ("100" if txt_pos=="Góc trên" else "(h-text_h)/2")
                    safe_txt = txt_content.replace(":", r"\:").replace("'", "")
                    filters.append(f"[{curr_v}]drawtext=fontfile='{font_path}':text='{safe_txt}':fontcolor={txt_color}:fontsize={fs}:x=(w-text_w)/2:y={y}[v_txt]")
                    curr_v = "v_txt"
                
                filters.append(f"[{curr_v}]null[v_out]")
                full_filter = ";".join(filters)

                inp_args = f'-i "{temp_in}"'
                if trim_args: inp_args = f'{trim_args} -i "{temp_in}"'
                if bg_music_path: inp_args += f' -stream_loop -1 -i "{bg_music_path}"'
                if logo_path: inp_args += f' -i "{logo_path}"'

                cmd_map = ""
                if mute_original:
                    if bg_music_path:
                        full_filter += f";[1:a]volume={audio_vol}[a_out]"
                        cmd_map = f'-map "[v_out]" -map "[a_out]"'
                    else:
                        cmd_map = f'-map "[v_out]" -an'
                else:
                    if speed_val != 1.0:
                         full_filter += f";[0:a]atempo={speed_val}[a_out]"
                         cmd_map = f'-map "[v_out]" -map "[a_out]"'
                    else:
                         cmd_map = f'-filter_complex "{full_filter}" -map "[v_out]" -map 0:a'
                         if speed_val == 1.0: cmd_map = f'-map "[v_out]" -map 0:a'

                cmd = f'"{get_ffmpeg_path()}" {inp_args} -filter_complex "{full_filter}" {cmd_map} -c:v libx264 -preset ultrafast -crf 28 -shortest -y "{out_path}"'
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return safe_name

            except Exception as e:
                return f"ERROR: {str(e)}"
            finally:
                try:
                    if temp_in and os.path.exists(temp_in): os.remove(temp_in)
                    if bg_music_path and os.path.exists(bg_music_path): os.remove(bg_music_path)
                    if logo_path and os.path.exists(logo_path): os.remove(logo_path)
                except: pass

        # --- ĐÂY LÀ CHỖ SỬA 2 LUỒNG ---
        workers = 2 # Đã fix cứng để không sập Cloud
        
        if st.button(f"🚀 BẮT ĐẦU RENDER (Chạy {workers} luồng)", use_container_width=True):
            st.session_state.is_running = True
            out_folder = "processed_videos"
            
            if not os.path.exists(out_folder):
                os.makedirs(out_folder)
            else:
                try:
                    for filename in os.listdir(out_folder):
                        file_path = os.path.join(out_folder, filename)
                        # --- ĐÂY LÀ CHỖ SỬA SYNTAX ERROR ---
                        try: 
                            if os.path.isfile(file_path): 
                                os.remove(file_path)
                        except: pass
                        # -----------------------------------
                except: pass

            prog_bar = st.progress(0)
            status_area = st.empty()
            result_area = st.empty()
            status_area.text("⏳ Đang khởi tạo...")
            
            completed_list = []
            total = len(uploaded_videos)
            logo_bytes = uploaded_logo.getvalue() if uploaded_logo else None

            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(process_single_video, i, vid, uploaded_audios, logo_bytes): vid.name for i, vid in enumerate(uploaded_videos)}
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    res = future.result()
                    if "ERROR" in res: st.toast(f"❌ Lỗi: {res}")
                    else: completed_list.append(res)
                    prog_bar.progress((i + 1) / total)
                    status_area.text(f"⏳ Đang xử lý: {i + 1}/{total} video...")
                    result_area.markdown(f"**✅ Đã xong:** {', '.join(completed_list[-3:])}...")

            st.success("🎉 Đã xong toàn bộ!")
            
            zip_name = "Video_Da_Edit"
            try: 
                if os.path.exists(f"{zip_name}.zip"): 
                    os.remove(f"{zip_name}.zip")
            except: pass
            
            shutil.make_archive(zip_name, 'zip', out_folder)
            with open(f"{zip_name}.zip", "rb") as fp:
                st.download_button("📥 TẢI ZIP VỀ", fp, "Edited_Pro.zip", "application/zip", use_container_width=True)

st.markdown("---")
st.markdown("<div style='text-align: center; color: #888;'>Developed by Thắng Nguyễn</div>", unsafe_allow_html=True)