<div align="center">

# 🎵 Spotify Rising Hacker Lyrics Overlay

### *Real-Time Floating Lyrics HUD with Dynamic Album Cover Color Adaptation*

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg?style=for-the-badge&logo=windows)](https://microsoft.com/windows)
[![Spotify Integration](https://img.shields.io/badge/Spotify-GSMTC%20Native-1DB954.svg?style=for-the-badge&logo=spotify)](https://spotify.com)

A futuristic, transparent desktop overlay for Windows. When playing music on Spotify, each lyric line spawns in its own tactical terminal card that gently floats upwards while swaying left and right, with cyber-matrix streams and card colors dynamically adapting to the album cover artwork.

</div>

---

## ⚡ Key Highlights

- **Rising Individual Cards**: Each sung lyric line spawns as its own tactical terminal card at the bottom of the screen and drifts smoothly upwards while swaying gently left and right.
- **Dynamic Color Quantization**: Extracts dominant hues, saturated neons, and ambient shades from the active Spotify album artwork to tint HUD cards and falling particles.
- **Cyber Matrix & Music Glyphs**: Digital matrix streams (`01`, `10`, `0x`, `λ`, `§`) intertwined with musical notes (`♪`, `♫`, `♬`, `♩`) falling from the top of the screen.
- **Zero-Delay Precision Sync**: Automatically compensates for Windows GSMTC timeline latency with high-resolution `time.perf_counter()` extrapolation.
- **Live Decryption Effect**: Lyrics rapidly resolve from scrambled hex bytes into readable text.
- **Integrated Audio Spectrum Equalizer**: Real-time pulsing 28-bar audio spectrum visualizer rendered directly onto each card.
- **Hardware-Accelerated Transparency**: Fullscreen borderless transparent overlay (`pygame.NOFRAME` + Win32 chroma-key) floating seamlessly over VS Code, games, browsers, or desktop wallpapers.

---

## 📸 Visual Architecture

```
  ┌─────────────────────────────────────────────────────────────┐
  │  ↓ ♪               ↓ 0x4F             ↓ ♫        ↓ 01       │  <-- Falling Matrix Rain
  │                                                             │
  │     ┌[LRC.DECODE // PID:0x5A] [01:32] [SYNC_ACTIVE]┐        │
  │     │ > "And the toughest part is that we both..." │        │  <-- Older Card (Fading out)
  │     │ ▂▃▅▆▇█▇▅▃                                    │        │
  │     └──────────────────────────────────────────────┘        │
  │                     ↑ floating upwards                      │
  │                                                             │
  │          ┌[LRC.DECODE // PID:0x6F] [01:38] [SYNC_ACTIVE]┐   │
  │          │ > "What happened to you"                     │   │  <-- Mid Card (Ascending)
  │          │ ▂▃▅▆▇█▇▅▃                                    │   │
  │          └──────────────────────────────────────────────┘   │
  │                          ↑ floating upwards                 │
  │                                                             │
  │     ┌[LRC.DECODE // PID:0x7B] [01:42] [SYNC_ACTIVE]┐        │
  │     │ > "Merry Christmas, please don't call" █     │        │  <-- Newest Active Card
  │     │ ▂▃▅▆▇█▇▅▃                                    │        │      (Bright & In Focus)
  │     │ [🖼️] BLEACHERS // MERRY CHRISTMAS // #DC1E14 │        │
  │     └──────────────────────────────────────────────┘        │
  └─────────────────────────────────────────────────────────────┘
```

---

## ⌨️ Controls & Hotkeys

All hotkeys work both inside the application and globally across Windows:

| Hotkey | Global Shortcut | Action | Description |
|---|---|---|---|
| `↑` / `]` | `Ctrl+Shift+↑` | **Advance Lyrics (+0.10s)** | Calibrate lyrics to appear earlier if audio leads. |
| `↓` / `[` | `Ctrl+Shift+↓` | **Delay Lyrics (-0.10s)** | Calibrate lyrics to appear later if text leads. |
| `0` | - | **Reset Calibration** | Reset sync offset to default (+0.25s vocal anticipation). |
| `K` | `Ctrl+Shift+K` | **Toggle Karaoke Mode** | Switch between real-time synced lyrics and track metadata. |
| `T` | `Ctrl+Shift+T` | **Toggle Click-Through** | Enable click-through mode to interact with windows behind. |
| `F` | `Ctrl+Shift+F` | **Toggle Falling Stream** | Toggle digital matrix rain and musical note particles. |
| `G` | `Ctrl+Shift+G` | **Toggle CRT Scanlines** | Toggle subtle terminal monitor scanlines on cards. |
| `Space` | - | **Play / Pause** | Toggle Spotify playback. |
| `Right` / `N` | - | **Next Track** | Skip to next track on Spotify. |
| `Left` / `P` | - | **Previous Track** | Return to previous track. |
| `Esc` / `Q` | - | **Terminate Daemon** | Exit overlay cleanly. |

---

## 🚀 Getting Started

### Prerequisites

- **OS**: Windows 10 or Windows 11
- **Python**: 3.10, 3.11, or 3.12
- **Spotify**: Spotify Desktop application (or web player)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/RobsHs/spotify-lyrics-overlay.git
   cd spotify-lyrics-overlay
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the overlay**:
   ```bash
   python song.py
   ```

---

## ⚙️ How It Works

1. **Media Capture**: Uses `winsdk.windows.media.control` (`GlobalSystemMediaTransportControlsSessionManager`) to monitor active Spotify sessions, playback states, track info, and cover art thumbnails without requiring a Spotify Developer API key.
2. **Lyric Synchronization**: Queries [LRCLIB](https://lrclib.net/) for synchronized timestamped lyrics (`[mm:ss.xx]`) and caches results in `.lyrics_cache/` for instant subsequent retrieval.
3. **Palette Extraction**: Color quantization and HSV analysis extract dominant colors, contrast borders, and vibrant accent hues from album art.
4. **Physics & Animation Engine**: Runs at 60 FPS via Pygame with independent rising cards, sinusoidal left-right sway, alpha dissipation curves, and particle systems.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
