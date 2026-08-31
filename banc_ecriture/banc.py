# Banc d'essai des modeles d'ecriture du studio.
# Ne modifie rien : il lit le corpus, appelle les modeles, juge avec les
# fonctions de serveur.py, et ecrit ses mesures dans /banc/resultats.jsonl.
import asyncio, json, os, sys, time, urllib.request

import serveur
import fournisseurs
from serveur import (SYS_ENRICHIR, SYS_ENRICHIR_DUR, _A_DECIDER, _ENRICHIT,
                     _cadre_technique, SYS_TRADUCTION, latin, _enrichi,
                     corps_ollama, OLLAMA)

CORPUS = [json.loads(l) for l in open("/banc/corpus_ecriture.jsonl", encoding="utf-8") if l.strip()]
SORTIE = open("/banc/resultats.jsonl", "a", encoding="utf-8")

LOCAUX = ["liquidai/lfm2.5-350m:latest", "digitsflow/bonsai-8b:latest",
          "qwen2.5vl:7b", "gemma4:26b"]
CANDIDATS = LOCAUX + ["anthropic"]


def note(**kw):
    SORTIE.write(json.dumps(kw, ensure_ascii=False) + "\n")
    SORTIE.flush()


# 240 s au lieu des 900 s du studio : un appel plus lent que cela est
# de toute facon inutilisable devant chaque rendu. Le depassement est
# compte comme un echec, et dit comme tel.
PLAFOND = int(os.environ.get("BANC_PLAFOND", "240"))


def poster(corps, timeout=None):
    timeout = timeout or PLAFOND
    data = json.dumps(corps).encode("utf-8")
    req = urllib.request.Request(OLLAMA + "/api/generate", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def charges():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/ps", timeout=15) as r:
            return [m.get("name") for m in json.load(r).get("models", [])]
    except Exception:
        return []


def decharger(modele):
    try:
        poster({"model": modele, "prompt": "", "keep_alive": 0}, timeout=180)
    except Exception:
        pass
    for _ in range(30):
        if modele not in charges():
            return True
        time.sleep(2)
    return False


def appel(modele, texte, systeme, temperature, garder="10m"):
    """Un appel, temps compris. Reproduit corps_ollama() du studio."""
    if modele == "anthropic":
        t0 = time.time()
        try:
            r = asyncio.run(fournisseurs.texte(
                "anthropic", serveur.cle_de("anthropic"), texte, systeme,
                temperature, False, serveur.modele_de("anthropic") or None))
            return r, time.time() - t0, ""
        except Exception as e:
            return "", time.time() - t0, f"{type(e).__name__}: {str(e)[:200]}"
    corps = corps_ollama(texte, None, systeme, False, modele, temperature, garder)
    t0 = time.time()
    try:
        d = poster(corps)
    except Exception as e:
        return "", time.time() - t0, f"{type(e).__name__}: {str(e)[:200]}"
    dt = time.time() - t0
    rep = d.get("response", "") or ""
    err = d.get("error")
    if not rep.strip() and err:
        return "", dt, str(err)[:200]
    if not rep.strip():
        return "", dt, f"reponse vide (arret={d.get('done_reason')} jetons={d.get('eval_count')})"
    return rep, dt, ""


def pourquoi_pas_latin(t):
    """Les quatre refus distincts que latin() confond sous un seul nom."""
    if sum(c.isalpha() for c in t) < 3:
        return "moins de 3 lettres"
    if any(a <= ord(c) <= b for c in t for a, b in serveur._PLAGES_NON_LATINES):
        return "ecriture non latine"
    if serveur._REPETITION.search(t):
        return "caractere repete 4 fois"
    utiles = sum(c.isalnum() or c.isspace() for c in t)
    if utiles < 0.8 * len(t):
        return "majorite de symboles"
    return ""


def pourquoi_pas_enrichi(avant, apres):
    if not apres:
        return "vide"
    if len(apres.split()) < len(avant.split()) + 5:
        return "pas assez long"
    if len(serveur._mots(apres) - serveur._mots(avant)) < 5:
        return "moins de 5 mots nouveaux"
    return ""


def taille(it):
    if it["intention"] == "personnage":
        return 832, 1216
    if it["intention"] in ("video", "video_image"):
        return 1280, 704
    if it["intention"] == "objet3d":
        return 1024, 1024
    return 1216, 832


def tache_enrichir(modele, it, froid=False):
    quoi = _ENRICHIT.get(it["intention"])
    l, h = taille(it)
    plan = {"modele": it["modele"], "intention": it["intention"],
            "prompt": it["texte"], "largeur": l, "hauteur": h}
    depart = it["texte"]
    base = SYS_ENRICHIR + _A_DECIDER[quoi] + _cadre_technique(plan)
    essais = []
    for n, systeme in enumerate((base, base + SYS_ENRICHIR_DUR), 1):
        brut, dt, err = appel(modele, depart, systeme, 0.4)
        propose = " ".join((brut or "").split())
        rl = pourquoi_pas_latin(propose) if propose else "vide"
        re_ = pourquoi_pas_enrichi(depart, propose)
        ok = bool(propose) and not rl and not re_
        essais.append({"essai": n, "s": round(dt, 2), "err": err,
                       "sortie": propose[:600], "ok": ok,
                       "refus_latin": rl, "refus_enrichi": re_})
        if ok:
            break
    note(tache="enrichir", modele=modele, id=it["id"], famille=it["famille"],
         intention=it["intention"], moteur=it["modele"], froid=froid,
         demande=depart, essais=essais,
         reussi=any(e["ok"] for e in essais),
         s_total=round(sum(e["s"] for e in essais), 2))


def tache_traduire(modele, it, froid=False):
    textes = [it["texte"]] + list(it.get("cases") or [])
    demande = "\n".join("%d. %s" % (n, " ".join(t.split()))
                        for n, t in enumerate(textes, 1))
    essais = []
    for n in (1, 2):
        brut, dt, err = appel(modele, demande, SYS_TRADUCTION, 0.1)
        import re as _re
        lignes = [_re.sub(r"^\s*\d+[.)]\s*", "", x).strip()
                  for x in (brut or "").splitlines() if x.strip()]
        bon_compte = len(lignes) == len(textes)
        vides = [i for i, x in enumerate(lignes) if not x]
        refus = [pourquoi_pas_latin(x) for x in lignes if x]
        refus = [r for r in refus if r]
        ok = bon_compte and all(lignes) and all(map(latin, lignes)) and bool(lignes)
        essais.append({"essai": n, "s": round(dt, 2), "err": err, "ok": ok,
                       "attendu": len(textes), "rendu": len(lignes),
                       "vides": len(vides), "refus_latin": refus,
                       "sortie": lignes[:6]})
        if ok:
            break
    note(tache="traduire", modele=modele, id=it["id"], famille=it["famille"],
         froid=froid, demande=textes, essais=essais,
         reussi=any(e["ok"] for e in essais),
         s_total=round(sum(e["s"] for e in essais), 2))


def main():
    serveur.charger_cles()
    voulus = sys.argv[1:] or CANDIDATS
    for modele in voulus:
        print("=== %s ===" % modele, flush=True)
        if modele != "anthropic":
            print("  dechargement…", decharger(modele), flush=True)
            # Appel a froid : le tout premier, modele hors memoire.
            t0 = time.time()
            brut, dt, err = appel(modele, "bonjour", None, 0.4)
            note(tache="froid_bonjour", modele=modele, s=round(dt, 2),
                 err=err, sortie=(brut or "")[:200])
            print("  froid 'bonjour' : %.1f s  err=%s" % (dt, err[:80]), flush=True)
            if err and "terminated" in err:
                print("  modele casse, on passe", flush=True)
                continue
        taches = os.environ.get("BANC_TACHES", "enrichir,traduire").split(",")
        if "enrichir" in taches:
            for i, it in enumerate(CORPUS):
                tache_enrichir(modele, it, froid=(i == 0))
        if "traduire" in taches:
            for i, it in enumerate(CORPUS):
                tache_traduire(modele, it, froid=False)
        if modele != "anthropic":
            decharger(modele)
        print("  fini", flush=True)


if __name__ == "__main__":
    main()
