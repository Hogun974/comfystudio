#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Une machine ne prete son modele de langage que si elle prete sa carte.

LA REGLE, donnee par l'utilisateur le 10 novembre 2026, mot pour mot : « Comfy
studio ne devrait pas avoir le droit d'appeler ollama sur un noeud dont le
comfy n'est pas lance ou en pause (meme s'il est disponible) ».

POURQUOI : sur le PC (RTX 2080 Ti, la carte avec laquelle son proprietaire
joue), Ollama tourne en permanence ; ComfyUI et l'agent ne sont lances que le
temps de preter la carte au studio. Fermer ComfyUI, ou mettre la machine en
pause, c'est dire « la carte est a moi ». Le 9 novembre 2026, quatre « analyse
par qwen2.5vl:7b » ont pourtant charge 5,7 Go sur cette carte, ComfyUI ferme :
le studio appelait l'Ollama du PC en direct, sans rien demander a personne.

CE QUE CE BANC COMPTE, C'EST CE QUE LES OLLAMA RECOIVENT. Des faux Ollama
ecoutent pour de bon sur la boucle locale — celui du PC, celui du NAS, celui
de la machine du studio (127.0.0.1) et un simple serveur de langage rattache a
aucune machine (127.0.0.2) — plus un faux ComfyUI pour la machine du studio.
Chacun note ce qu'on lui demande : une GENERATION, un
DECHARGEMENT (prompt vide, keep_alive 0) ou une LECTURE (/api/tags, /api/ps).
UNE MACHINE FERMEE, ON N'Y TOUCHE PAS DU TOUT : ni generation, ni meme un
dechargement — son proprietaire se sert d'Ollama pour lui-meme, et le studio
pourrait decharger le modele qu'il emploie. Seules les lectures restent. Le
studio, lui, est le vrai : _appeler_llm, _ollama_local, liberer_modele_a,
poser_a, et les vraies routes de l'agent (annonce, question, reponse). Aucun
reseau au-dela de la boucle locale, aucun vrai Ollama, aucun vrai ComfyUI.

    python banc_pret.py
"""
import asyncio
import base64
import json
import os
import socket
import sys
import tempfile


def _prise(hote="127.0.0.1"):
    """Une prise deja liee : son port est connu AVANT d'importer le studio,
    qui lit OLLAMA_URL et COMFY_URL une fois, au chargement."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((hote, 0))
    return s


# QUATRE OLLAMA. Ceux du PC et du NAS sont rattaches a leur machine par le
# cache, comme le fait le releve. « ici » ecoute sur 127.0.0.1 : pour le
# studio, c'est l'Ollama de SA machine. « libre » ecoute sur 127.0.0.2, une
# adresse de bouclage que le studio ne tient pas pour la sienne (il ne
# reconnait que 127.0.0.1, localhost et ::1) : c'est le simple serveur de
# langage, rattache a aucune machine.
HOTES = {"pc": "127.0.0.1", "nas": "127.0.0.1", "ici": "127.0.0.1",
         "comfy": "127.0.0.1", "libre": "127.0.0.2"}
PRISES = {nom: _prise(hote) for nom, hote in HOTES.items()}
ADRESSE = {nom: f"http://{HOTES[nom]}:{s.getsockname()[1]}"
           for nom, s in PRISES.items()}
PC, NAS, LIBRE, ICI = (ADRESSE["pc"], ADRESSE["nas"], ADRESSE["libre"],
                       ADRESSE["ici"])

os.environ["OLLAMA_URL"] = ",".join((PC, NAS, LIBRE))
# Les images jointes du banc vont dans un dossier a lui, pas dans le dossier
# d'entree d'un ComfyUI de cette machine.
os.environ["COMFY_ENTREE"] = tempfile.mkdtemp(prefix="banc_pret_entrees_")
# LE ComfyUI DU STUDIO EST UN FAUX, lui aussi : sans cette ligne, la sonde du
# noeud local irait frapper a 127.0.0.1:8188 — le vrai ComfyUI de la machine
# qui lance le banc, s'il tourne.
os.environ["COMFY_URL"] = ADRESSE["comfy"]
os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_pret_")
os.environ["STUDIO_AUTH"] = "libre"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402
from aiohttp import web  # noqa: E402

S.ADMIN_JETON = "jeton-d-administration-du-banc"

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


MODELE = "qwen2.5vl:7b"
MODELES = [{"name": MODELE, "size": 5_970_000_000,
            "capabilities": ["vision", "completion"]}]
PHRASE_FERME = ("PC (RTX 2080 Ti) : ComfyUI n'y tourne pas — son modele de "
                "langage n'est pas utilise")


class FauxOllama:
    """Un Ollama qui note ce qu'on lui demande, et repond ce qu'on lui dicte."""

    def __init__(self, nom):
        self.nom = nom
        self.vider()

    def vider(self):
        self.generes = []       # ce que la regle interdit sur une machine fermee
        self.decharges = []     # keep_alive 0 : interdit la aussi
        self.lus = []           # /api/tags, /api/ps : la seule chose permise
        self.reponse = "{}"     # un texte, (statut, corps), ou une fonction
        self.au_dechargement = None

    async def _generer(self, req):
        corps = await req.json()
        if not corps.get("prompt") and corps.get("keep_alive") == 0:
            self.decharges.append(corps)
            if self.au_dechargement:
                await self.au_dechargement()
            return web.json_response({"done": True, "done_reason": "unload"})
        self.generes.append(corps)
        rep = self.reponse
        if callable(rep):
            rep = await rep(corps)
        if isinstance(rep, tuple):
            return web.Response(status=rep[0], text=rep[1])
        return web.json_response({"response": rep, "done": True,
                                  "done_reason": "stop"})

    async def _tags(self, req):
        self.lus.append("/api/tags")
        return web.json_response({"models": MODELES})

    async def _ps(self, req):
        self.lus.append("/api/ps")
        return web.json_response({"models": [
            dict(name=m["name"], size=m["size"], size_vram=m["size"])
            for m in MODELES]})

    async def demarrer(self):
        app = web.Application()
        app.router.add_post("/api/generate", self._generer)
        app.router.add_get("/api/tags", self._tags)
        app.router.add_get("/api/ps", self._ps)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        await web.SockSite(self.runner, PRISES[self.nom]).start()


class FauxComfy:
    """Le ComfyUI de la machine du studio : ouvert, il repond ; ferme, non."""

    def __init__(self):
        self.ouvert = True

    async def _stats(self, req):
        if not self.ouvert:
            return web.Response(status=503, text="ferme")
        return web.json_response({"devices": [
            {"name": "cuda:0 RTX 2080 Ti", "type": "cuda",
             "vram_total": 11 * 1024 ** 3, "vram_free": 9 * 1024 ** 3}]})

    async def _file(self, req):
        if not self.ouvert:
            return web.Response(status=503, text="ferme")
        return web.json_response({"queue_running": [], "queue_pending": []})

    async def demarrer(self):
        app = web.Application()
        app.router.add_get("/system_stats", self._stats)
        app.router.add_get("/queue", self._file)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        await web.SockSite(self.runner, PRISES["comfy"]).start()


FAUX = {nom: FauxOllama(nom) for nom in ("pc", "nas", "libre", "ici")}
PCF, NASF, LIBREF, ICIF = FAUX["pc"], FAUX["nas"], FAUX["libre"], FAUX["ici"]
COMFY = FauxComfy()
ADRESSE_D_ANNONCE = {"pc": "10.0.0.1", "zima": "10.0.0.2"}


class Req(dict):
    """Ce qu'attendent les routes de l'agent et celle de l'essai de /admin."""

    def __init__(self, jeton="", corps=None, match=None, admin=False,
                 remote="10.0.0.9"):
        super().__init__()
        self.headers = {"X-Jeton": jeton}
        if admin:
            self.headers["X-Admin"] = S.ADMIN_JETON
        self.cookies = {}
        self.query = {}
        self.remote = remote
        self.match_info = match or {}
        self._corps = corps or {}

    async def json(self):
        return self._corps


def poser(ollamas=None):
    """Le parc de la maison : le PC et le NAS derriere leur agent, ComfyUI
    OUVERT et hors pause, et les trois Ollama. Chaque cas part de la."""
    maintenant = S.time.time()
    S.OLLAMAS[:] = [PC, NAS, LIBRE] if ollamas is None else ollamas
    S.REGISTRE.clear()
    S.REGISTRE["pc"] = {"id": "pc", "titre": "PC (RTX 2080 Ti)", "agent": True,
                        "jeton": "jeton-du-pc", "pause": None}
    S.REGISTRE["zima"] = {"id": "zima", "titre": "NAS ZimaOS", "agent": True,
                          "jeton": "jeton-du-nas", "pause": None}
    S.ETAT_NOEUDS.clear()
    # « annonce » : les deux agents se sont annonces a l'instant, ComfyUI
    # ouvert — c'est le champ que seule la route d'annonce pose.
    S.ETAT_NOEUDS["pc"] = {"repond": True, "vram": 11.0, "ram": 63.8,
                           "vu": maintenant, "annonce": maintenant,
                           "ip": "10.0.0.1"}
    S.ETAT_NOEUDS["zima"] = {"repond": True, "vram": 8.0, "ram": 23.4,
                             "vu": maintenant, "annonce": maintenant,
                             "ip": "10.0.0.2"}
    S.noeud_local().pop("pause", None)
    S.SERVI_DEPUIS[0] = 0.0
    S.JUGEMENTS_IMAGE.clear()
    S._CERVEAUX.clear()
    for url, ident in ((PC, "pc"), (NAS, "zima"), (LIBRE, None), (ICI, None)):
        # « quand » dans l'avenir : le cache ne se releve pas tout seul, et le
        # rattachement reste celui qu'on pose. Un cas le fait relever expres.
        S._CERVEAUX[url] = {"quand": maintenant + 3600, "noeud": ident,
                            "modeles": [dict(m) for m in MODELES],
                            "en_cours": False, "repond": True}
    S._PLACEMENT.clear()
    for url in (PC, NAS, LIBRE, ICI):
        S._PLACEMENT[url] = {"part": 1.0, "quand": maintenant}
    for registre in (S.VERROUS_NOEUD, S.MODELES_CASSES, S.QUARANTAINES,
                     S._VUS_DEGENERE, S._DECHARGE_DEGENERE, S.QUESTIONS,
                     S.REPONSES, S._CHAUD):
        registre.clear()
    S.DEGENERESCENCES.clear()
    # Le studio tourne depuis une heure : l'attente des premieres annonces ne
    # joue pas. Le cas du reveil la remet a zero lui-meme.
    S.DEMARRE = maintenant - 3600
    COMFY.ouvert = True
    for f in FAUX.values():
        f.vider()


_NUMERO = [0]


def tache(nom):
    _NUMERO[0] += 1
    tid = f"pret-{_NUMERO[0]:02d}-{nom}"
    S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
    return tid


def fil(tid):
    return [e["msg"] for e in (S.TACHES.get(tid) or {}).get("etapes", [])]


async def annoncer(ident, comfy=True):
    """Un battement de l'agent, par la VRAIE route. « comfy=False » est mot
    pour mot ce qu'agent_noeud.py envoie quand ComfyUI ne repond plus — avec
    son Ollama qui, lui, repond toujours : c'est toute la situation."""
    langage = {"ok": True, "modeles": [MODELE]}
    corps = ({"carte": "RTX 2080 Ti", "vram": S.ETAT_NOEUDS[ident].get("vram"),
              "libre": 9.0, "ram": 63.8, "travaux": [], "llm": langage}
             if comfy else {"comfy": False, "travaux": [], "llm": langage})
    rep = await S.api_noeud_annonce(Req(S.REGISTRE[ident]["jeton"], corps,
                                        remote=ADRESSE_D_ANNONCE[ident]))
    return rep.status


PHRASES = {
    "ferme": PHRASE_FERME,
    "muet": "PC (RTX 2080 Ti) : son agent ne s'annonce plus, ComfyUI y est "
            "tenu pour ferme — son modele de langage n'est pas utilise",
    "pause": "PC (RTX 2080 Ti) est en pause — son modele de langage avec elle"}
ETATS = (("ferme", "ComfyUI ferme"), ("muet", "agent muet"), ("pause", "pause"))


async def fermer(ident, etat):
    """Met la machine dans l'un des trois etats ou elle ne prete plus."""
    if etat == "ferme":
        await annoncer(ident, comfy=False)
    elif etat == "muet":
        S.ETAT_NOEUDS[ident]["vu"] = S.time.time() - 100
    else:
        S.REGISTRE[ident]["pause"] = S.time.time()


async def appel(tid, image=None, borne=8):
    """Un appel au modele par le vrai chemin. Rend le texte, ou l'exception.
    Borne : un garde qui manque ne doit pas suspendre le banc, il doit le
    faire rougir."""
    try:
        return await asyncio.wait_for(
            S._appeler_llm("un chat roux endormi sur un fauteuil vert", image,
                           None, True, None, 0.1, tid), borne)
    except Exception as e:
        return e


async def essai_admin(borne=4):
    """L'essai du modele du PC, lance depuis /admin. Rend (statut, corps).
    Borne lui aussi : sans son garde, l'essai deposerait sa question et
    l'attendrait 180 s — le banc doit rougir, pas pendre."""
    try:
        rep = await asyncio.wait_for(
            S.api_admin_essai_llm(Req(admin=True, match={"ident": "pc"})), borne)
    except Exception as e:
        return 0, {"erreur": f"a leve {type(e).__name__}"}
    return rep.status, json.loads(rep.text)


async def jusqu_a(condition, secondes=3.0):
    fin = S.time.time() + secondes
    while S.time.time() < fin:
        if condition():
            return True
        await asyncio.sleep(0.02)
    return False


async def agent(ident, faux):
    """Un tour de servir_le_langage() d'agent_noeud.py : chercher une question
    au studio, la poser a SON Ollama sans rien demander a personne, rapporter.
    Rend le statut de la remise (204 : rien a faire)."""
    jeton = S.REGISTRE[ident]["jeton"]
    rep = await S.api_noeud_question(Req(jeton))
    if rep.status != 200:
        return rep.status
    q = json.loads(rep.text)
    async with S.aiohttp.ClientSession() as s:
        async with s.post(f"{ADRESSE[faux.nom]}/api/generate",
                          json=q["corps"]) as r:
            d = await r.json()
    await S.api_noeud_reponse(Req(jeton, {"qid": q["qid"],
                                          "reponse": d.get("response", "")}))
    return 200


# ══════════════════════════════════════════════════════════════════════
async def verite():
    print("\n  ── qui prete son modele de langage ──")
    poser()
    dit(S.cerveau_ferme("pc") == "" and S.cerveau_ferme(None) == ""
        and S.cerveau_ferme("jamais-vue") == "",
        "ComfyUI ouvert et hors pause, la machine prete ; pas de machine, ou "
        "une machine que le parc ne connait pas, ne ferme rien",
        f"{S.cerveau_ferme('pc')!r}")
    st_ = await annoncer("pc", comfy=False)
    dit(st_ == 200 and S.cerveau_ferme("pc") == "ferme"
        and S.time.time() - S.ETAT_NOEUDS["pc"]["vu"] < 5,
        "l'annonce « comfy: False » de l'agent ferme le pret, alors meme que "
        "l'agent s'annonce a l'instant", f"{st_}, {S.cerveau_ferme('pc')!r}")
    await annoncer("pc")
    dit(S.cerveau_ferme("pc") == "",
        "et l'annonce suivante, ComfyUI revenu, le rouvre",
        repr(S.cerveau_ferme("pc")))
    # ── LA FENETRE : l'agent et ComfyUI arretes ENSEMBLE, sans un mot ──
    # Fermer la fenetre de l'agent, c'est le scenario meme de la regle. A
    # SILENCE_MAX (45 s) le PC pretait encore son Ollama 44 s apres.
    etats_ = {}
    for age in (5, 12, 16, 20, 40, 44, 46):
        S.ETAT_NOEUDS["pc"]["vu"] = S.time.time() - age
        etats_[age] = (S.cerveau_ferme("pc"),
                       PC in [u for u, _ in S.cerveaux_utilisables()])
    dit(all(etats_[a] == ("", True) for a in (5, 12))
        and all(etats_[a] == ("muet", False) for a in (16, 20, 40, 44, 46))
        and 10 < S.SILENCE_PRET <= 15 < S.SILENCE_MAX,
        "plus aucun signe de l'agent, « repond » encore vrai : le PC cesse de "
        "preter son Ollama au bout de SILENCE_PRET (15 s), pas de SILENCE_MAX "
        "— a 16, 20, 40 et 44 s il ne prete plus ; a 5 et 12 s, si",
        str({a: e[0] for a, e in etats_.items()}))
    S.ETAT_NOEUDS["pc"]["vu"] = S.time.time() - 20
    vert_ = {x["id"]: x["repond"] for x in S.noeuds_agents()}["pc"]
    dit(vert_ is True and S.SILENCE_MAX == 45,
        "TEMOIN : SILENCE_MAX garde son role pour le reste — a 20 s de "
        "silence la machine reste verte dans la console et bonne pour un rendu",
        f"repond={vert_}, SILENCE_MAX={S.SILENCE_MAX}")
    # Un agent occupe continue de donner signe : chacune de ses trois routes
    # suffit, et un rendu bat toutes les deux secondes.
    signes_ = {}
    for nom, route, corps in (
            ("travail", S.api_noeud_travail, None),
            ("question", S.api_noeud_question, None),
            ("progres", S.api_noeud_progres,
             {"tid": "rendu-en-cours", "fait": 3, "total": 20})):
        S.ETAT_NOEUDS["pc"]["vu"] = S.time.time() - 30
        await route(Req(S.REGISTRE["pc"]["jeton"], corps))
        signes_[nom] = S.cerveau_ferme("pc")
    dit(signes_ == {"travail": "", "question": "", "progres": ""},
        "un agent qui rend, qui livre ou qui attend du travail ne passe pas "
        "pour muet : une demande de travail, de question ou un battement de "
        "progression remet le compteur a zero", str(signes_))
    # Mais des demandes de question ne valent pas une annonce : si rien n'a
    # dit que ComfyUI tourne depuis SILENCE_MAX — ni annonce, ni battement de
    # progression —, « repond » n'est qu'un souvenir.
    poser()
    vieux_ = S.time.time() - S.SILENCE_MAX - 1
    S.ETAT_NOEUDS["pc"].update(vu=S.time.time(), annonce=vieux_)
    seul_ = S.cerveau_ferme("pc")
    dit(seul_ == "muet",
        "un agent qui vient encore chercher des questions, mais sans annonce "
        "ni battement de progression depuis SILENCE_MAX, ne prete plus : "
        "« repond » est trop vieux pour valoir une permission", repr(seul_))
    # UNE MACHINE QUI REND N'EST PAS MUETTE PARCE QUE SON ANNONCE TARDE : un
    # agent d'avant le fil d'annonce, ou un fil retenu dans le listage des
    # modeles. Le battement passe par la vraie route.
    await S.api_noeud_progres(Req(S.REGISTRE["pc"]["jeton"],
                                  {"tid": "rendu-en-cours", "fait": 3, "total": 20}))
    rend_ = (S.cerveau_ferme("pc"), S.ETAT_NOEUDS["pc"]["annonce"] == vieux_)
    S.ETAT_NOEUDS["pc"].update(vu=S.time.time(), progres=vieux_)
    fini_ = S.cerveau_ferme("pc")
    dit(rend_ == ("", True) and fini_ == "muet",
        "une machine qui REND n'est pas muette parce que son annonce a plus de "
        "SILENCE_MAX : un battement de progression vaut une annonce — et seule "
        "l'absence des deux retire la permission",
        f"annonce vieille + battement : {rend_[0]!r} ; les deux vieux : {fini_!r}")
    poser()
    S.REGISTRE["pc"]["pause"] = 1.0
    dit(S.cerveau_ferme("pc") == "pause",
        "une machine en pause ne prete pas, ComfyUI ouvert ou non",
        repr(S.cerveau_ferme("pc")))

    # ── le rattachement d'un Ollama a une machine ──
    # Par l'ADRESSE d'ou l'agent s'annonce : c'est le vrai relevé qui tourne,
    # contre le faux Ollama — et il ne fait que LIRE.
    poser()
    S.ETAT_NOEUDS["pc"]["ip"] = "127.0.0.1"
    S._CERVEAUX[PC].update(noeud=None, quand=0.0)
    await S._rafraichir_cerveau(PC)
    dit(S._CERVEAUX[PC]["noeud"] == "pc" and S.noeud_du_cerveau(PC) == "pc"
        and PCF.lus == ["/api/tags"] and not PCF.generes,
        "un Ollama est rattache a la machine dont l'agent s'annonce depuis la "
        "meme adresse — par /api/tags, un inventaire, qui reste permis",
        f"{S._CERVEAUX[PC]['noeud']!r}, lus={PCF.lus}")
    poser()
    S._CERVEAUX[LIBRE].update(noeud=None, quand=0.0)
    await S._rafraichir_cerveau(LIBRE)
    dit(S._CERVEAUX[LIBRE]["noeud"] is None and S.noeud_du_cerveau(LIBRE) is None,
        "une adresse d'ou aucun agent ne s'annonce n'est rattachee a aucune "
        "machine : un simple serveur de langage",
        repr(S._CERVEAUX[LIBRE]["noeud"]))


async def en_direct():
    print("\n  ── l'appel en direct ──")
    poser()
    tid = tache("temoin")
    r_ = await appel(tid)
    dit(r_ == "{}" and len(PCF.generes) == 1 and not NASF.generes
        and not LIBREF.generes
        and not any("n'est pas utilise" in l or "en pause" in l for l in fil(tid)),
        "TEMOIN : ComfyUI ouvert et pas de pause — l'analyse part sur l'Ollama "
        "du PC, comme avant, et le fil n'en dit rien de plus",
        f"{r_!r}, pc={len(PCF.generes)}, nas={len(NASF.generes)}")

    poser()
    await annoncer("pc", comfy=False)
    adresses_ = [u for u, _ in S.cerveaux_utilisables()]
    dit(adresses_ == [NAS, LIBRE],
        "ComfyUI ferme : l'Ollama du PC sort de la liste des cerveaux, les "
        "autres y restent", str(adresses_))
    tid = tache("ferme")
    r_ = await appel(tid)
    dit(r_ == "{}" and not PCF.generes and len(NASF.generes) == 1,
        "ComfyUI ferme + Ollama joignable : AUCUN appel de generation ne part "
        "vers le PC (compte sur le faux Ollama) — l'analyse va au NAS",
        f"{r_!r}, pc={len(PCF.generes)}, nas={len(NASF.generes)}")
    dit(not any("PC (RTX 2080 Ti)" in l for l in fil(tid)),
        "et quand un autre cerveau repond, RIEN dans le fil de la demande : "
        "le PC est eteint la moitie du temps, le redire a chaque demande "
        "serait du bruit", str([l for l in fil(tid) if "PC (" in l]))

    poser()
    S.ETAT_NOEUDS["pc"]["vu"] = S.time.time() - 100
    tid = tache("muet")
    r_ = await appel(tid)
    dit(r_ == "{}" and not PCF.generes and len(NASF.generes) == 1
        and not any("PC (RTX 2080 Ti)" in l for l in fil(tid)),
        "AGENT MUET, Ollama joignable (le PC dont on a arrete l'agent et "
        "ComfyUI) : aucun appel de generation ne part vers lui, et le fil "
        "n'en dit rien tant que le NAS repond",
        f"{r_!r}, pc={len(PCF.generes)}, {[l for l in fil(tid) if 'PC (' in l]}")

    poser()
    S.REGISTRE["pc"]["pause"] = 1.0
    tid = tache("pause")
    r_ = await appel(tid)
    dit(r_ == "{}" and not PCF.generes and len(NASF.generes) == 1
        and not any("PC (RTX 2080 Ti)" in l for l in fil(tid)),
        "PAUSE : aucun appel de generation ne part vers le PC, et le fil n'en "
        "dit rien tant que le NAS repond, comme avant",
        f"{r_!r}, pc={len(PCF.generes)}")

    poser()
    await annoncer("pc", comfy=False)
    S.REGISTRE["zima"]["pause"] = 1.0
    tid = tache("sans-noeud")
    r_ = await appel(tid)
    dit(r_ == "{}" and len(LIBREF.generes) == 1 and not PCF.generes
        and not NASF.generes,
        "TEMOIN : l'Ollama rattache a AUCUNE machine reste utilise quand les "
        "deux machines sont fermees ou en pause — la regle ne le concerne pas",
        f"{r_!r}, libre={len(LIBREF.generes)}")

    # ── la porte de l'appel lui-meme ──
    poser()
    await annoncer("pc", comfy=False)
    corps_ = S.corps_ollama("x", None, None, True, None, 0.1, 0)
    try:
        await S._ollama_local(corps_, PC, 5)
        leve_ = None
    except Exception as e:
        leve_ = e
    libre_ = await S._ollama_local(corps_, LIBRE, 5)
    dit(isinstance(leve_, S.CerveauFerme) and isinstance(leve_, RuntimeError)
        and not PCF.generes and libre_ == "{}" and len(LIBREF.generes) == 1,
        "_ollama_local, la derniere porte : rien ne part vers une machine "
        "fermee (CerveauFerme, une RuntimeError pour qui ne la connait pas) ; "
        "vers un Ollama sans machine, si",
        f"{type(leve_).__name__}, pc={len(PCF.generes)}")


async def pendant_l_attente():
    print("\n  ── pendant que l'analyse attend la carte ──")
    poser([PC])
    pc = S.verrou_noeud("pc")
    await pc.acquire()                      # un rendu tient la carte du PC
    tid = tache("attente")
    en_vol = asyncio.ensure_future(appel(tid))
    attend_ = await jusqu_a(lambda: any("attend que sa carte se libere" in l
                                         for l in fil(tid)))
    await annoncer("pc", comfy=False)       # son proprietaire ferme ComfyUI
    pc.release()                            # et le rendu finit
    r_ = await en_vol
    dit(attend_ and isinstance(r_, S.CerveauFerme) and not PCF.generes
        and not pc.locked(),
        "ComfyUI se ferme PENDANT que l'analyse attend la carte : elle ne part "
        "pas sur cette machine, la carte est rendue, et l'appelant recoit "
        "CerveauFerme", f"{r_!r}, pc={len(PCF.generes)}, tenue={pc.locked()}")
    dit(any("PC (RTX 2080 Ti) : ComfyUI n'y tourne plus — ferme pendant "
            "l'attente" in l for l in fil(tid)),
        "et le fil dit que c'est pendant l'attente que ComfyUI s'est ferme",
        str(fil(tid)[-3:]))

    poser([PC])
    pc = S.verrou_noeud("pc")
    await pc.acquire()
    tid = tache("attente-pause")
    en_vol = asyncio.ensure_future(appel(tid))
    await jusqu_a(lambda: any("attend que sa carte" in l for l in fil(tid)))
    S.REGISTRE["pc"]["pause"] = S.time.time()
    pc.release()
    r_ = await en_vol
    dit(isinstance(r_, S.CerveauFerme) and not PCF.generes and not pc.locked()
        and any("est passee en pause pendant l'attente" in l for l in fil(tid)),
        "TEMOIN du garde d'avant : la pause arrivee pendant l'attente retient "
        "l'appel de la meme facon", f"{r_!r}, pc={len(PCF.generes)}")

    # ── la course entre cartes (ronde 11) ──
    poser([PC, NAS])
    corps_ = S.corps_ollama("x", None, None, True, None, 0.1, 0)
    liste_ = [(PC, "pc"), (NAS, "zima")]
    avant_ = [i for _, _, i in S._rivaux_de_carte(liste_, 1, corps_, PC, "pc")]
    await annoncer("zima", comfy=False)
    apres_ = [i for _, _, i in S._rivaux_de_carte(liste_, 1, corps_, PC, "pc")]
    dit(avant_ == ["zima"] and apres_ == [],
        "une machine qui a ferme ComfyUI n'entre plus dans la course : on "
        "n'attend pas la carte d'une machine sur laquelle on ne lancera rien",
        f"{avant_} puis {apres_}")

    poser([PC, NAS])
    pc, nas = S.verrou_noeud("pc"), S.verrou_noeud("zima")
    await pc.acquire()
    await nas.acquire()
    tid = tache("course")
    en_vol = asyncio.ensure_future(appel(tid))
    course_ = await jusqu_a(lambda: any(
        "calculent — l'analyse prendra la premiere carte" in l for l in fil(tid)))
    await annoncer("zima", comfy=False)     # le NAS ferme ComfyUI…
    nas.release()                           # …et se libere le premier
    refuse_ = await jusqu_a(lambda: any(
        "NAS ZimaOS : ComfyUI n'y tourne plus" in l for l in fil(tid)))
    au_milieu_ = (len(NASF.generes), nas.locked())
    pc.release()
    r_ = await en_vol
    dit(course_ and refuse_ and au_milieu_ == (0, False) and r_ == "{}"
        and not NASF.generes and len(PCF.generes) == 1
        and not pc.locked() and not nas.locked(),
        "LA COURSE ENTRE CARTES : le NAS gagne la course mais a ferme ComfyUI "
        "pendant l'attente — rien n'y part, sa carte est rendue, et l'analyse "
        "passe sur le PC quand il se libere",
        f"{r_!r}, nas={len(NASF.generes)}, pc={len(PCF.generes)}, "
        f"au milieu={au_milieu_}")


async def en_vol_et_liberation():
    print("\n  ── un appel deja parti finit, et on ne touche plus a la machine ──")
    poser([PC, NAS])

    async def ferme_puis_repond(corps):
        await annoncer("pc", comfy=False)
        return '{"intention": "image"}'

    PCF.reponse = ferme_puis_repond
    tid = tache("en-vol")
    r_ = await appel(tid)
    dit(r_ == '{"intention": "image"}' and len(PCF.generes) == 1
        and not NASF.generes,
        "un appel DEJA en train de generer finit : ComfyUI ferme pendant la "
        "generation, la reponse est rendue — ni jetee, ni redemandee ailleurs",
        f"{r_!r}, pc={len(PCF.generes)}, nas={len(NASF.generes)}")

    # ── UNE REPONSE DEGENEREE D'UNE MACHINE QUI VIENT DE SE FERMER ──
    # « Son proprietaire s'en sert : on ne lui decharge rien, meme casse. »
    # C'etait la regle de la pause ; elle vaut pour les trois etats.
    for etat, nom in ETATS:
        poser([PC, NAS])

        async def ferme_puis_vide(corps, etat=etat):
            await fermer("pc", etat)
            return ""

        PCF.reponse = ferme_puis_vide
        tid = tache("degenere-" + etat)
        r_ = await appel(tid)
        dit(r_ == "{}" and len(PCF.generes) == 1 and len(NASF.generes) == 1,
            f"reponse degeneree, {nom} pendant l'appel : rien n'y est retente, "
            f"la reprise va au NAS",
            f"{r_!r}, pc={len(PCF.generes)}, nas={len(NASF.generes)}")
        dit(not PCF.decharges,
            f"reponse degeneree, {nom} pendant l'appel : la machine n'est PAS "
            f"dechargee — zero « keep_alive: 0 » recu par son Ollama",
            f"decharges={len(PCF.decharges)}")
        dit(any("on n'y touche pas" in l
                and ("machine en pause" if etat == "pause"
                     else "ComfyUI n'y tourne plus") in l for l in fil(tid))
            and not S._DECHARGE_DEGENERE,
            f"reponse degeneree, {nom} pendant l'appel : le fil dit qu'on n'y "
            f"touche pas, et aucun dechargement n'est compte",
            str([l for l in fil(tid) if "a rendu" in l][:1]))

    # ── la reprise et la relance passent par la porte ──
    poser([PC, NAS])
    PCF.reponse = ""                        # degenere ; la machine prete encore

    async def ferme():                      # …et ferme ComfyUI juste apres
        await annoncer("pc", comfy=False)

    PCF.au_dechargement = ferme
    tid = tache("reprise")
    r_ = await appel(tid)
    dit(r_ == "{}" and len(PCF.generes) == 1 and len(PCF.decharges) == 1
        and len(NASF.generes) == 1,
        "ComfyUI se ferme entre le dechargement qui repare et la reprise : la "
        "reprise ne part PAS sur le PC, elle va au NAS",
        f"{r_!r}, pc={len(PCF.generes)}, decharges={len(PCF.decharges)}, "
        f"nas={len(NASF.generes)}")
    dit(any(l == PHRASE_FERME + " — on cherche ailleurs" for l in fil(tid)),
        "et le fil dit pourquoi elle n'est pas partie",
        str([l for l in fil(tid) if "ailleurs" in l][:2]))

    poser([PC, NAS])
    plantage_ = S.PAUSE_PLANTAGE
    S.PAUSE_PLANTAGE = 0.05

    async def ferme_puis_plante(corps):
        await annoncer("pc", comfy=False)
        return (500, '{"error":"llama runner process has terminated: CUDA '
                     'error: an illegal memory access was encountered"}')

    PCF.reponse = ferme_puis_plante
    tid = tache("relance")
    try:
        r_ = await appel(tid)
    finally:
        S.PAUSE_PLANTAGE = plantage_
    dit(r_ == "{}" and len(PCF.generes) == 1 and len(NASF.generes) == 1
        and any("le moteur d'Ollama a plante" in l for l in fil(tid)),
        "la relance apres un plantage du moteur ne part pas non plus sur une "
        "machine qui vient de fermer ComfyUI",
        f"{r_!r}, pc={len(PCF.generes)}, nas={len(NASF.generes)}")

    # ── une machine fermee n'est pas un repli ──
    # Le PC degenere et ne peut plus etre decharge (le plafond de la fenetre
    # est atteint) : la boucle n'annonce « on reessaie ailleurs » que s'il y a
    # un ailleurs. Le NAS, qui a ferme ComfyUI pendant que l'analyse attendait
    # les deux cartes — donc apres que la liste a ete dressee — n'en est pas un.
    poser([PC, NAS])
    S._DECHARGE_DEGENERE[(PC, MODELE)] = {
        "machine": "PC (RTX 2080 Ti)", "modele": MODELE,
        "quand": [S.time.time()] * S.DECHARGES_PAR_FENETRE,
        "numero": S._DECHARGES_NUMERO[0]}
    PCF.reponse = ""
    pc, nas = S.verrou_noeud("pc"), S.verrou_noeud("zima")
    await pc.acquire()
    await nas.acquire()
    tid = tache("pas-un-repli")
    en_vol = asyncio.ensure_future(appel(tid))
    await jusqu_a(lambda: any("calculent" in l for l in fil(tid)))
    await annoncer("zima", comfy=False)
    pc.release()                            # le PC se libere le premier
    asyncio.get_running_loop().call_later(
        0.4, lambda: nas.locked() and nas.release())
    r_ = await en_vol
    await asyncio.sleep(0.5)                # le NAS a fini son travail a lui
    dit(r_ == "" and len(PCF.generes) == 1 and not NASF.generes
        and not PCF.decharges
        and not any("on reessaie ailleurs" in l for l in fil(tid)),
        "une machine qui a ferme ComfyUI n'est pas comptee comme un repli : la "
        "reponse est rendue telle quelle, sans annoncer « on reessaie "
        "ailleurs » pour une machine ou rien ne partira",
        f"{r_!r}, nas={len(NASF.generes)}, {[l for l in fil(tid) if 'ailleurs' in l]}")

    # ── rien n'est envoye a une machine fermee, pas meme un dechargement ──
    for etat, nom in ETATS:
        poser()
        await fermer("pc", etat)
        parti_ = await S.liberer_modele_a(PC, MODELE)
        S._CHAUD["pret-rafale"] = (PC, MODELE)
        await S.liberer_modele("pret-rafale")   # la fin de rafale d'une demande
        dit(parti_ is False and not PCF.decharges and not PCF.generes,
            f"rien n'est envoye a une machine fermee, pas meme un dechargement "
            f"({nom}) : zero « keep_alive: 0 » recu, ni a la demande, ni en "
            f"fin de rafale — le modele partira par son keep_alive",
            f"{parti_}, decharges={len(PCF.decharges)}, generes={len(PCF.generes)}")
    poser()
    parti_ = await S.liberer_modele_a(PC, MODELE)
    dit(parti_ is True and len(PCF.decharges) == 1
        and PCF.decharges[0].get("keep_alive") == 0
        and not PCF.decharges[0].get("prompt"),
        "TEMOIN : ComfyUI ouvert et hors pause, le dechargement part comme "
        "avant (prompt vide, keep_alive 0)", f"{parti_}")

    # ── les lectures, elles, restent permises ──
    poser()
    await annoncer("pc", comfy=False)
    S._CERVEAUX[PC]["quand"] = 0.0
    await S._rafraichir_cerveau(PC)
    S._PLACEMENT.clear()
    await S.relever_placement(PC, MODELE)
    dit(PCF.lus == ["/api/tags", "/api/ps"] and not PCF.generes
        and not PCF.decharges and S.sur_processeur(PC) is False,
        "seules les LECTURES restent permises sur une machine fermee : "
        "/api/tags et /api/ps sont lus, rien n'est genere ni decharge",
        f"lus={PCF.lus}, generes={len(PCF.generes)}, "
        f"decharges={len(PCF.decharges)}")


async def par_l_agent():
    print("\n  ── le detour par l'agent ──")
    corps_ = S.corps_ollama("x", None, None, True, None, 0.1, 0)

    poser([])
    S.ETAT_NOEUDS["pc"].update(llm=True, llm_modeles=[MODELE])
    tid = tache("agent-temoin")
    en_vol = asyncio.ensure_future(appel(tid))
    deposee_ = await jusqu_a(lambda: S.QUESTIONS.get("pc"))
    st_ = await agent("pc", PCF)
    r_ = await en_vol
    dit(deposee_ and st_ == 200 and r_ == "{}" and len(PCF.generes) == 1,
        "TEMOIN du detour : ComfyUI ouvert, la question est remise a l'agent, "
        "qui la pose a son Ollama, et la reponse revient",
        f"{st_}, {r_!r}, pc={len(PCF.generes)}")

    poser([])
    await annoncer("pc", comfy=False)       # « llm: ok » y est, ComfyUI non
    dit(S.ETAT_NOEUDS["pc"].get("llm") is True and S.noeuds_a_llm() == [],
        "ComfyUI ferme : la machine annonce toujours son modele de langage, "
        "et n'est plus de celles qui le pretent par leur agent",
        f"llm={S.ETAT_NOEUDS['pc'].get('llm')}, {S.noeuds_a_llm()}")
    tid = tache("agent-ferme")
    r_ = await appel(tid)
    st_ = await agent("pc", PCF)
    dit(isinstance(r_, S.CerveauFerme) and st_ == 204 and not PCF.generes
        and fil(tid).count(PHRASE_FERME) == 1,
        "LE DETOUR PAR L'AGENT : ComfyUI ferme, aucune question n'est deposee "
        "pour cet agent, son Ollama ne recoit rien, et le fil dit pourquoi",
        f"{r_!r}, agent={st_}, pc={len(PCF.generes)}")

    poser([])
    await annoncer("pc", comfy=False)
    try:
        rep_, err_ = await asyncio.wait_for(
            S.poser_a("pc", dict(corps_), None, 0.5), 5)
    except Exception as e:
        rep_, err_ = "", f"a leve {type(e).__name__}"
    dit(rep_ == "" and err_ == PHRASE_FERME and not S.QUESTIONS.get("pc"),
        "poser_a ne depose rien pour une machine dont ComfyUI est ferme, quel "
        "que soit l'appelant, et rend la raison", f"{err_!r}")

    poser([])
    S.ETAT_NOEUDS["pc"].update(llm=True, llm_modeles=[MODELE])
    pc = S.verrou_noeud("pc")
    await pc.acquire()
    en_vol = asyncio.ensure_future(S.poser_a("pc", dict(corps_), None, 0.5,
                                             patience=5))
    await asyncio.sleep(0.1)
    await annoncer("pc", comfy=False)
    pc.release()
    try:
        rep_, err_ = await asyncio.wait_for(en_vol, 5)
    except Exception as e:
        rep_, err_ = "", f"a leve {type(e).__name__}"
    dit(rep_ == "" and err_ == PHRASE_FERME and not pc.locked(),
        "et si ComfyUI se ferme pendant que la question attend la carte, elle "
        "n'est pas deposee non plus", f"{err_!r}")

    poser([])
    S.ETAT_NOEUDS["pc"].update(llm=True, llm_modeles=[MODELE])
    en_vol = asyncio.ensure_future(S.poser_a("pc", dict(corps_), None, 3))
    deposee_ = await jusqu_a(lambda: S.QUESTIONS.get("pc"))
    await annoncer("pc", comfy=False)       # ferme avant que l'agent passe
    st_ = await agent("pc", PCF)
    try:
        rep_, err_ = await asyncio.wait_for(en_vol, 5)
    except Exception as e:
        rep_, err_ = "", f"a leve {type(e).__name__}"
    dit(deposee_ and st_ == 204 and not PCF.generes and rep_ == ""
        and err_ == PHRASE_FERME and not S.QUESTIONS.get("pc"),
        "une question deposee AVANT la fermeture n'est pas remise a l'agent — "
        "qui, lui, l'aurait posee a son Ollama sans rien demander : elle est "
        "rendue a l'appelant avec la raison",
        f"agent={st_}, pc={len(PCF.generes)}, {err_!r}")

    # ── l'essai de /admin ──
    poser([])
    S.ETAT_NOEUDS["pc"].update(llm=True, llm_modeles=[MODELE])
    S.REGISTRE["pc"]["pause"] = S.time.time()
    st_, d_ = await essai_admin()
    dit(st_ == 409 and "est en pause" in (d_.get("erreur") or "")
        and "l'essai n'est pas lance" in (d_.get("erreur") or "")
        and not S.QUESTIONS.get("pc") and not PCF.generes,
        "l'essai de /admin n'est pas lance sur une machine EN PAUSE (il "
        "l'etait : il ne regardait que « repond ») — 409, et la raison",
        f"{st_}, {d_.get('erreur')!r}")
    poser([])
    await annoncer("pc", comfy=False)
    st_, d_ = await essai_admin()
    poser([])
    S.ETAT_NOEUDS["pc"].update(llm=True, llm_modeles=[MODELE],
                               vu=S.time.time() - 100)
    st2_, d2_ = await essai_admin()
    dit(st_ == 409 and "ComfyUI n'y tourne pas" in (d_.get("erreur") or "")
        and st2_ == 409
        and "son agent ne s'annonce plus" in (d2_.get("erreur") or "")
        and not S.QUESTIONS.get("pc") and not PCF.generes,
        "ni ComfyUI ferme, ni agent muet (« repond » encore vrai : il aurait "
        "attendu ses 180 s)", f"{st_} {d_.get('erreur')!r} / "
                              f"{st2_} {d2_.get('erreur')!r}")
    poser([])
    S.ETAT_NOEUDS["pc"].update(llm=True, llm_modeles=[MODELE])
    PCF.reponse = '{"intention": "image"}'
    en_vol = asyncio.ensure_future(essai_admin(borne=8))
    await jusqu_a(lambda: S.QUESTIONS.get("pc"))
    await agent("pc", PCF)
    st_, d_ = await en_vol
    dit(st_ == 200 and d_.get("lisible") is True and len(PCF.generes) == 1,
        "TEMOIN : ComfyUI ouvert et hors pause, l'essai part et rend son plan",
        f"{st_}, lisible={d_.get('lisible')}, pc={len(PCF.generes)}")


async def vision():
    print("\n  ── la lecture d'image ──")
    poser([PC, NAS])
    tid = tache("vision-temoin")
    r_ = await appel(tid, image="AAAA")
    dit(r_ == "{}" and len(PCF.generes) == 1
        and PCF.generes[0].get("images") == ["AAAA"] and not NASF.generes,
        "TEMOIN : ComfyUI ouvert, l'image est lue par le modele de vision du PC",
        f"{r_!r}, pc={len(PCF.generes)}")
    poser([PC, NAS])
    await annoncer("pc", comfy=False)
    tid = tache("vision-ferme")
    r_ = await appel(tid, image="AAAA")
    dit(r_ == "{}" and not PCF.generes and len(NASF.generes) == 1
        and NASF.generes[0].get("images") == ["AAAA"],
        "LA VISION : ComfyUI ferme, l'image n'est pas envoyee au PC — elle est "
        "lue par le NAS", f"{r_!r}, pc={len(PCF.generes)}, nas={len(NASF.generes)}")
    poser([PC])
    await annoncer("pc", comfy=False)
    tid = tache("vision-seule")
    r_ = await appel(tid, image="AAAA")
    dit(isinstance(r_, S.CerveauFerme) and not PCF.generes
        and fil(tid).count(PHRASE_FERME) == 1,
        "et sans autre machine elle n'est pas lue du tout : rien ne part, et "
        "le fil dit pourquoi", f"{r_!r}, pc={len(PCF.generes)}")


async def aucun_cerveau():
    print("\n  ── aucun cerveau : le repli par mots-cles ──")
    # LES TROIS RAISONS, chacune avec ses mots, et seulement ici : c'est quand
    # la demande part aux mots-cles que l'utilisateur a besoin de savoir.
    for etat, nom in ETATS:
        poser([PC])
        await fermer("pc", etat)
        tid = tache("aucun-" + etat)
        r_ = await appel(tid)
        await appel(tid)
        await appel(tid)
        dit(isinstance(r_, S.CerveauFerme) and str(r_) == PHRASES[etat]
            and fil(tid).count(PHRASES[etat]) == 1
            and not PCF.generes and not PCF.decharges,
            f"aucun cerveau utilisable ({nom}) : le fil dit la raison, mot "
            f"pour mot, et UNE SEULE fois pour les trois appels de la demande",
            f"{fil(tid).count(PHRASES[etat])} fois — "
            f"{[l for l in fil(tid) if 'PC (' in l][:1]}")
    poser([PC])
    await annoncer("pc", comfy=False)
    tid = tache("repli")
    conv = S._vide(proprietaire="u" * 32)
    try:
        plan = await asyncio.wait_for(
            S.aiguiller("un chat roux endormi sur un fauteuil vert", tid, conv), 12)
    except Exception as e:
        plan = e
    lignes_ = fil(tid)
    dit(isinstance(plan, dict) and plan.get("intention") == "image"
        and not PCF.generes
        and "Ollama indisponible (CerveauFerme) — aiguillage par mots-cles"
        in lignes_,
        "AUCUN CERVEAU (le seul Ollama est celui d'une machine dont ComfyUI "
        "est ferme) : la demande est aiguillee par mots-cles, sans un appel",
        f"{plan if not isinstance(plan, dict) else plan.get('intention')!r}, "
        f"pc={len(PCF.generes)}")
    dit(lignes_.count(PHRASE_FERME) == 1,
        "le fil dit la vraie raison a l'utilisateur, en une ligne",
        str([l for l in lignes_ if "ComfyUI" in l]))
    dit(not any("injoignable" in l for l in lignes_),
        "et ne parle pas d'un modele « injoignable » : l'Ollama repond, c'est "
        "la regle qui le ferme", str([l for l in lignes_ if "injoignable" in l]))
    dit(S._pourquoi_aucun_cerveau() == PHRASE_FERME,
        "_pourquoi_aucun_cerveau nomme la machine et la raison",
        S._pourquoi_aucun_cerveau())
    S.REGISTRE["zima"]["pause"] = 1.0
    S.OLLAMAS[:] = [PC, NAS]
    deux_ = S._pourquoi_aucun_cerveau()
    dit("NAS ZimaOS est en pause — son modele de langage avec elle" in deux_
        and PHRASE_FERME in deux_,
        "une machine en pause et une machine fermee : la phrase dit les deux",
        deux_)


async def machine_du_studio():
    print("\n  ── l'Ollama de la machine du studio ──")
    # DECISION DU 10 NOVEMBRE 2026 : « ComfyUI ferme » ne vaut que pour les
    # machines a agent. Sur la machine du studio, c'est le studio qui relance
    # ComfyUI lui-meme : ferme, il ne dit pas « la carte est a moi ». Seule la
    # pause y ferme le cerveau — et de la meme facon quelle que soit
    # l'histoire. La premiere version en dependait : carte jamais vue,
    # l'Ollama servait ; carte vue une fois, plus aucun cerveau.
    local = S.noeud_local()
    lan = "http://192.168.77.10:11434"      # la meme machine, par son adresse
    S.ADRESSES_MACHINE.add("192.168.77.10")
    histoires_ = {}
    try:
        for nom, vue, ouvert in (("carte jamais vue, ComfyUI ferme", False, False),
                                 ("carte vue, ComfyUI ferme", True, False),
                                 ("carte vue, ComfyUI ouvert", True, True)):
            poser([ICI, lan])
            S._CERVEAUX[lan] = dict(S._CERVEAUX[ICI])
            if vue:
                COMFY.ouvert = True
                await S.sonder_noeud(local)     # la vraie sonde voit la carte
            COMFY.ouvert = ouvert
            await S.sonder_noeud(local)
            tid = tache("studio")
            r_ = await appel(tid)
            histoires_[nom] = (
                S.carte_locale(), bool(S.ETAT_NOEUDS[local["id"]].get("repond")),
                S.noeud_du_cerveau(ICI), S.noeud_du_cerveau(lan),
                S.cerveau_ferme(local["id"]),
                [u for u, _ in S.cerveaux_utilisables()], r_, len(ICIF.generes))
        attendu_ = (local["id"], local["id"], "", [ICI, lan], "{}", 1)
        dit(all(h[2:] == attendu_ for h in histoires_.values())
            and [h[:2] for h in histoires_.values()]
            == [(False, False), (True, False), (True, True)],
            "machine du studio, ComfyUI ferme ou ouvert, carte deja vue ou "
            "jamais : son Ollama sert dans les trois histoires — ComfyUI ferme "
            "n'y ferme pas le cerveau, c'est le studio qui le relance",
            str({n: (h[4], h[6], h[7]) for n, h in histoires_.items()}))
        dit(all(h[2] == h[3] == local["id"] for h in histoires_.values()),
            "et l'Ollama est reconnu comme celui de la machine du studio qu'il "
            "soit ecrit par 127.0.0.1 ou par son adresse sur le reseau",
            str({n: h[2:4] for n, h in histoires_.items()}))

        # LA PAUSE, elle, ferme — et pareil dans les trois histoires, par les
        # deux adresses.
        pauses_ = {}
        for nom, vue, ouvert in (("jamais vue", False, False),
                                 ("vue, ferme", True, False),
                                 ("vue, ouvert", True, True)):
            poser([ICI, lan])
            S._CERVEAUX[lan] = dict(S._CERVEAUX[ICI])
            if vue:
                await S.sonder_noeud(local)
            COMFY.ouvert = ouvert
            await S.sonder_noeud(local)
            local["pause"] = S.time.time()
            tid = tache("studio-pause")
            r_ = await appel(tid)
            pauses_[nom] = (S.cerveau_ferme(S.noeud_du_cerveau(ICI)),
                            S.cerveau_ferme(S.noeud_du_cerveau(lan)),
                            S.cerveaux_utilisables(), type(r_).__name__,
                            len(ICIF.generes))
            local.pop("pause", None)
        dit(all(p == ("pause", "pause", [], "CerveauFerme", 0)
                for p in pauses_.values()),
            "en pause, la machine du studio ne prete pas son Ollama — de la "
            "meme facon carte vue ou non, ComfyUI ouvert ou non, par "
            "127.0.0.1 comme par l'adresse du reseau",
            str({n: p[:2] + p[3:] for n, p in pauses_.items()}))
    finally:
        S.ADRESSES_MACHINE.discard("192.168.77.10")
        local.pop("pause", None)
        S.ETAT_NOEUDS.pop(local["id"], None)

    # Une machine DECLAREE PAR SON ADRESSE dans noeuds.json n'a pas d'agent :
    # elle non plus n'est pas fermee par « ComfyUI ferme ».
    # Son Ollama lui est rattache par le nom d'hote qu'il partage avec son
    # ComfyUI — pour la PAUSE seule, et pour savoir a qui il appartient.
    # (Aujourd'hui /admin ne met en pause que les machines a agent : le
    # drapeau est pose ici a la main, comme pour la machine du studio.)
    # Aucun appel : atelier.lan n'existe pas, on ne lit que le choix.
    poser([LIBRE])
    atelier = "http://atelier.lan:11434"
    S.NOEUDS.append({"id": "atelier", "url": "http://atelier.lan:8188",
                     "titre": "Atelier", "local": False})
    S.NOEUDS.append({"id": "tunnel", "url": "http://127.0.0.1:8189",
                     "titre": "Tunnel", "local": False})
    try:
        S.OLLAMAS[:] = [atelier, ICI]
        S._CERVEAUX[atelier] = dict(S._CERVEAUX[ICI])
        S.ETAT_NOEUDS["atelier"] = {"repond": False, "vram": 8.0}
        ferme_ = (S.noeud_du_cerveau(atelier), S.cerveau_ferme("atelier"),
                  [u for u, _ in S.cerveaux_utilisables()])
        dit(ferme_ == ("atelier", "", [atelier, ICI]),
            "TEMOIN : une machine sans agent, declaree par son adresse, n'est "
            "pas fermee par « ComfyUI ferme » — son Ollama reste dans la liste",
            str(ferme_[:2]))
        S.NOEUDS[-2]["pause"] = {"depuis": S.time.time()}
        pause_ = (S.cerveau_ferme(S.noeud_du_cerveau(atelier)),
                  [u for u, _ in S.cerveaux_utilisables()])
        S.NOEUDS[-2].pop("pause")
        dit(pause_ == ("pause", [ICI]),
            "une machine declaree par son adresse, EN PAUSE : son Ollama lui "
            "est rattache par le nom d'hote, et il sort de la liste des "
            "cerveaux — la pause ferme, comme l'ecrit la regle", str(pause_))
        dit(S.avertissements_du_pret() == []
            and S.etiquette_du_cerveau(atelier) == "  [Atelier]",
            "et le studio ne dit pas qu'il « ne sait pas a quelle machine il "
            "appartient » d'un Ollama dont il connait la machine",
            f"{S.avertissements_du_pret()}, {S.etiquette_du_cerveau(atelier)!r}")
        dit(S.noeud_du_cerveau(ICI) == S.noeud_local()["id"],
            "une adresse de bouclage reste celle de la machine du studio, "
            "jamais celle d'une machine declaree sur 127.0.0.1 : ce peut etre "
            "un tunnel vers n'importe ou", repr(S.noeud_du_cerveau(ICI)))
    finally:
        del S.NOEUDS[-2:]
        S.ETAT_NOEUDS.pop("atelier", None)


async def machine_fermee_pour_un_rendu():
    print("\n  ── ComfyUI ferme, et un rendu que seule cette machine sait faire ──")
    # Le fil disait deux choses contraires : « PC : ComfyUI n'y tourne pas »,
    # puis « PC travaille — ta demande attend son tour » pendant ATTENTE_CARTE
    # (trente minutes), avant « Rallume-la ». Une machine dont l'agent vient
    # de dire « comfy: False » n'est pas occupee.
    cle = "klein9b"

    def parc_de_rendu():
        poser([PC])
        dossiers = {}
        for c in S.CATALOGUE:
            for sous, nom, _r, _d in S.CATALOGUE[c].get("fichiers") or []:
                dossiers.setdefault(sous, set()).add(nom)
        S.MODELES_NOEUD.clear()
        S.MODELES_NOEUD["pc"] = {"quand": S.time.time(), "dossiers": dossiers}
        S.REGISTRE.pop("zima")
        S.ETAT_NOEUDS.pop("zima")

    async def patienter(borne=1.5):
        """(ce que rend patienter_machine, ou « attend », et le fil)."""
        tid = tache("patienter")
        en_vol = asyncio.ensure_future(S.patienter_machine(cle, tid))
        try:
            rendu_ = await asyncio.wait_for(asyncio.shield(en_vol), borne)
        except asyncio.TimeoutError:
            rendu_ = "attend"
            en_vol.cancel()
            await asyncio.gather(en_vol, return_exceptions=True)
        return rendu_, fil(tid)

    parc_de_rendu()
    await annoncer("pc", comfy=False)
    rendu_, lignes_ = await patienter()
    dit(S.comfy_dit_ferme("pc") and rendu_ is None
        and not any("travaille" in l for l in lignes_),
        "une machine dont l'agent vient de dire « comfy: False » n'est pas "
        "« occupee » : la demande ne l'attend pas trente minutes, et le fil "
        "ne dit pas qu'elle travaille", f"{rendu_!r}, {lignes_}")
    refus_ = S.refus_moteur(cle, [])
    cle_ = (refus_.marque or {}).get("cle")
    try:
        rendus_ = [S.traductions.rendre(refus_.marque, lg) for lg in ("fr", "en")]
    except Exception as e:
        rendus_ = [f"a leve {type(e).__name__}", ""]
    dit(cle_ == "panne.moteur_comfy_ferme"
        and "PC (RTX 2080 Ti)" in str(refus_)
        and "Relance ComfyUI sur cette machine" in str(refus_)
        and "Rallume" not in str(refus_) and "agent" not in str(refus_)
        and rendus_[0] == str(refus_) and "Start ComfyUI" in rendus_[1],
        "et le refus dit quoi faire — « relance ComfyUI sur cette machine » — "
        "au lieu de « rallume-la, ou verifie son agent » ; la phrase se rend "
        "en francais et en anglais", f"{cle_!r} — {str(refus_)[:150]}")

    # Par le vrai executer() : une chanson, moteur que seule cette machine
    # porte, aucune autre machine dans le parc.
    parc_de_rendu()
    await annoncer("pc", comfy=False)
    pid = "u" * 32
    conv = S._vide(proprietaire=pid)
    conv["id"] = "c-pret-chanson"
    S.CONVERSATIONS[conv["id"]] = conv
    tid = "pretchanson" + "0" * 21
    texte = "une chanson rock sur la pluie, avec des paroles"
    S.TACHES[tid] = {"etapes": [], "etat": "en cours", "debut": S.time.time(),
                     "demande": texte, "conv": conv["id"], "proprietaire": pid}
    t0_ = S.time.time()
    try:
        await asyncio.wait_for(S.executer(tid, texte, conv), 10)
    except Exception as e:
        journal_ = f"a leve {type(e).__name__}"
        S.TACHES[tid]["etapes"].append({"msg": journal_})
    lignes_ = fil(tid)
    erreur_ = next((l for l in lignes_ if l.startswith("ERREUR")), "")
    dit(S.TACHES[tid].get("etat") == "erreur" and S.time.time() - t0_ < 5
        and "Relance ComfyUI sur cette machine" in erreur_
        and "PC (RTX 2080 Ti)" in erreur_ and "agent" not in erreur_
        and not any("travaille" in l for l in lignes_),
        "une demande que seul le PC sait rendre, ComfyUI ferme : elle s'arrete "
        "tout de suite sur « relance ComfyUI », sans « PC travaille » ni "
        "« leur agent tourne-t-il ? »",
        f"{S.time.time() - t0_:.1f} s — {erreur_[:170] or lignes_[-2:]}")

    # ── les temoins : ce qui doit rester attendu, ou dit autrement ──
    parc_de_rendu()
    S.ETAT_NOEUDS["pc"]["vu"] = S.time.time() - 60      # un agent qui se tait
    rendu_, lignes_ = await patienter(0.5)
    dit(rendu_ == "attend" and any("travaille" in l for l in lignes_),
        "TEMOIN : une machine silencieuse dont le dernier mot etait « je "
        "reponds » est toujours attendue — elle travaille peut-etre",
        f"{rendu_!r}")
    parc_de_rendu()
    S.ETAT_NOEUDS["pc"] = {"repond": False, "vu": 0, "vram": 11.0, "ram": 63.8}
    S.DEMARRE = S.time.time()
    rendu_, lignes_ = await patienter(0.5)
    dit(not S.comfy_dit_ferme("pc") and rendu_ == "attend",
        "TEMOIN : au reveil du studio, une machine qui ne s'est pas encore "
        "annoncee est toujours attendue — « repond » faux sans annonce n'est "
        "pas « comfy: False »", f"{rendu_!r}")
    parc_de_rendu()
    vieux_ = S.time.time() - S.SILENCE_MAX - 5
    S.ETAT_NOEUDS["pc"].update(repond=False, vu=vieux_, annonce=vieux_)
    refus_ = S.refus_moteur(cle, [])
    dit((refus_.marque or {}).get("cle") == "panne.moteur_machines_absentes"
        and "Rallume-la" in str(refus_),
        "TEMOIN : si l'agent s'est tu depuis, ce n'est plus « relance "
        "ComfyUI » — on ne sait plus rien de la machine, le refus garde "
        "« rallume-la, ou verifie son agent »", str(refus_)[:130])
    S.MODELES_NOEUD.clear()


async def reveil():
    print("\n  ── au reveil du studio ──")

    def au_reveil():
        # Tel que charger_parc() laisse une machine au redemarrage : sa carte
        # et son adresse, mais ni « repond », ni « vu », ni « annonce ».
        poser([PC])
        S.ETAT_NOEUDS["pc"] = {"repond": False, "vu": 0, "vram": 11.0,
                               "ram": 63.8, "ip": "10.0.0.1"}
        S.DEMARRE = S.time.time()

    au_reveil()
    tid = tache("reveil")
    en_vol = asyncio.ensure_future(appel(tid))
    await asyncio.sleep(0.8)
    patiente_ = not en_vol.done() and not PCF.generes
    await annoncer("pc")                    # le premier battement arrive
    r_ = await en_vol
    dit(patiente_ and r_ == "{}" and len(PCF.generes) == 1,
        "AU REVEIL DU STUDIO, l'analyse attend le premier battement d'une "
        "machine jamais entendue au lieu de la declarer fermee : les demandes "
        "reprises de la file ne partent pas toutes aux mots-cles",
        f"patiente={patiente_}, {r_!r}, pc={len(PCF.generes)}")

    # ── UNE DEMANDE DE QUESTION OU DE TRAVAIL N'EST PAS UNE ANNONCE ──
    # L'agent vient chercher une question toutes les 3 s, dans un fil qui ne
    # sait rien de ComfyUI ; ces routes posent « vu » sans toucher « repond ».
    # L'attente s'arretait la : « ComfyUI n'y tourne pas », CerveauFerme, et
    # les mots-cles — pour une machine qui s'annoncait dans les dix secondes.
    for nom, route in (("question", S.api_noeud_question),
                       ("travail", S.api_noeud_travail)):
        au_reveil()
        rep = await route(Req(S.REGISTRE["pc"]["jeton"]))
        avant_ = (rep.status, S.ETAT_NOEUDS["pc"]["vu"] > 0,
                  S.cerveau_ferme("pc"), S._pas_encore_annoncee("pc"))
        tid = tache("reveil-" + nom)
        en_vol = asyncio.ensure_future(appel(tid))
        await asyncio.sleep(0.8)
        patiente_ = not en_vol.done() and not PCF.generes
        await annoncer("pc")
        r_ = await en_vol
        dit(avant_ == (204, True, "muet", True) and patiente_ and r_ == "{}"
            and len(PCF.generes) == 1
            and not any("ComfyUI n'y tourne pas" in l for l in fil(tid)),
            f"une demande de {nom} recue avant la premiere annonce ne defait "
            f"pas l'attente du reveil : la machine est « pas encore "
            f"annoncee », pas « ComfyUI ferme », et l'analyse l'attend",
            f"{avant_}, patiente={patiente_}, {r_!r}, pc={len(PCF.generes)}")

    # ── L'ECHEANCE SE COMPTE DEPUIS QUE LE STUDIO SERT, pas depuis l'import ──
    au_reveil()
    S.DEMARRE = S.time.time() - 3600        # l'import, et un long releve
    S.SERVI_DEPUIS[0] = S.time.time()       # le studio se met a servir
    tid = tache("reveil-service")
    en_vol = asyncio.ensure_future(appel(tid))
    await asyncio.sleep(0.8)
    patiente_ = not en_vol.done() and not PCF.generes
    await annoncer("pc")
    r_ = await en_vol
    dit(patiente_ and r_ == "{}" and len(PCF.generes) == 1,
        "l'echeance de l'attente court depuis que le studio SERT : un import "
        "ancien (le releve bloquant des Ollama, 8 s par hote eteint) ne la "
        "consomme pas", f"patiente={patiente_}, {r_!r}")

    # ── la premiere annonce clot l'attente, quoi qu'elle dise ──
    au_reveil()
    await annoncer("pc", comfy=False)
    tid = tache("reveil-ferme")
    t0_ = S.time.time()
    r_ = await appel(tid)
    dit(S.cerveau_ferme("pc") == "ferme" and isinstance(r_, S.CerveauFerme)
        and S.time.time() - t0_ < 2 and fil(tid).count(PHRASE_FERME) == 1,
        "la premiere ANNONCE clot l'attente, meme quand elle dit « comfy: "
        "False » : la machine est alors fermee pour de bon, et dite telle — "
        "c'est l'annonce, horodatee a part, qui fait foi",
        f"{S.cerveau_ferme('pc')!r}, {r_!r}, {S.time.time() - t0_:.1f} s")

    # ── passe l'echeance : muette, et le fil ne l'accuse pas a tort ──
    au_reveil()
    S.DEMARRE = S.time.time() - S.ATTENTE_ANNONCES - 1
    await S.api_noeud_question(Req(S.REGISTRE["pc"]["jeton"]))
    tid = tache("reveil-passe")
    t0_ = S.time.time()
    r_ = await appel(tid)
    dit(isinstance(r_, S.CerveauFerme) and S.time.time() - t0_ < 2
        and not PCF.generes and 25 <= S.ATTENTE_ANNONCES <= 40
        and fil(tid).count(PHRASES["muet"]) == 1
        and not any("ComfyUI n'y tourne pas" in l for l in fil(tid)),
        "passe ATTENTE_ANNONCES (une trentaine de secondes), une machine qui "
        "ne s'est toujours pas annoncee n'est plus attendue et est tenue pour "
        "MUETTE — meme si son agent vient chercher des questions, le fil ne "
        "dit pas « ComfyUI n'y tourne pas »",
        f"{r_!r}, {S.time.time() - t0_:.1f} s, {S.ATTENTE_ANNONCES} s")

    # ── une machine en pause ne s'attend pas ──
    au_reveil()
    S.REGISTRE["pc"]["pause"] = S.time.time()
    tid = tache("reveil-pause")
    t0_ = S.time.time()
    r_ = await appel(tid)
    dit(isinstance(r_, S.CerveauFerme) and S.time.time() - t0_ < 2,
        "TEMOIN : au reveil, une machine en pause n'est pas attendue — "
        "annoncee ou non, elle ne pretera rien", f"{S.time.time() - t0_:.1f} s")


async def erreurs_dites():
    print("\n  ── ce que l'utilisateur lit quand sa demande s'arrete ──")
    pid = "u" * 32
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
        "hQGAhKmMIQAAAABJRU5ErkJggg==")

    async def lire_image(rang):
        """« decris cette image », image jointe, par le vrai executer().
        Rend (etat, lignes du fil)."""
        nom = f"pret_lecture{rang}.png"
        with open(os.path.join(S.DOSSIER_ENTREE, nom), "wb") as f:
            f.write(png)
        S.ENTREES[nom] = pid
        conv = S._vide(proprietaire=pid)
        conv["id"] = f"c-pret-lecture{rang}"
        S.CONVERSATIONS[conv["id"]] = conv
        tid = f"pretlecture{rang:02d}" + "0" * 19
        S.TACHES[tid] = {"etapes": [], "etat": "en cours",
                         "debut": S.time.time(), "demande": "decris cette image",
                         "conv": conv["id"], "proprietaire": pid}
        try:
            await asyncio.wait_for(
                S.executer(tid, "decris cette image", conv, image=nom), 20)
        except Exception as e:
            journal_ = f"a leve {type(e).__name__}"
            return journal_, [journal_]
        return S.TACHES[tid].get("etat"), fil(tid)

    for rang, (etat, nom) in enumerate(ETATS, 1):
        poser([PC])
        await fermer("pc", etat)
        fini_, lignes_ = await lire_image(rang)
        erreur_ = next((l for l in lignes_ if l.startswith("ERREUR")), "")
        geste_ = ("sors-la de pause dans l'administration" if etat == "pause"
                  else "relance ComfyUI sur cette machine")
        dit(fini_ == "erreur" and PHRASES[etat] in erreur_ and geste_ in erreur_
            and "reessaie quand elle sera revenue" in erreur_
            and "ollama pull" not in erreur_ and "CerveauFerme" not in erreur_
            and not PCF.generes,
            f"image a lire, {nom} sur la seule machine qui sait voir : "
            f"l'erreur dit la vraie raison et le geste, sans conseil "
            f"d'installation", erreur_[:230] or str(lignes_[-2:]))
    poser([PC])
    PCF.reponse = "un petit carre gris"
    fini_, lignes_ = await lire_image(8)
    dit(fini_ == "fini" and len(PCF.generes) == 1,
        "TEMOIN : ComfyUI ouvert, l'image est lue et decrite", f"{fini_}")
    poser([PC])
    S._CERVEAUX[PC]["modeles"] = [{"name": "mistral:7b", "size": 4_370_000_000,
                                   "capabilities": ["completion"]}]
    fini_, lignes_ = await lire_image(9)
    erreur_ = next((l for l in lignes_ if l.startswith("ERREUR")), "")
    dit(fini_ == "erreur" and "ollama pull" in erreur_,
        "TEMOIN : quand AUCUN modele de la maison ne sait voir, et que rien "
        "n'est ferme, le conseil d'installation reste — il est alors juste",
        erreur_[:160])

    # ── la chanson ──
    for etat, nom in ETATS:
        poser([PC])
        await fermer("pc", etat)
        tid = tache("paroles-" + etat)
        try:
            r_ = await asyncio.wait_for(
                S.ecrire_paroles("une chanson rock sur un chat roux", 60, tid), 12)
        except Exception as e:
            r_ = e
        dit(type(r_) is RuntimeError and PHRASES[etat] in str(r_)
            and "les paroles n'ont pas pu etre ecrites" in str(r_)
            and "relance la demande" not in str(r_)
            and "reessaie quand elle sera revenue" in str(r_)
            and not PCF.generes and not PCF.decharges
            and not any("essai 2" in l for l in fil(tid)),
            f"paroles a ecrire, {nom} : l'erreur dit la vraie raison au lieu "
            f"de « relance la demande », sans trois essais pour rien",
            str(r_)[:200])
    # Le refrain est ecrit, puis ComfyUI se ferme : les couplets ne partiront
    # pas, et l'erreur le dit de la meme facon.
    poser([PC])

    async def refrain_puis_ferme(corps):
        await annoncer("pc", comfy=False)
        return ("Le chat roux dort au soleil\nIl reve de souris dorees\n"
                "Le fauteuil vert est son royaume\nEt la nuit tombe doucement")

    PCF.reponse = refrain_puis_ferme
    tid = tache("paroles-couplets")
    try:
        r_ = await asyncio.wait_for(
            S.ecrire_paroles("une chanson rock sur un chat roux", 60, tid), 12)
    except Exception as e:
        r_ = e
    dit(type(r_) is RuntimeError and PHRASE_FERME in str(r_)
        and len(PCF.generes) == 1 and not PCF.decharges,
        "ComfyUI se ferme apres le refrain : les couplets ne partent pas, "
        "l'erreur dit pourquoi, et la fin de rafale ne decharge rien sur "
        "cette machine", f"{str(r_)[:150]}, pc={len(PCF.generes)}")
    poser([PC])
    PCF.reponse = "{}"
    tid = tache("paroles-vides")
    try:
        r_ = await asyncio.wait_for(
            S.ecrire_paroles("une chanson rock sur un chat roux", 60, tid), 12)
    except Exception as e:
        r_ = e
    dit(r_ == "",
        "TEMOIN : ComfyUI ouvert et un modele qui n'ecrit rien d'exploitable "
        "— les paroles reviennent vides, et l'appelant garde son message",
        repr(r_)[:80])


async def image_jointe():
    print("\n  ── l'image jointe qui partirait au nuage ──")
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
        "hQGAhKmMIQAAAABJRU5ErkJggg==")
    nom = "pret_jugee.png"
    with open(os.path.join(S.DOSSIER_ENTREE, nom), "wb") as f:
        f.write(png)

    async def juger():
        S.JUGEMENTS_IMAGE.clear()
        tid = tache("jugee")
        try:
            return await asyncio.wait_for(S.image_adulte(nom, tid), 15)
        except Exception as e:
            return f"a leve {type(e).__name__}"

    for etat, nom_etat in ETATS:
        poser([PC])
        await fermer("pc", etat)
        v_ = await juger()
        dit(v_ == "retenue" and not PCF.generes
            and nom not in S.JUGEMENTS_IMAGE,
            f"image jointe, {nom_etat} sur la machine qui sait voir : elle "
            f"n'est pas « non jugee » mais RETENUE — le doute ne sort pas de "
            f"la maison — et ce verdict n'est pas garde en memoire", repr(v_))
    # Une autre machine repond mal pendant que celle qui sait voir est fermee.
    poser([PC, NAS])
    await annoncer("pc", comfy=False)
    NASF.reponse = (400, '{"error":"image illisible"}')
    v_ = await juger()
    dit(v_ == "retenue" and not PCF.generes and len(NASF.generes) >= 1,
        "et si une autre machine echoue pendant que le PC, ferme, aurait su "
        "juger : retenue aussi", repr(v_))
    poser([PC])
    PCF.reponse = '{"adulte": false}'
    sain_ = await juger()
    PCF.reponse = '{"adulte": true}'
    adulte_ = await juger()
    dit((sain_, adulte_) == ("saine", "adulte"),
        "TEMOIN : ComfyUI ouvert, la vision locale juge comme avant",
        f"{sain_!r}, {adulte_!r}")
    # Le studio sans carte ni cerveau voyant, tout au nuage : comme avant.
    poser([LIBRE])
    S.REGISTRE.clear()
    S.ETAT_NOEUDS.clear()
    S._CERVEAUX[LIBRE]["modeles"] = []
    v_ = await juger()
    dit(v_ == "non jugee",
        "TEMOIN : un studio sans aucune machine ni modele qui sache voir, "
        "tout au nuage, garde son comportement — « non jugee », l'image part",
        repr(v_))


async def rattachement():
    print("\n  ── a quelle machine appartient un Ollama ──")
    # Deux agents vus a la MEME adresse (un mandataire) : on rattachait
    # l'Ollama au premier trouve.
    # C'est le vrai releve qui tourne, contre le faux Ollama de 127.0.0.2.
    poser([LIBRE])
    S.ETAT_NOEUDS["pc"]["ip"] = "127.0.0.2"
    S._CERVEAUX[LIBRE].update(noeud=None, quand=0.0)
    await S._rafraichir_cerveau(LIBRE)
    seul_ = S._CERVEAUX[LIBRE].get("noeud")
    S.ETAT_NOEUDS["zima"]["ip"] = "127.0.0.2"
    S._CERVEAUX[LIBRE]["quand"] = 0.0
    await S._rafraichir_cerveau(LIBRE)
    S._CERVEAUX[LIBRE]["quand"] = S.time.time() + 3600
    ambigu_ = (S._CERVEAUX[LIBRE].get("noeud"), S.noeud_du_cerveau(LIBRE),
               S._CERVEAUX[LIBRE].get("ambigu"))
    S.REGISTRE["pc"]["pause"] = S.time.time()
    en_pause_ = [u for u, _ in S.cerveaux_utilisables()]
    S.REGISTRE["pc"]["pause"] = None
    lignes_ = S.avertissements_du_pret()
    dit(seul_ == "pc" and ambigu_ == (None, None, ["pc", "zima"])
        and en_pause_ == [LIBRE],
        "deux machines qui s'annoncent depuis la meme adresse : l'Ollama "
        "n'est rattache a AUCUNE des deux, plutot qu'a la premiere trouvee — "
        "la pause de l'une ne ferme pas l'Ollama de l'autre par hasard",
        f"seule : {seul_!r} ; a deux : {ambigu_}, en pause : "
        f"{len(en_pause_)} adresse(s)")
    dit(len(lignes_) == 1 and LIBRE in lignes_[0]
        and "PC (RTX 2080 Ti) et NAS ZimaOS" in lignes_[0]
        and "la meme adresse" in lignes_[0],
        "et un avertissement le dit, en nommant les deux machines",
        str(lignes_))
    S.ETAT_NOEUDS["zima"]["ip"] = "10.0.0.2"
    S._CERVEAUX[LIBRE]["quand"] = 0.0
    await S._rafraichir_cerveau(LIBRE)
    dit(S._CERVEAUX[LIBRE].get("noeud") == "pc"
        and "ambigu" not in S._CERVEAUX[LIBRE],
        "et quand l'adresse redevient celle d'une seule machine, l'Ollama lui "
        "est de nouveau rattache", repr(S._CERVEAUX[LIBRE].get("noeud")))

    # Un Ollama que rien ne rattache, dans un parc qui a des agents.
    poser()
    lignes_ = S.avertissements_du_pret()
    dit(lignes_ == [f"la regle du pret ne s'applique pas a {LIBRE} : je ne "
                    f"sais pas a quelle machine il appartient"],
        "un Ollama rattache a aucune machine alors que le parc a des agents "
        "est signale en une ligne : la regle du pret ne s'y applique pas",
        str(lignes_))
    rep = await S.api_admin_noeuds(Req(admin=True))
    d_ = json.loads(rep.text)
    try:
        page = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "web", "admin.html"), encoding="utf-8").read()
    except OSError:
        page = ""
    dit(d_.get("avertissements_pret") == lignes_
        and "d.avertissements_pret" in page and 'id="pretAvertit"' in page,
        "/admin porte cette ligne et l'affiche",
        "web/admin.html absent" if not page else str(d_.get("avertissements_pret")))
    S.REGISTRE.clear()
    dit(S.avertissements_du_pret() == [],
        "TEMOIN : sans aucune machine a agent, un Ollama sans machine est "
        "l'etat ordinaire — rien n'est signale", str(S.avertissements_du_pret()))
    poser([PC, NAS])
    dit(S.avertissements_du_pret() == [],
        "TEMOIN : quand chaque Ollama a sa machine, rien n'est signale",
        str(S.avertissements_du_pret()))


async def le_service():
    print("\n  ── le moment ou le studio se met a servir ──")
    # Le vrai demarrer_file(), arrete aussitot : ses travailleurs n'ont rien a
    # faire, et le veilleur ne sonde que le faux ComfyUI de ce banc.
    poser()
    avant_ = S.time.time()
    a = {}
    try:
        await asyncio.wait_for(S.demarrer_file(a), 15)
        pose_ = S.SERVI_DEPUIS[0]
    finally:
        try:
            await asyncio.wait_for(S.arreter_file(a), 15)
        except Exception as e:
            print(f"  (arret du faux service : {type(e).__name__})")
    dit(avant_ <= pose_ <= S.time.time(),
        "demarrer_file() note l'instant ou le studio se met a servir : c'est "
        "de la que court l'attente des premieres annonces",
        f"{pose_ - avant_:.2f} s apres l'appel")
    S.SERVI_DEPUIS[0] = 0.0


async def affichage():
    print("\n  ── ce que l'administration en montre ──")
    poser()
    S.ETAT_NOEUDS["pc"].update(llm=True, llm_modeles=[MODELE])
    S.REGISTRE["muette"] = {"id": "muette", "titre": "Sans langage",
                            "agent": True, "jeton": "z", "pause": None}
    S.ETAT_NOEUDS["muette"] = {"repond": True, "vram": 6.0,
                               "vu": S.time.time(), "ip": "10.0.0.3"}
    etats_ = {x["id"]: x.get("cerveau_ferme", "absent") for x in S.noeuds_agents()}
    dit(etats_ == {"pc": "", "zima": "", "muette": None},
        "/api/admin/noeuds : une machine qui prete dit \"\", une machine a qui "
        "le studio ne connait aucun modele de langage ne dit rien",
        str(etats_))
    await annoncer("pc", comfy=False)
    S.REGISTRE["zima"]["pause"] = S.time.time()
    etats_ = {x["id"]: x.get("cerveau_ferme", "absent") for x in S.noeuds_agents()}
    S.ETAT_NOEUDS["pc"]["vu"] = S.time.time() - 100
    muet_ = {x["id"]: x.get("cerveau_ferme", "absent")
             for x in S.noeuds_agents()}["pc"]
    dit(etats_["pc"] == "ferme" and etats_["zima"] == "pause" and muet_ == "muet",
        "et l'etat du pret y est porte, machine par machine : ComfyUI ferme, "
        "pause, agent muet", f"{etats_}, puis pc={muet_!r}")
    try:
        page = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "web", "admin.html"), encoding="utf-8").read()
    except OSError:
        page = ""
    dit("n.cerveau_ferme" in page and "modèle de langage non utilisé" in page
        and "ComfyUI n’y tourne pas" in page and 'data-pret="' in page,
        "la console d'administration l'affiche sur la ligne de la machine",
        "web/admin.html absent" if not page else "")

    poser()
    libre_ = S.etiquette_du_cerveau(LIBRE)
    ouvert_ = S.etiquette_du_cerveau(PC)
    await annoncer("pc", comfy=False)
    ferme_ = S.etiquette_du_cerveau(PC)
    S.REGISTRE["pc"]["pause"] = 1.0
    pause_ = S.etiquette_du_cerveau(PC)
    S.REGISTRE["pc"]["pause"] = None
    S.ETAT_NOEUDS["pc"].update(repond=False, vu=0)
    demarrage_ = S.etiquette_du_cerveau(PC)
    dit(libre_ == "" and ouvert_ == "  [PC (RTX 2080 Ti)]"
        and "ComfyUI ferme : non utilise" in ferme_
        and "en pause : non utilise" in pause_
        and "sert seulement quand son ComfyUI tourne" in demarrage_,
        "la banniere de demarrage ne laisse plus croire que l'Ollama d'une "
        "machine sert quoi qu'il arrive : elle dit l'etat, ou la condition "
        "tant qu'aucun agent n'a battu",
        f"{ouvert_!r} / {ferme_!r} / {pause_!r} / {demarrage_!r}")

    poser([PC])
    await annoncer("pc", comfy=False)
    ligne_ = S._ligne_cerveau()
    cle_ = (ligne_.get("dit") or {}).get("cle")
    try:
        phrases_ = [S.traductions.rendre(ligne_["dit"], lg) for lg in ("fr", "en")]
    except Exception as e:
        phrases_ = [f"a leve {type(e).__name__}", ""]
    dit(cle_ == "demarrage.cerveau.ferme" and not ligne_.get("bloquant")
        and all("PC (RTX 2080 Ti)" in p for p in phrases_)
        and "ComfyUI" in phrases_[0] and "ComfyUI" in phrases_[1],
        "l'ecran de mise en route ne dit pas « aucun modele joignable » d'un "
        "Ollama qui repond : il nomme la machine qui ne prete pas sa carte, "
        "en francais et en anglais", f"{cle_!r} — {phrases_[0][:70]}")
    poser([PC])
    dit((S._ligne_cerveau().get("dit") or {}).get("cle") == "demarrage.cerveau.oui",
        "TEMOIN : ComfyUI ouvert, l'ecran annonce le modele comme avant",
        str((S._ligne_cerveau().get("dit") or {}).get("cle")))


async def main():
    for f in FAUX.values():
        await f.demarrer()
    await COMFY.demarrer()
    try:
        await verite()
        await en_direct()
        await pendant_l_attente()
        await en_vol_et_liberation()
        await par_l_agent()
        await vision()
        await aucun_cerveau()
        await machine_du_studio()
        await machine_fermee_pour_un_rendu()
        await reveil()
        await erreurs_dites()
        await image_jointe()
        await rattachement()
        await affichage()
        await le_service()
    finally:
        for f in FAUX.values():
            await f.runner.cleanup()
        await COMFY.runner.cleanup()
    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    for r in rate:
        print("    a regarder :", r)
    return 1 if rate else 0

sys.exit(asyncio.run(main()))
