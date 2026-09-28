"""
wumpus_kb.py
Knowledge Base untuk Agent OTONOM (tanpa search problem) yang menjelajah
peta sambil menyimpulkan sendiri ruangan mana yang aman, memakai
Negation as Failure (NAF) -- mirip penalaran Wumpus World asli.

Peta ruangan (topologi diketahui Agent sejak awal -- ini "denah gedung",
bukan isi/bahaya di dalamnya):

     R2(Musuh) --- R4(Kunci) --- R6(PINTU / Goal)
      |               |              |
     R1(Start) --- R3(Jebakan) --- R5(Aman)

PENTING -- Perbedaan dengan kb_data.py (studi kasus sebelumnya):
    - Di kb_data.py, SEMUA fakta (termasuk AdaKunci/AdaMusuh/AdaJebakan)
      sudah diketahui Agent sejak awal (fully observable).
    - Di sini, TRUE_WORLD berisi kebenaran yang TERSEMBUNYI dari Agent.
      Agent hanya mengetahui topologi (Terhubung) dan posisinya sendiri.
      Ia baru "mengetahui" AdaMusuh/AdaJebakan/AdaKunci lewat PERSEPSI
      (Berbau/Berangin/Berkilau) yang di-TELL oleh "environment" saat ia
      benar-benar berada di suatu ruangan -- sama seperti Wumpus World asli.
"""

# ============================================================
# DUNIA NYATA (Tersembunyi dari Agent -- hanya dipakai "environment")
# ============================================================
TRUE_WORLD = {
    "AdaKunci": {"R4"},
    "AdaMusuh": {"R2"},
    "AdaJebakan": {"R3"},
}

# Topologi peta -- INI diketahui Agent sejak awal (denah, bukan isi bahaya)
TERHUBUNG = [
    ("R1", "R2"), ("R1", "R3"), ("R2", "R4"),
    ("R3", "R4"), ("R3", "R5"), ("R4", "R6"), ("R5", "R6"),
]

START = "R1"
DOOR = "R6"
KEY_ROOM = "R4"  # dipakai environment untuk cek Glitter; Agent TIDAK tahu ini di awal

MAX_HP = 3


def adjacency():
    """Bangun adjacency list (dua arah) dari TERHUBUNG untuk dipakai environment."""
    adj = {}
    for a, b in TERHUBUNG:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return adj


def known_facts_awal(agent="Agent"):
    """Fakta yang Agent ketahui SEJAK AWAL: topologi peta (dua arah) + posisi awal.
    TIDAK termasuk AdaKunci/AdaMusuh/AdaJebakan -- itu tersembunyi."""
    facts = []
    for a, b in TERHUBUNG:
        facts.append(("Terhubung", a, b))
        facts.append(("Terhubung", b, a))
    facts.append(("DiRuangan", agent, START))
    facts.append(("Dikunjungi", START))
    return facts


# ============================================================
# ATURAN PENALARAN AGENT (Horn Clause + NAF)
# ============================================================
AGENT_RULES = [
    {
        # Ruangan y PASTI aman jika ada tetangga x yang SUDAH dikunjungi,
        # dan TIDAK ada Bau maupun Angin yang tercium di x.
        # (Ini padanan logis dari "tidak ada Breeze di sini -> semua tetangga bebas Pit")
        "name": "AmanPasti_dariTetanggaBersih",
        "premises": [
            ("Terhubung", "?x", "?y"),
            ("Dikunjungi", "?x"),
            ("NAF", ("Berbau", "?x")),
            ("NAF", ("Berangin", "?x")),
        ],
        "conclusion": ("AmanPasti", "?y"),
    },
    {
        # Ruangan yang sudah pernah dikunjungi otomatis dianggap "aman"
        # (karena Agent sudah membuktikan sendiri ia selamat sampai di sana).
        "name": "AmanPasti_sudahDikunjungi",
        "premises": [("Dikunjungi", "?x")],
        "conclusion": ("AmanPasti", "?x"),
    },
    {
        "name": "BukaPintu",
        "premises": [("MemilikiKunci", "Agent"), ("DiRuangan", "Agent", DOOR)],
        "conclusion": ("PintuTerbuka",),
    },
]

GOAL_PINTU_TERBUKA = ("PintuTerbuka",)
