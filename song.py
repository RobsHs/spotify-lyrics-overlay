"""
Spotify Real-Time Synced Lyrics Overlay (Aesthetic Floating Cards Edition)
==========================================================================
Clean, aesthetic, TikTok-ready desktop lyrics overlay for Windows.
When playing songs on Spotify, each lyric line appears in its own separate
frosted glass card that rises smoothly upwards while gently swaying left and right.
Features:
  - Real-time character-by-character typewriter reveal synchronized with music.
  - Radiant white blink/flash effect upon reaching the top before dissolving.
  - Dynamic album cover color palette extraction with smooth crossfade.
  - Falling musical note particles (♪, ♫, ♬, ♩) matching active album accent colors.
  - Zero-delay hardware timestamp extrapolation.
"""

import math
import os
import random
import sys
import asyncio
import time
import threading
import queue
import io
import urllib.request
import urllib.parse
import json
import re
import colorsys
import ctypes
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

import pygame

# Ensure UTF-8 output on Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

# Set Pygame window origin to top-left of the screen
os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

# Initialize Pygame
pygame.init()
pygame.font.init()

# -------------------------------------------------------------
# Configuration & Theme Defaults
# -------------------------------------------------------------
SPEED_MULTIPLIER = 1.0
BASE_FLOAT_SPEED = 1.45  # Smooth, graceful rising speed
DEFAULT_SYNC_OFFSET = 0.20  # Subtle vocal anticipation offset for natural reading

# Elegant aesthetic fallback palette (warm twilight wine)
DARK_CARD = {
    "bg": "#120B10",
    "card": "#21141D",
    "text": "#FDFEFE",
    "accent": "#E63956",          # Vibrant crimson rose accent
    "glass_border": "#542435",
    "shadow_outer": "#0A0609",
    "sub_text": "#B39DA8"
}

def hex_to_rgb(hex_str):
    """Converts '#RRGGBB' to (R, G, B) tuple."""
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    """Converts (R, G, B) tuple to '#RRGGBB'."""
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"

DEFAULT_THEME_RGB = {k: hex_to_rgb(v) for k, v in DARK_CARD.items()}

# Cache directory for fetched lyrics
CACHE_DIR = Path(__file__).parent / ".lyrics_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# Windows Transparency & Always-On-Top Setup
# -------------------------------------------------------------
user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
LWA_COLORKEY = 0x00000001

KEY_COLOR = (1, 1, 1)  # Desktop Chroma-Key

def setup_overlay_window(hwnd, click_through=False):
    """Configures the Pygame window as a transparent, always-on-top desktop overlay."""
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    new_style = style | WS_EX_LAYERED | WS_EX_TOPMOST
    if click_through:
        new_style |= WS_EX_TRANSPARENT
    else:
        new_style &= ~WS_EX_TRANSPARENT
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
    
    colorkey_ref = KEY_COLOR[0] | (KEY_COLOR[1] << 8) | (KEY_COLOR[2] << 16)
    user32.SetLayeredWindowAttributes(hwnd, colorkey_ref, 0, LWA_COLORKEY)
    
    HWND_TOPMOST = -1
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)

# -------------------------------------------------------------
# Color Extraction & Dynamic Palette Generator
# -------------------------------------------------------------
def extract_palette_from_image(image_bytes):
    """Extracts dominant, harmonic color palette from album artwork bytes."""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_small = img.resize((48, 48), Image.Resampling.LANCZOS)
        
        raw_pixels = (
            img_small.get_flattened_data()
            if hasattr(img_small, "get_flattened_data")
            else img_small.getdata()
        )
        
        color_counts = {}
        for r, g, b in raw_pixels:
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            saturation_weight = 1.0 + (s * 3.5)
            brightness_weight = 1.2 if (0.22 < v < 0.92) else 0.4
            bucket = ((r // 16) * 16, (g // 16) * 16, (b // 16) * 16)
            color_counts[bucket] = color_counts.get(bucket, 0) + (saturation_weight * brightness_weight)

        if not color_counts:
            return DEFAULT_THEME_RGB

        best_rgb = max(color_counts.items(), key=lambda item: item[1])[0]
        h, s, v = colorsys.rgb_to_hsv(best_rgb[0] / 255.0, best_rgb[1] / 255.0, best_rgb[2] / 255.0)

        # 1. Vibrant Accent Color (for notes, highlights, and pill notch)
        acc_s = max(s, 0.72)
        acc_v = max(v, 0.88)
        acc_rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, acc_s, acc_v))

        # 2. Rich Dark Frosted Card Surface
        card_s = min(max(s, 0.40), 0.65)
        card_v = 0.17 if s > 0.15 else 0.12
        card_rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, card_s, card_v))

        # 3. Soft Elegant Glass Border
        border_s = min(s, 0.65)
        border_v = min(card_v + 0.32, 0.70)
        border_rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, border_s, border_v))

        # 4. Muted Subtitle / Timestamp Text
        sub_s = min(s * 0.3, 0.25)
        sub_v = 0.75
        sub_rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, sub_s, sub_v))

        bg_rgb = tuple(max(0, c - 15) for c in card_rgb)

        return {
            "bg": bg_rgb,
            "card": card_rgb,
            "text": (252, 253, 255),
            "accent": acc_rgb,
            "glass_border": border_rgb,
            "shadow_outer": (10, 8, 12),
            "sub_text": sub_rgb
        }
    except Exception:
        return DEFAULT_THEME_RGB

# -------------------------------------------------------------
# Lyrics Parser & Cache (LRCLIB Integration)
# -------------------------------------------------------------
def clean_filename(name):
    """Sanitizes track/artist names for local filesystem caching."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def parse_lrc(lrc_text):
    """Parses synced LRC text into sorted list of (timestamp_seconds, line_text)."""
    pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")
    entries = []
    for line in lrc_text.strip().split("\n"):
        line = line.strip()
        m = pattern.match(line)
        if m:
            m_min = int(m.group(1))
            m_sec = float(m.group(2))
            t = m_min * 60 + m_sec
            txt = m.group(3).strip()
            if txt:
                entries.append((t, txt))
    entries.sort(key=lambda x: x[0])
    return entries

def fetch_lyrics_lrclib(title, artist, album=""):
    """Fetches synchronized lyrics from LRCLIB with local file caching."""
    safe_name = clean_filename(f"{artist} - {title}")
    cache_path = CACHE_DIR / f"{safe_name}.json"
    
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
                print(f"[Lyrics] Cache hit: {title} - {artist}", flush=True)
                return cached.get("synced_entries", []), cached.get("plain", "")
        except Exception:
            pass

    url = f"https://lrclib.net/api/get?artist_name={urllib.parse.quote(artist)}&track_name={urllib.parse.quote(title)}"
    req = urllib.request.Request(url, headers={"User-Agent": "SpotifyLyricsOverlay/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            synced = data.get("syncedLyrics")
            plain = data.get("plainLyrics") or ""
            entries = parse_lrc(synced) if synced else []
            
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"synced_entries": entries, "plain": plain}, f, ensure_ascii=False)
            
            print(f"[Lyrics] Fetched from LRCLIB: {title} - {artist}", flush=True)
            return entries, plain
    except Exception:
        try:
            search_url = f"https://lrclib.net/api/search?q={urllib.parse.quote(f'{artist} {title}')}"
            search_req = urllib.request.Request(search_url, headers={"User-Agent": "SpotifyLyricsOverlay/1.0"})
            with urllib.request.urlopen(search_req, timeout=6) as resp:
                results = json.loads(resp.read().decode("utf-8"))
                if results and isinstance(results, list):
                    item = results[0]
                    synced = item.get("syncedLyrics")
                    plain = item.get("plainLyrics") or ""
                    entries = parse_lrc(synced) if synced else []
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump({"synced_entries": entries, "plain": plain}, f, ensure_ascii=False)
                    print(f"[Lyrics] Found via LRCLIB search: {title} - {artist}", flush=True)
                    return entries, plain
        except Exception:
            pass
        return [], ""

def fetch_itunes_artwork(title, artist):
    """Fallback: downloads cover artwork from iTunes Search API."""
    query = urllib.parse.quote(f"{artist} {title}")
    url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=1"
    req = urllib.request.Request(url, headers={"User-Agent": "SpotifyLyricsOverlay/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("results"):
                art_url = data["results"][0].get("artworkUrl100", "").replace("100x100bb", "600x600bb")
                if art_url:
                    with urllib.request.urlopen(art_url, timeout=5) as art_resp:
                        return art_resp.read()
    except Exception:
        pass
    return None

# -------------------------------------------------------------
# Spotify Playback Monitor (Hardware Precision Extrapolation)
# -------------------------------------------------------------
class SpotifyMonitor:
    def __init__(self, state_queue):
        self.state_queue = state_queue
        self.last_track = None
        self.last_artist = None
        self.last_position = 0.0
        self.is_playing = False
        self.running = True

    async def get_media_session_async(self):
        """Asynchronously accesses Windows Global System Media Transport Controls."""
        try:
            from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
            from winsdk.windows.storage.streams import DataReader

            manager = await MediaManager.request_async()
            sessions = manager.get_sessions()
            
            spotify_session = None
            for s in sessions:
                app_id = (s.source_app_user_model_id or "").lower()
                if "spotify" in app_id:
                    spotify_session = s
                    break

            session = spotify_session or manager.get_current_session()
            if not session:
                return None

            media_props = await session.try_get_media_properties_async()
            if not media_props:
                return None

            title = media_props.title or ""
            artist = media_props.artist or ""
            album = media_props.album_title or ""

            pb_info = session.get_playback_info()
            status = pb_info.playback_status if pb_info else 0
            is_playing = (status == 4)

            # Precision Timeline Extrapolation (Eliminating 2-3s GSMTC caching latency)
            timeline = session.get_timeline_properties()
            if timeline and timeline.position:
                raw_pos = timeline.position.total_seconds()
                duration = timeline.end_time.total_seconds() if timeline.end_time else 0.0
                
                if is_playing and timeline.last_updated_time:
                    now_utc = datetime.now(timezone.utc)
                    elapsed_since_update = (now_utc - timeline.last_updated_time).total_seconds()
                    elapsed_since_update = max(0.0, min(10.0, elapsed_since_update))
                    true_pos = raw_pos + elapsed_since_update
                else:
                    true_pos = raw_pos
            else:
                true_pos = 0.0
                duration = 0.0

            thumb_bytes = None
            if media_props.thumbnail:
                try:
                    stream = await media_props.thumbnail.open_read_async()
                    if stream and stream.size > 0:
                        reader = DataReader(stream)
                        await reader.load_async(stream.size)
                        buf = bytearray(stream.size)
                        reader.read_bytes(buf)
                        thumb_bytes = bytes(buf)
                except Exception:
                    pass

            return {
                "title": title,
                "artist": artist,
                "album": album,
                "position": true_pos,
                "duration": duration,
                "is_playing": is_playing,
                "thumb_bytes": thumb_bytes
            }
        except Exception:
            return None

    def get_spotify_window_title_fallback(self):
        """Win32 window title enumeration fallback if Windows Media Control is unavailable."""
        titles = []
        def enum_cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    class_buf = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(hwnd, class_buf, 256)
                    if "Spotify" in class_buf.value or "Chrome_WidgetWin_0" in class_buf.value:
                        if title and title not in ("Spotify", "Spotify Free", "Spotify Premium"):
                            if " - " in title:
                                titles.append(title)
            return True
        cb = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(enum_cb)
        user32.EnumWindows(cb, 0)
        if titles:
            parts = titles[0].split(" - ", 1)
            return {"artist": parts[0].strip(), "title": parts[1].strip()}
        return None

    def worker_loop(self):
        """Background thread monitoring Spotify state continuously."""
        print("[SpotifyMonitor] Active and listening for Spotify playback...", flush=True)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self.running:
            try:
                media_data = loop.run_until_complete(self.get_media_session_async())
                if media_data and media_data["title"]:
                    title = media_data["title"]
                    artist = media_data["artist"]
                    album = media_data["album"]
                    pos = media_data["position"]
                    duration = media_data["duration"]
                    is_playing = media_data["is_playing"]
                    thumb_bytes = media_data["thumb_bytes"]
                else:
                    fb = self.get_spotify_window_title_fallback()
                    if fb:
                        title = fb["title"]
                        artist = fb["artist"]
                        album = ""
                        pos = self.last_position + (0.15 if self.is_playing else 0.0)
                        duration = 0.0
                        is_playing = True
                        thumb_bytes = None
                    else:
                        title = None
                        artist = None
                        album = None
                        pos = 0.0
                        duration = 0.0
                        is_playing = False
                        thumb_bytes = None

                track_changed = (title != self.last_track or artist != self.last_artist)
                
                if track_changed and title:
                    self.last_track = title
                    self.last_artist = artist
                    print(f"[Spotify] Now Playing: {title} — {artist}", flush=True)

                    if not thumb_bytes:
                        thumb_bytes = fetch_itunes_artwork(title, artist)

                    palette = extract_palette_from_image(thumb_bytes) if thumb_bytes else DEFAULT_THEME_RGB
                    lyrics_entries, plain_lyrics = fetch_lyrics_lrclib(title, artist, album)

                    self.state_queue.put({
                        "type": "track_change",
                        "title": title,
                        "artist": artist,
                        "album": album,
                        "duration": duration,
                        "palette": palette,
                        "thumb_bytes": thumb_bytes,
                        "lyrics": lyrics_entries,
                        "plain": plain_lyrics,
                        "position": pos,
                        "is_playing": is_playing,
                        "timestamp": time.perf_counter()
                    })

                elif title:
                    self.state_queue.put({
                        "type": "tick",
                        "position": pos,
                        "duration": duration,
                        "is_playing": is_playing,
                        "timestamp": time.perf_counter()
                    })

            except Exception:
                pass

            time.sleep(0.15)

    def start(self):
        t = threading.Thread(target=self.worker_loop, daemon=True)
        t.start()
        return t

# -------------------------------------------------------------
# Aesthetic Falling Musical Notes Particle System
# -------------------------------------------------------------
class FallingNoteParticle:
    """Aesthetic musical notes drifting gently downwards in matching album colors with multi-tier depth & high visibility."""
    NOTES = ["♪", "♫", "♬", "♩"]

    def __init__(self, screen_w, screen_h, initial_scatter=False):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.note = random.choice(self.NOTES)
        # Depth tiers: sm (24px), md (34px), lg (46px)
        self.tier = random.choices(["sm", "md", "lg"], weights=[30, 45, 25])[0]

        if self.tier == "lg":
            self.speed_y = random.uniform(2.2, 3.6) * SPEED_MULTIPLIER
            self.sway_amp = random.uniform(18, 30)
            self.sway_freq = random.uniform(0.9, 1.6)
        elif self.tier == "md":
            self.speed_y = random.uniform(1.6, 2.6) * SPEED_MULTIPLIER
            self.sway_amp = random.uniform(13, 22)
            self.sway_freq = random.uniform(1.0, 1.8)
        else:  # sm
            self.speed_y = random.uniform(1.1, 1.9) * SPEED_MULTIPLIER
            self.sway_amp = random.uniform(8, 16)
            self.sway_freq = random.uniform(1.1, 1.9)

        self.x = random.uniform(15, screen_w - 15)
        self.base_x = self.x
        self.y = random.uniform(0, screen_h) if initial_scatter else random.uniform(-60, -10)
        self.phase = random.uniform(0, math.pi * 2)
        # High opacity for rich visibility (180 to 255)
        self.alpha = random.randint(180, 255)
        self.is_sparkle = (random.random() < 0.25)

    def update(self, dt, current_time):
        self.y += self.speed_y * dt * 60.0
        self.x = self.base_x + math.sin(current_time * self.sway_freq + self.phase) * self.sway_amp

        if self.y > self.screen_h + 35:
            self.reset()

    def reset(self):
        self.note = random.choice(self.NOTES)
        self.tier = random.choices(["sm", "md", "lg"], weights=[30, 45, 25])[0]

        if self.tier == "lg":
            self.speed_y = random.uniform(2.2, 3.6) * SPEED_MULTIPLIER
            self.sway_amp = random.uniform(18, 30)
            self.sway_freq = random.uniform(0.9, 1.6)
        elif self.tier == "md":
            self.speed_y = random.uniform(1.6, 2.6) * SPEED_MULTIPLIER
            self.sway_amp = random.uniform(13, 22)
            self.sway_freq = random.uniform(1.0, 1.8)
        else:  # sm
            self.speed_y = random.uniform(1.1, 1.9) * SPEED_MULTIPLIER
            self.sway_amp = random.uniform(8, 16)
            self.sway_freq = random.uniform(1.1, 1.9)

        self.base_x = random.uniform(15, self.screen_w - 15)
        self.x = self.base_x
        self.y = random.uniform(-50, -10)
        self.phase = random.uniform(0, math.pi * 2)
        self.alpha = random.randint(180, 255)
        self.is_sparkle = (random.random() < 0.25)

# -------------------------------------------------------------
# Individual Rising Aesthetic Card (Typewriter & White Blink)
# -------------------------------------------------------------
class RisingAestheticCard:
    """
    Frosted glass rounded card that rises gracefully upwards while swaying
    gently left and right, with real-time character-by-character typewriter reveal,
    smooth side entry from left/right, radiant white flash/blink upon reaching the top,
    and smooth dissolve.
    """
    def __init__(self, text, start_x, start_y, palette, time_tag, cover_surface=None, fonts=None, title="", artist="", start_time=None, next_time=None, side="left"):
        self.text = text.strip().strip('"').strip("'")
        self.card_w = 480
        self.card_h = 195
        self.base_x = start_x
        self.x = start_x
        self.y = start_y
        self.side = side
        
        # Smooth slide-in entry animation from left or right
        self.entry_duration = 0.60
        self.entry_offset = -80.0 if side == "left" else 80.0
        
        # Smooth upward floating speed
        self.speed_y = random.uniform(1.25, 1.55) * BASE_FLOAT_SPEED
        # Left-right swaying physics ('kiri-kanan goyang dikit')
        self.sway_amp = random.uniform(20.0, 34.0)
        self.sway_freq = random.uniform(0.95, 1.35)
        self.phase = random.uniform(0, math.pi * 2)
        
        self.palette = dict(palette)
        self.time_tag = time_tag
        self.cover_surface = cover_surface
        self.fonts = fonts
        self.title = title
        self.artist = artist
        
        self.start_time = start_time
        self.next_time = next_time
        self.spawn_time = time.time()

        # Calculate natural singing/typing duration for character reveal
        if start_time is not None and next_time is not None and next_time > start_time:
            line_interval = next_time - start_time
            char_based_est = max(1.4, len(self.text) * 0.09)
            self.typing_duration = min(line_interval * 0.78, char_based_est)
            self.typing_duration = max(1.2, min(5.0, self.typing_duration))
        else:
            self.typing_duration = max(1.4, min(4.0, len(self.text) * 0.08))

        # Pre-wrap text into lines to avoid layout shift during typing
        self.full_quote_text = f'"{self.text}"'
        self.wrapped_lines = self._precompute_wrapped_lines()
        self.chars_to_show = 1

        # White Blink / Flash & Dissolve state
        self.alpha = 255.0
        self.white_flash = 0.0
        self.is_flashing = False
        self.flash_elapsed = 0.0
        self.flash_duration = 0.42  # ~0.42 seconds total for flash peak and dissolve
        self.is_alive = True

    def _precompute_wrapped_lines(self):
        """Pre-calculates wrapped line structure from full text."""
        max_text_w = self.card_w - 70
        words = self.full_quote_text.split()
        lines = []
        curr_l = ""
        for w in words:
            test_line = f"{curr_l} {w}".strip()
            if self.fonts["lyric"].size(test_line)[0] <= max_text_w:
                curr_l = test_line
            else:
                if curr_l:
                    lines.append(curr_l)
                curr_l = w
        if curr_l:
            lines.append(curr_l)
        return lines if lines else [self.full_quote_text]

    def update(self, dt, playback_pos, current_time, screen_h):
        # 1. Rise upwards
        self.y -= self.speed_y * dt * 60.0
        
        # 2. Smooth slide-in entry from left or right side
        age = current_time - self.spawn_time
        if age < self.entry_duration:
            t = age / self.entry_duration
            ease_out = 1.0 - ((1.0 - t) ** 3)
            current_entry_offset = self.entry_offset * (1.0 - ease_out)
        else:
            current_entry_offset = 0.0

        # 3. Sway gently left and right ('kiri-kanan goyang dikit')
        sway_offset = math.sin(current_time * self.sway_freq + self.phase) * self.sway_amp
        self.x = self.base_x + current_entry_offset + sway_offset

        # 4. Real-Time Character-by-Character Typewriter Sync with Music
        if self.start_time is not None:
            elapsed = playback_pos - self.start_time
            if self.typing_duration > 0:
                progress = max(0.0, min(1.0, elapsed / self.typing_duration))
            else:
                progress = 1.0
        else:
            elapsed = current_time - self.spawn_time
            progress = max(0.0, min(1.0, elapsed / self.typing_duration))

        total_chars = len(self.full_quote_text)
        self.chars_to_show = max(1, min(total_chars, int(total_chars * progress)))

        # 4. White Blink / Flash Effect Before Card Fades Out
        flash_threshold_y = screen_h * 0.38
        if self.y <= flash_threshold_y and not self.is_flashing:
            self.is_flashing = True
            self.flash_elapsed = 0.0

        if self.is_flashing:
            self.flash_elapsed += dt
            t = self.flash_elapsed / self.flash_duration
            if t <= 0.28:
                # Fast bright white radiant flash peak (blink)
                self.white_flash = t / 0.28
                self.alpha = 255.0
            elif t <= 1.0:
                # Dissolve smoothly to air
                decay = (t - 0.28) / 0.72
                self.white_flash = max(0.0, 1.0 - (decay * 1.5))
                self.alpha = max(0.0, 255.0 * (1.0 - (decay ** 1.3)))
            else:
                self.white_flash = 0.0
                self.alpha = 0.0
                self.is_alive = False
        else:
            self.white_flash = 0.0
            self.alpha = 255.0

        if self.y < -self.card_h or self.alpha <= 2:
            self.is_alive = False

    def render(self):
        """Renders the aesthetic frosted glass card with typing and white flash."""
        surf = pygame.Surface((self.card_w, self.card_h), pygame.SRCALPHA)
        
        card_col = self.palette["card"]
        border_col = self.palette["glass_border"]
        accent_col = self.palette["accent"]
        text_col = self.palette["text"]
        sub_col = self.palette["sub_text"]

        alpha_int = int(self.alpha)
        flash_ratio = self.white_flash

        # 1. Main Frosted Rounded Card Surface (with white flash blend)
        card_r = int(card_col[0] + (255 - card_col[0]) * flash_ratio)
        card_g = int(card_col[1] + (255 - card_col[1]) * flash_ratio)
        card_b = int(card_col[2] + (255 - card_col[2]) * flash_ratio)
        bg_rgba = (card_r, card_g, card_b, min(240, int(alpha_int * 0.94)))

        border_r = int(border_col[0] + (255 - border_col[0]) * flash_ratio)
        border_g = int(border_col[1] + (255 - border_col[1]) * flash_ratio)
        border_b = int(border_col[2] + (255 - border_col[2]) * flash_ratio)
        border_rgba = (border_r, border_g, border_b, min(230, int(alpha_int * 0.88)))

        accent_r = int(accent_col[0] + (255 - accent_col[0]) * flash_ratio)
        accent_g = int(accent_col[1] + (255 - accent_col[1]) * flash_ratio)
        accent_b = int(accent_col[2] + (255 - accent_col[2]) * flash_ratio)
        accent_border = (accent_r, accent_g, accent_b, min(180, int(alpha_int * 0.65)))

        pygame.draw.rect(surf, bg_rgba, (0, 0, self.card_w, self.card_h), border_radius=24)
        pygame.draw.rect(surf, border_rgba, (0, 0, self.card_w, self.card_h), width=2, border_radius=24)
        pygame.draw.rect(surf, accent_border, (2, 2, self.card_w - 4, self.card_h - 4), width=1, border_radius=22)

        # White Blink Radiant Sheen & Glow
        if flash_ratio > 0.05:
            white_fill_alpha = int(flash_ratio * min(210, alpha_int))
            pygame.draw.rect(surf, (255, 255, 255, white_fill_alpha), (0, 0, self.card_w, self.card_h), border_radius=24)
            white_glow_alpha = int(flash_ratio * min(240, alpha_int))
            pygame.draw.rect(surf, (255, 255, 255, white_glow_alpha), (-1, -1, self.card_w + 2, self.card_h + 2), width=3, border_radius=25)

        # 2. Sleek Top Pill Notch (Dynamic Island Aesthetic)
        notch_w = 80
        notch_h = 7
        notch_x = (self.card_w - notch_w) // 2
        notch_y = 13
        notch_rgba = (accent_r, accent_g, accent_b, min(230, int(alpha_int * 0.88)))
        pygame.draw.rect(surf, notch_rgba, (notch_x, notch_y, notch_w, notch_h), border_radius=4)

        # 3. Clean Serif Lyric Text - Real-Time Character-by-Character Typewriter
        line_h = 32
        total_text_h = len(self.wrapped_lines) * line_h
        body_top = 28
        body_bottom = self.card_h - 42
        available_h = body_bottom - body_top
        start_y = body_top + max(4, (available_h - total_text_h) // 2)

        chars_left = self.chars_to_show
        for i, full_line in enumerate(self.wrapped_lines):
            if chars_left <= 0:
                continue

            if chars_left >= len(full_line):
                visible_str = full_line
                chars_left -= len(full_line)
                if chars_left > 0:
                    chars_left -= 1  # count space between lines
            else:
                visible_str = full_line[:chars_left]
                chars_left = 0

            if visible_str:
                curr_text_col = (255, 255, 255) if flash_ratio > 0.3 else text_col
                ls = self.fonts["lyric"].render(visible_str, True, curr_text_col)
                ls.set_alpha(alpha_int)
                full_w = self.fonts["lyric"].size(full_line)[0]
                line_x = (self.card_w - full_w) // 2
                surf.blit(ls, (line_x, start_y + (i * line_h)))

        # 4. Bottom Divider Line
        divider_y = self.card_h - 38
        div_rgba = (border_r, border_g, border_b, min(120, int(alpha_int * 0.45)))
        pygame.draw.line(surf, div_rgba, (24, divider_y), (self.card_w - 24, divider_y), 1)

        # 5. Bottom Left: Mini Album Artwork + Track & Artist
        thumb_size = 22
        thumb_x = 24
        thumb_y = self.card_h - 29

        if self.cover_surface:
            surf.blit(self.cover_surface, (thumb_x, thumb_y))
            pygame.draw.rect(surf, border_rgba, (thumb_x, thumb_y, thumb_size, thumb_size), width=1, border_radius=4)
            info_x = thumb_x + thumb_size + 10
        else:
            pygame.draw.rect(surf, (accent_r, accent_g, accent_b), (thumb_x, thumb_y + 3, 14, 14), border_radius=4)
            info_x = thumb_x + 22

        track_str = f"{self.title}  ·  {self.artist}" if self.title else "Spotify Playing"
        if len(track_str) > 36:
            track_str = track_str[:34] + "…"

        info_surf = self.fonts["sub"].render(track_str, True, sub_col)
        info_surf.set_alpha(min(210, alpha_int))
        surf.blit(info_surf, (info_x, thumb_y + 3))

        # 6. Bottom Right: Clean Timestamp [mm:ss]
        if self.time_tag:
            time_surf = self.fonts["sub"].render(self.time_tag, True, sub_col)
            time_surf.set_alpha(min(200, alpha_int))
            time_x = self.card_w - 24 - time_surf.get_width()
            surf.blit(time_surf, (time_x, thumb_y + 3))

        return surf

# -------------------------------------------------------------
# Main Application Engine
# -------------------------------------------------------------
class FloatingLyricsApp:
    def __init__(self):
        info = pygame.display.Info()
        self.screen_w = info.current_w
        self.screen_h = info.current_h
        self.screen = pygame.display.set_mode((self.screen_w, self.screen_h), pygame.NOFRAME)
        pygame.display.set_caption("Spotify Aesthetic Floating Lyrics Overlay")
        
        self.hwnd = pygame.display.get_wm_info()["window"]
        self.click_through = False
        setup_overlay_window(self.hwnd, click_through=self.click_through)

        self.clock = pygame.time.Clock()
        self.running = True

        self.state_queue = queue.Queue()
        self.monitor = SpotifyMonitor(self.state_queue)
        self.monitor.start()

        # Track & Lyrics State
        self.current_title = "Waiting for Spotify..."
        self.current_artist = ""
        self.current_album = ""
        self.lyrics_entries = []
        self.plain_lyrics = ""
        self.current_position = 0.0
        self.total_duration = 0.0
        self.last_sync_time = time.perf_counter()
        self.is_playing = False
        self.karaoke_mode = True

        # Precision Sync Offset (in seconds)
        self.sync_offset = DEFAULT_SYNC_OFFSET

        # Rising Aesthetic Cards List & Alternating Left/Right Sides
        self.cards = []
        self.last_spawned_lyric = ""
        self.spawn_side = "left"

        # Color Palettes & Smooth Transition
        self.current_theme = dict(DEFAULT_THEME_RGB)
        self.target_theme = dict(DEFAULT_THEME_RGB)
        self.cover_surface = None

        # Clean Elegant Fonts
        self.fonts = {
            "lyric": pygame.font.SysFont("georgia", 21, bold=True),
            "sub": pygame.font.SysFont("segoeui", 11),
            "music_sm": pygame.font.SysFont("segoeuisymbol", 24),
            "music_md": pygame.font.SysFont("segoeuisymbol", 34),
            "music_lg": pygame.font.SysFont("segoeuisymbol", 46),
        }

        # Falling Musical Note Particles (increased to 70 for vibrant visibility)
        self.particles = [FallingNoteParticle(self.screen_w, self.screen_h, initial_scatter=True) for _ in range(70)]
        self.falling_notes_enabled = True

        # Global Hotkey debounce
        self.last_key_press_time = 0.0

    def lerp_color(self, c1, c2, t):
        """Linearly interpolates between two RGB tuples."""
        return (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t)
        )

    def update_palette_lerp(self, dt):
        """Smoothly blends current card colors toward target album cover colors."""
        blend_factor = min(1.0, dt * 3.5)
        for key in ["card", "accent", "glass_border", "bg", "sub_text"]:
            if key in self.current_theme and key in self.target_theme:
                self.current_theme[key] = self.lerp_color(
                    self.current_theme[key], self.target_theme[key], blend_factor
                )

    def process_queue_events(self):
        """Processes state updates from the background Spotify monitor."""
        while not self.state_queue.empty():
            try:
                msg = self.state_queue.get_nowait()
                msg_type = msg.get("type")
                if msg_type == "track_change":
                    self.current_title = msg["title"]
                    self.current_artist = msg["artist"]
                    self.current_album = msg.get("album", "")
                    self.total_duration = msg.get("duration", 0.0)
                    self.lyrics_entries = msg["lyrics"]
                    self.plain_lyrics = msg["plain"]
                    self.target_theme = msg["palette"]
                    self.current_position = msg["position"]
                    self.is_playing = msg["is_playing"]
                    self.last_sync_time = msg["timestamp"]
                    self.last_spawned_lyric = ""

                    thumb_bytes = msg.get("thumb_bytes")
                    if thumb_bytes:
                        try:
                            pil_img = Image.open(io.BytesIO(thumb_bytes)).convert("RGB")
                            pil_img = pil_img.resize((22, 22), Image.Resampling.LANCZOS)
                            mode = pil_img.mode
                            size = pil_img.size
                            data = pil_img.tobytes()
                            self.cover_surface = pygame.image.fromstring(data, size, mode)
                        except Exception:
                            self.cover_surface = None
                    else:
                        self.cover_surface = None

                elif msg_type == "tick":
                    self.current_position = msg["position"]
                    if msg.get("duration"):
                        self.total_duration = msg["duration"]
                    self.is_playing = msg["is_playing"]
                    self.last_sync_time = msg["timestamp"]
            except queue.Empty:
                break

    def get_interpolated_playback_time(self):
        """Calculates exact current playback timestamp in seconds."""
        if self.is_playing:
            now = time.perf_counter()
            elapsed = now - self.last_sync_time
            return self.current_position + elapsed + self.sync_offset
        return self.current_position + self.sync_offset

    def update_lyrics_and_spawn_cards(self):
        """
        Detects active lyric line and spawns a new separate rising aesthetic card
        that starts from the bottom and floats upwards while swaying left/right,
        with realtime character-by-character typewriter reveal.
        """
        curr_time = self.get_interpolated_playback_time()
        found = None
        found_time = None
        next_time = None

        if not self.karaoke_mode:
            current_line = f"{self.current_title} · {self.current_artist}"
            found_time = curr_time
            next_time = curr_time + 4.0
        elif not self.lyrics_entries:
            if self.current_title != "Waiting for Spotify...":
                current_line = f"♫ {self.current_title}"
            else:
                current_line = "Play a song on Spotify..."
            found_time = curr_time
            next_time = curr_time + 4.0
        else:
            for i, (t, txt) in enumerate(self.lyrics_entries):
                if t <= curr_time:
                    found = txt
                    found_time = t
                    if i + 1 < len(self.lyrics_entries):
                        next_time = self.lyrics_entries[i + 1][0]
                    else:
                        next_time = t + 4.5
                else:
                    break

            if found:
                current_line = found
            else:
                current_line = f"♫ {self.current_title}"
                found_time = curr_time
                next_time = curr_time + 4.0

        # When a new lyric line begins, spawn a new separate card at the bottom!
        if current_line and current_line != self.last_spawned_lyric:
            self.last_spawned_lyric = current_line
            
            card_w = 480
            card_h = 195

            # Alternate spawn sides between Left and Right for dual-stream aesthetic
            current_side = self.spawn_side
            self.spawn_side = "right" if self.spawn_side == "left" else "left"

            margin = 55
            half_w = self.screen_w // 2

            if current_side == "left":
                # Left side zone: comfortable placement on left side of the screen
                target_center = self.screen_w * 0.22
                base_calc = target_center - (card_w // 2) + random.uniform(-25, 30)
                max_left = max(margin, half_w - card_w - 30)
                spawn_x = max(margin, min(max_left, base_calc))
            else:
                # Right side zone: comfortable placement on right side of the screen
                target_center = self.screen_w * 0.78
                base_calc = target_center - (card_w // 2) + random.uniform(-30, 25)
                min_right = min(self.screen_w - card_w - margin, half_w + 30)
                spawn_x = max(min_right, min(self.screen_w - card_w - margin, base_calc))

            spawn_y = float(self.screen_h - card_h - 50)

            # Format current timestamp tag [mm:ss]
            mins = int(curr_time // 60)
            secs = int(curr_time % 60)
            time_tag = f"{mins:02d}:{secs:02d}"

            new_card = RisingAestheticCard(
                text=current_line,
                start_x=spawn_x,
                start_y=spawn_y,
                palette=self.current_theme,
                time_tag=time_tag,
                cover_surface=self.cover_surface,
                fonts=self.fonts,
                title=self.current_title,
                artist=self.current_artist,
                start_time=found_time,
                next_time=next_time,
                side=current_side
            )
            self.cards.append(new_card)

    def update_cards_physics(self, dt):
        """Updates physics, realtime typing, and white flash dissolve for all active rising cards."""
        curr_t = time.time()
        playback_pos = self.get_interpolated_playback_time()
        for card in self.cards:
            card.update(dt, playback_pos, curr_t, self.screen_h)

        # Remove dead cards that have drifted off-screen or dissolved after white flash
        self.cards = [c for c in self.cards if c.is_alive]

    def draw(self):
        """Draws transparent background, falling musical notes, and rising aesthetic cards."""
        self.screen.fill(KEY_COLOR)

        accent_col = self.current_theme["accent"]

        # 1. Render Falling Musical Notes (High Visibility & Contrast)
        if self.falling_notes_enabled:
            shadow_col = (12, 12, 18)
            for p in self.particles:
                font = self.fonts.get(f"music_{p.tier}", self.fonts["music_md"])
                
                # 1a. Drop shadow for distinct contrast on any desktop background
                shadow_surf = font.render(p.note, True, shadow_col)
                shadow_surf.set_alpha(int(p.alpha * 0.75))
                self.screen.blit(shadow_surf, (int(p.x + 2), int(p.y + 2)))

                # 1b. Vibrant core note with optional luminous sparkle highlight
                if p.is_sparkle:
                    note_col = (
                        min(255, accent_col[0] + 65),
                        min(255, accent_col[1] + 65),
                        min(255, accent_col[2] + 65)
                    )
                else:
                    note_col = accent_col

                note_surf = font.render(p.note, True, note_col)
                note_surf.set_alpha(p.alpha)
                self.screen.blit(note_surf, (int(p.x), int(p.y)))

        # 2. Render All Separate Rising Aesthetic Cards
        for card in self.cards:
            card_surf = card.render()
            self.screen.blit(card_surf, (int(card.x), int(card.y)))

        pygame.display.flip()

    def check_global_hotkeys(self):
        """Allows hotkey control even when another application is focused."""
        now = time.time()
        if now - self.last_key_press_time < 0.25:
            return

        VK_CONTROL = 0x11
        VK_SHIFT = 0x10
        ctrl_down = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
        shift_down = (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0

        if ctrl_down and shift_down:
            if (user32.GetAsyncKeyState(ord('K')) & 0x8000) != 0:
                self.last_key_press_time = now
                self.karaoke_mode = not self.karaoke_mode
                print(f"[Overlay] Lyrics Display: {'ON' if self.karaoke_mode else 'OFF'}", flush=True)

            elif (user32.GetAsyncKeyState(ord('T')) & 0x8000) != 0:
                self.last_key_press_time = now
                self.click_through = not self.click_through
                setup_overlay_window(self.hwnd, click_through=self.click_through)
                mode_str = "Click-Through (Transparent)" if self.click_through else "Interactive"
                print(f"[Overlay] Mode: {mode_str}", flush=True)

            elif (user32.GetAsyncKeyState(ord('F')) & 0x8000) != 0:
                self.last_key_press_time = now
                self.falling_notes_enabled = not self.falling_notes_enabled
                print(f"[Overlay] Falling Notes: {'ON' if self.falling_notes_enabled else 'OFF'}", flush=True)

            elif (user32.GetAsyncKeyState(0x26) & 0x8000) != 0:
                self.last_key_press_time = now
                self.sync_offset += 0.10
                print(f"[Sync] Calibration Offset: {self.sync_offset:+.2f}s (Earlier)", flush=True)

            elif (user32.GetAsyncKeyState(0x28) & 0x8000) != 0:
                self.last_key_press_time = now
                self.sync_offset -= 0.10
                print(f"[Sync] Calibration Offset: {self.sync_offset:+.2f}s (Later)", flush=True)

    def handle_events(self):
        """Handles Pygame window events."""
        self.check_global_hotkeys()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self.running = False

                elif event.key == pygame.K_k:
                    self.karaoke_mode = not self.karaoke_mode
                    status_str = "ON" if self.karaoke_mode else "OFF"
                    print(f"[Overlay] Lyrics Display: {status_str}", flush=True)

                elif event.key == pygame.K_t:
                    self.click_through = not self.click_through
                    setup_overlay_window(self.hwnd, click_through=self.click_through)
                    mode_str = "Click-Through (Transparent)" if self.click_through else "Interactive"
                    print(f"[Overlay] Mode: {mode_str}", flush=True)

                elif event.key == pygame.K_f:
                    self.falling_notes_enabled = not self.falling_notes_enabled
                    print(f"[Overlay] Falling Notes: {'ON' if self.falling_notes_enabled else 'OFF'}", flush=True)

                # Up Arrow / ] : Advance lyrics earlier
                elif event.key in (pygame.K_UP, pygame.K_RIGHTBRACKET):
                    self.sync_offset += 0.10
                    print(f"[Sync] Calibration Offset: {self.sync_offset:+.2f}s (Earlier)", flush=True)

                # Down Arrow / [ : Delay lyrics later
                elif event.key in (pygame.K_DOWN, pygame.K_LEFTBRACKET):
                    self.sync_offset -= 0.10
                    print(f"[Sync] Calibration Offset: {self.sync_offset:+.2f}s (Later)", flush=True)

                elif event.key == pygame.K_0:
                    self.sync_offset = DEFAULT_SYNC_OFFSET
                    print(f"[Sync] Calibration Reset: {self.sync_offset:+.2f}s", flush=True)

                elif event.key == pygame.K_SPACE:
                    VK_MEDIA_PLAY_PAUSE = 0xB3
                    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
                    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)

                elif event.key in (pygame.K_RIGHT, pygame.K_n):
                    VK_MEDIA_NEXT_TRACK = 0xB0
                    user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0)
                    user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 2, 0)

                elif event.key in (pygame.K_LEFT, pygame.K_p):
                    VK_MEDIA_PREV_TRACK = 0xB1
                    user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0)
                    user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 2, 0)

    def run(self):
        """Main loop running at 60 FPS."""
        print("==================================================", flush=True)
        print("  SPOTIFY AESTHETIC FLOATING LYRICS OVERLAY", flush=True)
        print("  Clean frosted cards with dynamic album theming", flush=True)
        print("  Shortcuts:", flush=True)
        print("    [Up / ] ]             : Lyrics earlier (+0.10s)", flush=True)
        print("    [Down / [ ]           : Lyrics later (-0.10s)", flush=True)
        print("    [0]                   : Reset sync offset (+0.20s)", flush=True)
        print("    [K] / [Ctrl+Shift+K]  : Toggle lyrics mode", flush=True)
        print("    [T] / [Ctrl+Shift+T]  : Toggle click-through mode", flush=True)
        print("    [F] / [Ctrl+Shift+F]  : Toggle falling notes", flush=True)
        print("    [Space]               : Play / Pause Spotify", flush=True)
        print("    [N / ->]              : Next song", flush=True)
        print("    [P / <-]              : Previous song", flush=True)
        print("    [Q / Esc]             : Exit overlay", flush=True)
        print("==================================================", flush=True)

        last_time = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            dt = min(0.05, now - last_time)
            last_time = now

            self.handle_events()
            self.process_queue_events()
            self.update_palette_lerp(dt)
            self.update_lyrics_and_spawn_cards()
            self.update_cards_physics(dt)

            if self.falling_notes_enabled:
                curr_t = time.time()
                for p in self.particles:
                    p.update(dt, curr_t)

            self.draw()
            self.clock.tick(60)

        pygame.quit()
        sys.exit(0)

# -------------------------------------------------------------
# Entry Point
# -------------------------------------------------------------
if __name__ == "__main__":
    app = FloatingLyricsApp()
    app.run()
