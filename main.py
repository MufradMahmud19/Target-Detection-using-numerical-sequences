
from OpenGL.GL import *
from OpenGL.GLUT import *
import math
import sys
import os
import glob
import importlib
from time import time

# ======================== SCORE TRACKER ========================
try:
    from score_tracker import update_score, get_best_score, is_available as tracker_available
    HAS_TRACKER = tracker_available()
except ImportError:
    HAS_TRACKER = False
    def update_score(*a, **kw): return None
    def get_best_score(*a, **kw): return None

# ======================== WINDOW CONFIG ========================
WIDTH, HEIGHT = 700, 700
FPS = 60
SCALE = 3                          # pixels per sequence unit
BORDER_MARGIN = 50
SEARCHER_RADIUS = 7
TARGET_RADIUS = 12
MAX_TRAIL = 500
STEP_RATE = 6                      # movement steps per second

# ======================== APP STATES ===========================
STATE_MENU = 0                     # series selection screen
STATE_INPUT_X = 1                  # typing target X coordinate
STATE_INPUT_Y = 2                  # typing target Y coordinate
STATE_RUNNING = 3                  # simulation running
STATE_RESULT = 4                   # result screen after catch

# ======================== GLOBAL STATE =========================
app_state = STATE_MENU
frame_count = 0
step_interval = max(FPS // STEP_RATE, 1)

# --- Discovered series ---
available_series = []              # list of imported modules
selected_index = -1                # index into available_series
movement = None                    # SeriesMovement instance

# --- Text input ---
input_buffer = ""
input_error = ""

# --- Border bounds ---
B_LEFT = BORDER_MARGIN
B_RIGHT = WIDTH - BORDER_MARGIN
B_TOP = BORDER_MARGIN              # y=0 at screen top (glOrtho)
B_BOTTOM = HEIGHT - BORDER_MARGIN

# --- Target ---
target_x = 0.0
target_y = 0.0

# --- Searcher ---
sx, sy = 0.0, 0.0
x_dir, y_dir = 1, 1
trail = []

# --- Timing & scoring ---
run_start_time = 0.0
result_time = 0.0
best_time_for_target = None

# --- Catch flash animation ---
catch_flash = 0.0
catch_fx, catch_fy = 0.0, 0.0


# =================== SERIES AUTO-DISCOVERY ====================
def discover_series():
    """
    Scan for *_series.py files in the script directory.
    Each must export SERIES_NAME (str) and SeriesMovement (class).
    """
    global available_series
    available_series = []
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    pattern = os.path.join(script_dir, '*_series.py')
    for filepath in sorted(glob.glob(pattern)):
        module_name = os.path.basename(filepath)[:-3]  # strip .py
        try:
            if module_name in sys.modules:
                mod = importlib.reload(sys.modules[module_name])
            else:
                mod = importlib.import_module(module_name)

            if hasattr(mod, 'SERIES_NAME') and hasattr(mod, 'SeriesMovement'):
                available_series.append(mod)
                print("[OK] Loaded series: {}".format(mod.SERIES_NAME))
            else:
                print("[SKIP] {} missing SERIES_NAME or SeriesMovement".format(module_name))
        except Exception as e:
            print("[WARN] Failed to load {}: {}".format(module_name, e))

    if not available_series:
        print("\n[ERROR] No series modules found!")
        print("Create *_series.py files with SERIES_NAME and SeriesMovement class.")
        print("See fibonacci_series.py as a template.\n")
        sys.exit(1)

    print("\nDiscovered {} series module(s).\n".format(len(available_series)))


# ===================== VALID TARGET RANGE ======================
def get_target_range():
    """Return (min_x, max_x, min_y, max_y) for valid target placement."""
    margin = TARGET_RADIUS + 5
    return (
        int(B_LEFT + margin),
        int(B_RIGHT - margin),
        int(B_TOP + margin),
        int(B_BOTTOM - margin)
    )


# =================== DRAWING PRIMITIVES =======================

# --- Midpoint Line Algorithm (8-zone) ---
def findzone(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    dX, dY = abs(dx), abs(dy)
    if dx >= 0 and dy >= 0: return 0 if dX > dY else 1
    if dx <= 0 and dy >= 0: return 3 if dX > dY else 2
    if dx <= 0 and dy <= 0: return 4 if dX > dY else 5
    if dx >= 0 and dy <= 0: return 7 if dX > dY else 6

def toZone0(x, y, z):
    if z == 0: return x, y
    if z == 1: return y, x
    if z == 2: return y, -x
    if z == 3: return -x, y
    if z == 4: return -x, -y
    if z == 5: return -y, -x
    if z == 6: return -y, x
    if z == 7: return x, -y
    return x, y

def toOriginal(x, y, z):
    if z == 0: return x, y
    if z == 1: return y, x
    if z == 2: return -y, x
    if z == 3: return -x, y
    if z == 4: return -x, -y
    if z == 5: return -y, -x
    if z == 6: return y, -x
    if z == 7: return x, -y
    return x, y

def mpLine(x1, y1, x2, y2):
    """Draw a line using the Midpoint Line Algorithm."""
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    if x1 == x2 and y1 == y2:
        glBegin(GL_POINTS)
        glVertex2f(x1, y1)
        glEnd()
        return
    z = findzone(x1, y1, x2, y2)
    if z is None:
        return
    cx1, cy1 = toZone0(x1, y1, z)
    cx2, cy2 = toZone0(x2, y2, z)
    dx, dy = cx2 - cx1, cy2 - cy1
    if dx == 0:
        return
    d = 2 * dy - dx
    incE, incNE = 2 * dy, 2 * (dy - dx)
    y = cy1
    glBegin(GL_POINTS)
    for x in range(cx1, cx2 + 1):
        px, py = toOriginal(x, y, z)
        glVertex2f(px, py)
        if d > 0:
            y += 1
            d += incNE
        else:
            d += incE
    glEnd()


# --- Midpoint Circle Algorithm ---
def _8way(x, y, a, b):
    """Plot 8 symmetric points of a circle centered at (a, b)."""
    for i, j in [(x,y),(x,-y),(-x,y),(-x,-y),(y,x),(-y,x),(y,-x),(-y,-x)]:
        glVertex2f(i + a, j + b)

def draw_circle(r, cx=0, cy=0):
    """Draw circle outline using the Midpoint Circle Algorithm."""
    r = int(r)
    if r <= 0:
        return
    d = 1 - r
    x, y = 0, r
    glBegin(GL_POINTS)
    _8way(x, y, cx, cy)
    while x < y:
        if d < 0:
            d += 2 * x + 3
        else:
            y -= 1
            d += 2 * (x - y) + 5
        x += 1
        _8way(x, y, cx, cy)
    glEnd()


# --- Text rendering helpers ---
def draw_text(x, y, text, color=(1, 1, 1), font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(*color)
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

def draw_text_large(x, y, text, color=(1, 1, 1)):
    draw_text(x, y, text, color, GLUT_BITMAP_TIMES_ROMAN_24)

def draw_text_small(x, y, text, color=(1, 1, 1)):
    draw_text(x, y, text, color, GLUT_BITMAP_HELVETICA_12)


# --- Custom digit renderer (7-segment style from original project) ---
def _df(i, X, Y):
    return X + (i % 2) * 10, Y + (i // 2) * 10

def draw_digits(value, start_x, start_y):
    """Draw integer digits with midpoint lines (7-segment look)."""
    seg = ['01540', '04', '013245', '0132354', '02315',
           '102354', '235401', '015', '3245102', '51023']
    x, y = start_x, start_y
    for ch in str(int(value)):
        pts = [_df(int(c), x, y) for c in seg[int(ch)]]
        for i in range(len(pts) - 1):
            mpLine(*pts[i], *pts[i + 1])
        x += 15 if ch != '1' else 10


# --- UI panel ---
def draw_panel(px, py, pw, ph, bg=(0.06, 0.06, 0.12), border=(0.15, 0.4, 0.7)):
    """Draw a styled rectangle with glow border."""
    # Background fill
    glColor3f(*bg)
    glBegin(GL_QUADS)
    glVertex2f(px, py)
    glVertex2f(px + pw, py)
    glVertex2f(px + pw, py + ph)
    glVertex2f(px, py + ph)
    glEnd()
    # Multi-layer glow border
    for i in range(3):
        off = i
        a = 1.0 - i * 0.3
        glColor3f(border[0] * a, border[1] * a, border[2] * a)
        glLineWidth(float(3 - i))
        glBegin(GL_LINE_LOOP)
        glVertex2f(px - off, py - off)
        glVertex2f(px + pw + off, py - off)
        glVertex2f(px + pw + off, py + ph + off)
        glVertex2f(px - off, py + ph + off)
        glEnd()
    glLineWidth(1.0)


# --- Input box ---
def draw_input_box(px, py, pw, ph, active=False, text="", show_cursor=True):
    """Draw a text input box with optional blinking cursor."""
    # Background
    bg = (0.1, 0.25, 0.18) if active else (0.07, 0.07, 0.11)
    glColor3f(*bg)
    glBegin(GL_QUADS)
    glVertex2f(px, py)
    glVertex2f(px + pw, py)
    glVertex2f(px + pw, py + ph)
    glVertex2f(px, py + ph)
    glEnd()
    # Border
    bc = (0.0, 1.0, 0.5) if active else (0.3, 0.3, 0.4)
    glColor3f(*bc)
    glLineWidth(2.0 if active else 1.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(px, py)
    glVertex2f(px + pw, py)
    glVertex2f(px + pw, py + ph)
    glVertex2f(px, py + ph)
    glEnd()
    glLineWidth(1.0)
    # Text with cursor
    cursor = ""
    if active and show_cursor:
        cursor = "_" if int(time() * 2) % 2 == 0 else " "
    tc = (1.0, 1.0, 1.0) if active else (0.6, 0.6, 0.6)
    draw_text(px + 8, py + ph - 8, text + cursor, tc)


# ================= STATE: MENU RENDERING ======================
def render_menu():
    """Draw the series selection menu."""
    t = time()

    # Background decoration: subtle floating dots
    glPointSize(2)
    for i in range(20):
        bx = 100 + (i * 137) % 500
        by = 80 + (i * 97 + int(t * 15 + i * 40) % 200) % 550
        alpha = 0.04 + 0.02 * math.sin(t * 1.5 + i)
        glColor3f(alpha, alpha * 2, alpha * 4)
        glBegin(GL_POINTS)
        glVertex2f(bx, by)
        glEnd()

    # Title panel
    draw_panel(60, 40, 580, 80, (0.04, 0.04, 0.1), (0.1, 0.3, 0.65))

    # Animated title
    r = 0.5 + 0.3 * math.sin(t * 2)
    g = 0.7 + 0.2 * math.sin(t * 2.5)
    draw_text_large(193, 90, "TARGET DETECTION", (r, g, 1.0))
    draw_text_small(215, 108, "Select a movement series to begin", (0.45, 0.45, 0.65))

    # Series options panel
    num_series = len(available_series)
    panel_h = 55 + num_series * 75
    draw_panel(60, 145, 580, panel_h, (0.05, 0.05, 0.1))

    draw_text(85, 178, "Available Series:", (0.65, 0.8, 1.0))

    for i, series in enumerate(available_series):
        y_base = 205 + i * 75

        # Option row background
        hover_br = 0.06 + 0.015 * math.sin(t * 3 + i * 1.5)
        glColor3f(hover_br, hover_br, hover_br + 0.03)
        glBegin(GL_QUADS)
        glVertex2f(80, y_base - 8)
        glVertex2f(620, y_base - 8)
        glVertex2f(620, y_base + 50)
        glVertex2f(80, y_base + 50)
        glEnd()

        # Number badge circle
        glColor3f(0.0, 0.8, 0.4)
        glPointSize(2)
        draw_circle(13, 105, y_base + 14)
        draw_text(100, y_base + 19, str(i + 1), (0.0, 0.05, 0.0))

        # Series name
        draw_text(130, y_base + 19, "{}. {}".format(i + 1, series.SERIES_NAME), (0.9, 0.9, 1.0))

        # Description
        desc = getattr(series, 'SERIES_DESCRIPTION', '')
        if desc:
            draw_text_small(130, y_base + 40, desc, (0.45, 0.45, 0.55))

    # Footer
    footer_y = 165 + panel_h + 15
    draw_text_small(85, footer_y,
                    "Press number key to select  |  ESC to quit",
                    (0.35, 0.35, 0.5))
    draw_text_small(85, footer_y + 18,
                    "To add series: create *_series.py with SERIES_NAME & SeriesMovement",
                    (0.22, 0.22, 0.33))


# ================ STATE: TARGET INPUT RENDERING ================
def render_input():
    """Draw the target coordinate input interface."""
    min_x, max_x, min_y, max_y = get_target_range()
    series_name = available_series[selected_index].SERIES_NAME

    # Header
    draw_panel(60, 40, 580, 55, (0.04, 0.04, 0.1), (0.1, 0.3, 0.65))
    draw_text_large(165, 75, "SET TARGET POSITION", (0.6, 0.8, 1.0))
    draw_text_small(255, 88, "Series: " + series_name, (0.35, 0.65, 0.35))

    # Main input panel
    draw_panel(60, 115, 380, 290)

    # --- X coordinate ---
    x_active = (app_state == STATE_INPUT_X)
    x_done = (app_state == STATE_INPUT_Y)
    x_lbl_col = (0.8, 0.95, 0.8) if x_active else (0.5, 0.5, 0.6)

    draw_text(80, 155, "X Coordinate", x_lbl_col)
    draw_text_small(80, 172, "Range: {} to {}".format(min_x, max_x), (0.4, 0.4, 0.55))

    if x_active:
        draw_input_box(80, 180, 300, 30, active=True, text=input_buffer)
    elif x_done:
        draw_input_box(80, 180, 300, 30, active=False, text=str(int(target_x)))

    # --- Y coordinate ---
    y_active = (app_state == STATE_INPUT_Y)
    y_lbl_col = (0.8, 0.95, 0.8) if y_active else (0.5, 0.5, 0.6)

    draw_text(80, 245, "Y Coordinate", y_lbl_col)
    draw_text_small(80, 262, "Range: {} to {}".format(min_y, max_y), (0.4, 0.4, 0.55))

    if y_active:
        draw_input_box(80, 270, 300, 30, active=True, text=input_buffer)
    else:
        draw_input_box(80, 270, 300, 30, active=False, text="")

    # Error message
    if input_error:
        draw_text(80, 330, input_error, (1.0, 0.3, 0.3))

    # Instructions
    draw_text_small(80, 380, "Type digits + ENTER to confirm  |  M = menu  |  X = quit",
                    (0.35, 0.35, 0.5))

    # --- Mini preview panel (right side) ---
    draw_panel(470, 115, 170, 290, (0.04, 0.04, 0.08), (0.1, 0.25, 0.5))
    draw_text_small(490, 138, "Field Preview", (0.45, 0.45, 0.6))

    # Mini playing field
    pv_x, pv_y = 485, 150
    pv_w, pv_h = 140, 140
    field_w = float(B_RIGHT - B_LEFT)
    field_h = float(B_BOTTOM - B_TOP)

    # Mini border
    glColor3f(0.2, 0.35, 0.55)
    glLineWidth(1.5)
    glBegin(GL_LINE_LOOP)
    glVertex2f(pv_x, pv_y)
    glVertex2f(pv_x + pv_w, pv_y)
    glVertex2f(pv_x + pv_w, pv_y + pv_h)
    glVertex2f(pv_x, pv_y + pv_h)
    glEnd()
    glLineWidth(1.0)

    # Start position marker (left middle)
    start_pvx = pv_x + 3
    start_pvy = pv_y + pv_h // 2
    glColor3f(0.0, 0.9, 0.4)
    glPointSize(3)
    draw_circle(4, start_pvx, start_pvy)
    draw_text_small(start_pvx + 7, start_pvy + 4, "S", (0.0, 0.7, 0.3))

    # Target position marker (if X is set)
    if app_state == STATE_INPUT_Y and target_x > 0:
        tx_norm = (target_x - B_LEFT) / field_w if field_w > 0 else 0.5
        tgt_pvx = int(pv_x + tx_norm * pv_w)

        # Vertical line for X position
        glColor3f(1.0, 0.3, 0.3)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        glVertex2f(tgt_pvx, pv_y + 2)
        glVertex2f(tgt_pvx, pv_y + pv_h - 2)
        glEnd()

        draw_text_small(tgt_pvx - 5, pv_y + pv_h + 14, "X={}".format(int(target_x)),
                        (1.0, 0.4, 0.4))

    # Coordinate labels on preview
    draw_text_small(pv_x - 5, pv_y + pv_h + 28,
                    "({},{})".format(int(B_LEFT), int(B_TOP)), (0.3, 0.3, 0.45))
    draw_text_small(pv_x + pv_w - 45, pv_y + pv_h + 28,
                    "({},{})".format(int(B_RIGHT), int(B_BOTTOM)), (0.3, 0.3, 0.45))


# ================ STATE: SIMULATION RENDERING ================
def render_running():
    """Draw the active simulation — border, trail, searcher, target, HUD."""

    # Subtle background grid
    glColor3f(0.035, 0.035, 0.07)
    glLineWidth(0.5)
    glBegin(GL_LINES)
    for gx in range(int(B_LEFT), int(B_RIGHT) + 1, 50):
        glVertex2f(gx, B_TOP)
        glVertex2f(gx, B_BOTTOM)
    for gy in range(int(B_TOP), int(B_BOTTOM) + 1, 50):
        glVertex2f(B_LEFT, gy)
        glVertex2f(B_RIGHT, gy)
    glEnd()
    glLineWidth(1.0)

    # Border glow
    for i in range(4):
        off = (3 - i) * 2
        br = 0.12 + i * 0.06
        glColor3f(0.05 + br * 0.3, 0.12 + br * 0.55, 0.35 + br * 0.9)
        glLineWidth(float(4 - i))
        glBegin(GL_LINE_LOOP)
        glVertex2f(B_LEFT - off, B_TOP - off)
        glVertex2f(B_RIGHT + off, B_TOP - off)
        glVertex2f(B_RIGHT + off, B_BOTTOM + off)
        glVertex2f(B_LEFT - off, B_BOTTOM + off)
        glEnd()
    glLineWidth(1.0)

    # Start marker (diamond at left-middle)
    start_y = (B_TOP + B_BOTTOM) / 2
    glColor3f(0.25, 0.55, 0.25)
    glBegin(GL_LINE_LOOP)
    glVertex2f(B_LEFT, start_y - 6)
    glVertex2f(B_LEFT + 6, start_y)
    glVertex2f(B_LEFT, start_y + 6)
    glVertex2f(B_LEFT - 6, start_y)
    glEnd()

    # Dashed line from searcher to target
    dx_t = target_x - sx
    dy_t = target_y - sy
    dist = math.sqrt(dx_t * dx_t + dy_t * dy_t)
    if dist > 1:
        glPointSize(1)
        glColor3f(0.1, 0.1, 0.18)
        segs = 30
        glBegin(GL_POINTS)
        for i in range(0, segs, 2):
            t = i / segs
            glVertex2f(sx + dx_t * t, sy + dy_t * t)
        glEnd()

    # Trail (line strip + dots)
    n = len(trail)
    if n > 1:
        glLineWidth(1.5)
        glBegin(GL_LINE_STRIP)
        for i in range(n):
            t = i / n
            glColor3f(0.0, 0.12 + 0.35 * t, 0.18 + 0.45 * t)
            glVertex2f(trail[i][0], trail[i][1])
        glEnd()
        glLineWidth(1.0)

    # Target (pulsing glow + rings)
    t_now = time()
    pulse = 1.0 + 0.25 * math.sin(t_now * 5)
    tr = int(TARGET_RADIUS * pulse)

    glColor3f(0.35, 0.08, 0.08)
    glPointSize(1)
    draw_circle(tr + 8, int(target_x), int(target_y))

    glColor3f(1.0, 0.2, 0.2)
    glPointSize(3)
    draw_circle(tr, int(target_x), int(target_y))

    glColor3f(1.0, 0.55, 0.3)
    glPointSize(2)
    draw_circle(max(tr // 2, 2), int(target_x), int(target_y))

    glColor3f(1.0, 1.0, 0.5)
    glPointSize(5)
    glBegin(GL_POINTS)
    glVertex2f(target_x, target_y)
    glEnd()

    draw_text_small(target_x - 16, target_y - TARGET_RADIUS - 14,
                    "GOAL", (1.0, 0.4, 0.3))

    # Searcher (glow + core)
    glColor3f(0.0, 0.22, 0.1)
    glPointSize(1)
    draw_circle(SEARCHER_RADIUS + 6, int(sx), int(sy))

    glColor3f(0.0, 1.0, 0.5)
    glPointSize(3)
    draw_circle(SEARCHER_RADIUS, int(sx), int(sy))

    glColor3f(0.4, 1.0, 0.8)
    glPointSize(2)
    draw_circle(max(SEARCHER_RADIUS // 2, 2), int(sx), int(sy))

    glColor3f(0.8, 1.0, 0.9)
    glPointSize(4)
    glBegin(GL_POINTS)
    glVertex2f(sx, sy)
    glEnd()

    # Catch flash
    if catch_flash > 0:
        rf = int(20 + (1.0 - catch_flash) * 70)
        a = catch_flash
        glColor3f(1.0 * a, 0.8 * a, 0.2 * a)
        glPointSize(2)
        draw_circle(rf, int(catch_fx), int(catch_fy))

    # ---- HUD ----
    elapsed = time() - run_start_time
    series_name = available_series[selected_index].SERIES_NAME

    # Top-left info
    draw_text_small(10, 16, series_name, (0.3, 0.6, 0.3))
    draw_text(10, 38, "Time: {:.2f}s".format(elapsed), (1.0, 0.9, 0.3))
    draw_text_small(10, 56, "Target: ({}, {})".format(int(target_x), int(target_y)),
                    (0.55, 0.55, 0.75))

    # Top-right: distance
    draw_text_small(WIDTH - 155, 20, "Dist: {:.0f}px".format(dist), (0.55, 0.55, 0.75))

    # Bottom: movement info
    if movement:
        x_label = movement.get_x_label()
        y_label = movement.get_y_label()
    else:
        x_label = y_label = "?"
    x_arrow = "RIGHT" if x_dir > 0 else "LEFT"
    y_arrow = "DOWN" if y_dir > 0 else "UP"
    info = "{}  |  {}  |  X: {}  |  Y: {}".format(x_label, y_label, x_arrow, y_arrow)
    draw_text_small(B_LEFT, B_BOTTOM + 22, info, (0.4, 0.45, 0.6))

    # Sequence preview
    if movement and hasattr(movement, 'get_sequence_preview'):
        draw_text_small(B_LEFT, B_BOTTOM + 40,
                        movement.get_sequence_preview(), (0.22, 0.22, 0.35))


# ================ STATE: RESULT RENDERING =====================
def render_result():
    """Draw the result screen after catching the target."""
    t = time()

    # Animated background sparkles
    glPointSize(3)
    for i in range(30):
        bx = 50 + (i * 149) % 600
        by = 50 + ((i * 113 + int(t * 30 + i * 50)) % 250) % 600
        alpha = 0.05 + 0.04 * math.sin(t * 2 + i * 0.7)
        glColor3f(alpha * 2, alpha * 4, alpha)
        glBegin(GL_POINTS)
        glVertex2f(bx, by)
        glEnd()

    # Main result panel
    draw_panel(85, 80, 530, 460, (0.04, 0.04, 0.09), (0.15, 0.55, 0.25))

    # "TARGET FOUND!" title with animation
    r = 0.7 + 0.3 * math.sin(t * 3)
    g = 1.0
    b = 0.4 + 0.3 * math.sin(t * 2.2)
    draw_text_large(210, 125, "TARGET FOUND!", (r, g, b))

    # Decorative line
    glColor3f(0.15, 0.5, 0.25)
    glLineWidth(2)
    glBegin(GL_LINES)
    glVertex2f(110, 140)
    glVertex2f(590, 140)
    glEnd()
    glLineWidth(1)

    # Result details
    series_name = available_series[selected_index].SERIES_NAME
    draw_text(115, 180, "Series:  " + series_name, (0.55, 0.8, 1.0))
    draw_text(115, 205, "Target:  ({}, {})".format(int(target_x), int(target_y)),
              (0.6, 0.6, 0.8))

    # Time — large highlight
    draw_panel(110, 225, 470, 50, (0.06, 0.1, 0.06), (0.1, 0.4, 0.15))
    draw_text_large(130, 260, "Time:  {:.3f} seconds".format(result_time), (1.0, 0.95, 0.4))

    # Best time comparison
    if best_time_for_target is not None:
        if result_time <= best_time_for_target:
            draw_text(115, 310, "*** NEW BEST! ***", (0.0, 1.0, 0.5))
            if best_time_for_target != result_time:
                draw_text_small(115, 330,
                                "Previous best: {:.3f}s".format(best_time_for_target),
                                (0.5, 0.7, 0.5))
        else:
            draw_text(115, 310, "Best:  {:.3f}s".format(best_time_for_target),
                      (0.5, 0.85, 1.0))
            diff = result_time - best_time_for_target
            draw_text_small(115, 330, "(+{:.3f}s from best)".format(diff), (0.6, 0.5, 0.4))
    else:
        draw_text(115, 310, "First attempt at this target!", (0.5, 0.85, 1.0))

    # Score saved indicator
    if HAS_TRACKER:
        draw_text_small(115, 355, "Score saved to scores.xlsx", (0.3, 0.5, 0.3))
    else:
        draw_text_small(115, 355, "pip install openpyxl to enable score tracking",
                        (0.5, 0.35, 0.3))

    # Action options
    y_opt = 395
    opt_spacing = 28

    draw_text(115, y_opt, "[R]  Run Again  (same target & series)", (0.65, 0.9, 0.65))
    draw_text(115, y_opt + opt_spacing, "[N]  New Target  (same series)", (0.65, 0.8, 0.9))
    draw_text(115, y_opt + opt_spacing * 2, "[M]  Main Menu", (0.65, 0.65, 0.8))
    draw_text(115, y_opt + opt_spacing * 3, "[X]  Quit", (0.5, 0.5, 0.6))


# ====================== MAIN RENDER ==========================
def render():
    """Master display callback — dispatches to the active state renderer."""
    glClearColor(0.02, 0.02, 0.06, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    if app_state == STATE_MENU:
        render_menu()
    elif app_state in (STATE_INPUT_X, STATE_INPUT_Y):
        render_input()
    elif app_state == STATE_RUNNING:
        render_running()
    elif app_state == STATE_RESULT:
        render_result()

    glutSwapBuffers()


# ====================== GAME LOGIC ===========================
def reset_searcher():
    """Reset the searcher to start position (leftmost middle)."""
    global sx, sy, x_dir, y_dir, trail
    sx = float(B_LEFT)
    sy = float((B_TOP + B_BOTTOM) / 2)
    x_dir = 1
    y_dir = 1
    trail = []
    if movement:
        movement.reset()


def start_run():
    """Begin a new simulation run."""
    global run_start_time, app_state
    reset_searcher()
    run_start_time = time()
    app_state = STATE_RUNNING


def do_step():
    """
    Execute one movement step:
      - Get X/Y step sizes from the selected series
      - Move searcher by step * direction * scale
      - Bounce on walls (reverse direction + reset sequence)
      - Check target collision → transition to RESULT state
    """
    global sx, sy, x_dir, y_dir
    global catch_flash, catch_fx, catch_fy
    global result_time, best_time_for_target, app_state

    if app_state != STATE_RUNNING or movement is None:
        return

    # Record trail
    trail.append((sx, sy))
    if len(trail) > MAX_TRAIL:
        trail.pop(0)

    # Get next step from the active series
    x_step, y_step = movement.get_next_step()

    # Apply movement
    sx += x_step * x_dir * SCALE
    sy += y_step * y_dir * SCALE

    # --- X wall bounce ---
    if sx >= B_RIGHT:
        sx = float(B_RIGHT)
        x_dir *= -1
        movement.on_x_wall_hit()
    elif sx <= B_LEFT:
        sx = float(B_LEFT)
        x_dir *= -1
        movement.on_x_wall_hit()

    # --- Y wall bounce ---
    if sy >= B_BOTTOM:
        sy = float(B_BOTTOM)
        y_dir *= -1
        movement.on_y_wall_hit()
    elif sy <= B_TOP:
        sy = float(B_TOP)
        y_dir *= -1
        movement.on_y_wall_hit()

    # --- Target collision ---
    dx = sx - target_x
    dy = sy - target_y
    dist_sq = dx * dx + dy * dy
    hit_dist = SEARCHER_RADIUS + TARGET_RADIUS
    if dist_sq <= hit_dist * hit_dist:
        result_time = time() - run_start_time

        # Fetch best BEFORE updating so we can compare
        series_name = available_series[selected_index].SERIES_NAME
        if HAS_TRACKER:
            best_time_for_target = get_best_score(target_x, target_y, series_name)
            update_score(target_x, target_y, series_name, result_time)
        else:
            best_time_for_target = None

        # Trigger catch flash
        catch_flash = 1.0
        catch_fx, catch_fy = target_x, target_y

        app_state = STATE_RESULT


# ==================== INPUT HANDLING ==========================
def keyboard(key, mx, my):
    """GLUT keyboard callback — dispatches based on app state."""
    global app_state, selected_index, movement
    global input_buffer, input_error
    global target_x, target_y

    # ESC always quits
    if key == b'\x1b':
        sys.exit(0)

    # ----- STATE_MENU -----
    if app_state == STATE_MENU:
        if key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(available_series):
                selected_index = idx
                movement = available_series[idx].SeriesMovement()
                input_buffer = ""
                input_error = ""
                app_state = STATE_INPUT_X

    # ----- STATE_INPUT_X -----
    elif app_state == STATE_INPUT_X:
        if key in (b'm', b'M'):
            app_state = STATE_MENU
        elif key in (b'\r', b'\n'):
            # Submit X value
            if not input_buffer:
                input_error = "Please enter a value!"
                return
            try:
                val = int(input_buffer)
                min_x, max_x, _, _ = get_target_range()
                if min_x <= val <= max_x:
                    target_x = float(val)
                    input_buffer = ""
                    input_error = ""
                    app_state = STATE_INPUT_Y
                else:
                    input_error = "X must be between {} and {}!".format(min_x, max_x)
            except ValueError:
                input_error = "Enter a valid integer!"
        elif key in (b'\x08', b'\x7f'):  # Backspace / Delete
            input_buffer = input_buffer[:-1]
            input_error = ""
        elif key.isdigit():
            if len(input_buffer) < 5:
                input_buffer += key.decode()
                input_error = ""

    # ----- STATE_INPUT_Y -----
    elif app_state == STATE_INPUT_Y:
        if key in (b'm', b'M'):
            app_state = STATE_MENU
        elif key in (b'\r', b'\n'):
            # Submit Y value
            if not input_buffer:
                input_error = "Please enter a value!"
                return
            try:
                val = int(input_buffer)
                _, _, min_y, max_y = get_target_range()
                if min_y <= val <= max_y:
                    target_y = float(val)
                    input_buffer = ""
                    input_error = ""
                    start_run()
                else:
                    input_error = "Y must be between {} and {}!".format(min_y, max_y)
            except ValueError:
                input_error = "Enter a valid integer!"
        elif key in (b'\x08', b'\x7f'):
            input_buffer = input_buffer[:-1]
            input_error = ""
        elif key.isdigit():
            if len(input_buffer) < 5:
                input_buffer += key.decode()
                input_error = ""

    # ----- STATE_RUNNING -----
    elif app_state == STATE_RUNNING:
        pass  # simulation runs automatically, no input

    # ----- STATE_RESULT -----
    elif app_state == STATE_RESULT:
        if key in (b'r', b'R'):
            # Run again: same target, same series
            start_run()
        elif key in (b'n', b'N'):
            # New target: same series, go back to input
            input_buffer = ""
            input_error = ""
            app_state = STATE_INPUT_X
        elif key in (b'm', b'M'):
            # Main menu
            app_state = STATE_MENU


# ====================== FRAME LOOP ===========================
def frame(z):
    """Timer callback — drives the game loop at fixed FPS."""
    global catch_flash

    if app_state == STATE_RUNNING:
        if z % step_interval == 0:
            do_step()

    # Decay catch flash animation
    if catch_flash > 0:
        catch_flash -= 0.02

    glutPostRedisplay()
    glutTimerFunc(1000 // FPS, frame, (z + 1) % 100000)


# ==================== WINDOW SETUP ============================
def setup(w, h):
    """GLUT reshape callback — handles window resize."""
    global WIDTH, HEIGHT, B_LEFT, B_RIGHT, B_TOP, B_BOTTOM
    WIDTH, HEIGHT = w, h
    B_LEFT = BORDER_MARGIN
    B_RIGHT = w - BORDER_MARGIN
    B_TOP = BORDER_MARGIN
    B_BOTTOM = h - BORDER_MARGIN
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, w, h, 0, 0.0, 1.0)  # y=0 at top, y=h at bottom
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


# ========================== MAIN ==============================
if __name__ == "__main__":
    print("=" * 60)
    print("   TARGET DETECTION SIMULATION")
    print("=" * 60)

    # Discover available series modules
    discover_series()

    # Initialize GLUT window
    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE)
    glutInitWindowSize(WIDTH, HEIGHT)
    glutInitWindowPosition(100, 50)
    glutCreateWindow(b"TARGET DETECTION SIMULATION")
    glPointSize(2)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Register GLUT callbacks
    glutDisplayFunc(render)
    glutTimerFunc(0, frame, 0)
    glutReshapeFunc(setup)
    glutKeyboardFunc(keyboard)

    print("[Ready] Use the OpenGL window to interact.\n")
    glutMainLoop()
