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

# 🛑 BẢO MẬT GIAO DIỆN (CHỐNG LỘ CODE)
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# 🔐 HỆ THỐNG QUẢN LÝ KEY (COOKIES)
VALID_KEYS = [
    "NCTHANG01",
    "NCTHANG002",
    "NCTHANG0003",
    "NCTHANG00004",
    "NCTHANG000005",
]

def get_manager(): return stx.CookieManager()
cookie_manager = get_manager()
cookie_val = cookie_manager.get(cookie="user_key")

if 'da_dang_nhap' not in st.session_state: st.session_state.da_dang_nhap = False

if cookie_val in VALID_KEYS:
    st.session_state.da_dang_nhap = True
    st.session_state.user_key = cookie_val
elif cookie_val is not None:
    cookie_manager.delete("user_key")
    st.session_state.da_dang_nhap = False

if not st.session_state.da_dang_nhap:
    st.title("🔒 HỆ THỐNG GIỚI HẠN TRUY CẬP")
    st.info("👋 Chào mừng! Vui lòng nhập Mã Kích Hoạt để tiếp tục.")
    col1, col2 = st.columns([2, 1])
    with col1: input_key = st.text_input("🔑 Nhập Key:", type="password")
    if st.button("🚀 Đăng Nhập"):
        if input_key in VALID_KEYS:
            expires_at = datetime.now() + timedelta(days=30)
            cookie_manager.set("user_key", input_key, expires_at=expires_at)
            st.session_state.da_dang_nhap = True
            st.session_state.user_key = input_key
            st.rerun()
        else: st.error("⛔ Mã sai!")
    st.stop()

# --- PHẦN TOOL CHÍNH ---
with st.sidebar:
    st.success(f"👤 User: **{st.session_state.user_key}**")
    if st.button("Đăng xuất"):
        cookie_manager.delete("user_key")
        st.session_state.da_dang_nhap = False
        st.rerun()

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: white; }
    [data-testid="stSidebar"] { background-color: rgba(0, 0, 0, 0.4); border-right: 1px solid rgba(255, 255, 255, 0.1); }
    .stButton > button { background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%); border: none; color: white; font-weight: bold; border-radius: 8px; transition: all 0.3s ease; }
</style>
""", unsafe_allow_html=True)

if 'log_messages' not in st.session_state: st.session_state.log_messages = []
if 'is_running' not in st.session_state: st.session_state.is_running = False

def log(msg): st.session_state.log_messages.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
def get_ffmpeg_path(): return os.path.abspath('ffmpeg.exe') if os.path.exists('ffmpeg.exe') else 'ffmpeg'
def get_ffprobe_path(): return os.path.abspath('ffprobe.exe') if os.path.exists('ffprobe.exe') else 'ffprobe'
def clear_downloads(folder="downloads"):
    if os.path.exists(folder): shutil.rmtree(folder)
    os.makedirs(folder)

with st.sidebar:
    st.header("⚙️ CẤU HÌNH DOWNLOAD")
    uploaded_cookie = st.file_uploader("Upload cookies.txt", type=['txt'])
    cookie_path = "cookies_temp.txt" if uploaded_cookie else ("cookies.txt" if os.path.exists("cookies.txt") else None)
    if uploaded_cookie: 
        with open("cookies_temp.txt", "wb") as f: f.write(uploaded_cookie.getbuffer())
    
    qty_option = st.selectbox("Số lượng:", ["50", "100", "Full", "Tùy chỉnh"])
    max_videos = st.number_input("Nhập số:", 1, value=5) if qty_option == "Tùy chỉnh" else (None if qty_option == "Full" else int(qty_option))
    dur_option = st.selectbox("Thời lượng <:", ["60 giây", "90 giây", "Full"])
    match_filter = yt_dlp.utils.match_filter_func(f"duration < {int(dur_option.split()[0])}") if dur_option != "Full" else None

st.title("Công cụ Download & Edit Hàng Loạt (Made by Thắng Nguyễn) 🚀")
st.markdown("Hệ thống tải video đa nền tảng & Edit tự động tối ưu hóa.")

tab1, tab2 = st.tabs(["📥 TẢI VIDEO (CONTROL MODE)", "✂️ EDIT HÀNG LOẠT (PRO)"])

# ================= TAB 1: DOWNLOAD =================
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1: url_input = st.text_input("🔗 Link Kênh/Video (TikTok/YouTube):", placeholder="https://www.tiktok.com/@username...")
    with col2:
        c1, c2 = st.columns(2)
        start_btn = c1.button("▶️ BẮT ĐẦU", use_container_width=True)
        if c2.button("⏹️ STOP", key="stop_dl", use_container_width=True):
            st.session_state.is_running = False
    
    st.markdown("### 📊 Log Hoạt Động")
    progress_bar = st.progress(0)
    status_text = st.empty()
    log_container = st.empty()
    
    def render_log():
        logs_html = "<br>".join(st.session_state.log_messages[-15:])
        log_container.markdown(f'<div class="log-box">{logs_html}</div>', unsafe_allow_html=True)

    if start_btn and url_input and cookie_path:
        st.session_state.is_running = True
        st.session_state.log_messages = []
        clear_downloads()
        try:
            log("🚀 Đang quét video...")
            render_log()
            ydl_opts = {'quiet': True, 'cookiefile': cookie_path, 'extract_flat': True, 'ignoreerrors': True}
            if max_videos: ydl_opts['playlistend'] = max_videos
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_input, download=False)
                vids = list(info['entries']) if 'entries' in info else [info]
            
            log(f"✅ Tìm thấy {len(vids)} video.")
            render_log()
            
            dl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
                'outtmpl': 'downloads/%(autonumber)s_%(title)s.%(ext)s',
                'cookiefile': cookie_path,
                'ffmpeg_location': get_ffmpeg_path(),
                'quiet': True
            }
            if match_filter: dl_opts['match_filter'] = match_filter
            
            for i, v in enumerate(vids):
                if not st.session_state.is_running: break
                if i > 0 and i % 5 == 0: time.sleep(15)
                title = v.get('title','Video')
                status_text.text(f"Đang tải: {title}")
                try:
                    with yt_dlp.YoutubeDL(dl_opts) as ydl: ydl.download([v['url']])
                    log(f"✅ Xong: {title}")
                    render_log()
                    progress_bar.progress((i+1)/len(vids))
                except: log(f"❌ Lỗi: {title}")
        except Exception as e: st.error(str(e))
        st.session_state.is_running = False

    if os.path.exists("downloads") and os.listdir("downloads"):
        shutil.make_archive("Video_Download", 'zip', "downloads")
        with open("Video_Download.zip", "rb") as f:
            st.download_button("📥 TẢI ZIP NGAY", f, "Video_Download.zip", "application/zip", use_container_width=True)

# ================= TAB 2: EDIT (GIỮ NGUYÊN GIAO DIỆN + FIX WORKER) =================
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
        c_row1_1, c_row1_2, c_row1_3 = st.columns(3)
        with c_row1_1: render_720 = st.checkbox("⚡ Render 720p (Nhanh)", value=True)
        with c_row1_2: enable_mirror = st.checkbox("Lật gương (Mirror)", True)
        with c_row1_3: enable_blur = st.checkbox("Blur Background", False)
        
        c_row2_1, c_row2_2, c_row2_3 = st.columns(3)
        with c_row2_1: speed_val = st.select_slider("Tốc độ", options=[0.8, 1.0, 1.25, 1.5], value=1.0)
        with c_row2_2: brightness_val = st.slider("Độ sáng (+)", 0.0, 0.5, 0.0)
        with c_row2_3: 
            mute_original = st.checkbox("Tắt âm gốc", True)
            audio_vol = st.slider("Volume Nhạc", 0.1, 2.0, 1.0) if uploaded_audios else 1.0

        st.markdown("---")
        c_row3_1, c_row3_2 = st.columns(2)
        with c_row3_1:
            cut_start = st.number_input("Cắt đầu (s):", 0)
            cut_end = st.number_input("Cắt cuối (s):", 0)
        with c_row3_2:
            uploaded_logo = st.file_uploader("Upload Logo", type=['png'])
            logo_pos = st.selectbox("Vị trí Logo:", ["Góc dưới phải", "Góc trên trái"])

        st.markdown("---")
        enable_text = st.checkbox("Kích hoạt Text", False, disabled=not has_font)
        txt_content = st.text_input("Nội dung:", "Follow Me") if enable_text else ""
        if enable_text:
            c_txt2, c_txt3 = st.columns(2)
            txt_color = c_txt2.selectbox("Màu:", ["white", "yellow", "red", "black"])
            txt_pos = c_txt3.selectbox("Vị trí Text:", ["Góc dưới", "Góc trên"])

        st.markdown("---")
        
        def process_single_video(file_idx, video_file, list_audios, logo_bytes):
            try:
                # In ra log terminal để kiểm tra
                print(f"🎬 Bắt đầu xử lý: {video_file.name}") 
                
                safe_name = "".join([c for c in video_file.name if c.isalnum()]).strip()
                t_in = f"t_{file_idx}_{safe_name}.mp4"
                with open(t_in, "wb") as f: f.write(video_file.getvalue())
                
                music = None
                if list_audios:
                    music = f"m_{file_idx}.mp3"
                    with open(music, "wb") as f: f.write(random.choice(list_audios).getvalue())
                
                l_path = None
                if logo_bytes:
                    l_path = f"l_{file_idx}.png"
                    with open(l_path, "wb") as f: f.write(logo_bytes)

                trim = ""
                if cut_start > 0 or cut_end > 0:
                    try:
                        res = subprocess.run(f'"{get_ffprobe_path()}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{t_in}"', capture_output=True, text=True, shell=True)
                        dur = float(res.stdout.strip()) - cut_start - cut_end
                        if dur > 0: trim = f"-ss {cut_start} -t {dur}"
                    except: pass
                
                w, h = (720, 1280) if render_720 else (1080, 1920)
                fil = []
                cv = "0:v"
                if speed_val != 1.0: fil.append(f"[{cv}]setpts={1/speed_val}*PTS[v1]"); cv="v1"
                if enable_mirror: fil.append(f"[{cv}]hflip[v2]"); cv="v2"
                if brightness_val > 0: fil.append(f"[{cv}]eq=brightness={brightness_val}[v3]"); cv="v3"
                
                if enable_blur:
                    fil.append(f"[{cv}]split[bg][fg];[bg]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=20:10[bg2];[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[fg2];[bg2][fg2]overlay=(W-w)/2:(H-h)/2[v4]")
                    cv="v4"
                else:
                    fil.append(f"[{cv}]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[v4]")
                    cv="v4"
                
                if l_path:
                    lid = 1 if not music else 2
                    fil.append(f"[{lid}:v]scale={int(w*0.15)}:-1[lsc];[{cv}][lsc]overlay=W-w-20:H-h-20[v5]")
                    cv="v5"

                if enable_text and has_font:
                    safe_txt = txt_content.replace(":", r"\:").replace("'", "")
                    y_pos = "h-th-100" if txt_pos=="Góc dưới" else "100"
                    fil.append(f"[{cv}]drawtext=fontfile='{font_path}':text='{safe_txt}':fontcolor={txt_color}:fontsize=h/30:x=(w-text_w)/2:y={y_pos}[v6]")
                    cv="v6"

                fil.append(f"[{cv}]null[vo]")
                
                inp = f'-i "{t_in}"'
                if trim: inp = f'{trim} -i "{t_in}"'
                if music: inp += f' -stream_loop -1 -i "{music}"'
                if l_path: inp += f' -i "{l_path}"'
                
                maps = f'-map "[vo]" -map 0:a'
                if music: maps = f'-map "[vo]" -map 1:a'

                out = os.path.join("processed_videos", f"Edit_{safe_name}.mp4")
                # BẬT LOG: Bỏ stderr=DEVNULL để nếu lỗi nó hiện ra bảng đen
                cmd = f'"{get_ffmpeg_path()}" {inp} -filter_complex "{";".join(fil)}" {maps} -c:v libx264 -preset ultrafast -y "{out}"'
                print(f"🛠️ Đang chạy lệnh: {cmd}") # In lệnh ra xem
                subprocess.run(cmd, shell=True) # Không chặn output nữa
                
                # Cleanup
                try: 
                    if os.path.exists(t_in): os.remove(t_in)
                    if music and os.path.exists(music): os.remove(music)
                    if l_path and os.path.exists(l_path): os.remove(l_path)
                except: pass
                
                print(f"✅ Xong video: {safe_name}")
                return safe_name
            except Exception as e: 
                print(f"❌ LỖI VIDEO {file_idx}: {e}")
                return f"Error: {e}"

        workers = 2 
        
        if st.button(f"🚀 BẮT ĐẦU RENDER (Chạy {workers} luồng)", use_container_width=True):
            st.session_state.is_running = True
            out_folder = "processed_videos"
            if not os.path.exists(out_folder): os.makedirs(out_folder)
            else:
                for f in os.listdir(out_folder):
                    try: os.remove(os.path.join(out_folder, f))
                    except: pass

            prog_bar = st.progress(0)
            status_area = st.empty()
            result_area = st.empty()
            # Đổi câu thông báo cho đỡ sốt ruột
            status_area.text("⏳ Đang xử lý... (Video đầu sẽ lâu, vui lòng chờ!)")
            
            completed_list = []
            l_bytes = uploaded_logo.getvalue() if uploaded_logo else None

            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(process_single_video, i, v, uploaded_audios, l_bytes): v for i, v in enumerate(uploaded_videos)}
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    res = future.result()
                    completed_list.append(res)
                    prog_bar.progress((i + 1) / len(uploaded_videos))
                    status_area.text(f"⏳ Đang xử lý: {i + 1}/{len(uploaded_videos)} video...")
                    result_area.markdown(f"**✅ Đã xong:** {', '.join([str(x) for x in completed_list[-3:]])}...")

            st.success("🎉 Đã xong toàn bộ!")
            shutil.make_archive("Edited", 'zip', "processed_videos")
            with open("Edited.zip", "rb") as f:
                st.download_button("📥 TẢI ZIP VỀ", f, "Video_Edit.zip", "application/zip", use_container_width=True)

st.markdown("---")
st.markdown("<div style='text-align: center; color: #888;'>Developed by Thắng Nguyễn</div>", unsafe_allow_html=True)