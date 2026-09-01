# -*- coding: utf-8 -*-
"""Le geste de la GRILLE, avec ce que la mediatheque sert VRAIMENT.

    sudo docker exec comfystudio python /app/recette_grille_variantes.py

Le serveur servait « tour » et « groupe » a la mediatheque depuis le matin, et
la grille les jetait : elle affichait le rang et la marque sans aucun moyen
d'agir. Or c'est LA qu'on compare quatre images indiscernables — le fil les
montre l'une sous l'autre, la grille cote a cote. Un banc etait vert sur un
contrat que la grille n'empruntait pas : c'est le defaut que ce projet passe
ses journees a fermer, et il etait revenu une fois de plus.

RECETTE et non banc : elle a besoin d'un studio qui tourne ET d'une carte —
deux brouillons, environ cent secondes sur une 2080 Ti. Elle ne peut donc pas
entrer dans la CI, et elle ne se lance pas pendant que quelqu'un joue.

Elle prend l'identifiant DANS CE QUE LA MEDIATHEQUE A SERVI, jamais dans la
conversation : c'est le seul moyen de prouver que la grille a de quoi agir.
"""
import json, secrets, time, urllib.error, urllib.request
B = "http://127.0.0.1:8199"
J = json.load(open("/donnees/_admin.json"))["jeton"]
NOM = "essai" + secrets.token_hex(3); MDP = secrets.token_urlsafe(16)
BIS = {}; ok = []; rate = []
def appel(c, corps=None, ent=None, meth=None):
    d = json.dumps(corps).encode() if corps is not None else None
    r = urllib.request.Request(B + c, data=d, method=meth or ("POST" if d else "GET"))
    r.add_header("Content-Type", "application/json"); r.add_header("Origin", B)
    for k, v in {**BIS, **(ent or {})}.items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=60) as rep:
            t = rep.read().decode()
            return rep.status, (json.loads(t) if t[:1] in "{[" else t), rep.headers.get_all("Set-Cookie") or []
    except urllib.error.HTTPError as e:
        t = e.read().decode()
        return e.code, (json.loads(t) if t[:1] == "{" else t), []
def dit(v, quoi, detail=""):
    (ok if v else rate).append(quoi)
    print(f"  {'ok ' if v else 'NON'}  {quoi}{' — ' + detail if detail else ''}", flush=True)

appel("/api/admin/comptes", {"nom": NOM, "mdp": MDP, "creer": True}, {"X-Admin": J})
_, _, ck = appel("/api/compte/entrer", {"nom": NOM, "mdp": MDP})
BIS["Cookie"] = "; ".join(c.split(";")[0] for c in ck)
_, d, _ = appel("/api/conversations"); CONV = d["courante"]

_, d, _ = appel("/api/generer", {"texte": "un phare sur une falaise", "conversation": CONV,
                                 "priorite": "brouillon", "variantes": 2})
tid = (d or {}).get("id")
dit(bool(tid), "deux variantes acceptees", json.dumps(d)[:90] if not tid else "")
depart = time.time()
while time.time() - depart < 400:
    _, c, _ = appel("/api/conversation/" + CONV)
    tours = [t for t in (c or {}).get("tours") or [] if (t.get("variantes") or {}).get("sur")]
    if len(tours) >= 2 and all(t.get("etat") == "fini" for t in tours):
        break
    time.sleep(3)
print(f"     {len(tours)} tirages, {time.time() - depart:.0f} s")

_, m, _ = appel("/api/mediatheque")
pieces = [f for f in ((m or {}).get("fichiers") or m or []) if isinstance(f, dict)
          and f.get("conversation") == CONV]
dit(bool(pieces) and all(p.get("tour") for p in pieces),
    "la grille recoit l'identifiant du tour", str([p.get("tour") for p in pieces])[:60])
dit(bool(pieces) and all(p.get("groupe") for p in pieces),
    "et le groupe, pour repeindre les soeurs d'un clic")
dit(any(p.get("variante") for p in pieces), "et le rang de chaque tirage",
    str([p.get("variante") for p in pieces]))
cible = next((p for p in pieces if not p.get("choisie")), None)
dit(cible is not None, "une piece non retenue a designer")
if cible:
    st, r, _ = appel("/api/variante", {"conversation": cible["conversation"],
                                       "tour": cible["tour"]})
    dit(st == 200, "le clic de la grille est accepte", json.dumps(r)[:80])
    _, m, _ = appel("/api/mediatheque")
    apres = [f for f in ((m or {}).get("fichiers") or m or []) if isinstance(f, dict)
             and f.get("conversation") == CONV]
    marquees = [p["tour"] for p in apres if p.get("choisie")]
    dit(marquees == [cible["tour"]], "une seule est retenue, et c'est la bonne",
        str(marquees))
appel("/api/conversation/" + CONV, None, None, "DELETE")
appel("/api/admin/comptes/" + NOM, None, {"X-Admin": J}, "DELETE")
print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
