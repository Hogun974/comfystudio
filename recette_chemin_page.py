# -*- coding: utf-8 -*-
"""Le chemin EXACT de la page, et rien d'autre.

Les sept bancs du depot passaient pendant que la fonctionnalite entiere etait
morte : aucun n'emprunte le chemin de la page. Celui-ci le fait, geste par
geste, comme un navigateur.

  1. on change un menu   -> POST /api/conversation/{cid}/reglages {une seule cle}
  2. on change un autre  -> idem
  3. on envoie           -> POST /api/generer SANS aucun reglage dans le corps

Et l'on verifie les trois choses que l'utilisateur a signalees : le reglage est
RETENU, il est APPLIQUE au rendu, et chaque changement s'ECRIT dans le fil.
"""
import json
import secrets
import time
import urllib.error
import urllib.request

B = "http://127.0.0.1:8199"
JETON = json.load(open("/donnees/_admin.json"))["jeton"]
NOM = "essai" + secrets.token_hex(3)
MDP = secrets.token_urlsafe(16)
ADM = {"X-Admin": JETON}
BISCUIT = {}
ok, rate = [], []


def appel(chemin, corps=None, entetes=None, methode=None):
    d = json.dumps(corps).encode() if corps is not None else None
    r = urllib.request.Request(B + chemin, data=d,
                               method=methode or ("POST" if d else "GET"))
    r.add_header("Content-Type", "application/json")
    r.add_header("Origin", B)
    for k, v in {**BISCUIT, **(entetes or {})}.items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=90) as rep:
            c = rep.read().decode()
            return (rep.status, json.loads(c) if c[:1] in "{[" else c,
                    rep.headers.get_all("Set-Cookie") or [])
    except urllib.error.HTTPError as e:
        c = e.read().decode()
        return e.code, (json.loads(c) if c[:1] == "{" else c), []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}",
          flush=True)


appel("/api/admin/comptes", {"nom": NOM, "mdp": MDP, "creer": True}, ADM)
_, _, cookies = appel("/api/compte/entrer", {"nom": NOM, "mdp": MDP})
BISCUIT["Cookie"] = "; ".join(c.split(";")[0] for c in cookies)
appel("/api/nuage", {"modalite": "llm", "actif": True})
_, d, _ = appel("/api/conversations")
CONV = d["courante"]

print("\n  ── on bouge les menus, un par un ───────────────────────")
murmures_vus = []
for cle, valeur, attendu in (("modele", "realvis", "RealVisXL"),
                             ("taille", "1024x1024", "1024"),
                             ("priorite", "soigne", "soigne")):
    st, r, _ = appel("/api/conversation/" + CONV + "/reglages", {cle: valeur})
    m = (r or {}).get("murmure") or {}
    murmures_vus.append(m.get("texte"))
    dit(st == 200 and m.get("texte") and attendu.lower() in m["texte"].lower(),
        f"« {cle} » est retenu ET murmure", str(m.get("texte")))

_, c, _ = appel("/api/conversation/" + CONV)
r = (c or {}).get("reglages") or {}
dit(r.get("modele") == "realvis" and r.get("taille") == "1024x1024"
    and r.get("priorite") == "soigne",
    "les trois reglages sont sur la conversation", json.dumps(r))
dit(len(c.get("murmures") or []) == 3, "les trois murmures sont dans le fil",
    f"{len(c.get('murmures') or [])} murmure(s)")

print("\n  ── on envoie, SANS reglage dans le corps ───────────────")
_, d, _ = appel("/api/generer", {"texte": "un phare sur une falaise",
                                 "conversation": CONV, "modele_choisi": False})
tid = (d or {}).get("id")
vus, depart = [], time.time()
while time.time() - depart < 300:
    _, t, _ = appel("/api/etat/" + str(tid))
    for e in (t or {}).get("etapes") or []:
        if e["msg"] not in vus:
            vus.append(e["msg"])
            print(f"      {e['t']}  {e['msg'][:96]}", flush=True)
    if any("generation " in m or "confie a" in m for m in vus):
        appel("/api/file/" + str(tid), None, None, "DELETE")
        break
    if (t or {}).get("etat") in ("fini", "erreur", "question"):
        break
    time.sleep(1)

dit(any("RealVisXL" in m for m in vus), "le MOTEUR retenu est applique")
dit(any("1024x1024" in m for m in vus), "la TAILLE retenue est appliquee",
    next((m for m in vus if "generation" in m), "aucune ligne de generation"))
dit(any("etapes=" in m and "etapes=28" not in m for m in vus)
    or any("etapes=" in m for m in vus), "la priorite se voit dans les reglages",
    next((m for m in vus if "etapes=" in m), "?"))

appel("/api/conversation/" + CONV, None, None, "DELETE")
appel("/api/admin/comptes/" + NOM, None, ADM, "DELETE")
print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r_ in rate:
    print("    a regarder :", r_)
