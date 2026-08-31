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
    """Un parc de deux machines, plus une adresse qui ne repond pas."""
    S.REGISTRE.clear()
    S.REGISTRE["pc"] = {"id": "pc", "titre": "PC (RTX 2080 Ti)", "agent": True,
                        "jeton": "x", "pause": 1.0 if pause_pc else None}
    S.REGISTRE["zima"] = {"id": "zima", "titre": "NAS ZimaOS", "agent": True,
                          "jeton": "y", "pause": None}
    S.ETAT_NOEUDS.clear()
    S.ETAT_NOEUDS["pc"] = {"repond": True, "vram": 11.0, "vu": S.time.time(),
                           "ip": "10.0.0.1"}
    S.ETAT_NOEUDS["zima"] = {"repond": True, "vram": 5.9, "vu": S.time.time(),
                             "ip": "10.0.0.2"}
    # Le cache des cerveaux, pose a la main : rien n'est joignable ici.
    S._CERVEAUX.clear()
    S._CERVEAUX[PC] = {"quand": S.time.time(), "noeud": "pc",
                       "modeles": [{"name": "qwen2.5vl:7b", "size": 6_000_000_000,
                                    "capabilities": ["completion", "vision"]},
                                   {"name": "gemma4:26b", "size": 18_600_000_000,
                                    "capabilities": ["completion"]}]}
    S._CERVEAUX[NAS] = {"quand": S.time.time(), "noeud": "zima",
                        "modeles": [{"name": "gemma3:4b", "size": 3_340_000_000,
                                     "capabilities": ["completion", "vision"]},
                                    {"name": "qwen3:4b", "size": 2_500_000_000,
                                     "capabilities": ["completion", "thinking"]}]}
    S._CERVEAUX[MORT] = {"quand": S.time.time(), "noeud": None, "modeles": []}
    S.VERROUS_NOEUD.clear()


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

    # ── le modele, par adresse ──────────────────────────────────────────
    poser()
    corps = {"model": S.MODELE_POUR_ECRIRE, "prompt": "x"}
    dit(S.corps_ici(corps, NAS)["model"] == "gemma3:4b",
        "l'intention d'ecriture prend le plus gros DU NAS",
        S.corps_ici(corps, NAS)["model"])
    dit(S.corps_ici(corps, PC)["model"] == "gemma4:26b",
        "et le plus gros DU PC", S.corps_ici(corps, PC)["model"])

    corps = {"model": "qwen2.5vl:7b", "prompt": "x"}
    dit(S.corps_ici(corps, PC) is corps, "un modele present passe tel quel")
    remplace = S.corps_ici(corps, NAS)
    dit(remplace["model"] != "qwen2.5vl:7b",
        "un modele absent est remplace", remplace["model"])

    # Un reglage global sur un parc qui ne l'est pas : STUDIO_LLM_ECRITURE
    # nomme un modele que le NAS a et que le PC n'a pas. Le PC ne doit pas en
    # devenir muet.
    S.MODELE_ECRITURE = "gemma3:4b"
    dit(S.modele_ecriture_de(NAS) == "gemma3:4b", "le reglage est suivi la ou il existe")
    dit(S.modele_ecriture_de(PC) == "gemma4:26b",
        "et ignore la ou il n'existe pas", S.modele_ecriture_de(PC))
    S.MODELE_ECRITURE = ""

    corps = {"model": "qwen2.5vl:7b", "prompt": "x", "images": ["…"]}
    dit(S.corps_ici(corps, PC) is corps,
        "une image reste sur le meilleur voyant quand c'est deja lui")
    # Le cas qui a coute une mesure : gemma3:4b DECLARE voir, et aiguille mal.
    # Une image jointe doit donc passer au plus gros voyant du NAS, pas rester
    # sur le modele d'aiguillage sous pretexte qu'il a la capacite.
    corps_g = {"model": "gemma3:4b", "prompt": "x", "images": ["…"]}
    S._CERVEAUX[NAS]["modeles"].append({"name": "qwen2.5vl:7b",
                                        "size": 5_970_000_000,
                                        "capabilities": ["completion", "vision"]})
    bascule_g = S.corps_ici(corps_g, NAS)
    poser()
    dit(bascule_g is not None and bascule_g["model"] == "qwen2.5vl:7b",
        "un modele voyant mais petit cede au plus gros voyant",
        str(bascule_g and bascule_g["model"]))
    # Le NAS n'a pas qwen2.5vl mais il a gemma3:4b, qui voit : on bascule sur
    # lui plutot que d'ecarter la machine. La regle n'est pas « ce modele-la »,
    # elle est « un modele qui voit, ou rien ».
    ailleurs = S.corps_ici(corps, NAS)
    dit(ailleurs is not None and ailleurs["model"] == "gemma3:4b",
        "une image trouve un modele voyant sur l'autre machine",
        str(ailleurs and ailleurs["model"]))

    # Installe ne veut pas dire capable : gemma4:26b est bien la sur le PC, et
    # il ne sait pas voir. Un modele de texte a qui l'on envoie une image ne
    # refuse pas, il decrit ce qu'il imagine.
    # Le PC porte gemma4:26b (aveugle) et qwen2.5vl:7b (voyant) : une image
    # demandee au premier doit basculer sur le second, pas echouer.
    corps = {"model": "gemma4:26b", "prompt": "x", "images": ["…"]}
    bascule = S.corps_ici(corps, PC)
    dit(bascule is not None and bascule["model"] == "qwen2.5vl:7b",
        "un modele aveugle cede la place a un modele qui voit",
        str(bascule and bascule["model"]))
    # Et sur une machine ou AUCUN modele ne voit, on n'envoie rien.
    S._CERVEAUX[NAS]["modeles"] = [{"name": "qwen3:4b", "size": 2_500_000_000,
                                    "capabilities": ["completion"]}]
    dit(S.corps_ici(corps, NAS) is None,
        "aucun modele voyant : l'adresse est ecartee, jamais substituee")
    poser()
    corps = {"model": "gemma3:4b", "prompt": "x", "images": ["…"]}
    dit(S.corps_ici(corps, NAS) is corps, "un modele qui sait voir la reçoit")

asyncio.run(main())
print(f"\n  {len([o for o in ok if o])} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
