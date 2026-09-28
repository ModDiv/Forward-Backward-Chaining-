"""
main.py
Menjalankan dan membandingkan Forward Chaining vs Backward Chaining
pada studi kasus "Pencarian Kunci Menuju Pintu Gerbang".

Skenario 1: Kondisi awal - Agent masih di R1 (belum bergerak).
Skenario 2: Setelah Agent bergerak (TELL posisi baru) - Agent ambil kunci
            di R4, lalu pindah ke R6 (pintu).
"""

from collections import deque

from kb_data import FACTS, RULES, GOAL, update_position
from forward_chaining import forward_chaining
from backward_chaining import bc_ask
from logic_engine import format_atom


# ============================================================
# Helper: BFS sederhana untuk mencari rute (reuse konsep dari tugas Search)
# ============================================================
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
# Helper cetak hasil
# ============================================================
def print_forward_result(label, result):
    print(f"--- Forward Chaining: {label} ---")
    print(f"Jumlah rules fired : {result['rules_fired']}")
    print(f"Jumlah iterasi      : {result['iterations']}")
    print("Fakta baru yang diturunkan:")
    for t in result["trace"]:
        print(f"   [iter {t['iteration']}] {t['rule']:16s} -> {format_atom(t['fact'])}")
    print(f"Apakah 'PintuTerbuka()' berhasil diturunkan? "
          f"{'YA' if ('PintuTerbuka',) in result['facts'] else 'TIDAK'}")
    print()


def print_backward_result(label, result):
    print(f"--- Backward Chaining: {label} ---")
    print(f"Goal                : {format_atom(GOAL)}")
    print(f"Jumlah goal dicek   : {result['goals_checked']}")
    print(f"Berhasil dibuktikan?: {'YA' if result['proven'] else 'TIDAK'}")
    print("Trace penelusuran (goal demi goal):")
    for t in result["trace"]:
        indent = "   " * (t["depth"] + 1)
        if t["type"] == "goal":
            print(f"{indent}? Membuktikan {format_atom(t['goal'])}")
        elif t["type"] == "fact_match":
            print(f"{indent}  -> cocok dengan fakta {format_atom(t['fact'])}")
        elif t["type"] == "rule_match":
            print(f"{indent}  -> coba aturan {t['rule']}")
        elif t["type"] == "fail":
            print(f"{indent}  -> GAGAL, tidak ada fakta/aturan yang cocok")
    print()


if __name__ == "__main__":
    # ============================================================
    # SKENARIO 1: Kondisi Awal (Agent di R1, belum bergerak)
    # ============================================================
    print("=" * 70)
    print(" SKENARIO 1: KONDISI AWAL (Agent di R1)")
    print("=" * 70 + "\n")

    fc_result_1 = forward_chaining(FACTS, RULES)
    print_forward_result("Kondisi Awal", fc_result_1)

    bc_result_1 = bc_ask(FACTS, RULES, GOAL)
    print_backward_result("Kondisi Awal", bc_result_1)

    print(">> KESIMPULAN SKENARIO 1: Kedua metode GAGAL membuktikan PintuTerbuka(),")
    print("   karena Agent belum berpindah dari R1 -- AdaKunci(R1) tidak pernah benar.")
    print("   Ini menunjukkan keterbatasan inferensi logika murni: KB statis tidak bisa")
    print("   'menggerakkan' Agent -- perlu lapisan aksi/planning di luar chaining.\n")

    # ============================================================
    # Cari rute yang dibutuhkan (mengaitkan ke tugas Search sebelumnya)
    # ============================================================
    print("=" * 70)
    print(" MENENTUKAN RUTE YANG DIBUTUHKAN (reuse BFS dari tugas Search)")
    print("=" * 70 + "\n")

    adj = build_adjacency(FACTS)
    route_to_key = bfs_route(adj, "R1", "R4")
    route_to_door = bfs_route(adj, "R4", "R6")
    print(f"Rute Start -> Kunci  : {' -> '.join(route_to_key)}")
    print(f"Rute Kunci -> Pintu  : {' -> '.join(route_to_door)}")
    print()

    # ============================================================
    # SKENARIO 2: Setelah Agent bergerak (TELL posisi baru)
    # ============================================================
    print("=" * 70)
    print(" SKENARIO 2: SETELAH AGENT BERGERAK (TELL posisi baru)")
    print("=" * 70 + "\n")

    print(">> TELL: Agent bergerak mengikuti rute Start->Kunci, sampai di R4 (ambil kunci)")
    facts_at_key = update_position(FACTS, "R4")
    fc_result_2a = forward_chaining(facts_at_key, RULES)
    print_forward_result("Agent di R4 (setelah ambil kunci)", fc_result_2a)

    print(">> TELL: Agent bergerak lagi mengikuti rute Kunci->Pintu, sampai di R6")
    print("   (Kunci yang sudah diambil tetap dibawa -- KB dilanjutkan dari hasil")
    print("    forward chaining sebelumnya, termasuk fakta MemilikiKunci(Agent))")
    facts_at_door = update_position(fc_result_2a["facts"], "R6")
    fc_result_2b = forward_chaining(facts_at_door, RULES)
    print_forward_result("Agent di R6 (setelah sampai pintu)", fc_result_2b)

    bc_result_2 = bc_ask(facts_at_door, RULES, GOAL)
    print_backward_result("Agent sudah di R6 dengan kunci", bc_result_2)

    print(">> KESIMPULAN SKENARIO 2: Setelah KB diperbarui (TELL) mencerminkan")
    print("   perpindahan Agent, KEDUA metode BERHASIL membuktikan PintuTerbuka().\n")

    # ============================================================
    # TABEL PERBANDINGAN
    # ============================================================
    print("=" * 70)
    print(" TABEL PERBANDINGAN FORWARD vs BACKWARD CHAINING")
    print("=" * 70 + "\n")

    print(f"{'Skenario':<30}{'Metode':<20}{'Proven?':<10}{'Rules Fired/Goal Dicek'}")
    print("-" * 80)
    print(f"{'1: Kondisi Awal':<30}{'Forward Chaining':<20}{'TIDAK':<10}{fc_result_1['rules_fired']}")
    print(f"{'1: Kondisi Awal':<30}{'Backward Chaining':<20}{'TIDAK':<10}{bc_result_1['goals_checked']}")
    print(f"{'2: Setelah Bergerak':<30}{'Forward Chaining':<20}{'YA':<10}{fc_result_2a['rules_fired'] + fc_result_2b['rules_fired']}")
    print(f"{'2: Setelah Bergerak':<30}{'Backward Chaining':<20}{'YA':<10}{bc_result_2['goals_checked']}")
