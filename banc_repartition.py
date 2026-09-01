# -*- coding: utf-8 -*-
"""Quelle machine recoit le travail, et le studio sans carte s'abstient-il ?

    python banc_repartition.py

Le studio du reseau tourne dans un conteneur sur une machine SANS GPU : il ne
fait que repartir le travail sur les noeuds. Trois endroits du code supposaient
pourtant qu'il pouvait calculer, et aucun ne posait la question.

Le defaut, signale par l'utilisateur — « il m'affiche souvent moteur local, le
studio n'en a pas, uniquement les noeuds, et du coup attend dans le vide » :

  - _vram_utile accordait la tolerance RAM a une machine SANS carte. La
    tolerance dit de combien on peut DEPASSER la carte ; sans carte, il n'y a
    rien a depasser. Un studio a 16 Go de RAM se presentait donc comme une
    carte de 2 Go, et a 64 Go comme une carte de 5 Go.
  - noeuds_pour dispense le studio du « le modele est-il la ? », parce qu'il
    peut le telecharger sur son disque. Sans carte, cette dispense le faisait
    retenir pour des moteurs qu'il n'a pas et ne saurait pas faire tourner.
  - choisir_noeud preferait le noeud local SANS CONDITION. Il gagnait donc
    contre la 2080 Ti, et le rendu partait sur une machine incapable.

Les trois ensemble donnent exactement le symptome decrit. Aucun banc ne
regardait la repartition ; celui-ci le fait.
"""
import os
import sys
import tempfile

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_repartition_")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# Le moteur le plus leger du catalogue : c'est celui pour lequel une machine
# sans carte avait le plus de chances de passer.
CLE = min(S.CATALOGUE, key=lambda c: S.CATALOGUE[c].get("vram", 0) or 99)
BESOIN = S.CATALOGUE[CLE].get("vram", 0)


def poser(vram_studio=0.0, ram_studio=64.0, vram_pc=11.0, vram_zima=5.9):
    """Le parc reel : un studio en conteneur, et deux machines a agent."""
    S.NOEUDS[:] = [{"id": "local", "url": "http://127.0.0.1:8188",
                    "titre": "cette machine", "local": True}]
    S.REGISTRE.clear()
    S.REGISTRE["pc"] = {"id": "pc", "titre": "PC (RTX 2080 Ti)", "agent": True,
                        "jeton": "x", "pause": None}
    S.REGISTRE["zima"] = {"id": "zima", "titre": "NAS ZimaOS (GTX 1060)",
                          "agent": True, "jeton": "y", "pause": None}
    S.ETAT_NOEUDS.clear()
    S.ETAT_NOEUDS["local"] = {"repond": True, "vram": vram_studio,
                              "ram": ram_studio, "vu": S.time.time()}
    S.ETAT_NOEUDS["pc"] = {"repond": True, "vram": vram_pc, "ram": 63.8,
                           "vu": S.time.time()}
    S.ETAT_NOEUDS["zima"] = {"repond": True, "vram": vram_zima, "ram": 23.4,
                             "vu": S.time.time()}
    S.VERROUS_NOEUD.clear()
    S.EN_VOL.clear()
    S.TACHES.clear()
    # Le moteur present PARTOUT : ce qu'on mesure ici est le choix, pas
    # l'inventaire. La dispense du local est eprouvee a part, plus bas.
    S.manquants = lambda cle, ident=None: []


print(f"\n  moteur du banc : {CLE} ({BESOIN} Go)\n")

# ── un studio SANS carte ne se choisit pas lui-meme ─────────────────────
poser(vram_studio=0.0, ram_studio=64.0)
dit(not S.carte_locale(), "sans VRAM, le studio sait qu'il n'a pas de carte")
dit(S._vram_utile("local") == 0.0,
    "et la tolerance RAM ne lui invente pas une carte de 5 Go",
    f"{S._vram_utile('local')} Go")
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] != "local",
    "le travail part sur une machine a carte, pas sur le studio",
    str(choisi and choisi["id"]))
dit("local" not in [x["id"] for x in S.noeuds_pour(CLE)],
    "il ne figure meme pas parmi les machines capables")

# ── et la dispense d'inventaire ne le sauve pas non plus ────────────────
# Sans carte, « il peut telecharger le modele sur son disque » ne veut plus
# rien dire : il ne le fera tourner nulle part.
S.manquants = lambda cle, ident=None: ["un_fichier.safetensors"] if ident != "pc" else []
dit("local" not in [x["id"] for x in S.noeuds_pour(CLE)],
    "un moteur absent partout ne le fait pas revenir dans la liste",
    ", ".join(x["id"] for x in S.noeuds_pour(CLE)) or "aucune")
S.manquants = lambda cle, ident=None: []

# ── chaque garde tient SEULE ────────────────────────────────────────────
# Les trois corrections se recouvrent : la premiere suffit a ecarter le studio,
# donc retirer l'une des deux autres ne changeait rien et mes deux cas ne
# mesuraient RIEN. C'est banc_mutations.py qui me l'a dit, dix minutes apres
# que j'aie ecrit ce fichier. On eprouve donc chaque garde a la place des deux
# autres : si la tolerance RAM revenait un jour — c'est un calcul, il bougera —
# les deux suivantes doivent encore tenir.
_vrai_vram = S._vram_utile
S._vram_utile = lambda i: ((S.ETAT_NOEUDS.get(i) or {}).get("vram") or 0)     + S.tolerance_ram((S.ETAT_NOEUDS.get(i) or {}).get("ram") or 0)

# DES CARTES TROP PETITES POUR CE MOTEUR, exprès : choisir_noeud garde d'abord
# les machines ou le moteur tient VRAIMENT (tient_vraiment lit la carte nue), et
# le studio sans carte en sort deja par la. Ce n'est qu'a partir du moment ou
# TOUT LE MONDE deborde qu'il revient dans le choix — et c'est la que la
# deuxieme garde travaille. Avec le parc ordinaire, mon cas ne mesurait rien.
poser(vram_studio=0.0, ram_studio=64.0, vram_pc=0.5, vram_zima=0.4)
dit(S._vram_utile("local") == 5.0,
    "le defaut d'origine remis : le studio se croit une carte de 5 Go",
    f"{S._vram_utile('local')} Go")
dit("local" in [x["id"] for x in S.noeuds_pour(CLE)],
    "il repasse donc la premiere barriere")
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] != "local",
    "mais choisir_noeud ne le prefere plus : la deuxieme garde tient seule",
    str(choisi and choisi["id"]))

S.manquants = lambda cle, ident=None: ["un_fichier.safetensors"]
dit("local" not in [x["id"] for x in S.noeuds_pour(CLE)],
    "et la dispense d'inventaire ne s'applique plus : la troisieme aussi",
    ", ".join(x["id"] for x in S.noeuds_pour(CLE)) or "aucune")
S._vram_utile = _vrai_vram

# ── un studio AVEC carte garde sa preference ────────────────────────────
# La correction ne doit pas retirer au studio qui a un GPU ce qui faisait son
# interet : pas de reseau a traverser, a egalite de charge il passe devant.
poser(vram_studio=24.0, ram_studio=64.0)
dit(S.carte_locale(), "avec une carte, le studio se reconnait")
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] == "local",
    "et il reprend la main a egalite de charge", str(choisi and choisi["id"]))

# ── la tolerance RAM reste entiere pour une VRAIE carte ─────────────────
poser(vram_studio=0.0)
# Les paliers sont 64 / 32 / 16 Go de RAM pour 5 / 3,5 / 2 Go de tolerance.
# 63,8 Go tombent donc dans le palier des 32, pas dans celui des 64 : c'est mon
# calcul qui etait faux, pas le code, et le banc l'a dit avant moi.
dit(S._vram_utile("pc") == 14.5, "11 Go de carte et 63,8 de RAM font 14,5 utiles",
    f"{S._vram_utile('pc')} Go")
dit(S._vram_utile("zima") == 7.9, "5,9 Go et 23,4 de RAM en font 7,9",
    f"{S._vram_utile('zima')} Go")

# ── la charge passe avant la taille ─────────────────────────────────────
poser(vram_studio=0.0)
# charge_noeud compte les taches EN VOL qui VISENT la machine, et lit le noeud
# sur TACHES et non sur EN_VOL : c'est l'intention, posee bien avant le verrou.
S.EN_VOL["t1"] = {}
S.TACHES["t1"] = {"noeud": "pc"}
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] == "zima",
    "une carte libre passe devant une plus grosse deja visee",
    str(choisi and choisi["id"]))

# ── et le mot dit la verite dans les deux cas ───────────────────────────
poser(vram_studio=0.0)
dit(S._mot_local() == "un modele du parc",
    "sans carte, on ne parle plus de « modele local »", S._mot_local())
poser(vram_studio=24.0)
dit(S._mot_local() == "le modele local",
    "avec une carte, le mot reste juste", S._mot_local())

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
