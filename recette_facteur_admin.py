# -*- coding: utf-8 -*-
"""Desarmer le second facteur d'un autre — le chemin reel, de bout en bout.

    sudo docker exec comfystudio python /app/recette_facteur_admin.py

C'est une RECETTE et non un banc : elle a besoin d'un studio qui tourne, donc
elle n'entre pas dans la CI. Elle existe parce que ce que banc_comptes.py
mesure de serveur.py, il le mesure par l'ARBRE DE SYNTAXE — il lit le fichier
sans l'importer, aiohttp viendrait derriere. Il peut donc dire que la garde est
ecrite avant le retrait ; il ne peut pas dire qu'une requete refusee laisse
vraiment le facteur en place. Cette recette-ci le demande au serveur.

Les gestes, dans l'ordre reel :

  1. deux comptes d'essai      -> POST /api/admin/comptes, avec le jeton
  2. l'un arme son facteur     -> entrer, mfa/preparer, mfa/confirmer, comme
                                  son navigateur le ferait, code TOTP calcule
  3. l'AUTRE, administrateur   -> il voit l'etat, la console lui annonce que le
     mais sans le jeton           bouton sera grise, et le serveur le refuse
  4. avec le jeton             -> le retrait passe, et une seconde fois est un
                                  refus et non un succes vide
  5. le compte se rouvre       -> mot de passe seul, puis reenrolement avec un
                                  secret NEUF

CE QU'ELLE NE PEUT PAS VOIR. Elle parle au serveur, pas a la page : elle
construit elle-meme les requetes. Si web/admin.html cessait d'envoyer le
DELETE, ou montrait le bouton a qui n'a pas le jeton, elle resterait verte —
c'est banc_comptes.py qui garde la forme des reponses, et l'oeil qui garde la
page. Ce qui est verifiable ici, et qui l'est : que ces requetes-la obtiennent
du serveur le comportement promis par docs/comptes.md.

ELLE EFFACE SES COMPTES, y compris quand elle echoue en route — le « finally »
est la pour ca. Les noms sont tires au hasard : une recette qui ecrase un
compte reel serait pire que le defaut qu'elle cherche.

ELLE N'IMPRIME NI LE JETON NI LES MOTS DE PASSE. Le jeton n'est lu que pour
etre pose dans un en-tete ; le secret TOTP n'est compare qu'a lui-meme.
"""
import http.cookiejar
import json
import secrets
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "/app")
import mfa  # noqa: E402

B = "http://127.0.0.1:8199"
JETON = json.load(open("/donnees/_admin.json", encoding="utf-8"))["jeton"]
PORTEUR = "facteur" + secrets.token_hex(3)   # celui qui arme son second facteur
ROLE = "role" + secrets.token_hex(3)         # administrateur, jamais le jeton
MDP_A = secrets.token_urlsafe(16)
MDP_B = secrets.token_urlsafe(16)

ok, rate = [], []


def dit(vrai, quoi, releve=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok  ' if vrai else 'RATE'} {quoi}" + (f" — {releve}" if releve else ""))


def appel(chemin, methode="GET", corps=None, jeton=False, nav=None):
    """(statut, dict). Aucune exception : un refus est une reponse a mesurer."""
    d = json.dumps(corps).encode() if corps is not None else None
    r = urllib.request.Request(B + chemin, data=d, method=methode)
    if d is not None:
        r.add_header("Content-Type", "application/json")
    if jeton:
        r.add_header("X-Admin", JETON)
    tireur = nav.open if nav else urllib.request.urlopen
    try:
        rep = tireur(r, timeout=20)
        brut = rep.read().decode("utf-8", "replace")
        return rep.status, (json.loads(brut) if brut else {})
    except urllib.error.HTTPError as e:
        brut = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(brut)
        except ValueError:
            return e.code, {"corps": brut[:120]}


def navigateur():
    """Un porteur de biscuits a lui, comme un onglet de plus."""
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def etat_de(nom, jeton=True, nav=None):
    _, d = appel("/api/admin/comptes", jeton=jeton, nav=nav)
    for c in d.get("comptes", []):
        if c["nom"] == nom:
            return c
    return {}


def menage():
    for n in (PORTEUR, ROLE):
        appel("/api/admin/comptes/" + n, "DELETE", jeton=True)


try:
    print("\n  ── deux comptes d'essai ──")
    s, _ = appel("/api/admin/comptes", "POST",
                 {"creer": True, "nom": PORTEUR, "mdp": MDP_A}, jeton=True)
    dit(s == 200, "le compte qui armera son facteur est cree", f"HTTP {s}")
    s, _ = appel("/api/admin/comptes", "POST",
                 {"creer": True, "nom": ROLE, "mdp": MDP_B, "admin": True},
                 jeton=True)
    dit(s == 200, "et un compte ADMINISTRATEUR, qui n'aura jamais le jeton",
        f"HTTP {s}")
    dit(etat_de(PORTEUR).get("mfa") == "", "aucun facteur au depart")

    print("\n  ── il arme son second facteur, par les vraies routes ──")
    nav = navigateur()
    s, _ = appel("/api/compte/entrer", "POST", {"nom": PORTEUR, "mdp": MDP_A},
                 nav=nav)
    dit(s == 200, "il ouvre une session", f"HTTP {s}")
    s, d = appel("/api/compte/mfa/preparer", "POST", {"mdp": MDP_A}, nav=nav)
    secret = d.get("secret", "")
    dit(s == 200 and len(secret) == 32, "l'enrolement est prepare",
        f"HTTP {s}, secret de {len(secret)} caracteres")
    dit(etat_de(PORTEUR).get("mfa") == "en_attente",
        "et /admin le voit « en attente », pas arme : les deux etats se "
        "distinguent depuis la console")
    # LE PAS EST EPINGLE, comme dans banc_comptes.py : deux appels a mfa.code()
    # de part et d'autre d'une frontiere de trente secondes tombent dans deux
    # fenetres, et la recette rendrait des verdicts opposes sur un code juste.
    s, d = appel("/api/compte/mfa/confirmer", "POST",
                 {"code": mfa.code(secret, pas=mfa.pas_de())}, nav=nav)
    dit(s == 200 and len(d.get("secours", [])) == 10,
        "il confirme, et recoit dix codes de secours", f"HTTP {s}")
    etat = etat_de(PORTEUR)
    dit(etat.get("mfa") == "arme" and etat.get("secours") == 10,
        "/admin annonce « arme » et compte les codes qui restent",
        f"{etat.get('mfa')}, {etat.get('secours')} codes")
    dit(secret not in json.dumps(etat) and "secret" not in json.dumps(etat),
        "et la liste des comptes ne porte NI le secret NI le mot",
        ", ".join(sorted(etat)))

    print("\n  ── un compte administrateur SANS le jeton n'y touche pas ──")
    nav2 = navigateur()
    s, _ = appel("/api/compte/entrer", "POST", {"nom": ROLE, "mdp": MDP_B},
                 nav=nav2)
    dit(s == 200, "il ouvre sa session d'administrateur", f"HTTP {s}")
    dit(etat_de(PORTEUR, jeton=False, nav=nav2).get("mfa") == "arme",
        "il voit bien l'etat du facteur des autres : la console lui repond, "
        "il n'y a rien de secret la-dedans")
    s, d = appel("/api/admin/comptes", jeton=False, nav=nav2)
    dit(d.get("peut_desarmer") is False,
        "mais elle lui dit d'avance que le bouton sera grise",
        f"peut_desarmer = {d.get('peut_desarmer')}")
    s, d = appel("/api/admin/comptes/" + PORTEUR + "/mfa", "DELETE", nav=nav2)
    dit(s == 403 and "jeton" in str(d.get("erreur", "")),
        "ET LE SERVEUR REFUSE : ce n'est pas la page qui garde",
        f"HTTP {s} — {str(d.get('erreur'))[:56]}")
    # LE CAS QUE L'ARBRE DE SYNTAXE NE PEUT PAS VOIR. Une garde ecrite avant le
    # retrait et un facteur qui survit au refus ne sont pas la meme chose.
    dit(etat_de(PORTEUR).get("mfa") == "arme",
        "et le facteur est TOUJOURS ARME apres ce refus")

    print("\n  ── avec le jeton, il tombe ──")
    s, d = appel("/api/admin/comptes/" + PORTEUR + "/mfa", "DELETE", jeton=True)
    dit(s == 200 and d.get("ok"), "le retrait passe", f"HTTP {s}")
    dit(etat_de(PORTEUR).get("mfa") == "", "/admin ne voit plus de facteur")
    s, _ = appel("/api/admin/comptes/" + PORTEUR + "/mfa", "DELETE", jeton=True)
    dit(s == 400,
        "recommencer sur un compte sans facteur est REFUSE, et non un succes "
        "vide : « c'est deja fait » et « ce n'est pas ce compte-la » se "
        "ressemblent trop", f"HTTP {s}")
    s, _ = appel("/api/admin/comptes/personne-de-ce-nom/mfa", "DELETE", jeton=True)
    dit(s == 404, "et un compte inconnu rend 404, non 400", f"HTTP {s}")

    print("\n  ── et son compte se rouvre avec son mot de passe seul ──")
    nav3 = navigateur()
    s, _ = appel("/api/compte/entrer", "POST", {"nom": PORTEUR, "mdp": MDP_A},
                 nav=nav3)
    dit(s == 200, "il entre sans code", f"HTTP {s}")
    s, d = appel("/api/compte/mfa", nav=nav3)
    dit(s == 200 and not d.get("arme") and not d.get("en_attente"),
        "son cote a lui dit la meme chose : rien d'arme, rien en attente")
    s, d = appel("/api/compte/mfa/preparer", "POST", {"mdp": MDP_A}, nav=nav3)
    dit(s == 200 and len(d.get("secret", "")) == 32,
        "il peut reenroler depuis zero", f"HTTP {s}")
    dit(d.get("secret") != secret,
        "avec un secret NEUF : le telephone qu'on venait de perdre ne rouvre "
        "rien")
finally:
    menage()
    dit(not etat_de(PORTEUR) and not etat_de(ROLE),
        "les deux comptes d'essai sont effaces")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    RATE :", x)
sys.exit(1 if rate else 0)
