#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les rappels signes, mesures contre un vrai serveur HTTP.

CE QUE CE BANC GARDE, DANS L'ORDRE DES DEGATS :

  1. LA LISTE DES HOTES (url_autorisee). C'est la defense contre la requete
     forgee cote serveur : le studio vit sur le reseau local, et une URL de
     rappel qu'elle laisse passer a tort fait POSTer le studio vers le routeur
     ou une console d'administration. Un cas par code de refus, un par regle
     de port, et les pieges classiques — « http://hote.autorise@ailleurs/ »,
     les schemas qui ne sont pas http, la liste vide.
  2. LA SIGNATURE (signature, signature_valide). Une verification trop
     laxiste fait accepter au recepteur un evenement forge ; un en-tete
     hostile qui la fait LEVER devient un 500 chez lui. Elle est confrontee a
     un calcul independant (hmac + hashlib ecrits ici), pas seulement a
     elle-meme : un aller-retour coherent peut etre faux pour tout recepteur
     qui suit le format.
  3. LA REDIRECTION NON SUIVIE. Un 302 qui serait suivi ferait sortir la
     requete de la liste : le serveur du banc compte qu'aucune requete
     n'atteint la cible.
  4. L'ANNULATION. Un livrer() qui avale asyncio.CancelledError empeche le
     studio de s'arreter pendant deux minutes et demie.
  5. LA POLITIQUE D'ESSAIS : ce qui re-essaie (5xx, 408, 425, 429, delai,
     reseau) et ce qui arrete (2xx, 3xx, les autres 4xx), avec les attentes
     DELAIS demandees dans l'ordre, et un horodatage NEUF a chaque essai.
  6. LE CORPS CANONIQUE : memes octets quel que soit l'ordre des cles, UTF-8
     non echappe.

livrer() est joue contre un vrai aiohttp.web lance sur 127.0.0.1, port 0 :
c'est le seul moyen de voir ce que le client ENVOIE (en-tetes, octets,
redirection suivie ou non). dormir() et horloge() sont factices : le banc
enregistre les attentes demandees au lieu de les subir, et tient en quelques
secondes.

    uv run --with aiohttp python banc_rappels.py
    python banc_rappels.py            (en CI, aiohttp y est installe)

CE QU'IL NE VOIT PAS :
  - le noeud Code de n8n : la recette crypto.createHmac de la docstring de
    rappels.py n'est jouee par aucun JavaScript ici. Seul le calcul Python
    independant la represente.
  - qui appelle url_autorisee() AVANT livrer(), et ou la liste des hotes est
    gardee : c'est le travail de serveur.py et d'acces.py, pas de ce module.
  - la resolution des noms : un hote autorise qui pointe vers le routeur
    passe, et c'est voulu (la comparaison est textuelle).
  - https : le serveur du banc parle http seulement.
  - les vraies attentes de 5, 30 et 120 s : on verifie qu'elles sont
    DEMANDEES, pas qu'asyncio.sleep les tient.
"""
import asyncio
import hashlib
import hmac
import json
import os
import socket
import sys
import time

# LA CONSOLE WINDOWS ECRIT EN cp1252, et ce banc n'importe pas serveur.py :
# sans ces lignes, il meurt sur son propre affichage au premier « — ». Voir
# banc_mfa.py, qui le paie depuis le 2 septembre 2026.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import rappels as R  # noqa: E402

# Lu AVANT que le banc n'importe aiohttp lui-meme : apres, la question n'aurait
# plus de sens.
SANS_AIOHTTP = "aiohttp" not in sys.modules

ok, rate = [], []
def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


SECRET = "secret-du-banc"
# Janvier 2027 : assez loin de l'horloge reelle pour qu'un appel qui l'oublie
# et lit time.time() se voie.
T = 1_800_000_000

print("\n  ── le module se lit sans aiohttp ──")
dit(SANS_AIOHTTP,
    "importer rappels n'importe pas aiohttp : un recepteur Python peut le recopier",
    "aiohttp deja charge par rappels" if not SANS_AIOHTTP else "")

# ══ 1. LA LISTE DES HOTES ════════════════════════════════════════════════
print("\n  ── la liste des hotes (SSRF) ──")
HOTES = ["n8n.local", "192.168.1.20:5678", "[::1]:5678",
         "studio.exemple.org:443",
         # NON normalisee, expres : acces.hote_valide() rend des minuscules,
         # mais url_autorisee() ne doit pas en dependre.
         "Majuscules.Local"]
CAS_URL = [
    # (url, attendu, pourquoi)
    ("http://n8n.local/webhook/abc", None, "entree sans port, port par defaut"),
    ("https://n8n.local/x", None, "entree sans port, en https : le 443"),
    # UNE ENTREE SANS PORT NE VAUT QUE POUR LE PORT PAR DEFAUT DU SCHEMA. Elle
    # valait pour tous les ports : declarer une machine pour son n8n laissait
    # une cle volee viser son ComfyUI ou sa console (revue du 4 novembre 2026).
    ("http://n8n.local:5678/webhook/abc", "hote",
     "entree sans port : PAS les autres ports de l'hote"),
    ("https://n8n.local:8443/x", "hote", "entree sans port, en https : pas le 8443"),
    ("http://n8n.local:8188/interrupt", "hote",
     "entree sans port : le ComfyUI de la meme machine non plus"),
    ("http://192.168.1.20:5678/webhook", None, "entree avec port, meme port"),
    ("http://192.168.1.20/webhook", "hote",
     "entree avec port : le 80 par defaut n'est pas le 5678"),
    ("http://192.168.1.20:5679/webhook", "hote",
     "entree avec port : un port different"),
    ("https://studio.exemple.org/rappel", None, "https sans port vaut 443"),
    ("https://studio.exemple.org:443/rappel", None, "443 ecrit en toutes lettres"),
    ("http://studio.exemple.org/rappel", "hote",
     "http sans port vaut 80, pas 443"),
    ("HTTP://N8N.LOCAL/Webhook", None, "majuscules dans l'URL"),
    ("http://majuscules.local/x", None, "entree de la liste en majuscules"),
    ("http://[::1]:5678/hook", None, "IPv6 entre crochets, bon port"),
    ("http://[::1]:5679/hook", "hote", "IPv6, port different"),
    ("http://[::1]/hook", "hote", "IPv6, port par defaut"),
    ("http://ailleurs.local/x", "hote", "hote absent de la liste"),
    ("http://n8n.local.evil.example/x", "hote", "l'hote autorise en prefixe"),
    ("http://evil.example/n8n.local", "hote", "l'hote autorise dans le chemin"),
    ("http://127.1/", "hote", "une autre ecriture d'une adresse"),
    ("http://n8n.local@ailleurs/", "identifiants",
     "le piege : l'hote reel est « ailleurs »"),
    ("http://user:mdp@n8n.local/", "identifiants",
     "des identifiants vers un hote autorise"),
    ("http://n8n.local:5678@192.168.1.1/", "identifiants",
     "un faux port devant l'arobase"),
    ("javascript:alert(1)", "schema", "javascript:"),
    ("file:///etc/passwd", "schema", "file:///"),
    ("ftp://n8n.local/x", "schema", "ftp://"),
    ("gopher://n8n.local:70/_x", "schema", "gopher://"),
    ("n8n.local/webhook", "schema", "sans schema"),
    ("http:///chemin", "illisible", "sans hote"),
    ("http://n8n.local:abc/", "illisible", "port non numerique"),
    ("http://n8n.local:99999/", "illisible", "port hors bornes"),
    ("http://[::1/", "illisible", "crochet IPv6 non ferme"),
    ("http://n8n.local\\@ailleurs/", "illisible",
     "barre inverse, lue differemment selon le client"),
    ("http://n8n.local /x", "illisible", "un espace dans l'URL"),
    ("", "illisible", "URL vide"),
    (None, "illisible", "None"),
]
for _url, _attendu, _pourquoi in CAS_URL:
    try:
        _obtenu = R.url_autorisee(_url, HOTES)
    except Exception as e:
        _obtenu = f"LEVE {type(e).__name__}"
    dit(_obtenu == _attendu,
        f"{_url!r} -> {_attendu or 'autorisee'} ({_pourquoi})",
        "" if _obtenu == _attendu else f"obtenu {_obtenu!r}")
# LE TEMOIN : sans lui, une table reduite a trois cas « autorisee » serait
# verte d'une fonction qui autorise tout.
_codes = {a for _, a, _ in CAS_URL}
dit(_codes == {None, "hote", "identifiants", "schema", "illisible"}
    and sum(1 for _, a, _ in CAS_URL if a is None) >= 5
    and sum(1 for _, a, _ in CAS_URL if a is not None) >= 15,
    "la table couvre les quatre codes de refus ET des URL autorisees",
    f"{len(CAS_URL)} cas")

dit(R.url_autorisee("http://n8n.local/", []) == "hote",
    "liste vide -> hote : pas de liste, aucune URL")
dit(R.url_autorisee("http://n8n.local/", None) == "hote",
    "liste None -> hote")
dit(R.url_autorisee("http://n8n.local/", "n8n.local") is None
    and R.url_autorisee("http://n.local/", "n8n.local") == "hote",
    "une chaine seule vaut une entree, pas une liste de lettres")
dit(R.url_autorisee("http://n8n.local/", ["", "  ", "[::1", "h:p", None,
                                           "n8n.local"]) is None,
    "une entree illisible est ignoree, sans lever, et les suivantes comptent")

# ══ 2. LA SIGNATURE ══════════════════════════════════════════════════════
print("\n  ── la signature ──")
EVT = {"evenement": "rendu.fini", "rendu": "r-42", "fichiers": ["a.png"],
       "invite": "un chateau en été"}
CORPS = R.corps_de(EVT)
ENT = R.signature(SECRET, T, CORPS)
# LE CALCUL INDEPENDANT, ecrit ici avec hmac et hashlib : c'est ce qu'un
# recepteur qui suit le format recalcule, et ce que le noeud Code de n8n fait.
_hex = hmac.new(SECRET.encode("utf-8"), f"{T}.".encode() + CORPS,
                hashlib.sha256).hexdigest()
dit(ENT == f"t={T},v1={_hex}",
    "la signature est hmac-sha256(secret, « t. » + corps), comme le recalcule un recepteur",
    ENT[:40])
dit(R.signature_valide(SECRET, ENT, CORPS, maintenant=T),
    "aller-retour : signature() puis signature_valide() dit oui")
_altere = CORPS[:-1] + bytes([CORPS[-1] ^ 1])
dit(_altere != CORPS and not R.signature_valide(SECRET, ENT, _altere, maintenant=T),
    "un octet du corps change -> refuse")
dit(not R.signature_valide("autre-secret", ENT, CORPS, maintenant=T),
    "un autre secret -> refuse")
dit(not R.signature_valide(SECRET, ENT, CORPS, maintenant=T + R.TOLERANCE + 1),
    "horodatage trop vieux -> refuse")
dit(R.signature_valide(SECRET, ENT, CORPS, maintenant=T + R.TOLERANCE),
    "et a la limite exacte de la tolerance, accepte (temoin du cas precedent)")
dit(not R.signature_valide(SECRET, ENT, CORPS, maintenant=T - R.TOLERANCE - 1),
    "horodatage trop dans le futur -> refuse")
dit(R.signature_valide(SECRET, ENT, CORPS, maintenant=T - R.TOLERANCE),
    "et a la limite exacte dans le futur, accepte (temoin)")
dit(not R.signature_valide(SECRET, ENT, CORPS, maintenant=T + 11, tolerance=10),
    "la tolerance passee en argument est bien celle appliquee")
# Sans « maintenant », c'est l'horloge reelle : T est en 2027, donc refuse,
# et une signature de l'instant est acceptee.
dit(not R.signature_valide(SECRET, ENT, CORPS)
    and R.signature_valide(SECRET, R.signature(SECRET, int(time.time()), CORPS),
                           CORPS),
    "sans « maintenant », l'horloge reelle tranche")
dit(R.signature_valide(SECRET, f"v1={_hex},t={T}", CORPS, maintenant=T),
    "ordre « v1=...,t=... » -> accepte")
dit(R.signature_valide(SECRET, f" t={T} , v1={_hex} ", CORPS, maintenant=T),
    "des espaces autour des champs -> accepte")
dit(R.signature_valide(SECRET, f"t={T},v1={'0' * 64},v1={_hex}", CORPS,
                       maintenant=T),
    "deux v1= dont le second est bon (rotation de secret) -> accepte")
dit(R.signature_valide(SECRET, f"t={T},v1={_hex},v1={'0' * 64}", CORPS,
                       maintenant=T),
    "deux v1= dont le premier est bon -> accepte")
dit(R.signature_valide(SECRET, f"t={T},v1=é,v1={_hex}", CORPS, maintenant=T),
    "un v1= non ASCII ne fait pas rater le v1= juste qui le suit")
dit(not R.signature_valide(SECRET, f"t={T},v1={'0' * 64},v1={'1' * 64}", CORPS,
                           maintenant=T),
    "deux v1= tous deux faux -> refuse (temoin de la rotation)")
MALFORMES = [
    ("", "vide"), (None, "None"), (12345, "un entier"),
    (f"v1={_hex}", "sans t="), (f"t={T}", "sans v1="),
    (f"t={T},v1=", "v1= vide"), (f"t=abc,v1={_hex}", "t= non numerique"),
    (f"t=,v1={_hex}", "t= vide"), (f"t=-{T},v1={_hex}", "t= negatif"),
    (f"t=²,v1={_hex}", "t= en exposant"),
    (f"t={T},t={T},v1={_hex}", "deux t="),
    (f"t={T};v1={_hex}", "point-virgule au lieu de virgule"),
    ("n'importe quoi", "du texte"), (",,,===,", "des separateurs seuls"),
]
for _entete, _quoi in MALFORMES:
    try:
        _rep = R.signature_valide(SECRET, _entete, CORPS, maintenant=T)
    except Exception as e:
        _rep = f"LEVE {type(e).__name__}"
    dit(_rep is False, f"entete malforme ({_quoi}) -> faux, sans lever",
        "" if _rep is False else repr(_rep))
dit(len(MALFORMES) >= 10, "la liste des en-tetes malformes n'est pas vide",
    f"{len(MALFORMES)} en-tetes")
try:
    _leve = R.signature_valide(None, ENT, CORPS, maintenant=T)
except Exception as e:
    _leve = f"LEVE {type(e).__name__}"
dit(_leve is False, "un secret None -> faux, sans lever", repr(_leve))

# ══ 6. LE CORPS CANONIQUE (court, et la signature en depend) ═════════════
print("\n  ── le corps canonique ──")
_inverse = dict(reversed(list(EVT.items())))
dit(list(_inverse) != list(EVT),
    "temoin : les deux dicts sont construits dans un ordre different")
dit(R.corps_de(_inverse) == CORPS,
    "meme evenement, cles dans un autre ordre -> memes octets")
dit("été".encode("utf-8") in CORPS and b"\\u00e9" not in CORPS,
    "un « é » reste un é en octets UTF-8, pas un \\u00e9")
dit(R.corps_de({"b": [1, 2], "a": {"y": 1, "x": 2}})
    == b'{"a":{"x":2,"y":1},"b":[1,2]}',
    "separateurs compacts et cles triees, jusque dans les dicts imbriques")
dit(json.loads(CORPS.decode("utf-8")) == EVT,
    "et le corps se relit en l'evenement d'origine")


# ══ 3-5. LIVRER, CONTRE UN VRAI SERVEUR ══════════════════════════════════
# Ce que le serveur du banc fait de chaque chemin. Les compteurs sont la
# preuve de ce que le client a reellement envoye.
RECU = []        # (chemin, en-tetes, corps)
COMPTE = {}
MUET = 1.5       # ce que dort /muet : plus que le delai laisse au client


async def _recepteur(request):
    from aiohttp import web
    corps = await request.read()
    chemin = request.path
    RECU.append((chemin, dict(request.headers), corps))
    COMPTE[chemin] = COMPTE.get(chemin, 0) + 1
    if chemin == "/ok":
        # LE RECEPTEUR VERIFIE AVEC signature_valide(), avec l'horloge reelle
        # et SON secret : 200 prouve la symetrie de bout en bout.
        bon = R.signature_valide(SECRET, request.headers.get(R.ENTETE_SIGNATURE),
                                 corps)
        return web.Response(status=200 if bon else 401)
    if chemin == "/panne-puis-ok":
        return web.Response(status=500 if COMPTE[chemin] == 1 else 200)
    if chemin == "/muet":
        await asyncio.sleep(MUET)
        return web.Response(status=200)
    if chemin.startswith("/statut/"):
        statut = int(chemin.rsplit("/", 1)[1])
        entetes = {"Location": "/cible"} if 300 <= statut < 400 else {}
        return web.Response(status=statut, headers=entetes)
    if chemin == "/cible":
        return web.Response(status=200)
    return web.Response(status=404)


class _Horloge:
    """Une horloge qui avance d'un pas a chaque lecture."""

    def __init__(self, depart, pas):
        self.t, self.pas = depart, pas

    def __call__(self):
        v = self.t
        self.t += self.pas
        return v


def _dormeur(journal):
    async def dormir(secondes):
        journal.append(secondes)
    return dormir


def _t_de(entetes):
    return int(entetes[R.ENTETE_SIGNATURE].split(",")[0].split("=")[1])


async def _jouer(session, base, chemin, **reglages):
    journal = []
    reglages.setdefault("dormir", _dormeur(journal))
    reglages.setdefault("delai", 2)
    reglages.setdefault("evenement", "rendu.fini")
    reglages.setdefault("livraison", "liv-" + chemin.strip("/").replace("/", "-"))
    rendu = await R.livrer(session, base + chemin, CORPS,
                           reglages.pop("secret", SECRET), **reglages)
    return rendu, journal


async def _livraisons():
    import aiohttp
    from aiohttp import web
    app = web.Application()
    app.router.add_route("*", "/{chemin:.*}", _recepteur)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    base = f"http://127.0.0.1:{port}"
    try:
        async with aiohttp.ClientSession() as session:
            await _livraisons_sur(session, base)
    finally:
        await runner.cleanup()


async def _livraisons_sur(session, base):
    print("\n  ── une livraison reussie ──")
    r, j = await _jouer(session, base, "/ok", livraison="liv-unique-1")
    dit(r == {"livre": True, "essais": 1, "statut": 200, "raison": "livre"},
        "/ok : livre au premier essai, et le recepteur a valide la signature",
        repr(r))
    dit(j == [0], "le premier essai part sans attendre (DELAIS[0] = 0)", repr(j))
    _ch, _ent, _corps = [x for x in RECU if x[0] == "/ok"][-1]
    dit(_corps == CORPS, "le recepteur a recu les octets exacts du corps signe")
    dit(R.signature_valide(SECRET, _ent.get(R.ENTETE_SIGNATURE), _corps),
        "et la signature RECUE se verifie aussi hors du serveur")
    dit(_ent.get("Content-Type") == "application/json",
        "Content-Type: application/json", _ent.get("Content-Type", ""))
    dit(_ent.get("User-Agent") == "ComfyStudio-rappel",
        "User-Agent: ComfyStudio-rappel", _ent.get("User-Agent", ""))
    dit(_ent.get(R.ENTETE_EVENEMENT) == "rendu.fini",
        "l'en-tete d'evenement porte l'evenement", _ent.get(R.ENTETE_EVENEMENT, ""))
    dit(_ent.get(R.ENTETE_LIVRAISON) == "liv-unique-1",
        "l'en-tete de livraison porte l'identifiant donne",
        _ent.get(R.ENTETE_LIVRAISON, ""))
    # LE TEMOIN DE /ok : sans lui, un /ok qui repondrait 200 a tout ferait
    # passer le premier cas sans rien prouver de la signature.
    r, _ = await _jouer(session, base, "/ok", secret="mauvais-secret")
    dit(r["statut"] == 401 and not r["livre"] and r["essais"] == 1,
        "temoin : signe avec un autre secret, le recepteur refuse (401), un seul essai",
        repr(r))

    for evt in R.EVENEMENTS:
        r, _ = await _jouer(session, base, "/ok", evenement=evt)
        dit(r["livre"] and RECU[-1][1].get(R.ENTETE_EVENEMENT) == evt,
            f"l'evenement {evt} part et arrive tel quel")
    _avant = len(RECU)
    r, j = await _jouer(session, base, "/ok", evenement="rendu.termine")
    dit(r["essais"] == 0 and not r["livre"] and r["raison"] == "evenement inconnu"
        and len(RECU) == _avant and j == [],
        "un evenement hors EVENEMENTS ne part pas", repr(r))

    print("\n  ── ce qui merite un nouvel essai ──")
    r, j = await _jouer(session, base, "/panne-puis-ok",
                        horloge=_Horloge(T, 7))
    dit(r == {"livre": True, "essais": 2, "statut": 200, "raison": "livre"},
        "500 puis 200 -> livre en deux essais", repr(r))
    dit(j == list(R.DELAIS[:2]), "les attentes demandees sont DELAIS[:2]", repr(j))
    _deux = [e for c, e, _ in RECU if c == "/panne-puis-ok"]
    dit(len(_deux) == 2 and _deux[0].get(R.ENTETE_LIVRAISON)
        == _deux[1].get(R.ENTETE_LIVRAISON),
        "les deux essais portent le MEME identifiant de livraison",
        " / ".join(e.get(R.ENTETE_LIVRAISON, "?") for e in _deux))

    for statut in (500, 502, 503, 408, 425, 429):
        COMPTE.pop(f"/statut/{statut}", None)
        r, j = await _jouer(session, base, f"/statut/{statut}")
        dit(r["essais"] == 4 and not r["livre"] and r["statut"] == statut
            and COMPTE.get(f"/statut/{statut}") == 4 and j == list(R.DELAIS),
            f"{statut} -> re-essai : quatre essais aux attentes DELAIS, puis echec",
            repr(r) + " " + repr(j))
    dit(len(R.DELAIS) == 4 and R.DELAIS[0] == 0,
        "DELAIS fait bien quatre essais, le premier sans attendre", repr(R.DELAIS))

    print("\n  ── un horodatage neuf a chaque essai ──")
    COMPTE.pop("/statut/503", None)
    _premier = len(RECU)
    r, _ = await _jouer(session, base, "/statut/503",
                        horloge=_Horloge(T, 1000))
    _essais = [(e, c) for ch, e, c in RECU[_premier:] if ch == "/statut/503"]
    _ts = [_t_de(e) for e, _ in _essais]
    dit(_ts == [T, T + 1000, T + 2000, T + 3000],
        "chaque essai signe avec l'heure de l'essai, pas celle du premier",
        repr(_ts))
    dit(all(R.signature_valide(SECRET, e[R.ENTETE_SIGNATURE], c, maintenant=t)
            for (e, c), t in zip(_essais, _ts)) and len(_essais) == 4,
        "et chacune se verifie a son propre instant")
    dit(len(_essais) == 4 and not R.signature_valide(
        SECRET, _essais[0][0][R.ENTETE_SIGNATURE], _essais[0][1],
        maintenant=_ts[-1]),
        "temoin : la signature du premier essai serait refusee a l'heure du dernier")

    print("\n  ── ce qui arrete les essais ──")
    for statut in (200, 201, 202, 204):
        COMPTE.pop(f"/statut/{statut}", None)
        r, _ = await _jouer(session, base, f"/statut/{statut}")
        dit(r["livre"] and r["essais"] == 1 and r["statut"] == statut
            and COMPTE.get(f"/statut/{statut}") == 1,
            f"{statut} -> livre, un seul essai", repr(r))
    for statut in (400, 401, 403, 404, 410, 422):
        COMPTE.pop(f"/statut/{statut}", None)
        r, j = await _jouer(session, base, f"/statut/{statut}")
        dit(not r["livre"] and r["essais"] == 1 and r["statut"] == statut
            and r["raison"] == "refuse par le recepteur"
            and COMPTE.get(f"/statut/{statut}") == 1 and j == [0],
            f"{statut} -> arret apres un essai : insister ne changera rien",
            repr(r))
    COMPTE.pop("/cible", None)
    for statut in (301, 302, 303, 307, 308):
        COMPTE.pop(f"/statut/{statut}", None)
        r, _ = await _jouer(session, base, f"/statut/{statut}")
        dit(not r["livre"] and r["essais"] == 1 and r["statut"] == statut
            and r["raison"] == "redirection"
            and COMPTE.get(f"/statut/{statut}") == 1,
            f"{statut} -> arret, raison redirection", repr(r))
    dit(COMPTE.get("/cible", 0) == 0,
        "aucune requete n'a atteint la cible des redirections : elles ne sont pas suivies",
        f"{COMPTE.get('/cible', 0)} requete(s) sur /cible")
    # LE TEMOIN DU COMPTEUR : sans lui, « zero requete sur /cible » serait
    # vrai d'un serveur qui ne compterait rien.
    async with session.post(base + "/cible", data=b"{}") as rep:
        _st = rep.status
    dit(_st == 200 and COMPTE.get("/cible", 0) == 1,
        "temoin : une requete directe sur /cible, elle, est comptee",
        f"{COMPTE.get('/cible', 0)}")

    print("\n  ── un recepteur muet, un port ferme ──")
    _debut = time.monotonic()
    r, j = await _jouer(session, base, "/muet", delai=0.3)
    dit(not r["livre"] and r["essais"] == 4 and r["statut"] is None
        and r["raison"] == "delai depasse" and j == list(R.DELAIS),
        "serveur muet plus longtemps que le delai -> quatre essais, puis echec",
        f"{r!r} en {time.monotonic() - _debut:.1f} s")
    # Un port qu'on vient de liberer : rien n'y ecoute.
    _s = socket.socket()
    _s.bind(("127.0.0.1", 0))
    _ferme = _s.getsockname()[1]
    _s.close()
    try:
        r, j = await _jouer(session, f"http://127.0.0.1:{_ferme}", "/x",
                            delai=1)
        _leve = ""
    except Exception as e:
        r, j, _leve = {}, [], f"LEVE {type(e).__name__}: {e}"
    dit(not _leve and not r.get("livre") and r.get("essais") == 4
        and r.get("statut") is None
        and r.get("raison") in ("injoignable", "delai depasse"),
        "port ferme -> quatre essais puis echec, sans lever", _leve or repr(r))

    # UNE COUPURE RESEAU NETTE, sans dependre de la facon dont l'OS refuse un
    # port ferme : sous Windows, un refus sur 127.0.0.1 met deux secondes et
    # arrive comme un delai depasse, et le cas precedent ne voit donc pas la
    # branche « injoignable ».
    class _SessionCoupee:
        def __init__(self):
            self.appels = 0

        def post(self, *_a, **_k):
            self.appels += 1
            raise ConnectionResetError("connexion coupee")
    _coupee = _SessionCoupee()
    try:
        r, j = await _jouer(_coupee, base, "/x")
        _leve = ""
    except Exception as e:
        r, j, _leve = {}, [], f"LEVE {type(e).__name__}"
    dit(not _leve and r.get("essais") == 4 and r.get("raison") == "injoignable"
        and _coupee.appels == 4 and j == list(R.DELAIS),
        "connexion coupee -> re-essais aux attentes DELAIS, raison injoignable",
        _leve or repr(r))

    # NE LEVE JAMAIS, meme quand ce qu'on lui passe casse.
    async def _dormir_casse(_s):
        raise RuntimeError("dormir casse")
    try:
        r, _ = await _jouer(session, base, "/ok", dormir=_dormir_casse)
        _leve = ""
    except Exception as e:
        r, _leve = {}, f"LEVE {type(e).__name__}"
    dit(not _leve and r.get("raison") == "erreur interne" and not r.get("livre"),
        "un dormir() qui leve donne un echec nomme, pas une exception",
        _leve or repr(r))

    print("\n  ── l'annulation passe ──")
    # Pendant la requete : le studio s'arrete pendant qu'un recepteur dort.
    tache = asyncio.ensure_future(
        _jouer(session, base, "/muet", delai=5, delais=(0,)))
    await asyncio.sleep(0.3)
    tache.cancel()
    try:
        _fin = await tache
        _annule = False
    except asyncio.CancelledError:
        _fin, _annule = None, True
    dit(_annule and tache.cancelled(),
        "annule pendant la requete -> CancelledError remonte", repr(_fin))

    # Pendant l'attente entre deux essais : c'est la que le studio passe
    # deux minutes et demie.
    _appels = []

    async def _dormir_annule(secondes):
        _appels.append(secondes)
        if len(_appels) == 2:
            raise asyncio.CancelledError()
    try:
        _fin = await _jouer(session, base, "/statut/503", dormir=_dormir_annule)
        _annule = False
    except asyncio.CancelledError:
        _fin, _annule = None, True
    dit(_annule and _appels == [0, 5],
        "annule pendant l'attente entre deux essais -> CancelledError remonte",
        repr(_fin))


try:
    asyncio.run(_livraisons())
except Exception as e:
    dit(False, "le banc de livraison s'est deroule jusqu'au bout",
        f"{type(e).__name__}: {e}")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
