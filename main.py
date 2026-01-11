import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import re

# ------------------ File Selection ------------------
def select_file():
    file_path = filedialog.askopenfilename(
        title="Select a media file",
        filetypes=[(
            "All supported",
            "*.ts *.mkv *.avi *.mp4 *.mov *.flv *.gif *.mp3 *.wav *.jpg *.png"
        )]
    )
    entry_file.delete(0, tk.END)
    entry_file.insert(0, file_path)

# ------------------ Duration ------------------
def get_duration(input_file):
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_file
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return None

# ------------------ FFmpeg Worker ------------------
def run_ffmpeg(input_file, output_file, conversion_type, total_duration, gpu_mode):
    try:
        if gpu_mode == "CPU":
            video_encoder = "libx264"
            hwaccel = None
        elif gpu_mode == "NVIDIA":
            video_encoder = "h264_nvenc"
            hwaccel = "cuda"
        elif gpu_mode == "Intel":
            video_encoder = "h264_qsv"
            hwaccel = "qsv"
        elif gpu_mode == "AMD":
            video_encoder = "h264_amf"
            hwaccel = "dxva2"
        else:
            video_encoder = "libx264"
            hwaccel = None

        if conversion_type == "video":
            cmd = ["ffmpeg"]
            if hwaccel:
                cmd += ["-hwaccel", hwaccel]
            cmd += ["-i", input_file, "-c:v", video_encoder, "-c:a", "aac", output_file]

        elif conversion_type == "copy":
            cmd = ["ffmpeg", "-i", input_file, "-c", "copy", output_file]

        elif conversion_type == "audio":
            cmd = ["ffmpeg", "-i", input_file, "-q:a", "0", output_file]

        elif conversion_type == "gif_from_video":
            palette = "palette.png"
            subprocess.run([
                "ffmpeg", "-y", "-i", input_file,
                "-vf", "fps=30,scale=800:-1:flags=lanczos,palettegen",
                palette
            ], check=True)

            cmd = [
                "ffmpeg", "-y", "-i", input_file, "-i", palette,
                "-lavfi",
                "fps=30,scale=800:-1:flags=lanczos[x];[x][1:v]paletteuse",
                output_file
            ]

        elif conversion_type == "video_from_gif":
            cmd = [
                "ffmpeg", "-i", input_file,
                "-movflags", "faststart",
                "-pix_fmt", "yuv420p",
                output_file
            ]
        else:
            return

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            log_text.insert(tk.END, line)
            log_text.see(tk.END)

            match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if match and total_duration:
                h, m, s = match.groups()
                current = int(h) * 3600 + int(m) * 60 + float(s)
                percent = min(100, (current / total_duration) * 100)
                progress_bar["value"] = percent
                progress_label.config(
                    text=f"{percent:.1f}% ({int(current)}/{int(total_duration)}s)"
                )

        process.wait()

        if process.returncode == 0:
            progress_bar["value"] = 100
            progress_label.config(text="100% (Done)")
            messagebox.showinfo("Success", f"File converted:\n{output_file}")
        else:
            messagebox.showerror("Error", "FFmpeg failed")

    except Exception as e:
        messagebox.showerror("Error", str(e))

    convert_btn.config(state="normal")

# ------------------ Convert Trigger ------------------
def convert_file():
    input_file = entry_file.get()
    output_ext = output_format.get()
    mode = mode_var.get()
    gpu_mode = gpu_var.get()

    if not input_file:
        messagebox.showerror("Error", "Select a file first")
        return

    base, _ = os.path.splitext(input_file)
    output_file = f"{base}.{output_ext}"

    log_text.delete(1.0, tk.END)
    progress_bar["value"] = 0
    progress_label.config(text="0%")
    convert_btn.config(state="disabled")

    total_duration = get_duration(input_file)

    conversion_type = "video"
    if mode == "copy":
        conversion_type = "copy"
    elif output_ext in ["mp3", "wav"]:
        conversion_type = "audio"
    elif output_ext == "gif":
        conversion_type = "gif_from_video"
    elif input_file.lower().endswith(".gif"):
        conversion_type = "video_from_gif"

    threading.Thread(
        target=run_ffmpeg,
        args=(input_file, output_file, conversion_type, total_duration, gpu_mode),
        daemon=True
    ).start()

# ------------------ GUI ------------------
root = tk.Tk()
root.title("Universal Media Converter (GPU Ready)")
root.geometry("750x600")
root.eval("tk::PlaceWindow . center")

style = ttk.Style(root)
style.theme_use("clam")

frame = ttk.Frame(root, padding=20)
frame.pack(expand=True)

ttk.Label(frame, text="Select File:").grid(row=0, column=0, sticky="w")
entry_file = ttk.Entry(frame, width=50)
entry_file.grid(row=0, column=1, padx=5)
ttk.Button(frame, text="Browse", command=select_file).grid(row=0, column=2)

ttk.Label(frame, text="Convert to:").grid(row=1, column=0, sticky="w")
output_format = tk.StringVar(value="mp4")
formats = ["mp4", "avi", "mkv", "mov", "flv", "gif", "mp3", "wav"]
ttk.OptionMenu(frame, output_format, *formats).grid(row=1, column=1, sticky="w")

mode_var = tk.StringVar(value="reencode")
ttk.Radiobutton(frame, text="Fast Copy", variable=mode_var, value="copy").grid(row=2, column=0, columnspan=2, sticky="w")
ttk.Radiobutton(frame, text="Re-encode", variable=mode_var, value="reencode").grid(row=3, column=0, columnspan=2, sticky="w")

ttk.Label(frame, text="GPU Mode:").grid(row=4, column=0, sticky="w")
gpu_var = tk.StringVar(value="CPU")
ttk.OptionMenu(frame, gpu_var, "CPU", "CPU", "NVIDIA", "Intel", "AMD").grid(row=4, column=1, sticky="w")

convert_btn = ttk.Button(frame, text="Convert", command=convert_file)
convert_btn.grid(row=5, column=1, pady=15)

progress_bar = ttk.Progressbar(frame, length=500, mode="determinate")
progress_bar.grid(row=6, column=0, columnspan=3)

progress_label = ttk.Label(frame, text="0%")
progress_label.grid(row=7, column=0, columnspan=3)

ttk.Label(frame, text="Verbose Log:").grid(row=8, column=0, sticky="w")
log_text = tk.Text(frame, height=12, width=90, bg="#222", fg="#eee", font=("Consolas", 9))
log_text.grid(row=9, column=0, columnspan=3, pady=10)

root.mainloop()
