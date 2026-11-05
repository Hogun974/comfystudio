# -*- coding: utf-8 -*-
"""Le studio choisit-il le bon Ollama ?

    python banc_cerveaux.py

Quatre regles, dans cet ordre :
  - une machine EN PAUSE ne pense pas ;
  - un Ollama qui calcule SUR LE PROCESSEUR passe apres tout le monde ;
  - une carte LIBRE passe devant une carte occupee ;
  - a egalite, la PLUS GROSSE carte.

CET EN-TETE DISAIT « la PLUS PETITE » jusqu'au 8 septembre 2026. L'ordre a ete
inverse par l'utilisateur le 1er septembre — le corps du banc le mesure depuis
—, et sa description est restee fausse une semaine, en tete du fichier qui
existe pour la garder. Un banc juste sous une docstring fausse trompe mieux
qu'un banc absent.

Et une cinquieme, qui est une regle de surete : une image a lire ne part JAMAIS
sur une machine sans modele de vision. Une description inventee est pire qu'une
erreur, parce que rien ne la signale.

Aucun Ollama n'est joignable ici : on remplit le cache a la main.
"""
import asyncio
import os
import sys
import tempfile

os.environ["OLLAMA_URL"] = ("http://pc.local:11434,http://nas.local:11434,"
                            "http://mort.local:11434")
os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_cerveaux_")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


PC = "http://pc.local:11434"
NAS = "http://nas.local:11434"
MORT = "http://mort.local:11434"


def poser(pause_pc=False):
    """Le parc REEL, releve sur les deux machines le 31 aout.

    Un decor invente ne prouve rien : la premiere version de ce banc donnait la
    vision a gemma3:4b et la refusait a gemma4:26b — l'inverse de ce que les
    deux Ollama annoncent. Dix-sept cas passaient sur un parc qui n'existe pas.
    """
    S.REGISTRE.clear()
    S.REGISTRE["pc"] = {"id": "pc", "titre": "PC (RTX 2080 Ti)", "agent": True,
                        "jeton": "x", "pause": 1.0 if pause_pc else None}
    S.REGISTRE["zima"] = {"id": "zima", "titre": "NAS ZimaOS", "agent": True,
                          "jeton": "y", "pause": None}
    S.ETAT_NOEUDS.clear()
    S.ETAT_NOEUDS["pc"] = {"repond": True, "vram": 11.0, "ram": 63.8,
                           "vu": S.time.time(), "ip": "10.0.0.1"}
    S.ETAT_NOEUDS["zima"] = {"repond": True, "vram": 5.9, "ram": 23.4,
                             "vu": S.time.time(), "ip": "10.0.0.2"}
    # Le cache des cerveaux, pose a la main : rien n'est joignable ici. Noms,
    # tailles et capacites recopies de /api/tags des deux machines.
    S._CERVEAUX.clear()
    S._CERVEAUX[PC] = {"quand": S.time.time(), "noeud": "pc", "modeles": [
        {"name": "gemma4:26b", "size": 18_600_000_000,
         "capabilities": ["completion", "tools", "thinking", "vision"]},
        {"name": "qwen2.5vl:7b", "size": 5_970_000_000,
         "capabilities": ["vision", "completion"]},
        {"name": "liquidai/lfm2.5-350m:latest", "size": 380_000_000,
         "capabilities": ["completion"]}]}
    S._CERVEAUX[NAS] = {"quand": S.time.time(), "noeud": "zima", "modeles": [
        {"name": "qwen3:4b", "size": 2_500_000_000,
         "capabilities": ["completion", "tools", "thinking"]},
        {"name": "mistral:7b", "size": 4_370_000_000,
         "capabilities": ["completion", "tools"]},
        {"name": "gemma3:4b", "size": 3_340_000_000,
         "capabilities": ["completion"]},
        {"name": "qwen2.5vl:7b", "size": 5_970_000_000,
         "capabilities": ["vision", "completion"]},
        # UN MODELE QUI NE COMPLETE PAS, et c'est tout ce qu'il fait ici. Un
        # Ollama qui sert aussi une recherche par similarite en porte un ; il
        # est minuscule — 270 Mo — donc il TIENT toujours sur la carte, et
        # « le plus gros modele de texte qui tienne » le choisissait des que
        # rien d'autre n'entrait. Le studio journalisait alors
        # « nomic-embed-text plutot que qwen2.5vl:7b » et lui envoyait un
        # /api/generate.
        {"name": "nomic-embed-text:latest", "size": 274_000_000,
         "capabilities": ["embedding"]}]}
    S._CERVEAUX[MORT] = {"quand": S.time.time(), "noeud": None, "modeles": []}
    S.VERROUS_NOEUD.clear()
    S.MODELES_CASSES.clear()
    S.MODELE_ECRITURE = ""


async def main():
    dit(S.OLLAMAS == [PC, NAS, MORT], "les trois adresses sont lues",
        str(len(S.OLLAMAS)))
    dit(S.OLLAMA == PC, "la premiere reste l'adresse principale")

    poser()
    l = S.cerveaux_utilisables()
    # L'ORDRE A ETE INVERSE PAR L'UTILISATEUR : « si analyse, prendre la plus
    # grosse (libre) pour l'analyse (rapide) ». L'ancienne regle — la plus
    # petite, pour ne pas retirer la meilleure au rendu — supposait que les
    # deux se disputent la carte pendant le meme temps. Une analyse dure
    # quelques secondes, un rendu des minutes.
    dit([u for u, _ in l] == [PC, NAS],
        "a cartes libres, la PLUS GROSSE d'abord", str([u for u, _ in l]))
    dit(MORT not in [u for u, _ in l],
        "une adresse sans aucun modele est ecartee")

    poser(pause_pc=True)
    l = S.cerveaux_utilisables()
    dit([u for u, _ in l] == [NAS], "une machine EN PAUSE est ecartee",
        str([u for u, _ in l]))
    S.REGISTRE["zima"]["pause"] = 2.0
    S._CERVEAUX[NAS]["quand"] = S.time.time()
    dit(S.cerveaux_utilisables() == [], "les deux en pause : plus rien")
    dit("PC" in S._pourquoi_aucun_cerveau() and "NAS" in S._pourquoi_aucun_cerveau(),
        "le message nomme les deux machines", S._pourquoi_aucun_cerveau())

    # Le cas qui TRANCHE : on occupe la petite. Sans la regle « libre d'abord »
    # elle resterait en tete parce qu'elle est la plus petite, et l'analyse
    # attendrait derriere un rendu pendant que la grosse carte dort.
    poser()
    await S.verrou_noeud("zima").acquire()
    l = S.cerveaux_utilisables()
    dit([u for u, _ in l] == [PC, NAS],
        "la petite occupee : la GROSSE libre passe devant", str([u for u, _ in l]))
    S.VERROUS_NOEUD["zima"].release()
    l = S.cerveaux_utilisables()
    dit([u for u, _ in l] == [PC, NAS], "relachee, la grosse reprend la tete",
        str([u for u, _ in l]))

    # ── l'image ne fait plus exception ──────────────────────────────────
    # Elle etait le SEUL cas ou la grosse carte passait devant, et pour une
    # raison qui vaut maintenant partout : mesure du 31 aout, la meme image lue
    # en 19 s sur la 2080 Ti et toujours pas rendue apres 900 s sur la GTX 1060.
    # Il n'y a plus deux regles, il n'y en a qu'une — et ce cas verifie qu'elles
    # se sont bien rejointes.
    # Lire une image est la seule tache ou la taille decide vraiment : mesure
    # du 31 aout, 19 s sur la 2080 Ti et toujours rien apres 900 s sur la
    # GTX 1060, ou le modele de vision deborde.
    poser()
    l = S.cerveaux_utilisables()
    dit([u for u, _ in l] == [PC, NAS], "pour du texte aussi, la plus GROSSE",
        str([u for u, _ in l]))
    l = S.cerveaux_utilisables(image=True)
    dit([u for u, _ in l] == [PC, NAS], "pour une image, la plus GROSSE d'abord",
        str([u for u, _ in l]))
    # La pause reste plus forte que tout.
    poser(pause_pc=True)
    l = S.cerveaux_utilisables(image=True)
    dit([u for u, _ in l] == [NAS], "et une machine en pause reste ecartee",
        str([u for u, _ in l]))
    poser()

    # ── le modele, par adresse ──────────────────────────────────────────
    poser()
    corps = {"model": S.MODELE_POUR_ECRIRE, "prompt": "x"}
    # Sur le NAS (5,9 Go de carte + 23,4 de RAM, soit 7,9 tenables) le plus gros
    # qui tienne est qwen2.5vl:7b a 5,97.
    dit(S.corps_ici(corps, NAS)["model"] == "qwen2.5vl:7b",
        "l'intention d'ecriture prend le plus gros QUI TIENNE au NAS",
        S.corps_ici(corps, NAS)["model"])
    # Sur le PC (11 + 5 = 16 tenables) gemma4:26b pese 18,6 : il est ecarte,
    # alors que « le plus gros » l'aurait choisi. Mesure du 31 aout : 165 s par
    # traduction quand il deborde.
    dit(S.corps_ici(corps, PC)["model"] == "qwen2.5vl:7b",
        "et ecarte celui qui ne tient pas sur la carte",
        S.corps_ici(corps, PC)["model"])

    corps = {"model": "qwen2.5vl:7b", "prompt": "x"}
    dit(S.corps_ici(corps, PC) is corps, "un modele present passe tel quel")

    # ── un modele qui deborde de la carte n'analyse pas ────────────────
    # Mesure du 7 septembre 2026, le PC en pause : qwen2.5vl:7b (5,97 Go) sur
    # la GTX 1060 de zima (5,9 Go), 119 a 261 s par appel — le meme appel fait
    # une a deux secondes sur la 2080 Ti. Le plafond ordinaire (carte + RAM
    # toleree, 7,9 Go) le disait « tenable » ; il tient, et deborde des que le
    # prompt est long. Les trois quarts de la carte, pas plus.
    dit(S.corps_ici(corps, NAS)["model"] == "mistral:7b",
        "sur le NAS (5,9 Go), qwen2.5vl:7b (5,97) deborde : le plus gros modele "
        "de texte qui tienne dans les trois quarts de la carte prend l'analyse "
        "— mistral:7b (4,37)", S.corps_ici(corps, NAS)["model"])
    dit(S.corps_ici(corps, PC) is corps,
        "sur le PC (11 Go) il tient dans les trois quarts, et passe tel quel")
    S.TACHES["banc-deborde"] = {"etapes": [], "etat": "en cours"}
    S.corps_ici(corps, NAS, "banc-deborde")
    dit(any("deborde" in e["msg"] and "mistral:7b" in e["msg"]
            for e in S.TACHES["banc-deborde"]["etapes"]),
        "et le fil de la demande dit quel modele a pris la place, et pourquoi",
        str([e["msg"] for e in S.TACHES["banc-deborde"]["etapes"]])[:90])
    _garde = S._CERVEAUX[NAS]["modeles"]
    S._CERVEAUX[NAS]["modeles"] = [m for m in _garde if m["name"] == "qwen2.5vl:7b"]
    dit(S.corps_ici(corps, NAS)["model"] == "qwen2.5vl:7b",
        "sans rien de plus petit installe, le demande reste : lent vaut mieux que muet")
    S._CERVEAUX[NAS]["modeles"] = _garde
    dit(S.corps_ici(corps, MORT) is None or S.corps_ici(corps, MORT).get("model"),
        "et une adresse sans machine connue n'est pas jugee sur une carte qu'on ignore")
    dit(S.PART_CARTE_ANALYSE == 0.75, "la part est de trois quarts", str(S.PART_CARTE_ANALYSE))

    # ── UN MODELE D'EMBEDDING NE REMPLACE PAS UN MODELE D'ANALYSE ──────
    # « Le plus gros modele de texte installe qui tienne » ne regardait que la
    # TAILLE. nomic-embed-text pese 270 Mo : il tient sur n'importe quelle
    # carte, et il devenait donc le remplacant tout designe des que le modele
    # demande debordait. Il ne sait pas completer — /api/generate lui rend une
    # erreur ou du vide —, et le fil de la demande annoncait pourtant
    # « nomic-embed-text plutot que qwen2.5vl:7b » comme un choix raisonne. La
    # capacite est annoncee par Ollama ; absente, on suppose qu'il complete,
    # comme partout ailleurs ici — un vieil Ollama ne doit pas devenir muet.
    poser()
    EMBED = "nomic-embed-text:latest"
    taille_embed = next(m["size"] for m in S._CERVEAUX[NAS]["modeles"]
                        if m["name"] == EMBED) / 1e9
    S.ETAT_NOEUDS["zima"]["vram"] = 0.5      # trois quarts : 0,375 Go de marge
    dit(taille_embed <= 0.5 * S.PART_CARTE_ANALYSE
        and S.modele_analyse_de(NAS, "qwen2.5vl:7b") == "qwen2.5vl:7b",
        "sur une carte ou l'embedding est le SEUL a tenir, l'analyse garde le "
        "modele demande : lent vaut mieux qu'un modele qui ne complete pas",
        f"{S.modele_analyse_de(NAS, 'qwen2.5vl:7b')}, "
        f"embedding {taille_embed:.2f} Go pour {0.5 * S.PART_CARTE_ANALYSE:.3f} de marge")
    # ET IL NE PREND PAS NON PLUS LA PLACE QUAND D'AUTRES TIENNENT : la carte
    # revenue, c'est mistral:7b — le plus gros qui COMPLETE — et jamais lui.
    poser()
    dit(S.modele_analyse_de(NAS, "qwen2.5vl:7b") == "mistral:7b",
        "et sur la vraie carte du NAS, c'est le plus gros modele QUI COMPLETE "
        "qui prend la place", S.modele_analyse_de(NAS, "qwen2.5vl:7b"))
    # Un modele qui n'annonce AUCUNE capacite est suppose completer : le parc
    # porte de vieux Ollama, et une absence d'annonce ne rend personne muet.
    poser()
    S._CERVEAUX[NAS]["modeles"] = [
        {"name": "vieux:7b", "size": 3_000_000_000},          # rien d'annonce
        {"name": "enorme:70b", "size": 40_000_000_000,
         "capabilities": ["completion"]}]
    S.ETAT_NOEUDS["zima"]["vram"] = 11.0     # 8,25 Go de marge
    dit(S.modele_analyse_de(NAS, "enorme:70b") == "vieux:7b",
        "un modele sans capacite annoncee est suppose completer : un vieil "
        "Ollama, qui n'annonce rien, ne devient pas muet",
        S.modele_analyse_de(NAS, "enorme:70b"))
    poser()

    # ── un Ollama peut avoir une carte et ne pas s'en servir ───────────
    # LA PANNE LA PLUS COUTEUSE DU PARC, ET LA SEULE QUI NE SE VOIE NULLE
    # PART : la machine repond, annonce ses modeles, le studio la choisit, et
    # chaque analyse prend deux a cinq minutes. Releve du 8 septembre 2026 sur
    # zima — gemma3:4b, 5,25 Go en memoire, 0,00 sur une carte de 6,3 Go
    # libres, vue en CUDA par le ComfyUI de la MEME machine. « /api/ps » le
    # dit, et lui seul. Ici on remplace la session HTTP : c'est le VRAI
    # relever_placement() qui tourne, sur une reponse d'Ollama fabriquee.
    print("\n  ── ou l'Ollama met vraiment le modele ──")
    poser()
    S._PLACEMENT.clear()
    dit(S.sur_processeur(NAS) is False,
        "sans mesure, une adresse n'est PAS declaree sur processeur : on ne "
        "declasse pas une machine sur une absence de mesure")
    dit(S.llm_sur_carte("zima") is None,
        "et la console ne dit rien plutot que d'accuser", str(S.llm_sur_carte("zima")))

    PS = {"charge": {"models": []}, "appels": [], "leve": False}

    class FausseReponse:
        async def json(self):
            return PS["charge"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class FausseSession:
        def __init__(self, *a, **k):
            pass

        def get(self, url):
            PS["appels"].append(url)
            if PS["leve"]:
                raise RuntimeError("injoignable")
            return FausseReponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    vraie_session = S.aiohttp.ClientSession
    S.aiohttp.ClientSession = FausseSession
    try:
        PS["charge"] = {"models": [{"name": "gemma3:4b", "size": 5_250_000_000,
                                    "size_vram": 0}]}
        await S.relever_placement(NAS, "gemma3:4b")
        dit(S.sur_processeur(NAS) is True and PS["appels"] == [f"{NAS}/api/ps"],
            "un modele entierement hors de la carte declare cette adresse sur "
            "processeur, et c'est /api/ps qui l'a dit",
            f"{S.sur_processeur(NAS)}, {PS['appels']}")
        dit(S.llm_sur_carte("zima") is False,
            "la console le montre sur la machine, pas sur l'adresse")

        del PS["appels"][:]
        await S.relever_placement(NAS, "gemma3:4b")
        dit(not PS["appels"],
            "une adresse deja mesuree n'est pas resondee dans l'heure : c'est un "
            "fait de machine, pas un fait de demande", str(PS["appels"]))

        S._PLACEMENT.clear()
        del PS["appels"][:]
        PS["charge"] = {"models": [{"name": "qwen2.5vl:7b", "size": 5_970_000_000,
                                    "size_vram": 5_970_000_000}]}
        await S.relever_placement(PC, "qwen2.5vl:7b")
        dit(S.sur_processeur(PC) is False and S.llm_sur_carte("pc") is True,
            "un modele pose sur la carte ne declasse rien", str(S.llm_sur_carte("pc")))

        S._PLACEMENT.clear()
        PS["charge"] = {"models": [{"name": "autre:7b", "size": 1, "size_vram": 0}]}
        await S.relever_placement(NAS, "gemma3:4b")
        dit(S.sur_processeur(NAS) is False,
            "un /api/ps qui ne porte pas LE modele employe n'apprend rien, et "
            "n'accuse personne")

        S._PLACEMENT.clear()
        PS["leve"] = True
        try:
            await S.relever_placement(NAS, "gemma3:4b")
            echappe = None
        except Exception as e:
            # CE QUE LE STUDIO EN FERAIT : la mesure est appelee dans le meme
            # « try » que l'appel au modele, et ce qui echappe ici passe pour
            # une panne de cerveau. On l'attrape donc pour ROUGIR, et non pour
            # casser le banc — un banc casse ne nomme pas la panne.
            echappe = type(e).__name__
        dit(echappe is None and S.sur_processeur(NAS) is False,
            "et une adresse qui ne repond pas a /api/ps ne leve rien : la mesure "
            "de confort ne peut pas casser l'analyse qui vient de reussir",
            echappe or "rien n'a echappe")
        PS["leve"] = False

        # ET LE CAS QUI COMPTE VRAIMENT : la machine qui DEPASSE l'echeance.
        # La mesure suit un appel REUSSI — or l'Ollama assez lent pour depasser
        # est justement celui qui a le plus besoin d'etre diagnostique, et il
        # n'aboutit jamais. Sans une seconde prise au moment du depassement, il
        # ne serait mesure qu'a l'appel ou il repond, c'est-a-dire peut-etre
        # jamais. Au depassement, le modele est charge la-bas et calcule
        # encore : /api/ps dit ou.
        poser()
        S._PLACEMENT.clear()
        del PS["appels"][:]
        PS["charge"] = {"models": [{"name": "qwen2.5vl:7b", "size": 5_970_000_000,
                                    "size_vram": 0}]}

        async def _depasse(corps, url=None, secondes=900):
            raise asyncio.TimeoutError()

        vrai_local = S._ollama_local
        S._ollama_local = _depasse
        S.TACHES["banc-depasse"] = {"etapes": [], "etat": "en cours"}
        try:
            await S._appeler_llm("x", None, None, True, None, 0.1, "banc-depasse")
        except Exception:
            pass
        finally:
            S._ollama_local = vrai_local
            S.TACHES.pop("banc-depasse", None)
        dit(S.sur_processeur(PC) is True and f"{PC}/api/ps" in PS["appels"],
            "une adresse qui DEPASSE l'echeance est mesuree elle aussi, sinon "
            "l'Ollama le plus lent du parc serait le seul jamais diagnostique",
            f"{S.sur_processeur(PC)}, {PS['appels']}")
    finally:
        S.aiohttp.ClientSession = vraie_session

    # L'ORDRE. La regle passe AVANT « libre d'abord », et c'est un choix ecrit :
    # deux a cinq minutes mesurees contre le reste d'une etape de rendu.
    poser()
    S._PLACEMENT.clear()
    S._PLACEMENT[PC] = {"part": 0.0, "quand": S.time.time()}
    l = S.cerveaux_utilisables()
    dit([u for u, _ in l] == [NAS, PC],
        "un Ollama sur processeur passe DERNIER, meme libre et meme sur la plus "
        "grosse carte du parc", str([u for u, _ in l]))
    await S.verrou_noeud("zima").acquire()
    l = S.cerveaux_utilisables()
    dit([u for u, _ in l] == [NAS, PC],
        "et la carte OCCUPEE passe quand meme devant le processeur : attendre la "
        "fin d'une etape coute moins que deux a cinq minutes",
        str([u for u, _ in l]))
    S.VERROUS_NOEUD["zima"].release()
    S._PLACEMENT[NAS] = {"part": 0.0, "quand": S.time.time()}
    l = S.cerveaux_utilisables()
    dit(len(l) == 2,
        "deux cerveaux sur processeur restent utilisables : un cerveau lent vaut "
        "mieux que pas de cerveau", str(len(l)))
    dit(S.PART_SUR_CARTE_MINIMUM == 0.05,
        "le seuil est a cinq pour cent : un Ollama qui ne pose que son cache de "
        "contexte sur la carte n'y calcule pas", str(S.PART_SUR_CARTE_MINIMUM))
    S._PLACEMENT.clear()

    # ── une analyse de texte a une echeance, et une demande ne l'attend qu'une fois ──
    # Mesure du 7 septembre 2026, le PC en pause : 119 a 300 s et plus par
    # appel sur zima, dont le modele tourne sur le processeur, et une demande
    # fait trois ou quatre appels. L'appel de texte n'avait que l'echeance des
    # images, 900 s. Ici, _ollama_local est remplace : on lit l'echeance qu'on
    # lui passe, et on le fait depasser.
    #
    # AUCUN OLLAMA N'EST JOIGNABLE ICI — c'est la promesse de l'en-tete — et
    # un depassement declenche desormais une mesure de placement. Sans les deux
    # lignes ci-dessous, chaque TimeoutError de cette section irait sonder
    # pc.local puis nas.local POUR DE VRAI, trois secondes chacune, sur des noms
    # qu'aucune machine de CI ne resout : un banc qui depend du reseau ne mesure
    # pas ce qu'il croit. Une mesure fraiche fait rendre la main a
    # relever_placement des sa premiere ligne. « part » a 1,0 et non 0,0 :
    # declasser les deux adresses les mettrait « sur processeur » et
    # inverserait l'ordre que ces cas empruntent.
    poser()
    S._PLACEMENT[PC] = {"part": 1.0, "quand": S.time.time()}
    S._PLACEMENT[NAS] = {"part": 1.0, "quand": S.time.time()}
    recus = []

    async def faux_local(corps, url=None, secondes=900):
        recus.append((bool(corps.get("images")), secondes, url))
        if corps.get("prompt") == "depasse":
            raise asyncio.TimeoutError()
        return "{}"

    vrai_local = S._ollama_local
    S._ollama_local = faux_local
    S.TACHES["banc-lent"] = {"etapes": [], "etat": "en cours"}
    try:
        await S._appeler_llm("x", None, None, True, None, 0.1, "banc-lent")
        dit(recus and recus[-1][0] is False and recus[-1][1] == S.ANALYSE_DELAI == 180,
            "un appel de TEXTE part avec ANALYSE_DELAI, 180 s, et non les 900 s des images",
            str(recus[-1:]))
        await S._appeler_llm("x", "aW1hZ2U=", None, True, None, 0.1, "banc-lent")
        dit(recus and recus[-1][0] is True and recus[-1][1] in (300, 900),
            "une IMAGE garde ses 300 ou 900 s : lire n'a pas de raccourci",
            str(recus[-1:]))
        del recus[:]
        try:
            await S._appeler_llm("depasse", None, None, True, None, 0.1, "banc-lent")
            issue = "rendu"
        except Exception as e:
            issue = type(e).__name__
        lignes = [e["msg"] for e in S.TACHES["banc-lent"]["etapes"]]
        dit(issue != "rendu" and S.TACHES["banc-lent"].get("cerveau_lent")
            and any("n'a pas repondu en 180 s" in l and "sans modele" in l for l in lignes),
            "au-dela de l'echeance, la demande est marquee « cerveau lent » et le fil dit "
            "que le reste se fera sans modele",
            f"{issue}, marque={S.TACHES['banc-lent'].get('cerveau_lent')!r}")
        dit(len(recus) >= 1 and all(not r[0] for r in recus),
            "et chaque cerveau a ete essaye a l'echeance, pas au-dela",
            f"{len(recus)} appel(s)")
        del recus[:]
        try:
            await S.appeler_ollama("encore", None, None, True, tid="banc-lent")
            issue = "rendu"
        except S.CerveauTropLent:
            issue = "CerveauTropLent"
        except Exception as e:
            issue = type(e).__name__
        dit(issue == "CerveauTropLent" and not recus,
            "l'appel SUIVANT de la meme demande ne part pas : CerveauTropLent, zero appel",
            f"{issue}, {len(recus)} appel(s)")
        S.TACHES["banc-autre"] = {"etapes": [], "etat": "en cours"}
        rendu = await S.appeler_ollama("x", None, None, True, tid="banc-autre")
        dit(rendu == "{}" and len(recus) == 1,
            "alors qu'une AUTRE demande part normalement : la marque est par demande",
            f"{len(recus)} appel(s)")
        rendu = await S.appeler_ollama("x", "aW1hZ2U=", None, True, tid="banc-lent")
        dit(rendu == "{}", "et une image de la demande lente part quand meme : elle n'a pas de raccourci")

        # ── LE PREMIER DEPASSE, LE SECOND REPOND ───────────────────────
        # LA MARQUE ETAIT POSEE DANS LE « except » DE CHAQUE ADRESSE, et la
        # boucle continue apres un depassement. Une demande dont le plan
        # expirait sur la petite carte puis revenait en une seconde sur la
        # grosse repartait donc avec son plan ET sa marque : enrichissement,
        # traduction et recherche de sujet levaient CerveauTropLent pour rien,
        # et le prompt partait en francais a un moteur qui ne lit que
        # l'anglais — ce que ce depot documente comme changeant le SUJET, pas
        # la qualite. Une adresse lente dans un parc de deux ne doit pas
        # decider pour la demande entiere.
        #
        # poser() ne touche pas a _PLACEMENT : les deux mesures posees en tete
        # de section tiennent encore, et rien ne part sur le reseau.
        poser()
        del recus[:]

        async def premier_lent(corps, url=None, secondes=900):
            recus.append((bool(corps.get("images")), secondes, url))
            if url == PC:
                raise asyncio.TimeoutError()
            return "{}"

        S._ollama_local = premier_lent
        S.TACHES["banc-mixte"] = {"etapes": [], "etat": "en cours"}
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1,
                                         "banc-mixte")
        except Exception as e:      # un banc qui meurt ne nomme pas la panne
            rendu = f"a leve {type(e).__name__}"
        dit(rendu == "{}" and [r[2] for r in recus] == [PC, NAS]
            and not S.TACHES["banc-mixte"].get("cerveau_lent"),
            "quand le PREMIER cerveau depasse et que le SECOND repond, la "
            "demande repart avec sa reponse et SANS la marque « cerveau lent »",
            f"{rendu!r}, marque={S.TACHES['banc-mixte'].get('cerveau_lent')!r}, "
            f"essais={[r[2] for r in recus]}")
        del recus[:]
        try:
            suite = await S.appeler_ollama("encore", None, None, True,
                                           tid="banc-mixte")
        except Exception as e:
            suite = f"a leve {type(e).__name__}"
        dit(suite == "{}" and [r[2] for r in recus] == [PC, NAS],
            "et l'appel SUIVANT de cette demande part vraiment, jusqu'a la "
            "seconde adresse : c'est l'enrichissement et la traduction qui "
            "levaient pour rien",
            f"{suite!r}, essais={[r[2] for r in recus]}")

        # ── ECRIRE N'EST PAS ANALYSER ──────────────────────────────────
        # L'echeance de 180 s ne visait que l'analyse, et s'appliquait pourtant
        # a « tout ce qui n'est pas une image ». Les appels d'ECRITURE —
        # enrichissement, traduction, refrain, couplets — prennent le plus gros
        # modele de la machine, dix-huit gigaoctets parfois, dont le chargement
        # seul depasse trois minutes. La premiere tentative de refrain expirait,
        # les cinq suivantes levaient sur la marque, _ecrire_paroles rendait ""
        # et la demande mourait sur « les paroles n'ont pas pu etre ecrites » :
        # une erreur DURE pour une carte simplement lente a charger.
        del recus[:]
        S._ollama_local = faux_local
        S.TACHES["banc-ecrit"] = {"etapes": [], "etat": "en cours"}
        await S._appeler_llm("x", None, None, True, S.MODELE_POUR_ECRIRE, 0.1,
                             "banc-ecrit")
        dit(recus and recus[-1][0] is False and recus[-1][1] == 900,
            "un appel d'ECRITURE part avec neuf cents secondes, et non les "
            f"{S.ANALYSE_DELAI} s de l'analyse : le plus gros modele de la "
            "machine met plus de trois minutes rien qu'a se charger",
            str(recus[-1:]))
        del recus[:]
        try:
            await S._appeler_llm("depasse", None, None, True,
                                 S.MODELE_POUR_ECRIRE, 0.1, "banc-ecrit")
            issue = "rendu"
        except Exception as e:
            issue = type(e).__name__
        dit(issue != "rendu" and not S.TACHES["banc-ecrit"].get("cerveau_lent")
            and len(recus) == 2 and all(r[1] == 900 for r in recus),
            "et le depassement d'une ECRITURE ne marque PAS la demande : ce "
            "n'est pas un diagnostic d'analyse lente, et le couplet suivant "
            "doit pouvoir partir",
            f"{issue}, marque={S.TACHES['banc-ecrit'].get('cerveau_lent')!r}, "
            f"delais={[r[1] for r in recus]}")
    finally:
        S._ollama_local = vrai_local
        S._PLACEMENT.clear()
        S.TACHES.pop("banc-lent", None)
        S.TACHES.pop("banc-autre", None)
        S.TACHES.pop("banc-mixte", None)
        S.TACHES.pop("banc-ecrit", None)
    S._CERVEAUX[NAS]["modeles"] = [m for m in S._CERVEAUX[NAS]["modeles"]
                                   if m["name"] != "qwen2.5vl:7b"]
    remplace = S.corps_ici(corps, NAS)
    dit(remplace["model"] != "qwen2.5vl:7b", "un modele absent est remplace",
        remplace["model"])
    poser()

    # ── un reglage impose sur un parc qui ne l'est pas ──────────────────
    S.MODELE_ECRITURE = "mistral:7b"          # le NAS l'a, le PC non
    corps = {"model": S.MODELE_POUR_ECRIRE, "prompt": "x"}
    dit(S.corps_ici(corps, NAS)["model"] == "mistral:7b",
        "le reglage est suivi la ou il existe")
    dit(S.corps_ici(corps, PC)["model"] != "mistral:7b",
        "et ignore la ou il n'existe pas", S.corps_ici(corps, PC)["model"])
    S.MODELE_ECRITURE = ""

    # ── une image ───────────────────────────────────────────────────────
    corps = {"model": "qwen2.5vl:7b", "prompt": "x", "images": ["…"]}
    dit(S.corps_ici(corps, PC) is corps,
        "une image reste sur le meilleur voyant quand c'est deja lui")
    dit(S.corps_ici(corps, NAS) is corps, "et de meme sur l'autre machine")

    # gemma4:26b DECLARE la vision et pese 18,6 Go sur une carte de 11 : il ne
    # doit pas etre choisi pour autant. « Le plus gros voyant » sans borne
    # l'aurait pris.
    corps = {"model": "gemma4:26b", "prompt": "x", "images": ["…"]}
    bascule = S.corps_ici(corps, PC)
    dit(bascule is not None and bascule["model"] == "qwen2.5vl:7b",
        "un voyant trop gros pour la carte cede au voyant qui tient",
        str(bascule and bascule["model"]))

    # gemma3:4b n'annonce PAS « vision » dans /api/tags, quoi qu'en dise
    # /api/show : c'est /api/tags que le studio lit. Une image ne doit donc pas
    # lui etre confiee.
    corps = {"model": "gemma3:4b", "prompt": "x", "images": ["…"]}
    v = S.corps_ici(corps, NAS)
    dit(v is not None and v["model"] == "qwen2.5vl:7b",
        "un modele qui n'annonce pas la vision cede la place",
        str(v and v["model"]))

    # ── STUDIO_VISION est un reglage, pas une decoration ────────────────
    # Il etait entierement recouvert : le studio annonçait « lecture par X »,
    # passait X, et corps_ici prenait le plus gros voyant sans le dire. Le
    # reglage n'avait aucun effet, et le message d'erreur envoyait installer un
    # modele qui n'avait jamais ete essaye.
    # LAISSE AU DEFAUT, il ne doit RIEN changer. C'est le defaut de STUDIO_LLM
    # aussi : sans le garde « impose », la branche s'ouvrait pour tout appel
    # portant une image et la regle du plus gros voyant ne s'appliquait plus
    # nulle part. Ce cas-la est celui qui est LIVRE — il passe en premier.
    S.MODELE_VISION_IMPOSE = False
    S.MODELE_VISION = "qwen2.5vl:7b"
    v = S.corps_ici({"model": "qwen2.5vl:7b", "prompt": "x", "images": ["…"]}, PC)
    dit(v is not None and v["model"] == "qwen2.5vl:7b",
        "sans reglage, c'est le voyant que la carte tient qui repond",
        str(v and v["model"]))
    S.MODELE_VISION = "gemma4:26b"
    v = S.corps_ici({"model": "gemma4:26b", "prompt": "x", "images": ["…"]}, PC)
    dit(v is not None and v["model"] == "qwen2.5vl:7b",
        "un defaut trop gros pour la carte ne s'impose pas non plus",
        str(v and v["model"]))

    S.MODELE_VISION_IMPOSE = True
    S.MODELE_VISION = "gemma4:26b"
    corps = {"model": "gemma4:26b", "prompt": "x", "images": ["…"]}
    v = S.corps_ici(corps, PC)
    dit(v is not None and v["model"] == "gemma4:26b",
        "le modele de vision NOMME est honore, meme plus gros que la carte",
        str(v and v["model"]))
    # La borne de la carte reste le defaut : elle ne s'applique qu'au choix
    # automatique, pas a un nom pose a la main.
    v = S.corps_ici({"model": "autre:1b", "prompt": "x", "images": ["…"]}, PC)
    dit(v is not None and v["model"] == "qwen2.5vl:7b",
        "et le choix automatique reste borne par la carte",
        str(v and v["model"]))
    # Absent de CETTE machine : on retombe sur ce qu'elle sait faire.
    v = S.corps_ici(corps, NAS)
    dit(v is not None and v["model"] == "qwen2.5vl:7b",
        "la ou il n'est pas installe, le voyant de la machine reprend la main",
        str(v and v["model"]))
    S.MODELE_VISION_IMPOSE = False
    S.MODELE_VISION = "qwen2.5vl:7b"
    corps = {"model": "gemma3:4b", "prompt": "x", "images": ["…"]}

    # Et sur une machine ou AUCUN modele ne voit, on n'envoie rien.
    S._CERVEAUX[NAS]["modeles"] = [m for m in S._CERVEAUX[NAS]["modeles"]
                                   if "vision" not in (m.get("capabilities") or [])]
    dit(S.corps_ici(corps, NAS) is None,
        "aucun modele voyant : l'adresse est ecartee, jamais substituee")
    poser()

    # ── un modele casse l'est SUR UNE MACHINE, pas partout ──────────────
    S._ecarter_modele("qwen2.5vl:7b", "carte pleine", NAS)
    corps = {"model": S.MODELE_POUR_ECRIRE, "prompt": "x"}
    dit(S.corps_ici(corps, NAS)["model"] != "qwen2.5vl:7b",
        "ecarte la ou il a echoue", S.corps_ici(corps, NAS)["model"])
    dit(S.corps_ici(corps, PC)["model"] == "qwen2.5vl:7b",
        "toujours employe la ou il marche", S.corps_ici(corps, PC)["model"])

    # ── un reglage impose ne s'efface pas sur un echec ──────────────────
    S.MODELE_ECRITURE = "mistral:7b"
    S.MODELE_ECRITURE_IMPOSE = True
    S._ecarter_modele("mistral:7b", "carte pleine", NAS)
    dit(S.MODELE_ECRITURE == "mistral:7b",
        "un reglage pose a la main survit a un echec", S.MODELE_ECRITURE)
    S.MODELE_ECRITURE_IMPOSE = False
    S._ecarter_modele("mistral:7b", "carte pleine", PC)
    dit(S.MODELE_ECRITURE == "", "un choix devine, lui, se refait")
    S.MODELE_ECRITURE = ""

    # ── une machine du parc SANS CARTE ──────────────────────────────────
    # LE PLAFOND NE DOIT PAS S'INVERSER. modele_ecriture_de et
    # modele_vision_de n'avaient aucun cas a eux : ils n'etaient eprouves qu'a
    # travers corps_ici, sur des machines qui ont toutes une carte. La panne a
    # donc pu passer.
    #
    # La precondition est etroite mais reelle : un ComfyUI dont /system_stats ne
    # porte aucun « vram_total », sur une machine qui prete par ailleurs son
    # Ollama. agent_noeud.py annonce exactement ce couple — vram=0, ram>0 — et
    # charger_parc() le fige d'un redemarrage a l'autre.
    #
    # Ce que ces cas gardent : « cette machine n'a pas de carte » ne se lit pas
    # « on ne sait pas ce qu'elle tient ». Le premier est un plafond bas, le
    # second est l'absence de plafond, et les confondre choisit gemma4:26b,
    # 18,6 Go — cent soixante-cinq secondes par traduction, mesurees le 31 aout.
    poser()
    S.ETAT_NOEUDS["pc"]["vram"] = 0.0        # la carte a disparu de l'annonce
    dit(S._vram_utile("pc") == 0.0,
        "sans carte, la machine ne tient rien a rendre : 0 Go utile",
        str(S._vram_utile("pc")))
    dit(S.modele_ecriture_de(PC) == "qwen2.5vl:7b",
        "et pour ecrire, elle reste plafonnee : pas gemma4:26b sur une machine "
        "sans carte", S.modele_ecriture_de(PC))
    dit(S.modele_vision_de(PC) == "qwen2.5vl:7b",
        "pour lire une image non plus : le voyant trop gros ne passe pas par "
        "la porte de derriere", S.modele_vision_de(PC))

    # QUAND AUCUN NE TIENT, LE PLUS PETIT — et non le plus gros. C'etait la
    # seconde porte : « tenables ou tous les voyants », puis max(), rendait
    # justement le modele que le plafond venait d'ecarter.
    S.ETAT_NOEUDS["pc"]["ram"] = 8.0         # trop peu pour tolerer quoi que ce soit
    dit(S.modele_vision_de(PC) == "qwen2.5vl:7b",
        "meme quand aucun voyant ne tient, c'est le plus petit qui repond",
        S.modele_vision_de(PC))

    # LA CARTE REVENUE, RIEN NE BOUGE : le correctif ne touche qu'au cas sans
    # carte.
    poser()
    dit(S.modele_ecriture_de(PC) == "qwen2.5vl:7b"
        and S.modele_vision_de(PC) == "qwen2.5vl:7b",
        "avec sa carte, la meme machine repond comme avant",
        f"{S.modele_ecriture_de(PC)} / {S.modele_vision_de(PC)}")

    # UNE MACHINE INCONNUE GARDE SON ABSENCE DE PLAFOND. On ne devine pas ce
    # qu'une machine dont on ignore tout peut charger, et lui refuser ses gros
    # modeles la rendrait muette pour rien. C'est le cas que la branche « sinon,
    # aucun plafond » sert VRAIMENT — et qu'il ne faut pas fermer en fermant
    # l'autre.
    poser()
    S._CERVEAUX[PC]["noeud"] = None          # un Ollama qui n'est rattache a rien
    dit(S.modele_ecriture_de(PC) == "gemma4:26b",
        "d'une machine inconnue, on prend le plus gros : aucun plafond a poser",
        S.modele_ecriture_de(PC))
    dit(S.modele_vision_de(PC) == "gemma4:26b",
        "et le plus gros voyant de meme", S.modele_vision_de(PC))
    poser()

    await degeneres()


async def degeneres():
    """Un modele resident qui repond 200, sans erreur, et RIEN.

    Mesure du 4 novembre 2026 : qwen2.5vl sur l'Ollama du PC a rendu des
    reponses vides pendant un essai ; le plan est retombe sur l'aiguillage par
    mots-cles sans un mot, et personne n'a decharge le modele — ce qui seul le
    repare. Ici, deux faux : _ollama_local rend ce que le scenario dit, et la
    session HTTP — celle du VRAI liberer_modele_a — note chaque dechargement
    sans rien envoyer.
    """
    print("\n  ── un modele qui repond sans rien dire ──")
    poser()
    # Mesures fraiches : relever_placement rend la main sans sonder personne.
    S._PLACEMENT[PC] = {"part": 1.0, "quand": S.time.time()}
    S._PLACEMENT[NAS] = {"part": 1.0, "quand": S.time.time()}
    S._DECHARGE_DEGENERE.clear()
    S.DEGENERESCENCES.clear()
    S._DEGENERES_TOTAL[0] = 0
    S.QUARANTAINES.clear()
    S._VUS_DEGENERE.clear()
    appels, decharges = [], []
    scenario = {}
    refus = {"leve": False}

    async def faux_local(corps, url=None, secondes=900):
        appels.append((url, corps.get("model")))
        file_ = scenario.get(url) or ["{}"]
        rep_ = file_.pop(0) if len(file_) > 1 else file_[0]
        if callable(rep_):
            r_ = rep_(corps, url)
            # Une reponse qui ATTEND : le temps, pour un second appel, de
            # partir pendant que celui-ci est en vol.
            return (await r_) if asyncio.iscoroutine(r_) else r_
        return rep_

    def neuf():
        # Chaque cas ci-dessous eprouve UNE regle. La mise de cote laissee par
        # le cas d'avant ferait sauter le PC, et le cas ne prouverait plus rien.
        S.QUARANTAINES.clear()
        S._VUS_DEGENERE.clear()

    def coupe(corps, url):
        # Ce qu'Ollama 0.40.14 rend sans « format » quand le modele sort « @ »
        # des le premier jeton (journal du PC, 5 novembre 2026).
        raise S.ReponseDegeneree("ollama 500 : {\"error\":\"prediction "
                                 "aborted, token repeat limit reached\"}")

    class FausseReponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class FausseSession:
        def __init__(self, *a, **k):
            pass

        def post(self, url, json=None):
            if refus["leve"]:
                raise RuntimeError("injoignable")
            decharges.append((url, (json or {}).get("model"),
                              (json or {}).get("keep_alive")))
            return FausseReponse()

        def get(self, url):
            raise RuntimeError(f"aucune sonde attendue ici : {url}")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    def fil(tid):
        return [e["msg"] for e in (S.TACHES.get(tid) or {}).get("etapes", [])]

    vrai_local = S._ollama_local
    vraie_session = S.aiohttp.ClientSession
    S._ollama_local = faux_local
    S.aiohttp.ClientSession = FausseSession
    tids = []
    try:
        # ── LE VIDE SANS ERREUR : decharger, puis retenter AU MEME ENDROIT ──
        tid = "banc-degen-vide"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        scenario[PC] = ["", "{}"]
        rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        modele_pc = appels[0][1] if appels else None
        dit(rendu == "{}" and [a[0] for a in appels] == [PC, PC],
            "une reponse VIDE sans erreur est retentee une fois, au meme "
            "endroit, et c'est la reprise qui est rendue",
            f"{rendu!r}, essais={[a[0] for a in appels]}")
        dit(decharges == [(f"{PC}/api/generate", modele_pc, 0)],
            "et entre les deux, CE modele est decharge A CETTE adresse "
            "(keep_alive 0)", str(decharges))
        dit(any("reponse vide" in l and "decharge" in l for l in fil(tid)),
            "le fil de la demande le dit : reponse vide, modele decharge",
            " | ".join(fil(tid))[-200:])
        r_ = S.releve_degenerescences()
        dit(r_["total"] == 1 and r_["derniers"]
            and r_["derniers"][0]["issue"] == "reparee"
            and r_["derniers"][0]["machine"] == "PC (RTX 2080 Ti)"
            and r_["derniers"][0]["decharge"] is True,
            "et la console en garde la trace : machine, modele, reparee",
            str(r_["derniers"][:1]))

        # ── LA MEME PANNE DANS LA FENETRE : pas de second dechargement ──
        del appels[:]
        del decharges[:]
        tid = "banc-degen-fenetre"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        scenario[PC] = [""]
        scenario[NAS] = ["{}"]
        rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        dit(not decharges,
            "dans la fenetre, le meme modele a la meme adresse n'est PAS "
            "decharge une seconde fois : on ne martele pas", str(decharges))
        dit(rendu == "{}" and [a[0] for a in appels] == [PC, NAS],
            "et la reprise part sur l'AUTRE machine, qui repond",
            f"{rendu!r}, essais={[a[0] for a in appels]}")
        dit(any("deja decharge" in l for l in fil(tid))
            and S.releve_degenerescences()["derniers"][0]["issue"]
            == "repondue par NAS ZimaOS",
            "le fil dit pourquoi, et la console dit qui a repondu",
            str(S.releve_degenerescences()["derniers"][:1]))
        # Decharge au cas d'avant, il degenere de nouveau : c'est la seconde
        # fois dans la fenetre, celle que le dechargement n'a pas reparee.
        dit((PC, modele_pc) in S.QUARANTAINES
            and any("mis de cote" in l for l in fil(tid)),
            "et cette seconde fois dans la fenetre le met de cote",
            str(list(S.QUARANTAINES)))

        # ── L'AUTRE MACHINE DEGENERE AUSSI : reparee, mais pas retentee ──
        # Le modele du PC est toujours dans la fenetre : la reprise part sur
        # le NAS, qui rend lui aussi du charabia. Il est decharge — le
        # prochain appel le trouvera repare —, et l'appel s'arrete la.
        del appels[:]
        del decharges[:]
        neuf()
        tid = "banc-degen-deux"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        scenario[PC] = [""]
        scenario[NAS] = ["#" * 4 + "%" * 30]
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        dit([a[0] for a in appels] == [PC, NAS] and rendu == "####" + "%" * 30
            and [d_[0] for d_ in decharges] == [f"{NAS}/api/generate"],
            "quand la reprise ailleurs degenere aussi, ce second modele est "
            "decharge mais l'appel n'est PAS retente une deuxieme fois",
            f"essais={[a[0] for a in appels]}, dechargements={decharges}")

        # ── L'AUTRE MACHINE NE REPOND PAS : la reponse d'origine revient ──
        del appels[:]
        del decharges[:]
        neuf()
        tid = "banc-degen-muet"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}

        def muet(corps, url):
            raise RuntimeError("connexion refusee")

        scenario[PC] = [""]
        scenario[NAS] = [muet]
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        dit(rendu == "" and [a[0] for a in appels] == [PC, NAS]
            and not S.TACHES[tid].get("cerveau_lent")
            and any("rendue telle quelle" in l for l in fil(tid)),
            "si la machine de reprise ne repond pas, l'appel rend le \"\" "
            "d'origine — pas une exception que l'appelant n'attend pas",
            f"{rendu!r}, essais={[a[0] for a in appels]}")

        # ── LE CHARABIA : la meme reparation, et UNE seule reprise ──────
        S._DECHARGE_DEGENERE.clear()
        del appels[:]
        del decharges[:]
        neuf()
        tid = "banc-degen-charabia"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        scenario[PC] = ['{"intention": "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'
                        '@@@@@@@@@@@']
        scenario[NAS] = ["{}"]
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        dit(len(decharges) == 1 and [a[0] for a in appels] == [PC, PC],
            "une repetition du meme caractere est reconnue, dechargee, et "
            "retentee UNE fois — pas une troisieme",
            f"dechargements={len(decharges)}, essais={[a[0] for a in appels]}")
        dit(rendu.startswith('{"intention": "@@@@')
            and S.releve_degenerescences()["derniers"][0]["issue"]
            == "toujours degeneree",
            "toujours degeneree apres la reprise : la reponse est rendue "
            "TELLE QUELLE, sans exception, et la console le dit", repr(rendu[:30]))

        # ── UN MODELE QUI NE SE CHARGE PAS n'est pas un modele degenere ──
        S._DECHARGE_DEGENERE.clear()
        del appels[:]
        del decharges[:]
        neuf()
        tid = "banc-degen-erreur"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}

        def casse(corps, url):
            S._ecarter_modele(corps.get("model"), "error loading model", url)
            return ""

        scenario[PC] = [casse]
        rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        dit(rendu == "" and not decharges and [a[0] for a in appels] == [PC],
            "vide AVEC un champ « error » : l'ecart existant s'en charge, ni "
            "dechargement ni reprise", f"{rendu!r}, {decharges}, "
                                       f"{[a[0] for a in appels]}")
        S.MODELES_CASSES.clear()

        # ── UNE MACHINE PASSEE EN PAUSE : on ne lui decharge rien ───────
        S._DECHARGE_DEGENERE.clear()
        del appels[:]
        del decharges[:]
        neuf()
        tid = "banc-degen-pause"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}

        def puis_pause(corps, url):
            S.REGISTRE["pc"]["pause"] = 1.0
            return ""

        scenario[PC] = [puis_pause]
        scenario[NAS] = ["{}"]
        rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        dit(not decharges and rendu == "{}"
            and [a[0] for a in appels] == [PC, NAS],
            "une machine passee en pause n'est pas dechargee : la reprise va "
            "ailleurs", f"{decharges}, {rendu!r}, {[a[0] for a in appels]}")
        S.REGISTRE["pc"]["pause"] = None

        # ── SEULE, ET LE DECHARGEMENT NE PART PAS : rien ne change ──────
        # Un appelant qui lit "" comme « pas de reponse » doit le lire encore :
        # ni exception, ni detour de plusieurs minutes par l'agent.
        S._DECHARGE_DEGENERE.clear()
        S.REGISTRE["zima"]["pause"] = 1.0
        S._CERVEAUX[NAS]["quand"] = S.time.time()
        del appels[:]
        del decharges[:]
        refus["leve"] = True
        neuf()
        tid = "banc-degen-seul"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        scenario[PC] = [""]
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        dit(rendu == "" and [a[0] for a in appels] == [PC]
            and any("n'a pas abouti" in l for l in fil(tid)),
            "seule et sans dechargement possible, la machine rend son \"\" "
            "comme avant — sans exception, sans reprise au meme modele "
            "corrompu, et le fil le dit", f"{rendu!r}, {[a[0] for a in appels]}")
        refus["leve"] = False
        S.REGISTRE["zima"]["pause"] = None

        # ══ LE 5 NOVEMBRE : LE DECHARGEMENT NE REPARE PAS ════════════════
        # ── la repetition COUPEE par Ollama (500) est une degenerescence ──
        neuf()
        S._DECHARGE_DEGENERE.clear()
        del appels[:]
        del decharges[:]
        tid = "banc-quar-coupee"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        scenario[PC] = [coupe, "{}"]
        scenario[NAS] = ["{}"]
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        dit(rendu == "{}" and [a[0] for a in appels] == [PC, PC]
            and [d_[0] for d_ in decharges] == [f"{PC}/api/generate"]
            and S.releve_degenerescences()["derniers"][0]["forme"] == "coupee",
            "un 500 « token repeat limit » est une reponse degeneree : "
            "decharge, retente au meme endroit, et non une panne qui part a "
            "l'agent", f"{rendu!r}, essais={[a[0] for a in appels]}, "
                        f"dechargements={decharges}")
        dit(any("token repeat limit" in l for l in fil(tid)),
            "et le fil nomme la coupure", " | ".join(fil(tid))[-200:])

        # ── le cas mesure : decharge, et le meme « @ » au rechargement ──
        neuf()
        S._DECHARGE_DEGENERE.clear()
        del appels[:]
        del decharges[:]
        tid = "banc-quar-cinq"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        scenario[PC] = [coupe]
        scenario[NAS] = ["{}"]
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        modele_pc = appels[0][1] if appels else None
        q_ = S.QUARANTAINES.get((PC, modele_pc)) or {}
        dit(rendu == "" and [a[0] for a in appels] == [PC, PC]
            and S.releve_degenerescences()["derniers"][0]["issue"]
            == "toujours degeneree",
            "decharge puis toujours degenere : la reponse est rendue telle "
            "quelle, comme avant (une reprise par appel)",
            f"{rendu!r}, essais={[a[0] for a in appels]}")
        dit(q_ and abs(q_["fin"] - q_["debut"] - S.QUARANTAINE_DEGENERE) < 1
            and S.QUARANTAINE_DEGENERE == 900
            and any("mis de cote 15 min" in l for l in fil(tid)),
            "degenere encore APRES le dechargement : (adresse, modele) est mis "
            "de cote quinze minutes, et le fil le dit",
            f"{q_}, {' | '.join(fil(tid))[-160:]}")

        # ── pendant la mise de cote : directement a la machine suivante ──
        del appels[:]
        del decharges[:]
        tid = "banc-quar-suivante"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        # Le PC rend : s'il fallait attendre sa carte, l'appel attendrait la
        # fin du rendu. Il ne doit meme pas la regarder. Le NAS mesure « sur
        # processeur » passe dernier : le PC, occupe, reste ainsi en tete de
        # liste, et c'est bien la mise de cote qui le fait sauter.
        await S.verrou_noeud("pc").acquire()
        S._PLACEMENT[NAS]["part"] = 0.0
        try:
            dit([u for u, _ in S.cerveaux_utilisables()] == [PC, NAS],
                "(decor : le PC occupe reste en tete)",
                str(S.cerveaux_utilisables()))
            rendu = await asyncio.wait_for(
                S._appeler_llm("x", None, None, True, None, 0.1, tid), 5)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        finally:
            S.VERROUS_NOEUD["pc"].release()
            S._PLACEMENT[NAS]["part"] = 1.0
        dit(rendu == "{}" and [a[0] for a in appels] == [NAS] and not decharges,
            "mis de cote, le modele du PC n'est plus interroge : l'appel va "
            "droit a la machine suivante, sans attendre la carte du PC",
            f"{rendu!r}, essais={[a[0] for a in appels]}")
        dit(any("est mis de cote" in l for l in fil(tid)),
            "et le fil dit pourquoi le PC est saute", " | ".join(fil(tid))[-160:])

        # ── seul et mis de cote : le repli existant (agent, puis rien) ──
        del appels[:]
        tid = "banc-quar-seul"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        vrai_poser = S.poser_a
        poses = []

        async def faux_poser(ident, corps, tid=None, secondes=900, patience=None):
            poses.append(ident)
            return "", "carte occupee"

        S.poser_a = faux_poser
        S.REGISTRE["zima"]["pause"] = 1.0
        S._CERVEAUX[NAS]["quand"] = S.time.time()
        for x_ in ("pc", "zima"):
            S.ETAT_NOEUDS[x_]["llm"] = True
            S.ETAT_NOEUDS[x_]["llm_modeles"] = [modele_pc]
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        finally:
            S.poser_a = vrai_poser
            S.REGISTRE["zima"]["pause"] = None
        dit(not appels and "pc" not in poses and rendu.startswith("a leve"),
            "seul et mis de cote : ni l'Ollama du PC, ni son agent (le meme "
            "modele) — l'appel tombe sur le repli de l'appelant",
            f"{rendu!r}, essais={appels}, agents={poses}")

        # ── la duree passee : UN appel d'essai, pas une rafale ──────────
        # La fenetre de dix minutes a oublie les echecs, comme apres quinze.
        S._VUS_DEGENERE.clear()
        S._DECHARGE_DEGENERE.clear()
        S.QUARANTAINES[(PC, modele_pc)]["fin"] = S.time.time() - 1
        del appels[:]
        del decharges[:]
        tid = "banc-quar-essai"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        pendant = {}

        async def essai_lent(corps, url):
            # PENDANT que l'essai est en vol : le modele reste ferme a tout
            # autre appel, et personne d'autre ne peut prendre l'essai.
            pendant["ferme"] = S.en_quarantaine(PC, modele_pc)
            pendant["second"] = S._prendre_essai(PC, modele_pc)
            await asyncio.sleep(0)
            return '{"intention": "image"}'

        scenario[PC] = [essai_lent]
        scenario[NAS] = ["{}"]
        try:
            rendu = await asyncio.wait_for(
                S._appeler_llm("x", None, None, True, None, 0.1, tid), 5)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        dit(rendu == '{"intention": "image"}' and [a[0] for a in appels] == [PC]
            and pendant.get("ferme") is True and pendant.get("second") is None,
            "la duree passee, UN appel d'essai part sur le PC ; pendant qu'il "
            "est en vol, le modele reste ferme et l'essai ne se prend pas deux "
            "fois", f"{rendu!r}, pendant={pendant}")
        dit((PC, modele_pc) not in S.QUARANTAINES
            and any("remis en service" in l for l in fil(tid)),
            "l'essai repond : le modele est remis en service, et le fil le dit",
            str(list(S.QUARANTAINES)))

        # ── l'essai degenere : remis de cote, sans reprise au meme endroit ──
        neuf()
        S._DECHARGE_DEGENERE.clear()
        S.QUARANTAINES[(PC, modele_pc)] = {
            "debut": S.time.time() - 901, "fin": S.time.time() - 1,
            "machine": "PC (RTX 2080 Ti)", "modele": modele_pc,
            "essai": False, "fois": 1}
        del appels[:]
        del decharges[:]
        tid = "banc-quar-rechute"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        scenario[PC] = [""]
        scenario[NAS] = ["{}"]
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        q_ = S.QUARANTAINES.get((PC, modele_pc)) or {}
        dit(rendu == "{}" and [a[0] for a in appels] == [PC, NAS],
            "l'essai degenere : PAS de reprise au meme endroit, la machine "
            "suivante repond", f"{rendu!r}, essais={[a[0] for a in appels]}")
        dit(q_.get("fois") == 2 and q_.get("fin", 0) > S.time.time() + 800
            and not q_.get("essai"),
            "et le modele est remis de cote pour une nouvelle duree, sur un "
            "seul echec", str(q_))

        # ── l'essai interrompu par une panne : rendu, pas perdu ─────────
        q_["fin"] = S.time.time() - 1
        del appels[:]
        tid = "banc-quar-panne"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}

        def panne(corps, url):
            raise RuntimeError("connexion coupee")

        scenario[PC] = [panne, "{}"]
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        dit(rendu == "{}" and [a[0] for a in appels] == [PC, NAS]
            and not S.en_quarantaine(PC, modele_pc)
            and not (S.QUARANTAINES.get((PC, modele_pc)) or {}).get("essai"),
            "un essai qui tombe en panne est rendu : le prochain appel "
            "reessaiera, le modele ne reste pas de cote pour toujours",
            f"{rendu!r}, {S.QUARANTAINES.get((PC, modele_pc))}")
        del appels[:]
        rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        dit(rendu == "{}" and [a[0] for a in appels] == [PC]
            and (PC, modele_pc) not in S.QUARANTAINES,
            "et le suivant est bien l'essai, qui le remet en service",
            f"{rendu!r}, essais={[a[0] for a in appels]}")

        # ── une machine mise de cote n'est pas un repli ─────────────────
        neuf()
        S._DECHARGE_DEGENERE.clear()
        S._DECHARGE_DEGENERE[(PC, modele_pc)] = S.time.time()
        # Le NAS ne prend pas le modele du PC : celui-ci deborde de sa carte.
        modele_nas = (S.corps_ici({"model": modele_pc, "prompt": "x"}, NAS)
                      or {}).get("model")
        S.QUARANTAINES[(NAS, modele_nas)] = {
            "debut": S.time.time(), "fin": S.time.time() + 900,
            "machine": "NAS ZimaOS", "modele": modele_nas, "essai": False,
            "fois": 1}
        del appels[:]
        del decharges[:]
        tid = "banc-quar-repli"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        scenario[PC] = [""]
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        dit(rendu == "" and [a[0] for a in appels] == [PC]
            and S.releve_degenerescences()["derniers"][0]["issue"]
            == "pas retentee"
            and not any("reessaie ailleurs" in l for l in fil(tid)),
            "la seule autre machine est mise de cote : on n'annonce pas une "
            "reprise ailleurs qui n'aura pas lieu",
            f"{rendu!r}, {S.releve_degenerescences()['derniers'][0]['issue']}")

        # ── PAR L'AGENT : compter, mettre de cote, demander a la suivante ──
        neuf()
        poses = []
        repond = {"pc": "", "zima": "{}"}

        async def poser_agent(ident, corps, tid=None, secondes=900,
                              patience=None):
            poses.append(ident)
            return repond[ident], ""

        S.poser_a = poser_agent
        tid = "banc-quar-agent"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        corps_ = {"model": modele_pc, "prompt": "x"}
        try:
            r1 = await S.demander_a_un_noeud(corps_, tid)
            r2 = await S.demander_a_un_noeud(corps_, tid)
            p12 = list(poses)
            del poses[:]
            r3 = await S.demander_a_un_noeud(corps_, tid)
            p3 = list(poses)
            de_cote = (PC, modele_pc) in S.QUARANTAINES
            # Le meme mal en charabia : il n'est plus rendu quand la suivante
            # repond.
            neuf()
            repond["pc"] = "@" * 40
            del poses[:]
            r4 = await S.demander_a_un_noeud(corps_, tid)
            # Mis de cote par la voie DIRECTE : l'agent du PC n'est pas
            # interroge non plus — c'est le meme Ollama.
            neuf()
            S.QUARANTAINES[(PC, modele_pc)] = {
                "debut": S.time.time(), "fin": S.time.time() + 900,
                "machine": "PC (RTX 2080 Ti)", "modele": modele_pc,
                "essai": False, "fois": 1}
            del poses[:]
            r5 = await S.demander_a_un_noeud(corps_, tid)
            p5 = list(poses)
        finally:
            S.poser_a = vrai_poser
        dit(r1 == r2 == r3 == "{}" and p12 == ["pc", "zima", "pc", "zima"]
            and p3 == ["zima"] and de_cote,
            "par l'agent, deux reponses vides du PC dans la fenetre le mettent "
            "de cote : la troisieme question va droit au NAS",
            f"{r1!r} {r2!r} {r3!r}, {p12} puis {p3}")
        dit(r4 == "{}",
            "le charabia rendu par un agent n'est plus pris pour une reponse "
            "quand la machine suivante repond", repr(r4))
        dit(r5 == "{}" and p5 == ["zima"],
            "et un modele mis de cote en direct ne l'est pas moins par l'agent "
            "de sa machine", f"{r5!r}, {p5}")
        for x_ in ("pc", "zima"):
            S.ETAT_NOEUDS[x_].pop("llm", None)
            S.ETAT_NOEUDS[x_].pop("llm_modeles", None)

        # ── CE QUE REND VRAIMENT OLLAMA 0.40.14, lu par le VRAI appel ────
        # Les deux formes du journal du PC, et les deux d'un modele qui ne se
        # charge pas, qui doivent rester ce qu'elles etaient.
        http = {}

        class ReponseHTTP:
            def __init__(self, statut, corps_):
                self.status = statut
                self._corps = corps_

            async def text(self):
                return (self._corps if isinstance(self._corps, str)
                        else S.json.dumps(self._corps))

            async def json(self):
                return (S.json.loads(self._corps)
                        if isinstance(self._corps, str) else self._corps)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

        class SessionHTTP(FausseSession):
            def post(self, url, json=None):
                if (json or {}).get("keep_alive") == 0 and not json.get("prompt"):
                    decharges.append((url, json.get("model"), 0))
                    return ReponseHTTP(200, {})
                file_ = http[url.rsplit("/api/", 1)[0]]
                return ReponseHTTP(*(file_.pop(0) if len(file_) > 1 else file_[0]))

        S.aiohttp.ClientSession = SessionHTTP
        corps_ = {"model": "qwen2.5vl:7b", "prompt": "x"}

        async def lire(*reponses):
            http[PC] = list(reponses)
            S.MODELES_CASSES.clear()
            try:
                return await vrai_local(dict(corps_), PC, 5)
            except Exception as e:
                return e

        r_ = await lire((500, '{"error":"prediction aborted, token repeat '
                              'limit reached"}'))
        dit(isinstance(r_, S.ReponseDegeneree) and isinstance(r_, RuntimeError)
            and not S.MODELES_CASSES,
            "500 « token repeat limit reached » : ReponseDegeneree (une "
            "RuntimeError pour qui ne la connait pas), et le modele n'est pas "
            "ecarte", f"{type(r_).__name__}, {S.MODELES_CASSES}")
        r_ = await lire((200, {"model": "", "response": "", "done": False}))
        dit(r_ == "" and not S.MODELES_CASSES,
            "200 {model: \"\", response: \"\", done: false} : un vide, que la "
            "boucle traite en degenerescence — pas un modele casse",
            f"{r_!r}, {S.MODELES_CASSES}")
        r_ = await lire((200, {"response": "", "error": "token repeat limit "
                                                         "reached"}))
        dit(isinstance(r_, S.ReponseDegeneree) and not S.MODELES_CASSES,
            "la meme coupure dite en 200 avec « error » n'ecarte pas le modele",
            f"{type(r_).__name__}, {S.MODELES_CASSES}")
        r_ = await lire((500, '{"error":"error loading model: cuda out of '
                              'memory"}'))
        dit(isinstance(r_, RuntimeError)
            and not isinstance(r_, S.ReponseDegeneree)
            and (PC, "qwen2.5vl:7b") in S.MODELES_CASSES,
            "un 500 de chargement reste un modele ecarte, et une panne",
            f"{type(r_).__name__}, {S.MODELES_CASSES}")
        r_ = await lire((200, {"response": "", "error": "error loading model"}))
        dit(r_ == "" and (PC, "qwen2.5vl:7b") in S.MODELES_CASSES,
            "un 200 avec « error » de chargement aussi",
            f"{r_!r}, {S.MODELES_CASSES}")
        S.MODELES_CASSES.clear()

        # De bout en bout, par le vrai appel : le 200 « done: false » est
        # decharge et retente comme le vide qu'il est.
        neuf()
        S._DECHARGE_DEGENERE.clear()
        del decharges[:]
        S._ollama_local = vrai_local
        tid = "banc-quar-fini"
        tids.append(tid)
        S.TACHES[tid] = {"etapes": [], "etat": "en cours"}
        http[PC] = [(200, {"model": "", "response": "", "done": False}),
                    (200, {"response": "{}", "done": True})]
        try:
            rendu = await S._appeler_llm("x", None, None, True, None, 0.1, tid)
        except Exception as e:
            rendu = f"a leve {type(e).__name__}"
        finally:
            S._ollama_local = faux_local
            S.aiohttp.ClientSession = FausseSession
        dit(rendu == "{}" and [d_[0] for d_ in decharges]
            == [f"{PC}/api/generate"]
            and S.releve_degenerescences()["derniers"][0]["issue"] == "reparee",
            "par le vrai appel, « done: false » sans reponse est decharge puis "
            "retente, et la reprise repond", f"{rendu!r}, {decharges}")

        # ── CE QUI N'EST PAS DEGENERE ───────────────────────────────────
        dit(all(not S.forme_degeneree(t) for t in (
                "Prix : 10000 euros...", "refrain\n----------------\ncouplet",
                '{"intention": "image", "prompt": "a cat"}',
                "========================")),
            "« 10000 », « ... » ou une ligne de tirets restent du texte")
        dit(S.forme_degeneree("  \n ") == "vide"
            and S.forme_degeneree("a photo.addTab{@@@@@@@@@@@@@@@@@@")
            == "repetition",
            "les blancs seuls sont du vide, et « {@@@@… » du charabia")
        dit(not S.latin("a photo of a cat @@@@"),
            "la traduction garde sa regle a quatre caracteres")

        # ── BORNE EN MEMOIRE ────────────────────────────────────────────
        S._DECHARGE_DEGENERE.clear()
        S._DECHARGE_DEGENERE[("http://vieux:11434", "x")] = S.time.time() - 9999
        # Des adresses CONNUES du decor : une adresse neuve ferait rafraichir
        # son inventaire par cerveau(), donc partir sur le reseau.
        for i in range(40):
            await S.reparer_degenere((PC, NAS)[i % 2], f"m{i}", "vide",
                                     None, f"m{i}")
        dit(len(S.DEGENERESCENCES) <= 20
            and len(S.releve_degenerescences()["derniers"]) <= 20
            and S.releve_degenerescences()["total"] >= 40,
            "la trace est bornee : vingt dernieres, et un compte",
            f"{len(S.DEGENERESCENCES)} gardees, total "
            f"{S.releve_degenerescences()['total']}")
        dit(("http://vieux:11434", "x") not in S._DECHARGE_DEGENERE,
            "et la fenetre oublie ce qui en est sorti")
        neuf()
        S._VUS_DEGENERE[("http://vieux:11434", "x")] = [S.time.time() - 9999]
        for i in range(40):
            for _ in range(S.SEUIL_QUARANTAINE + 3):
                S._compter_degenere((PC, NAS)[i % 2], f"q{i}", f"m{i}", None)
        dit(S.QUARANTAINES_MAX == 20 and len(S.QUARANTAINES) == 20
            and len(S.releve_degenerescences().get("quarantaines") or "") <= 20
            and ("http://vieux:11434", "x") not in S._VUS_DEGENERE
            and all(len(v) <= S.SEUIL_QUARANTAINE
                    for v in S._VUS_DEGENERE.values()),
            "les mises de cote sont bornees (vingt), et le compte des echecs "
            "oublie ce qui est sorti de la fenetre",
            f"{len(S.QUARANTAINES)} de cote, "
            f"{max(len(v) for v in S._VUS_DEGENERE.values())} instants au plus")
        neuf()
    finally:
        S._ollama_local = vrai_local
        S.aiohttp.ClientSession = vraie_session
        S._PLACEMENT.clear()
        for t_ in tids:
            S.TACHES.pop(t_, None)

    # ── LA CONSOLE LE MONTRE ────────────────────────────────────────────
    S.QUARANTAINES.clear()
    S._VUS_DEGENERE.clear()
    for _ in range(S.SEUIL_QUARANTAINE):
        S._compter_degenere(PC, "qwen2.5vl:7b", "PC (RTX 2080 Ti)", None)
    vrai_ok = S.admin_ok
    S.admin_ok = lambda req: True
    try:
        rep = await S.api_admin_noeuds(None)
        d = S.json.loads(rep.text)
    except Exception as e:
        d = {"erreur": f"{type(e).__name__} : {e}"}
    finally:
        S.admin_ok = vrai_ok
    deg = d.get("modeles_degeneres") or {}
    dit(deg.get("total", 0) >= 1 and deg.get("derniers")
        and {"machine", "modele", "forme", "issue", "heure"}
        <= set(deg["derniers"][0]),
        "/api/admin/noeuds porte le releve des reponses degenerees",
        str(d.get("erreur") or (deg.get("derniers") or [None])[0]))
    q_ = (deg.get("quarantaines") or [{}])[0]
    dit(q_.get("modele") == "qwen2.5vl:7b"
        and q_.get("machine") == "PC (RTX 2080 Ti)"
        and q_.get("fin") and q_.get("debut")
        and 890 <= (q_.get("reste") or 0) <= 900
        and deg.get("quarantaine") == S.QUARANTAINE_DEGENERE,
        "et les mises de cote en cours, avec leur fin", str(q_))
    S.QUARANTAINES.clear()
    S._VUS_DEGENERE.clear()
    try:
        page = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "web", "admin.html"), encoding="utf-8").read()
    except OSError:
        page = ""
    dit('id="langueDegenere"' in page and "d.modeles_degeneres" in page
        and "x.issue" in page,
        "et la console d'administration l'affiche",
        "web/admin.html absent" if not page else "")
    dit("deg.quarantaines" in page and "${ech(q.fin)}" in page
        and "${ech(q.machine)}" in page and "!deCote.length" in page,
        "la console montre aussi ce qui est mis de cote, et jusqu'a quand",
        "web/admin.html absent" if not page else "")
    poser()

asyncio.run(main())
print(f"\n  {len([o for o in ok if o])} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
