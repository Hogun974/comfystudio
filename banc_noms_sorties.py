"""Deux rendus ne portent-ils jamais le meme nom de fichier ?

    python banc_noms_sorties.py

LE DEFAUT, VU LE 5 NOVEMBRE 2026. Le prefixe des sorties etait
« <compte>/<type>/<date>_<moteur> » : tous les rendus d'une journee le
partageaient, et c'est ComfyUI qui les departageait par son compteur
« _00001_ ». Or ce compteur ne retient rien — il repart du plus grand numero
ENCORE PRESENT sur le disque. Apres le menage des fichiers d'essai, le rendu
suivant a repris « ..._00007_.png », un nom que trois conversations
designaient deja : elles se sont mises a montrer une image qui n'etait pas la
leur, sans aucune erreur.

LE REMEDE : l'identifiant de la tache dans le prefixe. Un nom n'est plus
partage que par les fichiers d'une meme tache — et une tache qui se rejoue
apres un redemarrage les VEUT au meme endroit.

Ce banc lit le prefixe dans le graphe REELLEMENT soumis a la carte, pas dans
prefixe_sortie() : c'est executer() qui choisit ce qu'il lui passe, et c'est
la qu'etait le defaut.
"""
import asyncio
import copy
import os
import sys
import tempfile
import time
import uuid

ICI = os.path.dirname(os.path.abspath(__file__))
os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_noms_sorties_")
os.environ["STUDIO_AUTH"] = "libre"
sys.path.insert(0, ICI)
import serveur as S  # noqa: E402

ok, rate = [], []
GRAPHES = []        # [(tid, graphe)] : ce que la carte a VRAIMENT recu
PID = "u" * 32
CLE = next(c for c in S.CATALOGUE if S.CATALOGUE[c].get("type") == "image")


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# La vraie signature de soumettre_robuste : un faux qui ne la suit pas meurt
# sur un TypeError au lieu de mesurer (banc_refaire.py l'a appris deux fois).
async def faux_soumettre(g, tid, ident, cle, patience=1800, viser="petite",
                         taille=None):
    GRAPHES.append((tid, copy.deepcopy(g)))
    return ([{"filename": f"{tid[:8]}_00001_.png", "subfolder": "u/image",
              "type": "output", "noeud": ident}], 1.0)


def poser(machines=("pc",)):
    """Un parc d'une ou deux machines qui tiennent le moteur du banc."""
    for d in (S.REGISTRE, S.ETAT_NOEUDS, S.MODELES_NOEUD, S.VERROUS_NOEUD,
              S.EN_FILE, S.EN_VOL, S.TACHES, S.CONVERSATIONS, S.NUAGE):
        d.clear()
    del S.ATTENTE[:]
    del GRAPHES[:]
    dossiers = {}
    for sous, nom, _repo, _distant in S.CATALOGUE[CLE]["fichiers"]:
        dossiers.setdefault(sous, set()).add(nom)
    for ident in machines:
        S.REGISTRE[ident] = {"id": ident, "titre": ident, "agent": True,
                             "jeton": ident}
        S.ETAT_NOEUDS[ident] = {"repond": True, "vram": 24.0, "ram": 64.0,
                                "vu": time.time()}
        S.MODELES_NOEUD[ident] = {"quand": time.time(), "dossiers": dossiers}
    conv = S._vide(proprietaire=PID)
    conv["id"] = "c1"
    S.CONVERSATIONS["c1"] = conv
    return conv


def prefixes(g):
    """Tous les « filename_prefix » d'un graphe, dans l'ordre des noeuds."""
    return [n["inputs"]["filename_prefix"] for n in g.values()
            if isinstance(n, dict) and "filename_prefix" in (n.get("inputs") or {})]


async def rendre(conv, tid=None):
    tid = tid or uuid.uuid4().hex
    S.TACHES[tid] = {"etapes": [], "etat": "en cours", "debut": time.time(),
                     "demande": "un renard roux dans la neige", "conv": conv["id"]}
    plan = {"intention": "image", "modele": CLE, "prompt": "a red fox in the snow",
            "largeur": 1024, "hauteur": 1024, "parametres": {}, "raison": "banc"}
    await S.executer(tid, "un renard roux dans la neige", conv,
                     plan_impose=plan, modele_choisi=True)
    return tid


async def main():
    S.soumettre_robuste = faux_soumettre
    print(f"\n  moteur du banc : {CLE}\n")

    conv = poser()
    t1 = await rendre(conv)
    t2 = await rendre(conv)
    g1 = dict(GRAPHES).get(t1) or {}
    g2 = dict(GRAPHES).get(t2) or {}
    p1, p2 = prefixes(g1), prefixes(g2)
    # LE TEMOIN D'ABORD : deux graphes soumis, chacun avec son prefixe. Sans
    # lui, « les prefixes different » serait vrai de deux listes vides.
    dit(len(GRAPHES) == 2 and len(p1) == 1 and len(p2) == 1,
        "temoin : deux rendus, deux graphes soumis, un prefixe chacun",
        f"{len(GRAPHES)} graphe(s), {p1} {p2}")
    dit(p1 and p2 and p1[0] != p2[0],
        "deux rendus du meme jour, meme compte, meme moteur : deux prefixes "
        "differents — le compteur de ComfyUI ne les departage plus a lui seul",
        f"{p1} / {p2}")
    dit(p1 and t1[:8] in p1[0] and p2 and t2[:8] in p2[0],
        "chaque prefixe porte l'identifiant de SA tache", f"{p1} / {p2}")
    jour = time.strftime("%Y%m%d")
    attendu = f"{S.dossier_utilisateur(PID)}/image/{jour}_"
    dit(p1 and p1[0].startswith(attendu),
        "et le rangement ne change pas : <compte>/<type>/<date>_…",
        f"{p1[0] if p1 else '?'} contre {attendu}…")

    # UNE TACHE REJOUEE (redemarrage du studio, reprise de la file) garde son
    # prefixe : ses fichiers restent ensemble, et le compteur de ComfyUI les
    # departage — c'est le seul cas ou il le doit.
    del GRAPHES[:]
    await rendre(conv, tid=t1)
    p3 = prefixes(GRAPHES[0][1]) if GRAPHES else []
    dit(p3 and p1 and p3 == p1,
        "une tache rejouee garde son prefixe", f"{p3} / {p1}")

    # UNE VARIANTE est une tache a elle (lancer_variantes) : elle a donc son
    # prefixe, et « refais celle-ci » vise un fichier qui n'est qu'a elle.
    del GRAPHES[:]
    t5 = await rendre(conv)
    p5 = prefixes(GRAPHES[0][1]) if GRAPHES else []
    dit(p5 and p5[0] not in (p1 + p2),
        "un troisieme rendu, un troisieme prefixe", f"{p5}")

    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    for r in rate:
        print("    a regarder :", r)
    return 1 if rate else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
