# Universal Media Converter (FFmpeg + Tkinter)

A lightweight desktop media converter built with **Python + Tkinter** using **FFmpeg**.  
Supports video, audio, and GIF conversion with GPU acceleration, automatic fallback, and a clean UI.

---

## ✨ Features

- 🎞 Convert video formats: `mp4, mkv, avi, mov, flv`
- 🎵 Extract audio: `mp3, wav`
- 🖼 Video → GIF (optimized palette pipeline)
- 🚀 GPU acceleration (NVIDIA NVENC) with **automatic CPU fallback**
- ⛔ Cancel button (instantly frees CPU/GPU)
- 📊 Progress bar with real-time FFmpeg logs
- 🔄 Correct orientation for mobile videos (Snapchat / phone HEVC)
- 🖥 Stable, optimized desktop UI

---

## 🧰 Requirements

- Python **3.9+**
- **FFmpeg** (must be available in system PATH)

Download FFmpeg (Windows):  
https://www.gyan.dev/ffmpeg/builds/

---

## ▶ How to Run

```bash
git clone <your-repo-url>
cd Media-Converter-Using-ffmpeg
python main.py
