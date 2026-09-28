"""
autonomous_agent.py
Agent OTONOM yang menjelajah peta dan memutuskan sendiri langkah demi langkah
(TANPA search problem seperti BFS/DFS/UCS/A*), memakai penalaran logika
(forward-style TELL persepsi + backward chaining berbasis NAF untuk menyimpulkan
ruangan aman), mirip pendekatan asli Wumpus World.

Aturan permainan:
    - Agent punya 3 HP.
    - Masuk ruangan berisi Musuh -> -1 HP (bisa selamat sampai beberapa kali).
    - Masuk ruangan berisi Jebakan -> mati seketika.
    - HP habis (0) -> mati.
    - Skor: +1000 kalau berhasil buka pintu, -1000 kalau mati,
            -1 untuk setiap aksi (bergerak/ambil kunci/buka pintu).
"""

from backward_chaining import bc_ask
from logic_engine import format_atom
from wumpus_kb import (
    TRUE_WORLD, TERHUBUNG, START, DOOR, MAX_HP,
    adjacency, known_facts_awal, AGENT_RULES, GOAL_PINTU_TERBUKA,
)


class SimulationResult:
    def __init__(self):
        self.log = []          # list of (text, tag) untuk ditampilkan
        self.score = 0
        self.hp = MAX_HP
        self.outcome = None    # "menang" / "mati_musuh" / "mati_jebakan" / "buntu"
        self.path = [START]    # urutan ruangan yang dikunjungi (untuk animasi)
        self.action_log = []   # urutan aksi terstruktur, dipakai animasi pygame


def _has_fact(facts, atom):
    return atom in facts


def run_simulation(max_steps=30):
    result = SimulationResult()
    facts = known_facts_awal()
    adj = adjacency()
    current = START
    has_key = False

    def log(text, tag="info"):
        result.log.append((text, tag))

    log(f"=== MULAI: Agent di {START}, HP={result.hp} ===", "header")

    for step in range(max_steps):
        # ---------------------------------------------------------
        # 1) SENSING: environment menghitung persepsi ruangan saat ini
        #    dan TELL ke KB Agent (hanya jika TRUE)
        # ---------------------------------------------------------
        neighbors_now = adj.get(current, set())
        ada_musuh_tetangga = any(n in TRUE_WORLD["AdaMusuh"] for n in neighbors_now)
        ada_jebakan_tetangga = any(n in TRUE_WORLD["AdaJebakan"] for n in neighbors_now)
        ada_kunci_disini = current in TRUE_WORLD["AdaKunci"]

        if ada_musuh_tetangga and not _has_fact(facts, ("Berbau", current)):
            facts.append(("Berbau", current))
            log(f"  [TELL] Berbau({current})  <- tercium bau di ruangan ini", "percept")
        if ada_jebakan_tetangga and not _has_fact(facts, ("Berangin", current)):
            facts.append(("Berangin", current))
            log(f"  [TELL] Berangin({current})  <- terasa angin di ruangan ini", "percept")
        if ada_kunci_disini and not _has_fact(facts, ("Berkilau", current)):
            facts.append(("Berkilau", current))
            log(f"  [TELL] Berkilau({current})  <- ada kilauan di ruangan ini", "percept")

        # ---------------------------------------------------------
        # 2) AKSI: ambil kunci jika ada kilauan & belum punya kunci
        # ---------------------------------------------------------
        if ada_kunci_disini and not has_key:
            has_key = True
            facts.append(("MemilikiKunci", "Agent"))
            result.score -= 1
            log(f"[AKSI] Ambil Kunci di {current}  (skor -1, sekarang {result.score})", "action")
            result.action_log.append({"type": "pickup", "room": current})
            continue

        # ---------------------------------------------------------
        # 3) AKSI: coba buka pintu jika sedang di ruang Pintu & punya kunci
        # ---------------------------------------------------------
        if current == DOOR and has_key:
            bc = bc_ask(facts, AGENT_RULES, GOAL_PINTU_TERBUKA)
            result.score -= 1
            log(f"[AKSI] Coba Buka Pintu di {current}  (skor -1, sekarang {result.score})", "action")
            log(f"  [ASK backward chaining] {format_atom(GOAL_PINTU_TERBUKA)}? "
                f"-> {'TERBUKTI' if bc['proven'] else 'GAGAL'} ({bc['goals_checked']} goal dicek)",
                "ask")
            result.action_log.append({"type": "open_door", "room": current, "proven": bc["proven"]})
            if bc["proven"]:
                result.score += 1000
                result.outcome = "menang"
                log(f"*** PINTU TERBUKA! Agent MENANG. Skor akhir: {result.score}, HP: {result.hp} ***", "win")
                return result
            else:
                log("  Pintu belum bisa dibuka -- syarat belum lengkap.", "fail")

        # ---------------------------------------------------------
        # 4) KEPUTUSAN GERAK: tanya AmanPasti(y) untuk tiap tetangga
        #    yang BELUM dikunjungi, via backward chaining + NAF
        # ---------------------------------------------------------
        unvisited = sorted(n for n in neighbors_now if not _has_fact(facts, ("Dikunjungi", n)))

        candidates_safe = []
        for n in unvisited:
            bc = bc_ask(facts, AGENT_RULES, ("AmanPasti", n))
            log(f"  [ASK backward chaining] AmanPasti({n})? -> "
                f"{'TERBUKTI AMAN' if bc['proven'] else 'tidak terbukti'} "
                f"({bc['goals_checked']} goal dicek)", "ask")
            if bc["proven"]:
                candidates_safe.append(n)

        target = None
        alasan = ""
        if DOOR in candidates_safe:
            target, alasan = DOOR, "menuju Pintu (terbukti aman)"
        elif candidates_safe:
            target, alasan = candidates_safe[0], "terbukti aman (NAF berhasil)"
        elif has_key and DOOR in unvisited:
            target, alasan = DOOR, "menuju Pintu (belum terbukti aman, tapi ini tujuan akhir)"
        elif unvisited:
            target, alasan = unvisited[0], "SPEKULASI/GAMBLE -- tidak ada info cukup"
        else:
            visited_neighbors = sorted(n for n in neighbors_now if n != current)
            if visited_neighbors:
                target, alasan = visited_neighbors[0], "backtrack (semua tetangga sudah dikunjungi)"
            else:
                result.outcome = "buntu"
                log("*** BUNTU: tidak ada ruangan yang bisa dituju. ***", "fail")
                return result

        log(f"[KEPUTUSAN] Pilih bergerak ke {target}  -- alasan: {alasan}", "decision")

        # ---------------------------------------------------------
        # 5) EKSEKUSI GERAK + cek bahaya nyata di ruangan tujuan
        # ---------------------------------------------------------
        result.score -= 1
        log(f"[AKSI] Bergerak {current} -> {target}  (skor -1, sekarang {result.score})", "action")
        result.action_log.append({"type": "move", "from": current, "to": target})

        move_entry = result.action_log[-1]
        move_entry["hazard"] = None

        if target in TRUE_WORLD["AdaJebakan"]:
            result.outcome = "mati_jebakan"
            result.score -= 1000
            move_entry["hazard"] = "jebakan"
            move_entry["hp_after"] = result.hp
            move_entry["game_over"] = True
            log(f"*** Agent MENGINJAK JEBAKAN di {target}! MATI SEKETIKA. "
                f"Skor akhir: {result.score} ***", "death")
            result.path.append(target)
            return result

        if target in TRUE_WORLD["AdaMusuh"]:
            result.hp -= 1
            move_entry["hazard"] = "musuh"
            log(f"  Agent BERTEMU MUSUH di {target}! HP -1 (sekarang {result.hp})", "damage")
            if result.hp <= 0:
                result.outcome = "mati_musuh"
                result.score -= 1000
                move_entry["hp_after"] = result.hp
                move_entry["game_over"] = True
                log(f"*** HP HABIS! Agent MATI. Skor akhir: {result.score} ***", "death")
                result.path.append(target)
                return result

        move_entry["hp_after"] = result.hp
        move_entry["game_over"] = False
        current = target
        facts.append(("DiRuangan", "Agent", current))
        facts.append(("Dikunjungi", current))
        result.path.append(current)

    result.outcome = "buntu"
    log("*** Batas langkah maksimum tercapai tanpa solusi. ***", "fail")
    return result


if __name__ == "__main__":
    hasil = run_simulation()
    for text, tag in hasil.log:
        print(text)
    print()
    print(f"Outcome  : {hasil.outcome}")
    print(f"Skor     : {hasil.score}")
    print(f"HP akhir : {hasil.hp}")
    print(f"Rute     : {' -> '.join(hasil.path)}")
