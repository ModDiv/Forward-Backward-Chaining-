"""
visualize_pygame.py
Visualisasi real-time untuk studi kasus "Pencarian Kunci Menuju Pintu Gerbang".

Menampilkan:
    - Peta 6 ruangan (graph) dengan ikon Kunci/Musuh/Jebakan.
    - Animasi Agent berpindah ruangan mengikuti rute (R1 -> R4 -> R6).
    - Log real-time trace Forward Chaining & Backward Chaining di panel kanan.

Kontrol:
    SPACE       - lanjut ke langkah berikutnya
    R           - ulangi dari awal
    ESC / close - keluar

Menjalankan:
    pip install pygame
    python visualize_pygame.py
"""

import sys
from collections import deque

import pygame

from kb_data import FACTS, RULES, GOAL, update_position
from forward_chaining import forward_chaining
from backward_chaining import bc_ask
from logic_engine import format_atom

# ============================================================
# KONFIGURASI TAMPILAN
# ============================================================
WIDTH, HEIGHT = 1100, 640
MAP_WIDTH = 780
LOG_WIDTH = WIDTH - MAP_WIDTH
FPS = 60
MOVE_DURATION_MS = 1200

COLOR_BG = (24, 26, 34)
COLOR_LOG_BG = (18, 19, 25)
COLOR_EDGE = (90, 95, 110)
COLOR_ROOM = (70, 110, 170)
COLOR_ROOM_BORDER = (200, 205, 215)
COLOR_START = (76, 175, 80)
COLOR_GOAL_CLOSED = (211, 47, 47)
COLOR_GOAL_OPEN = (255, 213, 79)
COLOR_AGENT = (255, 255, 255)
COLOR_TEXT = (230, 230, 235)
COLOR_TEXT_DIM = (140, 145, 155)
COLOR_TEXT_FAIL = (239, 83, 80)
COLOR_TEXT_OK = (129, 199, 132)
COLOR_TEXT_RULE = (129, 212, 250)

# Posisi ruangan di kanvas (pixel), mengikuti layout peta di README:
#   R2(Musuh) --- R4(Kunci) --- R6(Pintu)
#    |               |              |
#   R1(Start) --- R3(Jebakan) --- R5(Aman)
ROOM_POS = {
    "R1": (140, 460),
    "R2": (140, 160),
    "R3": (430, 460),
    "R4": (430, 160),
    "R5": (700, 460),
    "R6": (700, 160),
}

ROOM_LABEL = {
    "R1": "R1 - Start",
    "R2": "R2 - Musuh",
    "R3": "R3 - Jebakan",
    "R4": "R4 - Kunci",
    "R5": "R5 - Aman",
    "R6": "R6 - Pintu",
}


def build_adjacency(facts):
    adj = {}
    for f in facts:
        if f[0] == "Terhubung":
            a, b = f[1], f[2]
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
    return adj


def bfs_route(adj, start, goal):
    frontier = deque([[start]])
    visited = {start}
    while frontier:
        path = frontier.popleft()
        node = path[-1]
        if node == goal:
            return path
        for neighbor in sorted(adj.get(node, [])):
            if neighbor not in visited:
                visited.add(neighbor)
                frontier.append(path + [neighbor])
    return None


# ============================================================
# LOG PANEL — menampung baris teks yang tumbuh seiring waktu
# ============================================================
class LogPanel:
    def __init__(self, font, font_bold):
        self.lines = []  # list of (text, color)
        self.font = font
        self.font_bold = font_bold

    def add(self, text, color=COLOR_TEXT):
        self.lines.append((text, color))

    def add_header(self, text):
        self.lines.append(("", COLOR_TEXT))
        self.lines.append((text, COLOR_TEXT_RULE))
        self.lines.append(("-" * 34, COLOR_TEXT_DIM))

    def draw(self, surface):
        pygame.draw.rect(surface, COLOR_LOG_BG, (MAP_WIDTH, 0, LOG_WIDTH, HEIGHT))
        line_height = 20
        max_lines = HEIGHT // line_height - 1
        visible = self.lines[-max_lines:]
        y = 12
        for text, color in visible:
            if text.startswith("-"):
                rendered = self.font.render(text, True, color)
            else:
                rendered = self.font.render(text, True, color)
            surface.blit(rendered, (MAP_WIDTH + 14, y))
            y += line_height


# ============================================================
# SCRIPT LANGKAH DEMI LANGKAH (state machine sederhana)
# ============================================================
def build_script():
    """Menyusun urutan 'adegan' yang akan diperagakan, masing-masing berupa
    dict beraksi salah satu dari: 'log', 'move', 'setflag'."""
    adj = build_adjacency(FACTS)
    route_to_key = bfs_route(adj, "R1", "R4")
    route_to_door = bfs_route(adj, "R4", "R6")

    script = []

    # ---- Skenario 1: backward chaining dari kondisi awal (gagal) ----
    script.append({"type": "log", "header": "SKENARIO 1: Kondisi Awal (Agent di R1)"})
    bc1 = bc_ask(FACTS, RULES, GOAL)
    script.append({"type": "log_trace_bc", "result": bc1})
    script.append({"type": "log", "text": f"Hasil: {'BERHASIL' if bc1['proven'] else 'GAGAL'} membuktikan {format_atom(GOAL)}",
                   "color": "ok" if bc1["proven"] else "fail"})

    # ---- Bergerak ke R4 (ambil kunci) ----
    for i in range(len(route_to_key) - 1):
        script.append({"type": "move", "from": route_to_key[i], "to": route_to_key[i + 1]})

    script.append({"type": "log", "header": f"TELL: DiRuangan(Agent, R4) -- Agent sampai di ruang Kunci"})
    script.append({"type": "setflag", "flag": "facts", "value": "at_key"})
    fc2a = forward_chaining(update_position(FACTS, "R4"), RULES)
    script.append({"type": "log_trace_fc", "result": fc2a, "label": "Forward Chaining setelah sampai di R4"})
    script.append({"type": "setflag", "flag": "has_key", "value": True})

    # ---- Bergerak ke R6 (buka pintu) ----
    for i in range(len(route_to_door) - 1):
        script.append({"type": "move", "from": route_to_door[i], "to": route_to_door[i + 1]})

    script.append({"type": "log", "header": "TELL: DiRuangan(Agent, R6) -- Agent sampai di Pintu"})
    facts_at_door = update_position(fc2a["facts"], "R6")
    fc2b = forward_chaining(facts_at_door, RULES)
    script.append({"type": "log_trace_fc", "result": fc2b, "label": "Forward Chaining setelah sampai di R6"})

    bc2 = bc_ask(facts_at_door, RULES, GOAL)
    script.append({"type": "log_trace_bc", "result": bc2, "label": "Backward Chaining (verifikasi ulang)"})
    proven = ("PintuTerbuka",) in fc2b["facts"]
    script.append({"type": "log", "text": f"Hasil akhir: {'PINTU TERBUKA!' if proven else 'GAGAL'}",
                   "color": "ok" if proven else "fail"})
    if proven:
        script.append({"type": "setflag", "flag": "door_open", "value": True})

    return script


# ============================================================
# MAIN LOOP
# ============================================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Logic Agent - Pencarian Kunci Menuju Pintu (Real-time)")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 15)
    font_bold = pygame.font.SysFont("consolas", 15, bold=True)
    font_room = pygame.font.SysFont("arial", 14, bold=True)
    font_title = pygame.font.SysFont("arial", 20, bold=True)

    log_panel = LogPanel(font, font_bold)

    def reset_state():
        return {
            "script": build_script(),
            "step_index": 0,
            "agent_room": "R1",
            "agent_pos": list(ROOM_POS["R1"]),
            "moving": False,
            "move_from": None,
            "move_to": None,
            "move_start_time": 0,
            "has_key": False,
            "door_open": False,
            "trace_queue": [],   # antrian baris log yang masih perlu "diketik" satu-satu
            "waiting_input": True,
        }

    state = reset_state()
    log_panel.lines = []
    log_panel.add("=== LOGIC AGENT: PENCARIAN KUNCI ===", COLOR_TEXT_RULE)
    log_panel.add("Tekan SPACE untuk mulai / lanjut langkah.", COLOR_TEXT_DIM)
    log_panel.add("Tekan R untuk mengulang dari awal.", COLOR_TEXT_DIM)

    def color_of(tag):
        return {"ok": COLOR_TEXT_OK, "fail": COLOR_TEXT_FAIL, "rule": COLOR_TEXT_RULE}.get(tag, COLOR_TEXT)

    def enqueue_bc_trace(result, label=None):
        if label:
            state["trace_queue"].append((f"[Backward Chaining] {label}", COLOR_TEXT_RULE))
        for t in result["trace"]:
            indent = "  " * t["depth"]
            if t["type"] == "goal":
                state["trace_queue"].append((f"{indent}? {format_atom(t['goal'])}", COLOR_TEXT))
            elif t["type"] == "fact_match":
                state["trace_queue"].append((f"{indent}  = fakta {format_atom(t['fact'])}", COLOR_TEXT_OK))
            elif t["type"] == "rule_match":
                state["trace_queue"].append((f"{indent}  > aturan {t['rule']}", COLOR_TEXT_RULE))
            elif t["type"] == "fail":
                state["trace_queue"].append((f"{indent}  x GAGAL", COLOR_TEXT_FAIL))
        state["trace_queue"].append((
            f"-> {'TERBUKTI' if result['proven'] else 'TIDAK TERBUKTI'} "
            f"({result['goals_checked']} goal dicek)",
            COLOR_TEXT_OK if result["proven"] else COLOR_TEXT_FAIL,
        ))

    def enqueue_fc_trace(result, label=None):
        if label:
            state["trace_queue"].append((f"[Forward Chaining] {label}", COLOR_TEXT_RULE))
        for t in result["trace"]:
            state["trace_queue"].append((f"  {t['rule']} => {format_atom(t['fact'])}", COLOR_TEXT))
        state["trace_queue"].append((
            f"-> {result['rules_fired']} rules fired, {result['iterations']} iterasi",
            COLOR_TEXT_DIM,
        ))

    def process_step():
        """Mengambil langkah berikutnya dari script dan mengeksekusinya."""
        script = state["script"]
        if state["step_index"] >= len(script):
            return
        step = script[state["step_index"]]
        state["step_index"] += 1

        if step["type"] == "log":
            if "header" in step:
                state["trace_queue"].append(("", COLOR_TEXT))
                state["trace_queue"].append((step["header"], COLOR_TEXT_RULE))
                state["trace_queue"].append(("-" * 34, COLOR_TEXT_DIM))
            else:
                state["trace_queue"].append((step["text"], color_of(step.get("color"))))

        elif step["type"] == "log_trace_bc":
            enqueue_bc_trace(step["result"], step.get("label"))

        elif step["type"] == "log_trace_fc":
            enqueue_fc_trace(step["result"], step.get("label"))

        elif step["type"] == "setflag":
            state[step["flag"]] = step["value"]

        elif step["type"] == "move":
            state["moving"] = True
            state["move_from"] = step["from"]
            state["move_to"] = step["to"]
            state["move_start_time"] = pygame.time.get_ticks()

    # proses semua step non-"move" secara berurutan sampai ketemu 'move' atau habis,
    # supaya SPACE terasa alami: satu SPACE = satu blok log ATAU satu animasi gerak
    def advance():
        if state["moving"]:
            return  # sedang animasi, tunggu selesai dulu
        while state["step_index"] < len(state["script"]):
            step = state["script"][state["step_index"]]
            process_step()
            if step["type"] == "move":
                break
            if step["type"] in ("log", "log_trace_bc", "log_trace_fc"):
                break

    running = True
    while running:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    advance()
                elif event.key == pygame.K_r:
                    state = reset_state()
                    log_panel.lines = []
                    log_panel.add("=== DIULANG DARI AWAL ===", COLOR_TEXT_RULE)

        # keluarkan 1-2 baris dari trace_queue per frame supaya terasa "real-time mengetik"
        for _ in range(2):
            if state["trace_queue"]:
                text, color = state["trace_queue"].pop(0)
                log_panel.add(text, color)

        # update animasi gerak Agent
        if state["moving"]:
            elapsed = pygame.time.get_ticks() - state["move_start_time"]
            t = min(1.0, elapsed / MOVE_DURATION_MS)
            fx, fy = ROOM_POS[state["move_from"]]
            tx, ty = ROOM_POS[state["move_to"]]
            state["agent_pos"][0] = fx + (tx - fx) * t
            state["agent_pos"][1] = fy + (ty - fy) * t
            if t >= 1.0:
                state["moving"] = False
                state["agent_room"] = state["move_to"]

        # ---- gambar ----
        screen.fill(COLOR_BG)

        title = font_title.render("Peta: Pencarian Kunci Menuju Pintu", True, COLOR_TEXT)
        screen.blit(title, (20, 16))

        adj = build_adjacency(FACTS)
        drawn_edges = set()
        for a, neighbors in adj.items():
            for b in neighbors:
                key = tuple(sorted((a, b)))
                if key in drawn_edges:
                    continue
                drawn_edges.add(key)
                pygame.draw.line(screen, COLOR_EDGE, ROOM_POS[a], ROOM_POS[b], 3)

        for room, pos in ROOM_POS.items():
            if room == "R1":
                color = COLOR_START
            elif room == "R6":
                color = COLOR_GOAL_OPEN if state["door_open"] else COLOR_GOAL_CLOSED
            else:
                color = COLOR_ROOM
            pygame.draw.circle(screen, color, pos, 34)
            pygame.draw.circle(screen, COLOR_ROOM_BORDER, pos, 34, 2)

            label = font_room.render(ROOM_LABEL[room], True, COLOR_TEXT)
            screen.blit(label, (pos[0] - label.get_width() // 2, pos[1] + 42))

        # ikon status ruangan
        icon_font = pygame.font.SysFont("arial", 18, bold=True)
        r4_pos = ROOM_POS["R4"]
        if not state["has_key"]:
            k = icon_font.render("K", True, (255, 215, 0))
            screen.blit(k, (r4_pos[0] - 6, r4_pos[1] - 10))
        r2_pos = ROOM_POS["R2"]
        m = icon_font.render("M", True, (255, 100, 100))
        screen.blit(m, (r2_pos[0] - 6, r2_pos[1] - 10))
        r3_pos = ROOM_POS["R3"]
        j = icon_font.render("J", True, (255, 180, 90))
        screen.blit(j, (r3_pos[0] - 6, r3_pos[1] - 10))

        # gambar Agent
        pygame.draw.circle(screen, COLOR_AGENT, (int(state["agent_pos"][0]), int(state["agent_pos"][1])), 12)
        pygame.draw.circle(screen, (0, 0, 0), (int(state["agent_pos"][0]), int(state["agent_pos"][1])), 12, 2)
        if state["has_key"]:
            key_label = font_room.render("+Kunci", True, (255, 215, 0))
            screen.blit(key_label, (int(state["agent_pos"][0]) - 22, int(state["agent_pos"][1]) - 32))

        # status bar bawah
        status = f"Agent di: {state['agent_room']}   |   Bawa Kunci: {'Ya' if state['has_key'] else 'Tidak'}   |   Pintu: {'TERBUKA' if state['door_open'] else 'Terkunci'}"
        status_render = font.render(status, True, COLOR_TEXT_DIM)
        screen.blit(status_render, (20, HEIGHT - 30))

        log_panel.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
