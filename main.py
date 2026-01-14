import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import re

# ------------------ Globals ------------------
ffmpeg_process = None
cancel_requested = False

# ------------------ File Selection ------------------
def select_file():
    file_path = filedialog.askopenfilename(
        title="Select a media file",
        filetypes=[("All supported", "*.mp4 *.mkv *.mov *.avi *.flv *.gif *.mp3 *.wav")]
    )
    entry_file.delete(0, tk.END)
    entry_file.insert(0, file_path)

# ------------------ Duration ------------------
def get_duration(input_file):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             input_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return None

# ------------------ Cancel ------------------
def cancel_conversion():
    global cancel_requested, ffmpeg_process
    cancel_requested = True
    if ffmpeg_process and ffmpeg_process.poll() is None:
        ffmpeg_process.terminate()

# ------------------ FFmpeg Worker ------------------
def run_ffmpeg(input_file, output_file, conversion_type, total_duration, gpu_mode):
    global ffmpeg_process, cancel_requested
    cancel_requested = False

    try:
        # -------- VIDEO --------
        if conversion_type == "video":
            encoder = "libx264" if gpu_mode != "NVIDIA" else "h264_nvenc"
            cmd = [
                "ffmpeg", "-y",
                "-i", input_file,
                "-pix_fmt", "yuv420p",
                "-c:v", encoder,
                "-c:a", "aac",
                output_file
            ]

        # -------- AUDIO --------
        elif conversion_type == "audio":
            cmd = ["ffmpeg", "-y", "-i", input_file, "-vn", "-q:a", "0", output_file]

        # -------- GIF (FIXED + AUTO ROTATION) --------
        elif conversion_type == "gif":
            palette = "palette.png"

            subprocess.run([
                "ffmpeg", "-y",
                "-i", input_file,
                "-vf", "fps=12,scale=720:-1:flags=lanczos,palettegen",
                "-frames:v", "1",
                "-update", "1",
                palette
            ], check=True)

            cmd = [
                "ffmpeg", "-y",
                "-i", input_file,
                "-i", palette,
                "-lavfi",
                "fps=12,scale=720:-1:flags=lanczos[x];[x][1:v]paletteuse",
                "-an",
                output_file
            ]
        else:
            return

        # -------- Run --------
        ffmpeg_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in ffmpeg_process.stdout:
            if cancel_requested:
                break

            log_text.insert(tk.END, line)
            log_text.see(tk.END)

            match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if match and total_duration:
                h, m, s = match.groups()
                current = int(h)*3600 + int(m)*60 + float(s)
                progress_bar["value"] = min(100, (current/total_duration)*100)

        if cancel_requested:
            ffmpeg_process.kill()
            progress_bar["value"] = 0
            progress_label.config(text="Cancelled")
            convert_btn.config(state="normal")
            return

        ffmpeg_process.wait()

        if ffmpeg_process.returncode != 0 and gpu_mode == "NVIDIA":
            messagebox.showwarning("NVENC Failed", "Falling back to CPU")
            run_ffmpeg(input_file, output_file, conversion_type, total_duration, "CPU")
            return

        progress_bar["value"] = 100
        progress_label.config(text="Done")
        messagebox.showinfo("Success", f"Saved:\n{output_file}")

    except Exception as e:
        messagebox.showerror("Error", str(e))

    convert_btn.config(state="normal")

# ------------------ Convert Trigger ------------------
def convert_file():
    input_file = entry_file.get()
    if not input_file:
        messagebox.showerror("Error", "Select a file first")
        return

    ext = output_format.get()
    output_file = os.path.splitext(input_file)[0] + "." + ext

    log_text.delete(1.0, tk.END)
    progress_bar["value"] = 0
    progress_label.config(text="0%")
    convert_btn.config(state="disabled")

    total_duration = get_duration(input_file)

    ctype = "gif" if ext == "gif" else "audio" if ext in ["mp3", "wav"] else "video"

    threading.Thread(
        target=run_ffmpeg,
        args=(input_file, output_file, ctype, total_duration, gpu_var.get()),
        daemon=True
    ).start()

# ------------------ GUI ------------------
root = tk.Tk()
root.title("Universal Media Converter")
root.geometry("560x380")
root.resizable(False, False)

style = ttk.Style(root)
style.theme_use("clam")
style.configure("green.Horizontal.TProgressbar", background="#2ecc71", thickness=18)

frame = ttk.Frame(root, padding=20)
frame.pack(fill="both", expand=True)
frame.columnconfigure(1, weight=1)

ttk.Label(frame, text="Input File").grid(row=0, column=0, sticky="w")
entry_file = ttk.Entry(frame)
entry_file.grid(row=0, column=1, sticky="ew", padx=8)
ttk.Button(frame, text="Browse", command=select_file).grid(row=0, column=2)

ttk.Label(frame, text="Output Format").grid(row=1, column=0, sticky="w", pady=10)
output_format = tk.StringVar(value="mp4")
ttk.OptionMenu(frame, output_format, "mp4", "mp4", "avi", "mkv", "mov", "flv", "gif", "mp3", "wav").grid(
    row=1, column=1, sticky="w"
)

ttk.Label(frame, text="GPU Mode").grid(row=2, column=0, sticky="w")
gpu_var = tk.StringVar(value="CPU")
ttk.OptionMenu(frame, gpu_var, "CPU", "CPU", "NVIDIA").grid(row=2, column=1, sticky="w")

btn_frame = ttk.Frame(frame)
btn_frame.grid(row=3, column=1, pady=15, sticky="w")

convert_btn = ttk.Button(btn_frame, text="Convert", width=16, command=convert_file)
convert_btn.pack(side="left", padx=(0, 10))

tk.Button(
    btn_frame, text="Cancel", width=16,
    bg="#e74c3c", fg="white",
    activebackground="#c0392b",
    command=cancel_conversion
).pack(side="left")

progress_bar = ttk.Progressbar(frame, style="green.Horizontal.TProgressbar")
progress_bar.grid(row=4, column=0, columnspan=3, sticky="ew")

progress_label = ttk.Label(frame, text="0%")
progress_label.grid(row=5, column=0, columnspan=3)

ttk.Label(frame, text="Verbose Log").grid(row=6, column=0, sticky="w")
log_text = tk.Text(frame, height=8, bg="#1e1e1e", fg="#dcdcdc", font=("Consolas", 9))
log_text.grid(row=7, column=0, columnspan=3, sticky="ew")

root.mainloop()
