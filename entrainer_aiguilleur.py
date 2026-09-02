# -*- coding: utf-8 -*-
"""Entraine l'aiguilleur et le mesure. A relancer quand le corpus change.

    python entrainer_aiguilleur.py

Le corpus a deux sources : des gabarits ecrits a la main (reproductibles, sans
reseau) et des demandes ecrites par un modele distant si une cle est posee. Les
secondes sont indispensables — mesure : entraine sur les seuls gabarits,
l'aiguilleur atteint 100 % sur mes propres phrases et 74 % sur celles ecrites
par quelqu'un d'autre. Il ne connaissait que mon vocabulaire.

La mesure qui compte est celle du banc, ecrit ailleurs et jamais appris.
"""
import json
import os
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import aiguilleur as _aiguilleur
from aiguilleur import Aiguilleur, MARGE_SURE, MODELE, MODELE_LOCAL  # noqa: E402
import corpus_aiguillage                                # noqa: E402

CORPUS = [
    "corpus_aiguillage.jsonl",   # gabarits, produits par corpus_aiguillage.py
    "corpus_llm.jsonl",          # demandes variees ecrites par un modele
    "corpus_llm2.jsonl",         # tournures indirectes, ou le verbe est absent
]
BANCS = ["banc_aiguillage.jsonl", "banc_neuf.jsonl"]


def _lire(nom):
    chemin = os.path.join(ICI, nom)
    if not os.path.exists(chemin):
        return []
    with open(chemin, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# Les demandes reelles sont rares et precieuses : on les compte plusieurs fois,
# sinon trois mille exemples fabriques les noieraient. Mais on plafonne leur
# apport par classe — mesure : sans plafond, dix-sept demandes reelles dont
# onze images faisaient pencher tout le classifieur vers « image », et la
# justesse sur les tournures indirectes tombait de 86 a 84 %.
POIDS_REEL = 8
PART_REELLE = 0.10          # au plus un dixieme d'une classe


def moissonner(dossier=None):
    """Les demandes passees par le studio dont l'intention est certaine.

    On ne prend que ce que l'utilisateur a lui-meme decide ou valide. Un tour
    « fini » sans pouce ne prouve rien : le studio a pu se tromper de modalite
    et produire quand meme quelque chose ; l'apprendre reviendrait a lui
    enseigner ses propres erreurs.

    ET LES CORRECTIONS. Un pouce en bas ne faisait qu'ecarter un exemple — « ce
    tour ne prouve rien ». C'est pourtant le cas le plus precieux : le studio
    s'est trompe, et l'utilisateur sait sur quoi. Quand il l'a dit, on apprend
    la bonne classe sur une formulation que le classifieur a DEJA ratee. Ce
    tour-la n'a pas besoin d'etre « fini » : ce qui l'etiquette est la
    correction, pas le resultat.
    """
    # LA MEME REGLE QUE LE STUDIO. « STUDIO_DONNEES a toujours designe
    # DIRECTEMENT le dossier des conversations » — c'est ecrit dans serveur.py,
    # et ce n'etait pas suivi ici : on cherchait dans ICI_DATA/conversations,
    # soit /app/conversations dans le conteneur, qui n'existe pas. Mesure :
    # moissonner() rendait ZERO exemple en production. Tout le travail du pouce
    # — les confirmations depuis des semaines, les corrections d'hier — n'est
    # jamais arrive jusqu'au corpus, et rien ne le disait.
    dossier = dossier or os.environ.get("STUDIO_DONNEES") or os.path.join(
        _aiguilleur.ICI_DATA, "conversations")
    if not os.path.isdir(dossier):
        return []
    connues = set(corpus_aiguillage.__dict__.get("_CLASSES", []) or
                  {e for _, e in corpus_aiguillage.GABARITS})
    recolte, par_personne = [], {}
    for nom in os.listdir(dossier):
        if not nom.endswith(".json") or nom.startswith("_"):
            continue
        try:
            with open(os.path.join(dossier, nom), encoding="utf-8") as f:
                conv = json.load(f)
        except Exception:
            continue
        # A QUI EST CETTE CONVERSATION. Le corpus est partage par tout le
        # studio : sans ce compte, n'importe qui etiquette le classifieur de
        # tout le monde — « un renard dans les hautes herbes », pouce en bas,
        # « c'etait plutot : de la musique », et le mot part en « audio »
        # pondere huit fois pour les autres. Et meme sans malveillance, celui
        # qui corrige beaucoup un jour monopolise l'apport reel.
        qui_ = conv.get("proprietaire") or "?"
        for t in conv.get("tours", []):
            texte = (t.get("demande") or "").strip()
            intention = t.get("type")
            corrigee = t.get("intention_voulue")
            if texte and corrigee in connues and t.get("avis") == -1:
                # Le meme filtre d'etat que pour une confirmation : un tour
                # jamais execute, ou reste a l'etat « question », ne dit rien de
                # ce que l'utilisateur voulait vraiment.
                if t.get("etat") not in ("fini", "erreur"):
                    continue
                recolte.append({"texte": texte, "intention": corrigee,
                                "source": "correction", "qui": qui_})
                continue
            if not texte or intention not in connues:
                continue
            if t.get("etat") != "fini" or t.get("avis") == -1:
                continue
            impose = str(t.get("raison") or "").startswith(
                ("modele impose", "moteur distant impose"))
            if not impose and t.get("avis") != 1:
                continue
            recolte.append({"texte": texte, "intention": intention,
                            "source": "reel", "qui": qui_})
    return recolte


# Mis a vrai par « --sans-reel ». C'est ainsi qu'on regenere le modele PUBLIE :
# sans une seule demande d'utilisateur dedans. Un drapeau de module plutot qu'un
# parametre, parce que corpus() est appele de trois endroits et qu'un seul
# oublie ferait publier ce qu'on cherche justement a retenir.
SANS_REEL = False


def corpus():
    """Tous les exemples, sans doublon. L'ordre des fichiers ne compte pas."""
    # On regenere TOUJOURS, et pas seulement quand le fichier manque. Les sept
    # gabarits « image » ajoutes le 31 aout pour qu'une creation en haute
    # definition cesse de partir a l'agrandissement ne sont jamais arrives
    # jusqu'au corpus : le .jsonl datait du 29, il existait, on ne le
    # reecrivait donc pas — et le correctif est reste inerte. Mesure du 31 aout
    # une fois le corpus reellement regenere : banc_neuf passe de 82 a 88 % de
    # justesse, et de 85 a 91 % sur les tranches d'office. La graine est fixe et
    # l'ecriture prend dix millisecondes : le fichier ne bouge que si les
    # gabarits ont bouge.
    corpus_aiguillage.ecrire(corpus_aiguillage.depuis_gabarits())
    tout, vus = [], set()
    for nom in CORPUS:
        for x in _lire(nom):
            cle = (x.get("texte") or "").strip().lower()
            if cle and cle not in vus:
                vus.add(cle)
                tout.append(x)
    fabriques = {}
    for x in tout:
        fabriques[x["intention"]] = fabriques.get(x["intention"], 0) + 1

    reels, ajoutes = ([] if SANS_REEL else moissonner()), {}
    # ── ET RIEN QUI NE SOIT PAS DANS LA LANGUE DU CORPUS ──────────────
    # LA MOISSON INVERSE LE REMEDE SUR UNE DEMANDE ETRANGERE. Mesure du
    # 2 septembre 2026 (mesures_langues/mesurer_apprentissage.py, corpus
    # francais plus K exemples par classe dans la langue visee, ponderation
    # reelle, trois tirages) : ONZE demandes allemandes confirmees font passer
    # les pannes silencieuses allemandes de 17 % a 44 %. La justesse, elle, ne
    # bouge presque pas — 45 % a 51 %. Ce n'est donc pas la justesse qui monte,
    # c'est la CONFIANCE, et le court-circuit tire plus souvent.
    #
    # La cause est POIDS_REEL. Il a ete regle sur des demandes francaises
    # entrant dans un corpus francais, ce que le commentaire de sa constante dit
    # deja. Huit exemplaires d'une phrase allemande creent des traits a fort
    # poids — les fragments de ses mots grammaticaux — que TOUTES les autres
    # phrases allemandes partagent, et qui les tirent avec assurance vers la
    # classe de ces huit exemplaires. En faisant varier la seule ponderation a
    # K=3, les pannes allemandes suivent : 27 % a x1, 31 % a x2, 39 % a x4,
    # 43 % a x8. Monotone.
    #
    # ET LES BANCS DU DEPOT N'EN VERRAIENT RIEN : sur le banc francais, l'ajout
    # ne change rien du tout (91 %, 90 %, 96 % pour K=0, 3, 5). C'est le profil
    # exact d'une panne qu'on ne voit pas.
    #
    # LE VOCABULAIRE DE REFERENCE EST CELUI DES GABARITS, jamais celui du modele
    # en service. Le prendre sur le modele ferait une boucle : trois demandes
    # allemandes admises relevent la couverture de l'allemand, ce qui en admet
    # d'autres, et la garde s'erode d'elle-meme sans qu'une ligne ait bouge.
    # « tout » ne contient a cet instant que les exemples FABRIQUES.
    #
    # CE QU'ELLE COUTE EN FRANCAIS, MESURE SUR LES 295 PHRASES FRANCAISES DES
    # BANCS : 5 ecartees, 1,7 % — « ajoute des aurores boreales », « commente
    # et recadre en carre », « de quoi ca parle ». Ce sont de vraies demandes
    # francaises, et les perdre est un vrai cout : la moisson existe justement
    # pour apprendre les formulations que le corpus n'a PAS. La garde ecarte
    # donc, par construction, une part de ce qu'elle devrait garder.
    #
    # ON L'ACCEPTE PARCE QUE LES DEUX ERREURS NE COUTENT PAS PAREIL. Ecarter
    # une demande francaise coute UN exemple sur des milliers, et la suivante
    # dans la meme tournure repassera. Admettre une demande etrangere coute
    # huit exemplaires ponderes, et la mesure ci-dessus dit ou cela mene. Sur
    # les 345 phrases etrangeres du meme banc, 338 sont ecartees : le meme
    # seuil, la meme ligne.
    if reels:
        connu = _aiguilleur.Aiguilleur().apprendre(tout)
        garde = [x for x in reels if connu.connu(x["texte"])]
        if len(garde) != len(reels):
            print(f"  {len(reels) - len(garde)} demande(s) ecartee(s) : leurs "
                  f"mots ne sont pas ceux du corpus (moins de "
                  f"{_aiguilleur.SEUIL_LANGUE:.0%} de couverture). Une demande "
                  f"etrangere apprise ici ne rend pas le studio meilleur dans "
                  f"cette langue, elle le rend plus SUR de ses erreurs")
        reels = garde
    # LES CORRECTIONS D'ABORD. Le plafond par classe est vite atteint, et une
    # confirmation apprend une formulation que le classifieur trouvait deja ;
    # une correction en apprend une qu'il a ratee. Si l'une des deux doit sauter,
    # ce n'est pas celle-la.
    reels.sort(key=lambda x: x.get("source") != "correction")
    # LE PLAFOND SE PARTAGE ENTRE LES PERSONNES. Le champ « qui » etait ecrit
    # par moissonner() puis jamais relu : le plafond restait par classe, et
    # quatre corrections d'un seul compte evinçaient toutes les confirmations
    # des autres dans cette classe — mesure : 27 exemplaires pour l'un, zero
    # pour l'autre. Le tri « corrections d'abord » rendait meme la chose plus
    # certaine qu'avant. Le corpus est partage : sa place l'est aussi.
    gens = {x.get("qui") for x in reels} or {None}
    par_personne = {}
    for x in reels:
        cle = x["texte"].strip().lower()
        if cle in vus:
            continue
        plafond = int(fabriques.get(x["intention"], 0) * PART_REELLE)
        # Sa part a lui : le plafond de la classe divise par le nombre de
        # personnes qui y ont contribue, et au moins POIDS_REEL pour que la
        # premiere demande de quelqu'un ne soit pas jetee d'office.
        sa_part = max(POIDS_REEL, plafond // max(1, len(gens)))
        cle_p = (x.get("qui"), x["intention"])
        deja = ajoutes.get(x["intention"], 0)
        sien = par_personne.get(cle_p, 0)
        if deja >= plafond or sien >= sa_part:
            continue
        vus.add(cle)
        combien = min(POIDS_REEL, plafond - deja, sa_part - sien)
        ajoutes[x["intention"]] = deja + combien
        par_personne[cle_p] = sien + combien
        tout += [x] * combien
    if ajoutes:
        print(f"  {len(reels)} demandes reelles recoltees, "
              f"{sum(ajoutes.values())} exemplaires retenus "
              f"(plafond : {PART_REELLE:.0%} par classe, partage entre "
              f"{len(gens)} personne(s))")
    # Le drapeau voyage avec la liste : c'est lui qui decide du fichier ecrit,
    # donc de ce qui peut etre publie.
    return tout, bool(ajoutes)


def mesurer(a, banc):
    """Justesse globale, et justesse sur les seuls cas tranches d'office.

    Les deux chiffres disent des choses differentes : le premier mesure le
    classifieur, le second mesure ce qu'on lui laisse decider tout seul. C'est
    le second qui compte pour l'utilisateur, puisque les cas incertains partent
    au modele de langage.
    """
    bons = surs = bons_surs = 0
    for x in banc:
        c, marge = a.classer(x["texte"])
        sur = marge >= MARGE_SURE
        juste = c == x["intention"]
        bons += juste
        surs += sur
        bons_surs += juste and sur
    return bons, len(banc), bons_surs, surs


if __name__ == "__main__":
    # « --sans-reel » : n'apprend QUE le corpus du depot. C'est la
    # commande qui regenere le modele publie.
    SANS_REEL = "--sans-reel" in sys.argv

    exemples, du_reel = corpus()
    par = {}
    for x in exemples:
        par[x["intention"]] = par.get(x["intention"], 0) + 1
    print(f"  {len(exemples)} exemples, {len(par)} classes")
    print("  ", ", ".join(f"{k} {v}" for k, v in sorted(par.items())))

    t0 = time.time()
    a = Aiguilleur().apprendre(exemples)
    print(f"\n  entraine en {time.time() - t0:.2f} s — {a.vocabulaire} traits")
    # Des qu'une demande reelle est entree dans le melange, le modele ne peut
    # plus etre celui qu'on publie : il part a cote, dans un fichier ignore par
    # git, et le studio le prefere puisqu'il connait cette installation.
    ou = MODELE_LOCAL if du_reel else MODELE
    a.ecrire(ou)
    print(f"  ecrit : {os.path.basename(ou)} "
          f"({os.path.getsize(ou) / 1e6:.2f} Mo)"
          + ("  — garde ici, hors du depot" if du_reel else ""))

    for nom in BANCS:
        banc = _lire(nom)
        if not banc:
            continue
        t0 = time.time()
        bons, total, bons_surs, surs = mesurer(a, banc)
        ms = (time.time() - t0) / max(total, 1) * 1000
        print(f"\n  {nom}")
        print(f"     {bons}/{total} justes ({bons * 100 / total:.0f} %), "
              f"{ms:.3f} ms par demande")
        print(f"     tranches d'office : {bons_surs}/{surs} "
              f"({bons_surs * 100 / max(surs, 1):.0f} %) — "
              f"{total - surs} renvoyes au modele de langage")
