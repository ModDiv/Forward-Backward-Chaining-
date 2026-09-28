"""
kb_data.py
Knowledge Base untuk studi kasus: "Pencarian Kunci Menuju Pintu Gerbang"
(varian Wumpus World dengan tujuan membuka pintu, bukan membunuh Wumpus).

Peta ruangan:

     R2(Musuh) --- R4(Kunci) --- R6(PINTU / Goal)
      |               |              |
     R1(Start) --- R3(Jebakan) --- R5(Aman)

Semua aturan sengaja dirancang sebagai HORN CLAUSE murni
(kesimpulan tunggal, positif, tanpa negasi) supaya valid diproses
oleh forward chaining maupun backward chaining.
"""

# ============================================================
# FAKTA AWAL (Initial KB) - Skenario 1: Agent masih di titik Start (R1)
# ============================================================
FACTS = [
    ("Terhubung", "R1", "R2"),
    ("Terhubung", "R1", "R3"),
    ("Terhubung", "R2", "R4"),
    ("Terhubung", "R3", "R4"),
    ("Terhubung", "R3", "R5"),
    ("Terhubung", "R4", "R6"),
    ("Terhubung", "R5", "R6"),
    ("AdaKunci", "R4"),
    ("AdaMusuh", "R2"),
    ("AdaJebakan", "R3"),
    ("DiRuangan", "Agent", "R1"),
]

# ============================================================
# ATURAN (Rules) - semua berbentuk Horn Clause: premises -> conclusion
# ============================================================
RULES = [
    {
        "name": "R1_Simetri",
        "premises": [("Terhubung", "?x", "?y")],
        "conclusion": ("Terhubung", "?y", "?x"),
    },
    {
        "name": "R2_Kilau",
        "premises": [("AdaKunci", "?x"), ("Terhubung", "?x", "?y")],
        "conclusion": ("Berkilau", "?y"),
    },
    {
        "name": "R3_Bau",
        "premises": [("AdaMusuh", "?x"), ("Terhubung", "?x", "?y")],
        "conclusion": ("Berbau", "?y"),
    },
    {
        "name": "R4_Angin",
        "premises": [("AdaJebakan", "?x"), ("Terhubung", "?x", "?y")],
        "conclusion": ("Berangin", "?y"),
    },
    {
        "name": "R5_AmbilKunci",
        "premises": [("DiRuangan", "Agent", "?x"), ("AdaKunci", "?x")],
        "conclusion": ("MemilikiKunci", "Agent"),
    },
    {
        "name": "R6_BukaPintu",
        "premises": [("MemilikiKunci", "Agent"), ("DiRuangan", "Agent", "R6")],
        "conclusion": ("PintuTerbuka",),
    },
]

# ============================================================
# GOAL - yang ingin dibuktikan
# ============================================================
GOAL = ("PintuTerbuka",)


def update_position(facts, new_room):
    """Mensimulasikan TELL: memindahkan Agent ke ruangan baru.
    Fakta DiRuangan(Agent, ...) yang lama dihapus, diganti posisi baru."""
    updated = [f for f in facts if not (f[0] == "DiRuangan" and f[1] == "Agent")]
    updated.append(("DiRuangan", "Agent", new_room))
    return updated
