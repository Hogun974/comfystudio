# -*- coding: utf-8 -*-
"""Le studio choisit-il le bon Ollama ?

    python banc_cerveaux.py

Trois regles, ce sont celles de l'utilisateur :
  - une machine EN PAUSE ne pense pas ;
  - une carte LIBRE passe devant une carte occupee ;
  - a egalite, la PLUS PETITE carte.

Et une quatrieme, qui est une regle de surete : une image a lire ne part JAMAIS
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
    dit([u for u, _ in l] == [NAS, PC],
        "a cartes libres, la PLUS PETITE d'abord", str([u for u, _ in l]))
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
    dit([u for u, _ in l] == [NAS, PC], "relachee, elle reprend la tete",
        str([u for u, _ in l]))

    # ── une image inverse l'ordre des cartes ────────────────────────────
    # Lire une image est la seule tache ou la taille decide vraiment : mesure
    # du 31 aout, 19 s sur la 2080 Ti et toujours rien apres 900 s sur la
    # GTX 1060, ou le modele de vision deborde.
    poser()
    l = S.cerveaux_utilisables()
    dit([u for u, _ in l] == [NAS, PC], "pour du texte, la plus PETITE d'abord",
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
