"""
backward_chaining.py
Implementasi Backward Chaining: dari goal mundur ke fakta (goal-driven).

Algoritma mencoba membuktikan suatu goal dengan:
    1. Mengecek apakah goal cocok (unify) dengan fakta yang sudah ada di KB.
    2. Jika tidak, mencari aturan yang kesimpulannya cocok dengan goal,
       lalu mencoba membuktikan seluruh premis aturan itu secara rekursif.

Setiap pemanggilan aturan di-"standardize apart" (variabelnya diganti nama unik)
supaya tidak terjadi tabrakan variabel antar pemanggilan rekursif yang berbeda.
"""

import itertools
from logic_engine import unify, apply_subst

_counter = itertools.count()


def _standardize_apart(rule):
    """Ganti nama semua variabel dalam suatu rule dengan nama unik,
    supaya aman dipakai berulang kali dalam pencarian rekursif."""
    suffix = next(_counter)
    mapping = {}

    def rename(term):
        if isinstance(term, str) and term.startswith("?"):
            if term not in mapping:
                mapping[term] = f"{term}_{suffix}"
            return mapping[term]
        return term

    def rename_atom(atom):
        if atom[0] == "NAF":
            return ("NAF", rename_atom(atom[1]))
        return tuple(rename(t) for t in atom)

    premises = [rename_atom(p) for p in rule["premises"]]
    conclusion = rename_atom(rule["conclusion"])
    return {"name": rule["name"], "premises": premises, "conclusion": conclusion}


def backward_chaining(facts, rules, goal, subst=None, depth=0, trace=None):
    """
    Generator: menghasilkan setiap substitusi (subst) yang berhasil membuktikan `goal`.
    Jika tidak ada substitusi yang di-yield sama sekali, berarti goal GAGAL dibuktikan.

    Mendukung premis khusus NAF (Negation as Failure): ("NAF", <atom>) berhasil
    dibuktikan JIKA DAN HANYA JIKA <atom> GAGAL dibuktikan sama sekali. Ini bukan
    negasi logis murni, melainkan "anggap salah kecuali berhasil dibuktikan benar" --
    cukup untuk merepresentasikan aturan seperti "ruangan aman jika tidak terbukti
    berbahaya", tanpa perlu mengubah Horn clause menjadi kesimpulan negatif.

    trace dikumpulkan sebagai list of dict, mencatat setiap goal yang dicek,
    apakah cocok fakta langsung, aturan mana yang dicoba, atau gagal total.
    """
    if subst is None:
        subst = {}
    if trace is None:
        trace = []

    # --- Penanganan khusus premis NAF ---
    if goal[0] == "NAF":
        inner_goal = goal[1]
        inner_display = apply_subst(inner_goal, subst)
        trace.append({"depth": depth, "type": "naf_check", "goal": inner_display})
        sub_trace = []
        proven = any(True for _ in backward_chaining(facts, rules, inner_goal, dict(subst), depth + 1, sub_trace))
        trace.extend(sub_trace)
        if not proven:
            trace.append({"depth": depth, "type": "naf_success", "goal": inner_display})
            yield subst
        else:
            trace.append({"depth": depth, "type": "naf_fail", "goal": inner_display})
        return

    goal_display = apply_subst(goal, subst)
    trace.append({"depth": depth, "type": "goal", "goal": goal_display})

    matched_any = False

    # 1) Coba cocokkan langsung dengan fakta yang sudah diketahui
    for fact in facts:
        s2 = unify(goal, fact, subst)
        if s2 is not None:
            matched_any = True
            trace.append({"depth": depth, "type": "fact_match", "fact": fact})
            yield s2

    # 2) Coba cocokkan dengan kesimpulan (head) tiap aturan
    for rule in rules:
        renamed = _standardize_apart(rule)
        s2 = unify(goal, renamed["conclusion"], subst)
        if s2 is not None:
            matched_any = True
            trace.append({"depth": depth, "type": "rule_match", "rule": rule["name"]})
            yield from _prove_all(renamed["premises"], facts, rules, s2, depth + 1, trace)

    if not matched_any:
        trace.append({"depth": depth, "type": "fail", "goal": goal_display})


def _prove_all(premises, facts, rules, subst, depth, trace):
    """Membuktikan SELURUH premis (konjungsi) secara berurutan, meneruskan
    substitusi dari satu premis ke premis berikutnya."""
    if not premises:
        yield subst
        return

    first, rest = premises[0], premises[1:]
    for s2 in backward_chaining(facts, rules, first, subst, depth, trace):
        yield from _prove_all(rest, facts, rules, s2, depth, trace)


def bc_ask(facts, rules, goal):
    """Fungsi pembungkus sederhana: mengembalikan (berhasil?, daftar solusi, trace)."""
    trace = []
    solutions = list(backward_chaining(facts, rules, goal, {}, 0, trace))
    return {
        "proven": len(solutions) > 0,
        "solutions": solutions,
        "trace": trace,
        "goals_checked": len([t for t in trace if t["type"] == "goal"]),
    }
