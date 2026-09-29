<div align="center">

# 🎵 Spotify Aesthetic Floating Lyrics Overlay

### *Real-Time Synced Lyrics Overlay with Dynamic Album Artwork Colors & Elegant Floating Cards*

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg?style=for-the-badge&logo=windows)](https://microsoft.com/windows)
[![Spotify Integration](https://img.shields.io/badge/Spotify-Native%20GSMTC-1DB954.svg?style=for-the-badge&logo=spotify)](https://spotify.com)
[![Zero API Key](https://img.shields.io/badge/Setup-Zero%20API%20Key-brightgreen.svg?style=for-the-badge)](#-zero-configuration-setup)

<br/>

<img src="assets/preview.png" alt="Spotify Aesthetic Floating Lyrics Overlay Preview" width="900" style="border-radius: 16px; box-shadow: 0 12px 36px rgba(0,0,0,0.4);" />

<br/>

**A clean, aesthetic desktop lyrics overlay designed for desktop recording and TikTok content creation.**  
Whenever you play a track on Spotify, each lyric line appears in its own separate frosted glass card that gently floats upwards while swaying naturally side to side. Musical notes drift softly in the background, and all visual accents, borders, and glows dynamically adapt in real-time to the color palette of the current album artwork.

</div>

---

## ✨ Features at a Glance

| Feature | Standard Lyrics Widgets | **Spotify Aesthetic Overlay** |
|:---|:---:|:---:|
| **Card Animation** | Static box or bouncing text | **Individual floating cards with natural sway** 🎈 |
| **Lyric Appearance**| Whole sentence pops up at once | **Real-time 1-by-1 character typewriter sync** ⌨️ |
| **Card Dissolve**   | Abrupt cut or plain fade | **Radiant white flash/blink peak before dissolve** 💡 |
| **Typography** | Generic monospace / sans | **High-legibility serif quotes & clean layouts** 🖋️ |
| **Color Theming** | Fixed dark or white mode | **Adaptive color extraction from album artwork** 🎨 |
| **Atmosphere Effect** | None | **Falling musical notes (`♪`, `♫`, `♬`, `♩`)** 🎵 |
| **API Key Setup** | Requires Spotify Developer account | **100% Zero API Keys Needed (Plug & Play)** 🔌 |
| **Sync Precision** | Often 2–3 seconds delayed | **Hardware timestamp extrapolation (Zero Delay)** ⚡ |
| **Desktop Integration**| Clunky windowed frame | **Transparent click-through desktop overlay** 🖥️ |
| **Content Creation** | Unsuitable for filming | **Optimized for TikTok & Reels screen recording** 📱 |

---

## 🌟 Core Highlights

- **🎈 Individual Rising Cards**: Each lyric line emerges as its own rounded frosted glass card at the bottom of the screen, floating upwards (`y -= speed`) with gentle horizontal sway (`Δx = sin(...) * amp`).
- **⌨️ Real-Time Typewriter Reveal**: Instead of popping up abruptly, each lyric line is revealed character-by-character in perfect real-time sync with the artist's vocal delivery.
- **💡 Radiant White Blink & Dissolve**: Upon reaching the upper screen threshold, the card pulses with a crisp, radiant white flash/blink before dissolving seamlessly into thin air (*just like in viral TikTok edits*).
- **🎨 Dynamic Album Cover Harmony**: Automatically samples dominant colors from the current album art to tint card backgrounds, glowing borders, dynamic island notch, and falling notes with smooth linear interpolation (*lerp crossfade*).
- **⚡ Zero-Delay Precision Synchronization**: Bypasses Windows GSMTC timeline lag through millisecond hardware timestamp extrapolation (`time.perf_counter()`), ensuring lyrics appear the instant the artist sings.
- **🎵 Ambient Falling Notes**: Graceful musical symbols (`♪`, `♫`, `♬`, `♩`) drift down across your desktop matching the album's mood.
- **📱 TikTok & Video Ready**: Designed specifically for clean screen recordings, aesthetic desktop captures, study/chill streams, and social media reels.
- **🖥️ Transparent Click-Through Overlay**: Press `T` to toggle click-through mode, allowing mouse interactions to pass directly through the overlay to your workspace, IDE, or game.
- **⌨️ Live Calibration**: Fine-tune lyric timing on the fly using `[` / `]` or arrow keys without ever restarting the app.

---

## ⌨️ Shortcuts & Hotkeys

All hotkeys function seamlessly inside the overlay and globally across Windows:

| Shortcut | Global Hotkey | Action | Description |
|:---|:---|:---|:---|
| `↑` / `]` | `Ctrl+Shift+↑` | **Advance Timing (+0.10s)** | Calibrate lyrics earlier if audio leads. |
| `↓` / `[` | `Ctrl+Shift+↓` | **Delay Timing (-0.10s)** | Calibrate lyrics later if text leads. |
| `0` | - | **Reset Timing** | Reset offset to default (+0.20s natural reading anticipation). |
| `K` | `Ctrl+Shift+K` | **Toggle Lyrics Mode** | Switch between synchronized lyrics and song metadata. |
| `T` | `Ctrl+Shift+T` | **Toggle Click-Through** | Let mouse clicks pass through overlay to underlying apps. |
| `F` | `Ctrl+Shift+F` | **Toggle Falling Notes** | Enable or disable the falling musical notes particle effect. |
| `Space` | - | **Play / Pause** | Toggle Spotify playback. |
| `Right` / `N` | - | **Next Track** | Skip to next track on Spotify. |
| `Left` / `P` | - | **Previous Track** | Return to previous track on Spotify. |
| `Esc` / `Q` | - | **Exit Overlay** | Close the overlay cleanly. |

---

## 🚀 Quick Start

### 1. Requirements
- Windows 10 or Windows 11
- Python 3.10+
- Official Spotify Desktop App

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/RobsHs/spotify-lyrics-overlay.git
cd spotify-lyrics-overlay

# Install dependencies
pip install -r requirements.txt
```

### 3. Launch
```bash
python song.py
```

*Open Spotify, play any song, and watch the floating aesthetic lyrics overlay seamlessly take over your desktop!*

---

## ⚙️ Architecture & Data Pipeline

```
┌──────────────────┐       Winsdk GSMTC       ┌────────────────────────┐
│  Spotify Desktop │ ───────────────────────► │ Windows Media Listener │
└──────────────────┘                          └───────────┬────────────┘
                                                          │ Title + Artist + Art
                                                          ▼
┌──────────────────┐        LRCLIB API        ┌────────────────────────┐
│ Local Disk Cache │ ◄──────────────────────► │  Lyrics Fetch Engine   │
└──────────────────┘                          └───────────┬────────────┘
                                                          │ Synced [mm:ss]
                                                          ▼
┌──────────────────┐    Pillow Color Thievery ┌────────────────────────┐
│ Dynamic Palette  │ ◄─────────────────────── │  Palette Lerp Engine   │
└──────────────────┘                          └───────────┬────────────┘
                                                          │ Interpolated Colors
                                                          ▼
┌──────────────────┐   Chroma-Key Win32 API   ┌────────────────────────┐
│ Windows Desktop  │ ◄─────────────────────── │  60 FPS Pygame Engine  │
│ Aesthetic Overlay│                          │ Rising Cards + Notes   │
└──────────────────┘                          └────────────────────────┘
```

---

## 📱 Content Creation & Social Media

If you record aesthetic desktop videos or TikTok reels with this overlay:
- Tag `@RobsHs` or mention `#SpotifyOverlay` so we can repost and feature your setup!
- Star ⭐ the repository on GitHub to support active open-source updates.

---

## 📄 License

Distributed under the [MIT License](LICENSE). Copyright © 2026 RobsHs.
