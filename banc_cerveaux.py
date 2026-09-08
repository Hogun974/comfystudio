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
         "capabilities": ["vision", "completion"]}]}
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
    poser()
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
    finally:
        S._ollama_local = vrai_local
        S.TACHES.pop("banc-lent", None)
        S.TACHES.pop("banc-autre", None)
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

asyncio.run(main())
print(f"\n  {len([o for o in ok if o])} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
