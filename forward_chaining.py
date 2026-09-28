"""
forward_chaining.py
Implementasi Forward Chaining: dari fakta menuju kesimpulan (data-driven).

Algoritma menyimpulkan semua fakta baru yang bisa diturunkan dari KB,
mengulang proses sampai tidak ada fakta baru yang muncul (fixpoint),
atau sampai max_iterations tercapai.
"""

from logic_engine import unify, apply_subst


def _match_premises(premises, kb, subst):
    """Mencari semua substitusi yang memenuhi SELURUH premis suatu aturan
    terhadap fakta-fakta yang ada di kb (proses unifikasi berantai/backtracking)."""
    if not premises:
        yield subst
        return

    first, rest = premises[0], premises[1:]
    for fact in kb:
        new_subst = unify(first, fact, subst)
        if new_subst is not None:
            yield from _match_premises(rest, kb, new_subst)


def forward_chaining(facts, rules, max_iterations=20):
    """
    Menjalankan forward chaining sampai tidak ada fakta baru (fixpoint).

    Return dict:
        facts        : set seluruh fakta akhir (awal + hasil turunan)
        trace        : urutan fakta baru yang ditemukan, beserta aturan & substitusi
        rules_fired  : jumlah total aturan yang berhasil "tertembak"
        iterations   : jumlah iterasi sampai fixpoint tercapai
    """
    kb = set(facts)
    trace = []
    iteration = 0

    for iteration in range(1, max_iterations + 1):
        new_facts_this_round = []

        for rule in rules:
            for subst in _match_premises(rule["premises"], kb, {}):
                new_fact = apply_subst(rule["conclusion"], subst)
                if new_fact not in kb and new_fact not in new_facts_this_round:
                    new_facts_this_round.append(new_fact)
                    trace.append({
                        "iteration": iteration,
                        "rule": rule["name"],
                        "subst": subst,
                        "fact": new_fact,
                    })

        if not new_facts_this_round:
            break
        kb.update(new_facts_this_round)

    return {
        "facts": kb,
        "trace": trace,
        "rules_fired": len(trace),
        "iterations": iteration,
    }
