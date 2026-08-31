# Agrege /banc/resultats.jsonl en tableaux.
import json, statistics, sys, collections

_brut = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
# Un meme (tache, modele, id) a pu etre rejoue : on garde la DERNIERE mesure.
_vu = {}
for _r in _brut:
    _vu[(_r["tache"], _r["modele"], _r.get("id"))] = _r
R = list(_vu.values())

ORDRE = ["liquidai/lfm2.5-350m:latest", "digitsflow/bonsai-8b:latest",
         "qwen2.5vl:7b", "gemma4:26b", "anthropic"]
COURT = {"liquidai/lfm2.5-350m:latest": "lfm2.5-350m",
         "digitsflow/bonsai-8b:latest": "bonsai-8b",
         "qwen2.5vl:7b": "qwen2.5vl:7b", "gemma4:26b": "gemma4:26b",
         "anthropic": "Anthropic (haiku-4.5)"}

froid = {r["modele"]: r for r in R if r["tache"] == "froid_bonjour"}

print("## Froid : premier appel apres chargement\n")
print("| modele | 'bonjour' a froid | erreur |")
print("|---|---:|---|")
for m in ORDRE:
    if m in froid:
        f = froid[m]
        print("| %s | %.1f s | %s |" % (COURT[m], f["s"], (f["err"] or "-")[:90]))

print()
for tache in ("enrichir", "traduire"):
    print("## Tache : %s\n" % tache)
    print("| modele | reussite | 1er essai seul | mediane/appel | p90 | max | appels |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for m in ORDRE:
        rs = [r for r in R if r["tache"] == tache and r["modele"] == m]
        if not rs:
            continue
        ok = sum(1 for r in rs if r["reussi"])
        e1 = sum(1 for r in rs if r["essais"] and r["essais"][0]["ok"])
        lat = [e["s"] for r in rs for e in r["essais"] if not e.get("err")]
        # on exclut le tout premier appel (a froid) de la mediane
        chauds = lat[1:] if lat else []
        if not chauds:
            chauds = lat
        med = statistics.median(chauds) if chauds else 0
        p90 = sorted(chauds)[int(len(chauds) * 0.9)] if chauds else 0
        print("| %s | %d/%d (%d%%) | %d/%d | %.1f s | %.1f s | %.1f s | %d |" % (
            COURT[m], ok, len(rs), round(100 * ok / len(rs)), e1, len(rs),
            med, p90, max(chauds) if chauds else 0, len(lat)))
    print()

print("## Nature des echecs\n")
for tache in ("enrichir", "traduire"):
    print("### %s\n" % tache)
    print("| modele | cause | occurrences |")
    print("|---|---|---:|")
    for m in ORDRE:
        rs = [r for r in R if r["tache"] == tache and r["modele"] == m]
        c = collections.Counter()
        for r in rs:
            if r["reussi"]:
                continue
            d = r["essais"][-1]
            if d.get("err"):
                c["appel en erreur : " + d["err"][:60]] += 1
            elif tache == "enrichir":
                if d.get("refus_latin"):
                    c["latin() : " + d["refus_latin"]] += 1
                else:
                    c["_enrichi() : " + (d.get("refus_enrichi") or "?")] += 1
            else:
                if d["rendu"] != d["attendu"]:
                    c["%d lignes rendues pour %d attendues" % (d["rendu"], d["attendu"])] += 1
                elif d["vides"]:
                    c["ligne vide"] += 1
                elif d["refus_latin"]:
                    c["latin() : " + d["refus_latin"][0]] += 1
                else:
                    c["autre"] += 1
        for cause, n in c.most_common():
            print("| %s | %s | %d |" % (COURT[m], cause, n))
    print()

print("## Par famille de demande (reussite enrichir / traduire)\n")
familles = sorted({r["famille"] for r in R if "famille" in r})
print("| modele | " + " | ".join(familles) + " |")
print("|---" * (len(familles) + 1) + "|")
for m in ORDRE:
    cells = []
    for f in familles:
        a = [r for r in R if r["modele"] == m and r.get("famille") == f and r["tache"] == "enrichir"]
        b = [r for r in R if r["modele"] == m and r.get("famille") == f and r["tache"] == "traduire"]
        if not a and not b:
            cells.append("-")
        else:
            cells.append("%d/%d · %d/%d" % (sum(1 for r in a if r["reussi"]), len(a),
                                            sum(1 for r in b if r["reussi"]), len(b)))
    if any(c != "-" for c in cells):
        print("| %s | %s |" % (COURT[m], " | ".join(cells)))

# ── Qualite, au-dela de la conformite ─────────────────────────────────────
# Heuristique A MOI, pas un juge du studio : une traduction "acceptee" qui est
# restee en francais, et un enrichissement qui recopie l'exemple du prompt.
import re
FR = re.compile(r"\b(le|la|les|une|des|dans|sur|avec|du|au|aux|qui|et|"
                r"pour|par|sous|entre|vers|depuis|leur|son|sa|ses|cette|"
                r"est|sont|plan|lumiere|lumière)\b", re.I)
EN = re.compile(r"\b(the|a|an|of|in|on|with|from|and|for|to|is|are|at|"
                r"by|shot|light|close-up|wide)\b", re.I)

def encore_francais(t):
    return len(FR.findall(t)) >= 2 and len(FR.findall(t)) > len(EN.findall(t))

print("\n## Qualite : traductions acceptees mais restees en francais\n")
print("| modele | acceptees | dont non traduites | reellement utiles |")
print("|---|---:|---:|---:|")
for m in ORDRE:
    rs = [r for r in R if r["tache"] == "traduire" and r["modele"] == m and r["reussi"]]
    tot = [r for r in R if r["tache"] == "traduire" and r["modele"] == m]
    if not tot:
        continue
    fr = 0
    for r in rs:
        lignes = r["essais"][-1]["sortie"]
        if any(encore_francais(x) for x in lignes):
            fr += 1
    print("| %s | %d/%d | %d | %d/%d (%d%%) |" % (
        COURT[m], len(rs), len(tot), fr, len(rs) - fr, len(tot),
        round(100 * (len(rs) - fr) / len(tot))))

print("\n## Qualite : enrichissements acceptes mais hors sujet\n")
CONTAMINE = re.compile(r"renard roux|clairiere enneigee|souffle visible", re.I)
print("| modele | acceptes | dont recopient l'exemple du prompt systeme |")
print("|---|---:|---:|")
for m in ORDRE:
    rs = [r for r in R if r["tache"] == "enrichir" and r["modele"] == m and r["reussi"]]
    tot = [r for r in R if r["tache"] == "enrichir" and r["modele"] == m]
    if not tot:
        continue
    c = sum(1 for r in rs if CONTAMINE.search(r["essais"][-1]["sortie"] or "")
            and "renard" not in r["demande"].lower())
    print("| %s | %d/%d | %d |" % (COURT[m], len(rs), len(tot), c))

print("\n## Qualite : le cadre technique recopie dans la description\n")
FUITE = re.compile(r"\d{3,4}\s*[x×]\s*\d{3,4}|ComfyUI|composition (verticale|horizontale|carree)", re.I)
print("| modele | enrichissements acceptes | dont recopient la taille/le moteur |")
print("|---|---:|---:|")
for m in ORDRE:
    rs = [r for r in R if r["tache"] == "enrichir" and r["modele"] == m and r["reussi"]]
    tot = [r for r in R if r["tache"] == "enrichir" and r["modele"] == m]
    if not tot:
        continue
    n = sum(1 for r in rs if FUITE.search(r["essais"][-1]["sortie"] or ""))
    print("| %s | %d/%d | %d |" % (COURT[m], len(rs), len(tot), n))
