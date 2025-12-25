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

st.title("Tool Download & Edit Đa Năng 🚀")
tab1, tab2 = st.tabs(["📥 DOWNLOAD", "✂️ EDIT"])

# TAB 1: DOWNLOAD
with tab1:
    url = st.text_input("🔗 Link Kênh/Video:")
    c1, c2 = st.columns(2)
    start = c1.button("▶️ BẮT ĐẦU")
    stop = c2.button("⏹️ STOP")
    if stop: st.session_state.is_running = False
    
    log_area = st.empty()
    prog_bar = st.progress(0)
    
    if start and url and cookie_path:
        st.session_state.is_running = True
        st.session_state.log_messages = []
        clear_downloads()
        try:
            ydl_opts = {'quiet': True, 'cookiefile': cookie_path, 'extract_flat': True}
            if max_videos: ydl_opts['playlistend'] = max_videos
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                vids = list(info['entries']) if 'entries' in info else [info]
            
            log(f"Tìm thấy {len(vids)} video.")
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
                log(f"Đang tải: {v.get('title','Video')}")
                log_area.text("\n".join(st.session_state.log_messages[-5:]))
                try:
                    with yt_dlp.YoutubeDL(dl_opts) as ydl: ydl.download([v['url']])
                    prog_bar.progress((i+1)/len(vids))
                except: pass
        except Exception as e: st.error(str(e))
        st.session_state.is_running = False

    if os.path.exists("downloads") and os.listdir("downloads"):
        shutil.make_archive("Video_Download", 'zip', "downloads")
        with open("Video_Download.zip", "rb") as f:
            st.download_button("📥 Tải Zip", f, "Video.zip", "application/zip")

# TAB 2: EDIT
with tab2:
    st.info("💡 Server Free: Chạy tối đa 2 luồng để tránh sập.")
    vids = st.file_uploader("Chọn Video:", accept_multiple_files=True)
    audios = st.file_uploader("Chọn Nhạc:", accept_multiple_files=True)
    
    if vids:
        c1, c2, c3 = st.columns(3)
        render_720 = c1.checkbox("720p (Nhanh)", True)
        mirror = c2.checkbox("Lật gương", True)
        blur = c3.checkbox("Blur Background", False)
        
        speed = st.select_slider("Tốc độ", options=[0.8, 1.0, 1.25, 1.5], value=1.0)
        bright = st.slider("Độ sáng", 0.0, 0.5, 0.0)
        
        st.markdown("---")
        c_cut, c_logo = st.columns(2)
        cut_s = c_cut.number_input("Cắt đầu (s)", 0)
        cut_e = c_cut.number_input("Cắt cuối (s)", 0)
        logo = c_logo.file_uploader("Logo (PNG)", type=['png'])
        logo_pos = c_logo.selectbox("Vị trí", ["Góc dưới phải", "Góc trên trái"])
        
        has_font = os.path.exists("fonts/font_mac_dinh.ttf")
        use_txt = st.checkbox("Chèn Text", False, disabled=not has_font)
        txt_cont = st.text_input("Nội dung Text", "Follow Me") if use_txt else ""

        def process(idx, v_file, a_list, l_bytes):
            try:
                safe = "".join([c for c in v_file.name if c.isalnum()]).strip()
                t_in = f"t_in_{idx}_{safe}.mp4"
                with open(t_in, "wb") as f: f.write(v_file.getvalue())
                
                music = None
                if a_list:
                    music = f"t_m_{idx}.mp3"
                    with open(music, "wb") as f: f.write(random.choice(a_list).getvalue())
                
                l_path = None
                if l_bytes:
                    l_path = f"t_l_{idx}.png"
                    with open(l_path, "wb") as f: f.write(l_bytes)

                trim = ""
                if cut_s > 0 or cut_e > 0:
                    try:
                        res = subprocess.run(f'"{get_ffprobe_path()}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{t_in}"', capture_output=True, text=True, shell=True)
                        dur = float(res.stdout.strip()) - cut_s - cut_e
                        if dur > 0: trim = f"-ss {cut_s} -t {dur}"
                    except: pass
                
                w, h = (720, 1280) if render_720 else (1080, 1920)
                fil = []
                cv = "0:v"
                if speed != 1.0: fil.append(f"[{cv}]setpts={1/speed}*PTS[v1]"); cv="v1"
                if mirror: fil.append(f"[{cv}]hflip[v2]"); cv="v2"
                if bright > 0: fil.append(f"[{cv}]eq=brightness={bright}[v3]"); cv="v3"
                
                if blur:
                    fil.append(f"[{cv}]split[bg][fg];[bg]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=20:10[bg2];[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[fg2];[bg2][fg2]overlay=(W-w)/2:(H-h)/2[v4]")
                    cv="v4"
                else:
                    fil.append(f"[{cv}]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[v4]")
                    cv="v4"
                
                if l_path:
                    lid = 1 if not music else 2
                    fil.append(f"[{lid}:v]scale={int(w*0.15)}:-1[lsc];[{cv}][lsc]overlay=W-w-20:H-h-20[v5]")
                    cv="v5"

                if use_txt and has_font:
                    safe_txt = txt_cont.replace(":", r"\:").replace("'", "")
                    fil.append(f"[{cv}]drawtext=fontfile='fonts/font_mac_dinh.ttf':text='{safe_txt}':fontcolor=white:fontsize=h/30:x=(w-text_w)/2:y=h-th-100[v6]")
                    cv="v6"

                fil.append(f"[{cv}]null[vo]")
                
                inp = f'-i "{t_in}"'
                if trim: inp = f'{trim} -i "{t_in}"'
                if music: inp += f' -stream_loop -1 -i "{music}"'
                if l_path: inp += f' -i "{l_path}"'
                
                maps = f'-map "[vo]" -map 0:a'
                if music: maps = f'-map "[vo]" -map 1:a'

                out = os.path.join("processed_videos", f"Edit_{safe}.mp4")
                cmd = f'"{get_ffmpeg_path()}" {inp} -filter_complex "{";".join(fil)}" {maps} -c:v libx264 -preset ultrafast -y "{out}"'
                subprocess.run(cmd, shell=True)
                
                # Cleanup
                try: 
                    if os.path.exists(t_in): os.remove(t_in)
                    if music and os.path.exists(music): os.remove(music)
                    if l_path and os.path.exists(l_path): os.remove(l_path)
                except: pass
                
                return safe
            except Exception as e: return f"Error: {e}"

        # --- FIX QUAN TRỌNG: WORKERS = 2 ---
        workers = 2 
        
        if st.button(f"🚀 BẮT ĐẦU RENDER ({workers} luồng)"):
            if not os.path.exists("processed_videos"): os.makedirs("processed_videos")
            else:
                # Xóa file cũ (Cách an toàn)
                for f in os.listdir("processed_videos"):
                    try: os.remove(os.path.join("processed_videos", f))
                    except: pass

            prog = st.progress(0)
            st.text("Đang xử lý...")
            l_bytes = logo.getvalue() if logo else None
            
            with concurrent.futures.ThreadPoolExecutor(workers) as ex:
                fus = {ex.submit(process, i, v, audios, l_bytes): v for i, v in enumerate(vids)}
                for i, fu in enumerate(concurrent.futures.as_completed(fus)):
                    prog.progress((i+1)/len(vids))
            
            shutil.make_archive("Edited", 'zip', "processed_videos")
            with open("Edited.zip", "rb") as f:
                st.download_button("📥 TẢI VỀ", f, "Video_Edit.zip", "application/zip")

st.markdown("---")
st.caption("Dev by Thắng Nguyễn")