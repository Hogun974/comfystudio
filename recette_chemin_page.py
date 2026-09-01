# -*- coding: utf-8 -*-
"""Le chemin EXACT de la page, et rien d'autre.

    sudo docker exec comfystudio python /app/recette_chemin_page.py

Les sept bancs du depot passaient pendant que la fonctionnalite entiere etait
morte : aucun n'emprunte le chemin de la page. Celle-ci le fait, geste par
geste, comme un navigateur — et c'est une RECETTE, pas un banc : elle a besoin
d'un studio qui tourne, donc elle ne peut pas entrer dans la CI.

Les gestes, dans l'ordre reel :

  1. un menu bouge      -> POST /api/conversation/{cid}/reglages, UNE seule cle
  2. une pastille saute -> POST idem, la cle a null : presente et vide, donc
                           elle efface (web/index.html, peindreActifs)
  3. on envoie          -> POST /api/generer avec { texte, image, conversation,
                           modele_choisi } et RIEN d'autre
  4. le bouton brouillon -> le meme envoi, plus « priorite: brouillon », qui
                           vaut pour CETTE demande et ne se retient pas

Une premiere version de cette recette se trompait sur deux points, et une
relecture adverse les a montres. Ils sont notes ici parce qu'ils se
reproduiront :

  - elle annoncait « SANS aucun reglage dans le corps » alors que la page y
    mettait encore « priorite ». Une recette qui decrit un chemin qu'elle
    n'emprunte pas ne vaut pas mieux qu'un banc.
  - sa verification de la priorite etait « etapes= present, sauf 28 — OU
    etapes= present ». Le second terme contient le premier : elle se reduisait
    a « une ligne de reglages existe », ce que TOUTE generation ecrit. Elle
    serait passee avec la priorite entierement ignoree. On exige donc la
    valeur : « soigne » multiplie les etapes par 1,35, soit 38 pour un moteur
    a 28. Un chiffre, ou rien.
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


def bouger_menu(cid, cle, valeur):
    """Ce que fait la page quand un menu change, ou qu'une pastille saute.

    UNE seule cle. La valeur est null pour « automatique » — presente et vide,
    donc elle efface ; c'est exactement ce que valeurReglage() renvoie.
    """
    st, r, _ = appel("/api/conversation/" + cid + "/reglages", {cle: valeur})
    return st, (r or {}).get("murmure") or {}


def envoyer(cid, texte, priorite=None, modele_choisi=False):
    """Ce que la page met dans le corps de /api/generer, et rien de plus.

    « priorite » n'y figure QUE pour le bouton brouillon : c'est un choix qui
    vaut pour cette demande. Le cran de priorite, lui, vit sur la conversation
    comme les trois autres reglages — l'y renvoyer a chaque demande refaisait
    le degat qu'on croyait ferme : un second onglet, reste ouvert avec ses
    menus d'avant, effaçait le reglage du premier au moment d'envoyer.
    """
    corps = {"texte": texte, "conversation": cid, "modele_choisi": modele_choisi}
    if priorite:
        corps["priorite"] = priorite
    _, d, _ = appel("/api/generer", corps)
    return (d or {}).get("id"), d


def suivre(tid, jusqu_a=("generation ", "confie a"), duree=300):
    """Le journal, jusqu'a ce que le plan soit pose — puis on annule.

    Ce qui se joue ici est AVANT la carte, et l'utilisateur se sert du studio
    pendant ce temps : on ne lui prend pas une carte pour lire trois lignes.
    """
    vus, depart = [], time.time()
    while time.time() - depart < duree:
        _, t, _ = appel("/api/etat/" + str(tid))
        for e in (t or {}).get("etapes") or []:
            if e["msg"] not in vus:
                vus.append(e["msg"])
                print(f"      {e['t']}  {e['msg'][:96]}", flush=True)
        if any(any(m.startswith(j) or j in m for j in jusqu_a) for m in vus):
            appel("/api/file/" + str(tid), None, None, "DELETE")
            break
        if (t or {}).get("etat") in ("fini", "erreur", "question"):
            break
        time.sleep(1)
    return vus


appel("/api/admin/comptes", {"nom": NOM, "mdp": MDP, "creer": True}, ADM)
_, _, cookies = appel("/api/compte/entrer", {"nom": NOM, "mdp": MDP})
BISCUIT["Cookie"] = "; ".join(c.split(";")[0] for c in cookies)
appel("/api/nuage", {"modalite": "llm", "actif": True})
_, d, _ = appel("/api/conversations")
CONV = d["courante"]

# Le quatrieme reglage, « noeud », que la premiere recette n'exerçait jamais.
_, NS, _ = appel("/api/noeuds")
NOEUDS = [n for n in ((NS or {}).get("noeuds") or NS or [])
          if isinstance(n, dict) and n.get("id")]
CIBLE = next((n for n in NOEUDS if not n.get("pause")), NOEUDS[0] if NOEUDS else None)

print("\n  ── on bouge les menus, un par un ───────────────────────")
GESTES = [("modele", "realvis", "RealVisXL"),
          ("taille", "1024x1024", "1024"),
          ("priorite", "soigne", "soigne")]
if CIBLE:
    GESTES.append(("noeud", CIBLE["id"], CIBLE.get("titre", CIBLE["id"])[:12]))

for cle, valeur, attendu in GESTES:
    st, m = bouger_menu(CONV, cle, valeur)
    dit(st == 200 and m.get("texte") and attendu.lower() in m["texte"].lower(),
        f"« {cle} » est retenu ET murmure", str(m.get("texte")))

_, c, _ = appel("/api/conversation/" + CONV)
r = (c or {}).get("reglages") or {}
dit(r.get("modele") == "realvis" and r.get("taille") == "1024x1024"
    and r.get("priorite") == "soigne"
    and (not CIBLE or r.get("noeud") == CIBLE["id"]),
    "les reglages sont tous sur la conversation", json.dumps(r))
dit(len((c or {}).get("murmures") or []) == len(GESTES),
    "un murmure par geste, ni plus ni moins",
    f"{len((c or {}).get('murmures') or [])} pour {len(GESTES)} gestes")

print("\n  ── on envoie, SANS aucun reglage dans le corps ─────────")
tid, d = envoyer(CONV, "un phare sur une falaise", modele_choisi=True)
dit(bool(tid), "la demande est acceptee", json.dumps(d)[:100] if not tid else "")
vus = suivre(tid) if tid else []

dit(any("RealVisXL" in m for m in vus), "le MOTEUR retenu est applique")
dit(any("1024x1024" in m for m in vus), "la TAILLE retenue est appliquee",
    next((m for m in vus if "generation" in m), "aucune ligne de generation"))
# UN CHIFFRE, OU RIEN. « soigne » multiplie les etapes par 1,35 : 28 -> 38.
# La version d'avant se contentait de « etapes= existe », ce que toute
# generation ecrit — elle serait passee avec la priorite jetee a la poubelle.
etapes = next((m for m in vus if "etapes=" in m), "")
dit("etapes=38" in etapes, "la PRIORITE retenue est appliquee — 28 x 1,35 = 38",
    etapes or "aucune ligne de reglages")
if CIBLE:
    dit(any(CIBLE.get("titre", "")[:12] in m for m in vus),
        "la MACHINE retenue est celle qui travaille",
        next((m for m in vus if "confie a" in m), "aucune ligne d'attribution"))

print("\n  ── le bouton brouillon : cette demande, pas les suivantes ─")
tid, _ = envoyer(CONV, "un phare sur une falaise", priorite="brouillon")
vus = suivre(tid) if tid else []
etapes = next((m for m in vus if "etapes=" in m), "")
dit(etapes and "etapes=38" not in etapes,
    "le brouillon l'emporte sur le cran de la conversation", etapes or "?")
_, c, _ = appel("/api/conversation/" + CONV)
dit(((c or {}).get("reglages") or {}).get("priorite") == "soigne",
    "et il ne se retient pas : la conversation garde « soigne »",
    json.dumps((c or {}).get("reglages")))

print("\n  ── une pastille saute : la cle est presente et vide ────")
avant = len((c or {}).get("murmures") or [])
st, m = bouger_menu(CONV, "modele", None)
dit(st == 200 and m.get("texte") and "automatique" in m["texte"].lower(),
    "revenir a l'automatique s'ecrit aussi", str(m.get("texte")))
_, c, _ = appel("/api/conversation/" + CONV)
r = (c or {}).get("reglages") or {}
dit(not r.get("modele") and r.get("taille") == "1024x1024",
    "elle efface SON reglage, et lui seul", json.dumps(r))
dit(len((c or {}).get("murmures") or []) == avant + 1,
    "un geste, un murmure")

appel("/api/conversation/" + CONV, None, None, "DELETE")
appel("/api/admin/comptes/" + NOM, None, ADM, "DELETE")
print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r_ in rate:
    print("    a regarder :", r_)
