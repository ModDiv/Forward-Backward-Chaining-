"""
logic_engine.py
Utilitas inti untuk representasi logika: unifikasi, substitusi variabel,
dan format tampilan predikat.

Representasi:
    - Predikat/atom ditulis sebagai tuple, misal ("Terhubung", "R1", "R2")
    - Variabel ditandai dengan awalan "?", misal "?x", "?y"
    - Konstanta ditulis apa adanya, misal "R1", "Agent"
"""


def is_variable(term):
    """Cek apakah suatu term adalah variabel (diawali '?')."""
    return isinstance(term, str) and term.startswith("?")


def walk(term, subst):
    """Telusuri substitusi berantai: jika term adalah variabel yang sudah
    terikat ke nilai lain di subst, ikuti terus sampai ke nilai akhirnya."""
    while is_variable(term) and term in subst:
        term = subst[term]
    return term


def unify_term(t1, t2, subst):
    """Unifikasi dua term tunggal, mengembalikan subst baru atau None jika gagal."""
    if subst is None:
        return None
    t1 = walk(t1, subst)
    t2 = walk(t2, subst)
    if t1 == t2:
        return subst
    if is_variable(t1):
        new_subst = dict(subst)
        new_subst[t1] = t2
        return new_subst
    if is_variable(t2):
        new_subst = dict(subst)
        new_subst[t2] = t1
        return new_subst
    return None  # dua konstanta berbeda -> gagal unifikasi


def unify(pattern_a, pattern_b, subst):
    """Unifikasi dua predikat (tuple), term demi term."""
    if subst is None:
        return None
    if len(pattern_a) != len(pattern_b):
        return None
    for a, b in zip(pattern_a, pattern_b):
        subst = unify_term(a, b, subst)
        if subst is None:
            return None
    return subst


def apply_subst(pattern, subst):
    """Terapkan substitusi ke seluruh term dalam suatu predikat.
    Mendukung juga bentuk khusus NAF: ("NAF", <atom_dalam>)."""
    if pattern[0] == "NAF":
        return ("NAF", apply_subst(pattern[1], subst))
    return tuple(walk(term, subst) for term in pattern)


def format_atom(pattern):
    """Format predikat/tuple menjadi string mudah dibaca, misal ('AdaKunci','R4') -> 'AdaKunci(R4)'.
    Mendukung juga bentuk khusus NAF: ("NAF", <atom_dalam>) -> 'NAF(AdaKunci(R4))'."""
    if pattern[0] == "NAF":
        return f"NAF({format_atom(pattern[1])})"
    if len(pattern) == 1:
        return f"{pattern[0]}()"
    return f"{pattern[0]}({', '.join(str(p) for p in pattern[1:])})"
