"""
autonomous_pygame.py
Visualisasi real-time Agent OTONOM yang menjelajah & memutuskan sendiri
langkah demi langkah (TANPA search problem seperti BFS/DFS/UCS/A*),
memakai penalaran NAF (Negation as Failure) untuk menyimpulkan ruangan aman.

Berbeda dari visualize_pygame.py sebelumnya:
    - Rute TIDAK dihitung di muka (bukan BFS) -- direncanakan Agent sendiri,
      langkah demi langkah, berdasarkan apa yang baru ia ketahui (TELL).
    - Ada sistem HP (3), skor, dan risiko kematian (Musuh: -1 HP, Jebakan: mati).
    - Panel log menampilkan hasil ASK (backward chaining + NAF) yang benar-benar
      menentukan ke mana Agent melangkah.

Kontrol:
    SPACE       - lanjut ke langkah berikutnya
    R           - ulangi simulasi dari awal (rute bisa SAMA karena deterministik,
                  kecuali kamu mengubah TRUE_WORLD di wumpus_kb.py)
    ESC / close - keluar

Menjalankan:
    pip install pygame
    python autonomous_pygame.py
"""

import sys
import pygame

from wumpus_kb import TRUE_WORLD, START, DOOR, MAX_HP
from autonomous_agent import run_simulation

# ============================================================
# KONFIGURASI TAMPILAN
# ============================================================
WIDTH, HEIGHT = 1150, 660
MAP_WIDTH = 780
LOG_WIDTH = WIDTH - MAP_WIDTH
FPS = 60
MOVE_DURATION_MS = 1000

COLOR_BG = (24, 26, 34)
COLOR_LOG_BG = (18, 19, 25)
COLOR_EDGE = (90, 95, 110)
COLOR_ROOM = (70, 110, 170)
COLOR_ROOM_VISITED = (90, 140, 90)
COLOR_ROOM_BORDER = (200, 205, 215)
COLOR_START = (76, 175, 80)
COLOR_DOOR_CLOSED = (211, 47, 47)
COLOR_DOOR_OPEN = (255, 213, 79)
COLOR_AGENT = (255, 255, 255)
COLOR_TEXT = (230, 230, 235)
COLOR_TEXT_DIM = (140, 145, 155)
COLOR_TEXT_FAIL = (239, 83, 80)
COLOR_TEXT_OK = (129, 199, 132)
COLOR_TEXT_RULE = (129, 212, 250)
COLOR_TEXT_DECISION = (255, 202, 58)
COLOR_HP_FULL = (239, 83, 80)
COLOR_HP_EMPTY = (60, 40, 40)

ROOM_POS = {
    "R1": (140, 480),
    "R2": (140, 180),
    "R3": (430, 480),
    "R4": (430, 180),
    "R5": (700, 480),
    "R6": (700, 180),
}

ROOM_LABEL = {
    "R1": "R1 - Start",
    "R2": "R2 - ???",
    "R3": "R3 - ???",
    "R4": "R4 - ???",
    "R5": "R5 - ???",
    "R6": "R6 - Pintu",
}

TAG_COLOR = {
    "header": COLOR_TEXT_RULE,
    "percept": COLOR_TEXT_DIM,
    "ask": COLOR_TEXT_RULE,
    "decision": COLOR_TEXT_DECISION,
    "action": COLOR_TEXT,
    "damage": COLOR_TEXT_FAIL,
    "death": COLOR_TEXT_FAIL,
    "win": COLOR_TEXT_OK,
    "fail": COLOR_TEXT_FAIL,
    "info": COLOR_TEXT,
}


def build_adjacency_edges():
    from wumpus_kb import TERHUBUNG
    return TERHUBUNG


class LogPanel:
    def __init__(self, font):
        self.lines = []
        self.font = font

    def add(self, text, color=COLOR_TEXT):
        self.lines.append((text, color))

    def draw(self, surface):
        pygame.draw.rect(surface, COLOR_LOG_BG, (MAP_WIDTH, 0, LOG_WIDTH, HEIGHT))
        line_height = 19
        max_lines = HEIGHT // line_height - 1
        visible = self.lines[-max_lines:]
        y = 10
        for text, color in visible:
            rendered = self.font.render(text, True, color)
            surface.blit(rendered, (MAP_WIDTH + 12, y))
            y += line_height


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Agent Otonom - Pencarian Kunci (NAF Reasoning, Real-time)")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 14)
    font_room = pygame.font.SysFont("arial", 14, bold=True)
    font_title = pygame.font.SysFont("arial", 20, bold=True)
    font_hud = pygame.font.SysFont("arial", 16, bold=True)

    log_panel = LogPanel(font)

    def reset_state():
        sim = run_simulation()
        return {
            "sim": sim,
            "action_index": 0,
            "log_index": 0,          # posisi baca di sim.log (untuk narasi bertahap)
            "log_cursor": {},        # pemetaan action_index -> berapa baris sim.log sudah ditampilkan
            "agent_room": START,
            "agent_pos": list(ROOM_POS[START]),
            "moving": False,
            "move_from": None,
            "move_to": None,
            "move_start_time": 0,
            "has_key": False,
            "door_open": False,
            "hp": MAX_HP,
            "score": 0,
            "visited": {START},
            "game_over": False,
            "outcome_shown": False,
            "flash_room": None,
            "flash_until": 0,
            "flash_color": None,
        }

    state = reset_state()
    log_panel.lines = []
    log_panel.add("=== AGENT OTONOM: NAF REASONING ===", COLOR_TEXT_RULE)
    log_panel.add("Agent memutuskan sendiri arah gerak -- TANPA BFS/DFS/UCS/A*.", COLOR_TEXT_DIM)
    log_panel.add("Tekan SPACE untuk mulai / lanjut satu event log.", COLOR_TEXT_DIM)
    log_panel.add("Tekan R untuk mengulang simulasi.", COLOR_TEXT_DIM)

    # Kelompokkan sim.log per action, supaya SPACE terasa alami:
    # setiap penekanan SPACE menampilkan SATU baris log berikutnya secara berurutan.
    def total_log_lines(state):
        return len(state["sim"].log)

    def advance_log_line():
        """Tampilkan satu baris log berikutnya dari sim.log, dan proses efek
        sampingnya (mulai animasi gerak, update HP/skor/status) begitu baris
        yang relevan tercapai."""
        sim = state["sim"]
        if state["log_index"] >= len(sim.log):
            return
        text, tag = sim.log[state["log_index"]]
        state["log_index"] += 1
        log_panel.add(text, TAG_COLOR.get(tag, COLOR_TEXT))

        if tag == "action" and "Ambil Kunci" in text:
            state["has_key"] = True
            state["score"] -= 1
        elif tag == "action" and "Bergerak" in text:
            # Format: "[AKSI] Bergerak R1 -> R2  (skor -1, sekarang -1)"
            parts = text.split("Bergerak")[1].split("(")[0].strip()
            frm, to = [p.strip() for p in parts.split("->")]
            state["moving"] = True
            state["move_from"] = frm
            state["move_to"] = to
            state["move_start_time"] = pygame.time.get_ticks()
            state["score"] -= 1
        elif tag == "action" and "Buka Pintu" in text:
            state["score"] -= 1
        elif tag == "damage":
            state["hp"] -= 1
            state["flash_room"] = state["agent_room"]
            state["flash_until"] = pygame.time.get_ticks() + 500
            state["flash_color"] = (200, 60, 60)
        elif tag == "win":
            state["door_open"] = True
            state["score"] += 1000
            state["game_over"] = True
        elif tag == "death":
            state["game_over"] = True
            state["score"] -= 1000
            state["flash_room"] = state["agent_room"] if not state["moving"] else state["move_to"]
            state["flash_until"] = pygame.time.get_ticks() + 900
            state["flash_color"] = (150, 0, 0)

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
                    if not state["moving"]:
                        advance_log_line()
                elif event.key == pygame.K_r:
                    state = reset_state()
                    log_panel.lines = []
                    log_panel.add("=== DIULANG DARI AWAL ===", COLOR_TEXT_RULE)

        # update animasi gerak
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
                state["visited"].add(state["move_to"])

        # ---- gambar ----
        screen.fill(COLOR_BG)
        title = font_title.render("Agent Otonom: Reasoning NAF (bukan search problem)", True, COLOR_TEXT)
        screen.blit(title, (20, 14))

        for a, b in build_adjacency_edges():
            pygame.draw.line(screen, COLOR_EDGE, ROOM_POS[a], ROOM_POS[b], 3)

        now = pygame.time.get_ticks()
        for room, pos in ROOM_POS.items():
            if room == START:
                color = COLOR_START
            elif room == DOOR:
                color = COLOR_DOOR_OPEN if state["door_open"] else COLOR_DOOR_CLOSED
            elif room in state["visited"]:
                color = COLOR_ROOM_VISITED
            else:
                color = COLOR_ROOM

            if state["flash_room"] == room and now < state["flash_until"]:
                color = state["flash_color"]

            pygame.draw.circle(screen, color, pos, 34)
            pygame.draw.circle(screen, COLOR_ROOM_BORDER, pos, 34, 2)

            # Sembunyikan isi ruangan yang belum dikunjungi (fog of war sederhana)
            if room in state["visited"] or room == START or room == DOOR:
                label_text = room
                if room in TRUE_WORLD["AdaMusuh"] and room in state["visited"]:
                    label_text += " (Musuh)"
                elif room in TRUE_WORLD["AdaJebakan"] and room in state["visited"]:
                    label_text += " (Jebakan)"
                elif room in TRUE_WORLD["AdaKunci"] and room in state["visited"]:
                    label_text += " (Kunci)"
                elif room == DOOR:
                    label_text += " (Pintu)"
            else:
                label_text = f"{room} - ???"

            label = font_room.render(label_text, True, COLOR_TEXT)
            screen.blit(label, (pos[0] - label.get_width() // 2, pos[1] + 42))

        # Agent
        pygame.draw.circle(screen, COLOR_AGENT, (int(state["agent_pos"][0]), int(state["agent_pos"][1])), 12)
        pygame.draw.circle(screen, (0, 0, 0), (int(state["agent_pos"][0]), int(state["agent_pos"][1])), 12, 2)
        if state["has_key"]:
            key_label = font_room.render("+Kunci", True, (255, 215, 0))
            screen.blit(key_label, (int(state["agent_pos"][0]) - 22, int(state["agent_pos"][1]) - 32))

        # HUD: HP + Skor
        hud_y = HEIGHT - 46
        hp_label = font_hud.render("HP:", True, COLOR_TEXT)
        screen.blit(hp_label, (20, hud_y))
        for i in range(MAX_HP):
            hx = 55 + i * 26
            color = COLOR_HP_FULL if i < state["hp"] else COLOR_HP_EMPTY
            pygame.draw.circle(screen, color, (hx, hud_y + 10), 10)
            pygame.draw.circle(screen, COLOR_ROOM_BORDER, (hx, hud_y + 10), 10, 1)

        score_label = font_hud.render(f"Skor: {state['score']}", True, COLOR_TEXT)
        screen.blit(score_label, (200, hud_y))

        status_text = f"Ruangan: {state['agent_room']}"
        if state["game_over"]:
            status_text += "   |   GAME OVER -- tekan R untuk ulang"
        status_render = font.render(status_text, True, COLOR_TEXT_DIM)
        screen.blit(status_render, (20, hud_y + 26))

        log_panel.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
