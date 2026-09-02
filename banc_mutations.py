# -*- coding: utf-8 -*-
"""Les bancs rougissent-ils encore sur les pannes qu'ils disent attraper ?

    python banc_mutations.py

Trois fois cette semaine, un banc vert a couvert une fonctionnalite morte. La
derniere est la pire : banc_page.py, ecrit expres pour empecher un defaut de
revenir, ne voyait pas ce defaut. Il cherchait « priorite: $("#priorite").value »
alors que le vrai code portait l'abreviation ES6, « priorite, ». La ligne fautive
restauree, le banc est reste vert.

Un banc ne se relit pas, il s'eprouve. Le seul geste qui l'a montre, c'est de
MUTER le code et d'exiger que le banc rougisse. Il a ete fait trois fois a la
main, dans des scripts jetables, et jete a chaque fois. Il est ici.

Chaque mutation copie dans un dossier temporaire ce dont le banc vise a besoin,
y applique la mutation, lance CE banc-la — pas les autres — et exige une ligne
rouge NOMMEE. Le depot n'est jamais touche.

Dix bancs y sont depuis le 1er septembre ; ils etaient quatre. Les six qui
manquaient portaient 355 verifications a eux tous, et pas une n'avait jamais
ete vue rougir : la regle de CONTRIBUTING.md, « si tu ajoutes un banc,
ajoute-lui sa mutation », avait ete ecrite et pas tenue.

Le onzieme est banc_refaire.py, arrive le 2 septembre avec ses douze mutations
— une par correction de 1ad6c0d, et DEUX pour le defaut de surete, dont les
gardes se recouvrent.

Le douzieme est verifier_formulations.py, le plus vieux banc du depot et le
dernier sans mutation, ferme le 2 septembre. Ce qui l'en tenait ecarte — il
nomme ses fautes par le NUMERO DE LIGNE de banc_formulations.jsonl — se regle
en ancrant sur la FORMULATION, qu'il imprime a cote du numero et qui ne bouge
pas quand un cas s'insere au milieu du fichier. Quatre mutations, et TROIS
TROUS dont le premier etait le plus grave de ce fichier : le banc ne voyait pas
la panne pour laquelle il a ete ecrit. Il recopiait dans aiguillage_ecrit() la
sequence de serveur.py au lieu de l'emprunter, alors que sa docstring promettait
que « toute permutation la-bas doit se voir ici » — c'etait « priorite, » une
seconde fois, sur le banc qui gardait « enleve le fond ».

LES TROIS SONT FERMES le 2 septembre au soir, et par une seule reparation :
la sequence est sortie d'aiguiller() dans serveur.raccourci_ecrit(), que le
studio ET le banc empruntent desormais. Tant qu'il y avait deux ecritures du
meme ordre, elles divergeaient ; il n'y en a plus qu'une. Les deux petits trous
tenaient a des cas qui n'atteignaient pas le motif qu'ils gardaient — deux ont
recu la piece jointe qui leur manquait, le troisieme une formulation que la
SECONDE garde ne voit pas. Sept mutations sur ce banc, plus aucun trou.

Trois facons d'echouer, et la premiere est la plus precieuse :

  - une mutation qui passe au VERT : le filet a un trou, exactement celui qui a
    laisse passer « priorite, ».
  - une mutation dont l'ANCRE n'existe plus : elle ne mesure plus rien, et
    personne ne s'en apercevrait. C'est un echec, pas un succes silencieux —
    d'ou l'ancrage sur un motif de texte et jamais sur un numero de ligne
    (serveur.py change plusieurs fois par jour).
  - le depot SAIN qui rougit : un banc qui rougit sur tout n'attrape rien non
    plus, et le sens inverse se verifie donc aussi.

Exiger la LIGNE attendue et pas seulement un code de retour non nul n'est pas
un raffinement : une mutation qui casse le banc par une exception rend elle
aussi un code non nul, et se ferait passer pour une reussite.

TROUS_CONNUS rassemble les mutations que la relecture adverse a trouvees et que
le banc vise laisse ENCORE passer. Elles sont ecrites, nommees et signalees,
mais ne font pas echouer : les compter en echec rendrait la CI rouge en
permanence, et une CI qui rougit pour rien finit ignoree. Les basculer dans
MUTATIONS est le geste qui clot la reparation du filet.

Ils etaient cinq, puis huit ; il en reste UN. Les quatre qui visaient
banc_page.py sont fermes et ont rejoint PAGE, les trois de
verifier_formulations.py sont fermes et ont rejoint FORMULATIONS.

Les quatre de banc_page.py disaient tous la meme chose : un releve par
expression reguliere decrit UNE facon d'ecrire la panne, jamais la panne.
Fermer le premier a d'ailleurs revele qu'il n'imitait pas encore le vrai
defaut — la mutation posait un « const », la page de 21c443c^ recevait le cran
en argument d'appel — et la mutation qui manquait est desormais dans PAGE elle
aussi. C'est le meme service que ce fichier rend aux bancs : une mutation aussi
s'eprouve.

Les trois de verifier_formulations.py en disaient une autre, et c'est la plus
chere : un banc qui RECOPIE la sequence qu'il verifie ne verifie rien de cette
sequence. Les fermer n'a pas demande trois corrections mais une seule — sortir
l'ordre dans une fonction que les deux empruntent — parce que tant qu'il y a
deux ecritures du meme enchainement, elles divergent.

LA DIAGONALE, ou la preuve inverse, menee le 1er septembre sur les dix-neuf
mutations de VARIANTES, CERVEAUX, COUT, CATALOGUE, ATTENTE, DUREES et ADULTE.
Qu'une mutation rougisse ne dit pas qu'elle mesure le bon trou : elle peut
rougir pour une autre raison que celle qu'elle nomme. Ce qui le dit, c'est de
la rejouer contre le FILET D'AVANT — le banc tel qu'il etait au commit qui
precede la correction — et de la voir passer au VERT. Si le vieux banc
l'attrape quand meme, une autre garde la voit et la mutation ne mesure pas ce
qu'elle nomme.

Le tout au commit de la correction, code ET banc : un banc de 3cecca2^ lance
contre le serveur.py d'aujourd'hui rougit sur une trentaine de cas sans rapport
— trois mois de derive — et ne mesure plus rien du tout.

  - SEIZE eprouvees dans les deux sens : rouges avec la garde, vertes sans.
  - DEUX ont d'abord resiste — « le choix fait a la main » et « le rang 1 tout
    court » restaient rouges sur le banc de 3cecca2^. Elles ne mesurent pas
    une garde de 3cecca2 : la regle du rang y a ete FUSIONNEE, pas ecrite, et
    ses deux gardes datent de cac8aa7. Rejouees sur le banc de cac8aa7^, elles
    passent au vert. Elles mesurent donc bien ce qu'elles nomment, et c'est le
    commentaire de VARIANTES qui les datait mal.
  - TROIS ne sont pas prouvables ainsi, et il faut le dire : banc_durees.py,
    banc_adulte.py et le poids() de banc_catalogue.py sont NES avec la
    correction qu'ils gardent (717fb23, f467e11, 02fdae6). Il n'existe pas de
    « filet d'avant » a leur opposer. Elles restent des mutations rouges dont
    on ne sait pas ce qu'elles mesurent d'autre.

Le sens inverse de banc_catalogue.py, lui, a ete pris autrement et il a
repondu : installation.py d'avant 3bb235d restaure, le banc REPARE rougit sur
quatre lignes dont les trois « ~0 Go a prendre » d'origine. Le banc d'avant
restait vert dessus — c'est le trou B ci-dessous.

LA DIAGONALE DU 2 SEPTEMBRE, sur les dix-huit mutations ajoutees pour 1ad6c0d.
Les dix-huit sont rouges sur le depot du jour ; voici ce que le sens inverse a
donne, et il a fallu deux facons de le prendre :

  - LES DOUZE DE banc_refaire.py ne peuvent pas se prouver par un filet
    d'avant : le banc est NE avec la correction, comme banc_durees et
    banc_adulte avant lui. Le sens inverse a donc ete pris comme pour
    banc_catalogue — serveur.py de 1ad6c0d^ restaure, le banc NEUF lance
    dessus. Il rougit sur 32 lignes, et les DOUZE que ces mutations nomment y
    sont toutes, une par une. C'est mieux qu'une diagonale : chaque mutation a
    ete vue rougir sur le vrai defaut, pas seulement sur son imitation.
  - LES QUATRE DE banc_repartition.py sont vertes sur le filet d'avant, et ce
    filet n'est pas celui de 1ad6c0d^ : le banc y lit deja « v._en_vol », que
    c337f82 avait ecrit pour un attribut que 1ad6c0d n'avait pas encore pose —
    lance sur son propre serveur.py, il s'arrete sur AttributeError. C'est
    contre banc_repartition.py de 0f0f3dc, la derniere version qui tourne, que
    la diagonale a ete prise : 35/35 VERT sur le serveur.py qui porte pourtant
    les six defauts. Et les defauts eux-memes ont ete releves a la main sur ce
    serveur-la : « rendu 1 puis rendu 2 puis analyse 1 puis analyse 2 » pour le
    vieillissement, la carte MOYENNE au lieu de la grosse et la descente sur
    une carte ou le moteur ne tient pas pour la reprise, et « B servi ET C
    servi » — deux titulaires — pour le release() de trop.
  - LES DEUX DE banc_durees.py sont vertes sur banc_durees.py de 1ad6c0d^,
    10/10, sur le meme serveur.py. Ce banc-la, ne avec la correction de
    717fb23, restait donc aveugle a la case de cache unique comme au devis qui
    comptait les rendus du voisin.

LA DECOUPE DE C2, trouvee le 2 septembre. La correction repare DEUX defauts —
la carte MOYENNE rendue quand on demande la grosse, et la descente sur une
carte ou le moteur ne tient pas — et le banc porte une ligne pour chacun. Une
seule mutation les couvrait : elle rougissait sur les deux a la fois, donc la
seconde ligne n'avait jamais ete vue mordre SEULE, et l'agent qui l'a posee
ecrivait n'avoir trouve aucune decoupe. Elle existe. Les deux defauts naissent
du meme geste — l'ordre du filtre de charge et du filtre natif — mais pas de la
meme facon : « grosse » se tranche AVANT tout filtre dans choisir_noeud, la
descente se joue APRES. Deux demi-copies suffisent donc, chacune reparant une
moitie : 47/48 chacune, sur SA ligne, la copie entiere rendant 46/48. Le sens
inverse est celui des quatre autres — banc_repartition.py de 0f0f3dc, 35/35
VERT sur les deux moities comme sur la copie entiere.

LES SIX DE LA DIXIEME RELECTURE, 2 septembre 2026 au soir. Trois defauts
nommes et laisses ouverts, dont aucun n'etait dangereux ce jour-la : le contrat
du « deja refait » qui tenait sur un mot du message francais, les deux boutons
qui refusaient les memes classes avec deux codes, et une assertion de
banc_refaire.py verte parce que la route avait refuse. Le sens inverse a demande
les DEUX manieres, et la seconde est neuve :

  - QUATRE se prouvent contre le code d'AVANT, comme les douze de banc_refaire :
    serveur.py et web/index.html de 1a762b9 restaures, les bancs NEUFS lances
    dessus. banc_page.py y rougit sur ses deux lignes, banc_refaire.py sur six,
    et les lignes que ces mutations nomment y sont. Avec la page NEUVE sur le
    serveur d'AVANT — pour que le releve de MARQUE_DEJA aboutisse et que la
    marque manquante soit la seule difference — « le second clic est refuse en
    409 ET porte la marque » rougit en imprimant le corps sans marque.
  - « la marque « deja » posee sur un second refus » N'A PAS DE CODE D'AVANT :
    la regle qu'elle garde — un seul refus la porte — nait avec la marque
    elle-meme, et le depot d'avant n'en avait aucune. Ce qui a ete mesure a la
    place, c'est son ISOLEMENT : posee seule, elle rend 80/81 sur banc_refaire,
    la SEULE ligne rouge etant la sienne, qui nomme le refus fautif. Elle ne
    rougit donc pas pour une autre raison que celle qu'elle dit.
  - « le repli de taille REFUSE au lieu de reprendre » est d'une autre famille
    encore : ce n'est pas le code qui a ete corrige mais le BANC. Son sens
    inverse se prend en remettant l'assertion creuse — « not
    plan_bd.get("largeur") » sans le temoin — et la mutation passe alors au VERT
    sur la ligne qu'elle nomme, « NonexNone » a l'appui, pendant que le banc
    rougit ailleurs. C'est exactement le reproche : verte parce que rien ne
    s'etait passe.

LES SEPT DE LA ONZIEME RELECTURE, 2 septembre 2026 au soir, pour quatre
corrections d'une seule famille : du texte ecrit pour etre LU servait de
contrat a du code. Une phrase de journal relue par expression reguliere pour en
tirer le devis, le libelle visible d'une <option> decoupe sur son tiret
cadratin, le debut d'un message d'erreur teste pour declencher une relecture —
sur un message que la page venait d'ecraser elle-meme —, et une exception
Python renvoyee telle quelle a l'ecran. Le remede est celui de MARQUE_DEJA
partout : le serveur pose un champ, la page lit le champ, et un banc releve le
nom du champ DANS la page pour exiger les deux moities.

Sept et non quatre parce que trois de ces corrections ont deux moities, et
qu'une moitie jamais vue rougir ne mesure rien. Le sens inverse a ete pris
comme pour les douze de banc_refaire : les deux fichiers remis dans leur etat
d'avant, les bancs NEUFS lances dessus, et les sept lignes nommees y rougissent
toutes. Le detail est ecrit au-dessus de PROSE.

DEUX CAS DE banc_variantes.py SONT PARTIS AVEC LA CORRECTION, et c'est leur
propre commentaire qui l'avait prevu : « il rougira encore le jour ou la page
lira le champ, puisque le cas sera devenu sans objet et qu'il faudra le retirer
avec le couplage ». Ils mesuraient l'ecart entre la phrase du journal et le
champ — la phrase arrondit, le champ non. La page lit le champ : il n'y a plus
d'ecart a mesurer, et le seuil de DEVIS_EN_SECONDES_JUSQUA n'a plus a le
borner. Le banc passe de 115 a 118 : trois cas de plus pour l'arret differe,
deux de moins pour l'ecart, et le releve de la phrase remplace par celui du
champ.

ET UNE MUTATION D'ICI EST PARTIE AVEC EUX : « la phrase du devis repasse aux
minutes des 90 s » ne nommait plus rien, faute du cas qu'elle faisait rougir.
La garder l'aurait rendue « MUTATION PERIMEE », c'est-a-dire un echec — une
mutation qui ne mesure plus rien se retire en meme temps que sa garde, jamais
apres. Le compte va de 99 a 105.

LES NEUF DES LANGUES, 2 septembre 2026 au soir, et un TREIZIEME banc :
banc_traductions.py. Le studio se traduit — les vingt-cinq refus que la page
affiche, les treize pannes que la page lit dans le journal, la langue de celui
qui lit. UNE TRADUCTION NE PLANTE PAS, ELLE MENT : chacune des neuf pannes
imitees laisse le studio rendre 200, la page s'afficher, le rendu se faire.
Elles ne se voient que depuis l'ecran d'un lecteur anglais.

Le sens inverse a demande les deux manieres, comme la dixieme relecture :

  - LES TROIS DE banc_traductions.py se prouvent contre le code d'AVANT. Les
    editions de la correction ont ete defaites une a une dans un dossier
    temporaire — les cles de panne retirees, les refus rendus a leur phrase
    francaise, la langue et la route des textes supprimees — et le banc NEUF
    lance dessus rougit 4 fois sur 31 : les TROIS lignes que ces mutations
    nomment, plus « aucune cle de panne ne dort », qui est la meme regle prise
    par l'autre bout.
  - LES SIX DE banc_refaire.py N'ONT PAS DE CODE D'AVANT QU'ON PUISSE LEUR
    OPPOSER, et c'est la troisieme fois que ce cas se presente. Ici la raison
    est nouvelle et vaut d'etre ecrite : la correction AJOUTE DES NOMS —
    MARQUE_PANNE, langue_de, COOKIE_LANGUE, api_textes — que le code d'avant
    n'a pas. Le banc neuf lance dessus ne rougit pas, il MEURT sur un
    AttributeError a la premiere ligne qui les cite, c'est-a-dire « le banc
    s'est casse au lieu de rougir ». Ce qui a ete mesure a la place est leur
    ISOLEMENT, mutation par mutation, et il est net : quatre des six n'allument
    QUE leur propre ligne (102/103) ; « le refus repart en francais » n'allume
    que la sienne ; « l'en-tete decide de la langue » en allume deux, et la
    seconde est le refus servi en anglais — c'est-a-dire l'autre bout du meme
    contrat, ce que la langue sert. Aucune ne touche a un cas d'un autre sujet.
  - LES TROIS DE banc_traductions.py, prises isolement, allument chacune leur
    ligne et « aucune cle de panne ne dort » : la meme regle vue de l'endroit
    et de l'envers. C'est voulu — une cle posee nulle part et une cle qui dort
    sont le meme fait.

ET LE RELEVE A TROUVE UN CAS CAPRICIEUX, qui n'a rien a voir avec les langues.
« le chrono est repose la carte EN MAIN » comparait « pose - depart » a 0,4 s
tout rond, quand asyncio.sleep() rend la main un peu TOT sous Windows — la
resolution du minuteur est de 15,6 ms. Sous la charge de ce fichier-ci, il a
rendu 0,39 s pour 0,4 s demandees et le banc a rougi sur un cas parfaitement
juste. Il compare desormais a l'instant OBSERVE de fin d'attente, et son voisin
porte les deux arrondis au dixieme de /api/etat. Une CI qui rougit pour rien
finit ignoree ; c'est le meme argument que TROUS_CONNUS, pris a l'envers.

CE QUE LE PARALLELISME DES LANCEMENTS COUTERAIT, mesure le 2 septembre et
refuse. Les huit bancs sans sommeil pourraient tourner ensemble, et l'ordre des
resultats se garderait sans peine — il suffit de collecter les verdicts dans
une liste indexee et de n'imprimer qu'a la fin. Ce n'est pas l'ordre qui
l'interdit, c'est la MESURE : ce fichier met 77,4 s seul sur cette machine, et
le meme lancement a depasse 300 s pendant que deux autres travaux occupaient
les coeurs. Un facteur quatre par la seule charge, sur des bancs dont plusieurs
temporisent — banc_variantes de 0,02 a 0,6 s, banc_refaire 0,4 s — dit que huit
processus simultanes les reordonneraient. On echangerait quarante secondes de
CI contre un banc capricieux, et c'est le mauvais sens de l'echange.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
ok, rate, signales = [], [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


def lire(rel):
    # newline=None : un depot clone sous Windows rend des CRLF, et les ancres
    # ci-dessous sont ecrites en "\n". Sans cette normalisation, TOUTES les
    # mutations seraient declarees perimees sur une machine et sur une seule.
    with io.open(os.path.join(ICI, *rel.split("/")), encoding="utf-8",
                 newline=None) as f:
        return f.read()


# ── Ce qu'il faut copier, et rien de plus ─────────────────────────────
# Mesure : le depot entier fait 138 fichiers et 0,12 s de copie, les neuf
# fichiers dont banc_conteneur.py a besoin en font 0,007 s. Sur les vingt-deux
# mutations, deux secondes de CI contre un huitieme de seconde.
def fichiers_du_conteneur():
    """La meme piste que celle que banc_conteneur.py suit lui-meme.

    Il ne releve pas le repertoire mais les IMPORTS de serveur.py — agent_noeud
    est dans l'image et ne tourne pas dans ce conteneur. Copier une liste ecrite
    a la main ici la ferait deriver de la sienne : le jour ou serveur.py
    importerait un module de plus, la mutation posee dedans tomberait dans un
    dossier ou le module n'est pas, et le banc rougirait sur un import manquant
    au lieu de la variable oubliee.

    « ^\\s* » comme lui, donc : les mutations qui deplacent un import en cours
    de fonction copieraient sinon un jeu de fichiers different du sien.

    ON SUIT LES IMPORTS EN PROFONDEUR DEPUIS LE 2 SEPTEMBRE 2026 AU SOIR, et
    c'est cette fonction-ci qui s'est fait prendre a ce qu'elle decrit. Elle ne
    relevait que les imports DIRECTS de serveur.py, ce qui tenait tant qu'aucun
    module du depot n'en importait un autre. comptes.py a importe mfa.py : le
    dossier temporaire recevait comptes.py sans mfa.py, et QUATRE-VINGT-DEUX
    mutations sur 144 se sont declarees rouges sur « ModuleNotFoundError: No
    module named 'mfa' ». Rouges pour la mauvaise raison, c'est-a-dire vertes
    pour de vrai : un filet qui rougit sur tout n'attrape rien, et l'on n'aurait
    pas su lesquelles des 82 mesuraient encore quelque chose.

    C'est mot pour mot ce que le paragraphe ci-dessus annonce — « la mutation
    posee dedans tombait dans un dossier ou le module n'est pas, et le banc
    rougirait sur un import manquant au lieu de la variable oubliee ». Le
    raisonnement etait juste, sa mise en oeuvre s'arretait au premier niveau.
    """
    fichiers = ["banc_conteneur.py", "serveur.py",
                "docker-compose.yml", "Dockerfile", ".env.exemple"]
    a_lire, vus = ["serveur.py"], {"serveur.py"}
    while a_lire:
        source = a_lire.pop()
        for mod in re.findall(r'(?m)^\s*(?:import|from)\s+([a-z_][a-z0-9_]*)',
                              lire(source)):
            nom = mod + ".py"
            if nom in vus or not os.path.exists(os.path.join(ICI, nom)):
                continue
            vus.add(nom)
            a_lire.append(nom)
            if nom not in fichiers:
                fichiers.append(nom)
    return fichiers


BESOINS = {
    "banc_conteneur.py": fichiers_du_conteneur(),
    # traductions.py DEPUIS LE 2 SEPTEMBRE 2026 AU SOIR : banc_page.py releve
    # le francais ecrit dans le HTML et exige qu'il soit exactement celui du
    # dictionnaire — la meme moitie de contrat que MARQUE_DEJA, mais sur cent
    # quatre-vingt-quinze chaines. Sans ce fichier, le banc meurt a l'import,
    # ce qui ressemblerait a une mutation attrapee.
    "banc_page.py": ["banc_page.py", "web/index.html", "traductions.py"],
    # Le banc importe serveur.py, donc tout ce que serveur.py importe.
    "banc_repartition.py": ["banc_repartition.py"] + fichiers_du_conteneur()[1:],
    "banc_cerveaux.py": ["banc_cerveaux.py"] + fichiers_du_conteneur()[1:],
    # banc_variantes.py relit web/index.html pour DEUX noms de champ, depuis
    # que le releve de la phrase du journal (RE_DEVIS) a laisse la place a la
    # lecture d'un champ : MARQUE_DEVIS et MARQUE_ARRET_DIFFERE. Sans cette
    # page, le banc annonce lui-meme que les couplages « NE SONT PLUS MESURES »
    # — et les mutations qui les visent rougiraient pour la mauvaise raison.
    "banc_variantes.py": (["banc_variantes.py", "web/index.html"]
                          + fichiers_du_conteneur()[1:]),
    # banc_cout.py et banc_attente.py importent serveur.py comme les autres.
    # aiohttp leur est en plus indispensable : fournisseurs.py l'importe en
    # tete de fichier, et sans lui le banc meurt a l'import — un plantage qui
    # ressemblerait a une mutation attrapee.
    "banc_cout.py": ["banc_cout.py"] + fichiers_du_conteneur()[1:],
    "banc_attente.py": ["banc_attente.py"] + fichiers_du_conteneur()[1:],
    "banc_durees.py": ["banc_durees.py"] + fichiers_du_conteneur()[1:],
    # banc_refaire.py monte un studio complet hors ligne comme banc_variantes,
    # et il relit la page pour UNE chose depuis le 2 septembre 2026 : MARQUE_DEJA,
    # le nom du champ par lequel /api/au_propre dit « c'est deja fait ». Sans
    # cette page, le banc annonce lui-meme que le couplage « N'EST PLUS MESURE »
    # — et les deux mutations de la marque rougiraient pour la mauvaise raison.
    # Tout le reste de ce qu'il mesure se lit dans le GRAPHE soumis et dans les
    # reponses HTTP.
    "banc_refaire.py": (["banc_refaire.py", "web/index.html"]
                        + fichiers_du_conteneur()[1:]),
    # banc_multilingue.py monte le studio hors ligne, remplace le modele de
    # langage par un compteur, et fait passer 460 demandes — les deux bancs du
    # depot traduits a la main. Il lui faut donc le conteneur entier, ses 460
    # cas (mesures_langues/banc_langues.py), ET entrainer_aiguilleur.py avec le
    # corpus : sa derniere section eprouve la garde de la MOISSON, qui vit
    # la-bas. Sans l'un d'eux il meurt a l'import, ce qui ressemblerait a une
    # mutation attrapee.
    # ET aiguilleur.json, LE MODELE PUBLIE. Il n'est dans la liste d'aucun
    # autre banc, et pour une raison qui vaut d'etre sue : quand le fichier
    # manque, charger() rend None — c'est ecrit dans sa docstring, « le studio
    # doit fonctionner sans lui » — et aiguiller() saute alors le court-circuit
    # entier, « if (AIGUILLEUR and ... ) ». Les onze autres bancs passent donc
    # au vert sans classifieur, sans rien remarquer. Celui-ci ouvre le fichier
    # en toutes lettres, pour epingler le modele VERSIONNE plutot que celui de
    # la machine : sans lui, il mourait sur un FileNotFoundError, « le banc
    # s'est casse au lieu de rougir ».
    "banc_multilingue.py": (["banc_multilingue.py", "aiguilleur.json",
                             "mesures_langues/banc_langues.py",
                             "entrainer_aiguilleur.py", "corpus_aiguillage.py",
                             "corpus_aiguillage.jsonl", "corpus_llm.jsonl",
                             "corpus_llm2.jsonl"]
                            + fichiers_du_conteneur()[1:]),
    # LE SEUL BANC QUI LIT serveur.py SANS L'IMPORTER, avec banc_adulte.py.
    # Il n'a besoin d'aucune dependance — traductions.py n'importe rien — et
    # aiohttp lui serait meme nuisible : il tourne sur la machine de celui qui
    # ecrit, ou pip n'a jamais servi. Ce qu'il regarde dans serveur.py, il le
    # regarde par l'arbre de syntaxe : quels sites de panne portent une cle,
    # quelles cles sont citees. Sans serveur.py, cette moitie-la du banc
    # meurt a l'ouverture — un plantage qui ressemblerait a une mutation
    # attrapee.
    "banc_traductions.py": ["banc_traductions.py", "traductions.py",
                            "serveur.py"],
    # Celui-la n'importe pas le studio : il preleve deux expressions
    # regulieres dans le TEXTE de serveur.py. Il lui faut donc serveur.py, et
    # rien d'autre — pas meme les modules qu'il importe.
    "banc_adulte.py": ["banc_adulte.py", "serveur.py"],
    # catalogue.py pour les tailles, installation.py et serveur.py parce que
    # le banc y cherche les poids encore mis en phrase a la main. Sans
    # serveur.py, son aveu d'ATTENDU_AILLEURS se declarerait perime.
    "banc_catalogue.py": ["banc_catalogue.py", "catalogue.py",
                          "installation.py", "serveur.py"],
    # Il importe serveur.py pour appeler les veut_* directement, et relit ses
    # 64 cas dans banc_formulations.jsonl. Sans ce fichier de cas, il ne
    # verifie plus rien et s'arrete sur une erreur d'ouverture — un plantage
    # qui ressemblerait a une mutation attrapee.
    "verifier_formulations.py": (["verifier_formulations.py",
                                  "banc_formulations.jsonl"]
                                 + fichiers_du_conteneur()[1:]),
}


# ── Ou se lit la ligne rouge ──────────────────────────────────────────
# Dix bancs sur quatorze impriment « NON » ; banc_cout.py, banc_multilingue.py
# et banc_traductions.py
# impriment « RATE », et
# banc_adulte.py comme verifier_formulations.py n'ont pas de dit() du tout —
# ils listent leurs fautes indentees sous leur compte. Sans cette table, TOUTE
# mutation qui les vise serait rendue « le banc s'est casse au lieu de
# rougir » alors qu'il l'a parfaitement attrapee : le faux positif que ce
# fichier existe pour interdire, retourne.
#
# L'exigence, elle, ne bouge pas — la ligne NOMMEE et pas un code de retour.
MARQUE_ROUGE = {"banc_cout.py": "  RATE ", "banc_adulte.py": "    ",
                "banc_multilingue.py": "  RATE ",
                "banc_traductions.py": "  RATE ",
                "verifier_formulations.py": "    "}


# ── Les deux formes d'ancre ───────────────────────────────────────────
# « brut » pour un morceau de ligne recopie tel quel, qui est le cas courant et
# se relit sans decoder d'echappement. « motif » pour ce qui s'etale sur des
# lignes dont on ne veut pas recopier le contenu — le bandeau de commentaire
# entre deux services, par exemple.
def brut(cherche, pose):
    return ("brut", cherche, pose)


def motif(cherche, pose):
    return ("motif", cherche, pose)


def appliquer(texte, edition):
    """Rend (texte mute, "") ou (None, raison). UNE occurrence, jamais zero.

    Zero occurrence est le cas qui compte : l'ancre a bouge, la mutation
    n'imite plus rien, et sans ce refus elle passerait pour appliquee. Plusieurs
    occurrences valent refus aussi : on ne sait plus laquelle on mute.
    """
    genre, cherche, pose = edition
    if genre == "brut":
        trouve = texte.count(cherche)
        neuf = texte.replace(cherche, pose)
    else:
        # lambda et non la chaine : un « \1 » ou un « \g » dans le remplacement
        # serait interprete, et une mutation se transformerait en silence.
        neuf, trouve = re.subn(cherche, lambda m: pose, texte, flags=re.M | re.S)
    if trouve != 1:
        return None, f"{trouve} occurrence(s) pour « {cherche.splitlines()[0][:60]} »"
    return neuf, ""


# ──────────────────────────────────────────────────────────────────────
#  banc_conteneur.py — dix-sept mutations, toutes verifiees rouges
# ──────────────────────────────────────────────────────────────────────
# Elles viennent de l'en-tete de banc_conteneur.py et des commits 537a205 et
# 77fb1ef, ou elles ont ete jouees a la main. Chacune dit la PANNE qu'elle
# imite, pas la manipulation : « OLLAMA_URL disparait du compose » se relit dans
# les deux lignes en dessous, « le studio ne trouve plus aucun Ollama » non.
CONTENEUR = [
    dict(
        nom="OLLAMA_URL retiree du compose et du Dockerfile",
        banc="banc_conteneur.py",
        imite="le studio en conteneur ne trouve plus aucun Ollama, et rien ne "
              "le dit : c'est la variable la plus importante du montage",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("docker-compose.yml", brut(
                '      OLLAMA_URL: "${OLLAMA_URL:-http://host.docker.internal:11434}"\n',
                "")),
            ("Dockerfile", brut("    OLLAMA_URL=http://ollama:11434 \\\n", "")),
        ]),
    dict(
        nom="un reglage deplace du compose vers le Dockerfile",
        banc="banc_conteneur.py",
        imite="la variable arrive bien au conteneur — avec la valeur de "
              "l'IMAGE, figee : ce qu'on pose dans .env reste lettre morte",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("docker-compose.yml", brut(
                '      STUDIO_TRAVAILLEURS: "${STUDIO_TRAVAILLEURS:-}"\n', "")),
            ("Dockerfile", brut("ENV COMFY_DIR=/comfy\n",
                                "ENV COMFY_DIR=/comfy\nENV STUDIO_TRAVAILLEURS=3\n")),
        ]),
    dict(
        nom="faute de frappe dans le nom substitue",
        banc="banc_conteneur.py",
        imite="la clef est relayee et sa valeur est vide POUR TOUJOURS : le "
              "reglage semble present et n'a jamais aucun effet",
        rougit="chaque ligne renvoie a SA variable",
        editions=[
            ("docker-compose.yml", brut(
                '      STUDIO_ANALYSE_MAX: "${STUDIO_ANALYSE_MAX:-}"',
                '      STUDIO_ANALYSE_MAX: "${STUDIO_ANALYSE_MAXX:-}"')),
        ]),
    dict(
        nom="faute de frappe sur une variable derivee",
        banc="banc_conteneur.py",
        imite="la banniere de demarrage annonce un port ou le studio ne repond "
              "pas, et sur une machine qui en heberge deux, cette adresse "
              "repond : c'est le studio d'a cote",
        rougit="chaque ligne renvoie a SA variable",
        editions=[
            ("docker-compose.yml", brut(
                '      STUDIO_PORT_HOTE: "${STUDIO_PORT:-8199}"',
                '      STUDIO_PORT_HOTE: "${STUDIO_PORTT:-8199}"')),
        ]),
    dict(
        nom="valeur figee non quotee dans le compose",
        banc="banc_conteneur.py",
        imite="le reglage est fige dans le YAML sans raison ecrite : .env ne "
              "peut plus rien pour lui, et personne ne sait pourquoi",
        rougit="aucune valeur figee sans raison ecrite",
        editions=[
            ("docker-compose.yml", brut(
                '      STUDIO_TRAVAILLEURS: "${STUDIO_TRAVAILLEURS:-}"',
                "      STUDIO_TRAVAILLEURS: 3")),
        ]),
    dict(
        nom="un reglage neuf lu par os.getenv",
        banc="banc_conteneur.py",
        imite="le scenario d'origine, rejoue sous le nez du filet ecrit pour "
              "lui : un reglage neuf lu hors conteneur, ignore dedans",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("serveur.py", brut(
                'TRAVAILLEURS = max(1, int(os.environ.get("STUDIO_TRAVAILLEURS") or 3))',
                'TRAVAILLEURS = max(1, int(os.environ.get("STUDIO_TRAVAILLEURS") or 3))\n'
                'REGLAGE_NEUF = os.getenv("STUDIO_NEUF", "")')),
        ]),
    dict(
        nom="le meme reglage neuf en apostrophes simples",
        banc="banc_conteneur.py",
        imite="la meme panne, ecrite dans l'autre sorte de guillemets — celle "
              "que le releve ne regardait pas",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("serveur.py", brut(
                'TRAVAILLEURS = max(1, int(os.environ.get("STUDIO_TRAVAILLEURS") or 3))',
                'TRAVAILLEURS = max(1, int(os.environ.get("STUDIO_TRAVAILLEURS") or 3))\n'
                "REGLAGE_NEUF = os.getenv('STUDIO_NEUF', '')")),
        ]),
    dict(
        nom="un reglage lu dans un module importe",
        banc="banc_conteneur.py",
        imite="la meme panne posee ailleurs que dans serveur.py : le module "
              "tourne dans le conteneur, sa variable n'y arrive pas",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("comptes.py", brut(
                "import secrets\nimport time\n",
                "import secrets\nimport time\n\n"
                'REGLAGE_NEUF = os.environ.get("STUDIO_NEUF", "")\n')),
        ]),
    dict(
        nom="les bandeaux retires, un reglage pose sur le conteneur voisin",
        banc="banc_conteneur.py",
        imite="COMFY_LANCEUR se retrouve dans la MAUVAISE machine apres un "
              "nettoyage anodin des commentaires : le studio ne le lit plus",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("docker-compose.yml", brut(
                '      COMFY_LANCEUR: "${COMFY_LANCEUR:-}"\n', "")),
            ("docker-compose.yml", brut(
                '      COMFY_ARGS: "${COMFY_ARGS:-}"\n',
                '      COMFY_ARGS: "${COMFY_ARGS:-}"\n'
                '      COMFY_LANCEUR: "${COMFY_LANCEUR:-}"\n')),
            ("docker-compose.yml", motif(r'^  #.*?(?=^  comfyui:)', "")),
        ]),
    dict(
        nom="une exception devenue inutile, sans guillemets",
        banc="banc_conteneur.py",
        imite="IMPOSEES affirme que l'image impose ce reglage alors que .env le "
              "gouverne : la liste des dispenses ment sur son propre contenu",
        rougit="aucune exception inutile",
        editions=[
            ("docker-compose.yml", brut(
                '      STUDIO_HOTE: "0.0.0.0"',
                "      STUDIO_HOTE: ${STUDIO_HOTE:-0.0.0.0}")),
        ]),
    dict(
        nom="un defaut du compose recopie en dur dans .env.exemple",
        banc="banc_conteneur.py",
        imite="deux maitres pour un reglage : le jour ou le defaut change, "
              "toute installation nee d'un « cp .env.exemple .env » garde "
              "l'ancien sans un mot",
        rougit="aucun defaut recopie en dur dans .env.exemple",
        editions=[(".env.exemple", brut("#ROUE=cu128", "ROUE=cu128"))],
    ),
    dict(
        nom="le meme defaut recopie, avec guillemets",
        banc="banc_conteneur.py",
        imite="la meme panne sous la forme que Compose nettoie a la lecture : "
              "les guillemets tombent, la valeur reste",
        rougit="aucun defaut recopie en dur dans .env.exemple",
        editions=[(".env.exemple", brut("#STUDIO_LLM=qwen2.5vl:7b",
                                        'STUDIO_LLM="qwen2.5vl:7b"'))],
    ),
    dict(
        nom="le meme defaut recopie, avec un commentaire en bout de ligne",
        banc="banc_conteneur.py",
        imite="l'autre forme que Compose nettoie : le commentaire tombe, la "
              "valeur reste",
        rougit="aucun defaut recopie en dur dans .env.exemple",
        editions=[(".env.exemple", brut("#COMFY_PORT=8188",
                                        "COMFY_PORT=8188  # le port de ComfyUI"))],
    ),
    # ── La troisieme relecture adverse ────────────────────────────────
    dict(
        nom="un module suivi importe a cote d'un import paresseux",
        banc="banc_conteneur.py",
        imite="serveur.py importe douze fois en cours de fonction ; un module "
              "importe la sortait du suivi, et le reglage qu'il lit n'arrivait "
              "jamais au conteneur — le commit f6a30ba rejoue entier",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("serveur.py", brut("import comptes as _comptes\n", "")),
            ("serveur.py", brut("        import av\n",
                                "        import av\n"
                                "        import comptes as _comptes\n")),
            ("comptes.py", brut(
                "import secrets\nimport time\n",
                "import secrets\nimport time\n\n"
                'CADENCE = os.getenv("STUDIO_CADENCE", "24")\n')),
        ]),
    dict(
        nom="un module suivi dont l'import passe en try / except ImportError",
        banc="banc_conteneur.py",
        imite="la meme sortie de suivi par un nettoyage encore plus banal : "
              "rendre un import facultatif indente sa ligne, et le releve ne "
              "lisait que la colonne 0",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("serveur.py", brut(
                "import comptes as _comptes\n",
                "try:\n    import comptes as _comptes\n"
                "except ImportError:\n    _comptes = None\n")),
            ("comptes.py", brut(
                "import secrets\nimport time\n",
                "import secrets\nimport time\n\n"
                'SEL_TOUR = os.environ.get("STUDIO_SEL_TOUR", "")\n')),
        ]),
    dict(
        nom="un module suivi charge par importlib",
        banc="banc_conteneur.py",
        imite="aucun import a relever, le module disparait du suivi sans qu'un "
              "seul chiffre bouge : les 25 variables sont toutes dans "
              "serveur.py, donc le releve ne peut pas s'en apercevoir",
        rougit="fichiers du conteneur sont suivis",
        editions=[
            ("serveur.py", brut(
                "import comptes as _comptes\n",
                '_comptes = importlib.import_module("comptes")\n')),
        ]),
    dict(
        nom="COMFY_MODELES en double, dans le compose ET dans .env.exemple",
        banc="banc_conteneur.py",
        imite="deux maitres pour un chemin dont le defaut est CALCULE par le "
              "code : defaut_du_code rendait « os.path.join(BASE_COMFY, », un "
              "fragment truthy qui court-circuitait le repli sur le compose et "
              "ne s'egalait jamais lui-meme",
        rougit="aucun defaut recopie en dur dans .env.exemple",
        editions=[
            ("docker-compose.yml", brut(
                '      COMFY_MODELES: "${COMFY_MODELES:-}"',
                '      COMFY_MODELES: "${COMFY_MODELES:-/comfy/models}"')),
            (".env.exemple", brut("#OLLAMA_PORT=11434\n",
                                  "#OLLAMA_PORT=11434\n"
                                  "COMFY_MODELES=/comfy/models\n")),
        ]),
]

# ──────────────────────────────────────────────────────────────────────
#  banc_page.py — onze mutations verifiees rouges (commit 21c443c)
# ──────────────────────────────────────────────────────────────────────
# Les cinq premieres viennent de 21c443c. Les cinq suivantes etaient des TROUS
# CONNUS : quatre trouvees par la relecture adverse, plus celle du point
# d'appel, trouvee en fermant la premiere. Les quatre trous ne faisaient qu'un
# seul et meme defaut de banc — quatre releves par expression reguliere qui
# decrivaient UNE facon d'ecrire la panne au lieu de la panne : le debut de
# ligne, le trait d'union, le mot au lieu de la classe, la forme de la
# propriete. Chacune a ete eprouvee dans les deux sens : rouge sur le banc
# repare, verte sur le banc d'avant sa correction, et verte sur le banc repare
# des trois AUTRES corrections seulement.
PAGE = [
    dict(
        nom="une pastille reprend le nom d'une classe de mise en page",
        banc="banc_page.py",
        imite="« .puce.moteur » : une pastille qui herite de display:flex, de "
              "flex-direction:column et des regles descendantes du panneau des "
              "machines — invisible tant que personne ne s'en sert",
        rougit="aucune pastille ne porte le nom d'une classe de mise en page",
        editions=[
            ("web/index.html", brut(
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}",
                ".puce.moteur{color:var(--braise)}\n"
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}")),
        ]),
    dict(
        nom="une regle de pastille qui n'est jamais posee",
        banc="banc_page.py",
        imite="une regle qui dort sans element : elle ne fait rien, elle ne "
              "leve rien, et le prochain qui la lit croit qu'elle sert",
        rougit="aucune pastille decrite sans etre jamais posee",
        editions=[
            ("web/index.html", brut(
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}",
                ".puce.fini{color:var(--vert)}\n"
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}")),
        ]),
    dict(
        nom="CLE_REGLAGE derive de MENU_REGLAGE",
        banc="banc_page.py",
        imite="le silence du 31 aout : deux tables inverses ecrites a deux "
              "cents lignes d'ecart, une seule qui derive, et un reglage cesse "
              "d'etre retenu sans que rien ne le dise",
        rougit="MENU_REGLAGE et CLE_REGLAGE disent la meme chose",
        editions=[
            ("web/index.html", brut('"#priorite": "priorite"', '"#priorite": "prio"')),
        ]),
    dict(
        nom="un reglage qui nomme un menu inexistant",
        banc="banc_page.py",
        imite="valeurReglage rend null pour toujours : le menu tourne dans le "
              "vide et la conversation ne retient plus rien",
        rougit="chaque reglage nomme un menu qui existe dans la page",
        editions=[
            ("web/index.html", brut('taille: "#taille" };', 'taille: "#tailles" };')),
        ]),
    dict(
        nom="le cran de priorite repart dans le corps de la demande",
        banc="banc_page.py",
        imite="un second onglet reste ouvert efface le cran du premier au "
              "simple envoi d'un message : le serveur raisonne sur la PRESENCE",
        rougit="aucun envoi ne renvoie le cran de priorite du menu",
        editions=[
            ("web/index.html", brut(
                "body: JSON.stringify({ texte: complet, conversation: cid,",
                "body: JSON.stringify({ texte: complet, conversation: cid,"
                ' priorite: $("#priorite").value,')),
        ]),
    # ── Les quatre trous fermes, et leur descendante ──────────────────
    dict(
        nom="le cran de priorite en abreviation ES6",
        banc="banc_page.py",
        imite="exactement la panne qui a lance ce fichier : la ligne fautive "
              "restauree sous sa vraie forme, « priorite, », que le releve ne "
              "voyait pas parce qu'il cherchait « priorite: $(\"#priorite\") »",
        rougit="aucun envoi ne renvoie le cran de priorite du menu",
        editions=[
            ("web/index.html", brut(
                "      if (reglageEnVol) { try { await reglageEnVol; } catch (e) {} }\n"
                '      const r = await fetch("/api/generer", {',
                "      if (reglageEnVol) { try { await reglageEnVol; } catch (e) {} }\n"
                '      const priorite = $("#priorite").value;\n'
                '      const r = await fetch("/api/generer", {')),
            ("web/index.html", brut(
                "body: JSON.stringify({ texte: complet, conversation: cid,",
                "body: JSON.stringify({ texte: complet, conversation: cid, priorite,")),
        ]),
    dict(
        nom="le cran de priorite entre par le point d'appel",
        banc="banc_page.py",
        imite="la panne d'origine dans sa VRAIE forme, relevee sur "
              "21c443c^ : le corps portait « priorite, » et le cran entrait "
              "deux mille lignes plus bas, en argument de lancerDemande. Ni "
              "« priorite: » ni « const » nulle part — la mutation ci-dessus, "
              "seule, se fermait sans fermer le defaut qu'elle imite",
        rougit="aucun envoi ne renvoie le cran de priorite du menu",
        editions=[
            ("web/index.html", brut(
                '$("#go").onclick = () => lancerDemande(null);',
                '$("#go").onclick = () => lancerDemande($("#priorite").value);')),
        ]),
    dict(
        nom="une classe de mise en page definie ailleurs qu'en debut de ligne",
        banc="banc_page.py",
        imite="« .puce.ligne » contre « .moteur .ligne » : le meme degat que "
              "« .puce.moteur », mais la classe heritee est definie en "
              "descendante — 24 classes sur 77 echappaient au releve",
        rougit="aucune pastille ne porte le nom d'une classe de mise en page",
        editions=[
            ("web/index.html", brut(
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}",
                ".puce.ligne{color:var(--braise)}\n"
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}")),
            # Posee pour de bon, sans quoi c'est « regle jamais posee » qui
            # rougirait — la mutation passerait pour attrapee alors que la
            # collision, elle, resterait invisible.
            # L'ancre a suivi la traduction de la page : le libelle
            # « brouillon » est passe par T(), et le litteral a disparu. La
            # classe, elle, n'a pas bouge — c'est elle que la mutation pose.
            ("web/index.html", brut(
                '(esquisse ? `<span class="puce esquisse">'
                '${ech(T("page.brouillon"))}</span>` : "");',
                '(esquisse ? `<span class="puce esquisse ligne">'
                '${ech(T("page.brouillon"))}</span>` : "");')),
        ]),
    dict(
        nom="un identifiant de menu a trait d'union",
        banc="banc_page.py",
        imite="« #forcer-moteur » : le reglage du moteur nomme un menu qui "
              "n'existe pas et cesse d'etre retenu. « \\w » ne franchit pas le "
              "trait d'union, donc l'entree DISPARAISSAIT des trois releves au "
              "lieu de rougir — le defaut du 31 aout dans sa forme la plus muette",
        rougit="chaque reglage nomme un menu qui existe dans la page",
        editions=[
            ("web/index.html", brut('modele: "#forcer"', 'modele: "#forcer-moteur"')),
            ("web/index.html", brut('"#forcer": "modele"', '"#forcer-moteur": "modele"')),
            # « nom » est une CLE du dictionnaire depuis la traduction de la
            # page : le mot francais n'y est plus, le selecteur si.
            ("web/index.html", brut('{ sel: "#forcer", nom: "page.moteur"',
                                    '{ sel: "#forcer-moteur", nom: "page.moteur"')),
        ]),
    dict(
        nom="une regle de pastille dont le nom traine dans du texte francais",
        banc="banc_page.py",
        imite="« .puce.file » dort sans element, et « en file — 3 devant », a "
              "deux lignes de la, suffisait a la faire passer pour posee : le "
              "releve cherchait un mot dans la ligne, pas une classe dans un "
              "attribut",
        rougit="aucune pastille decrite sans etre jamais posee",
        editions=[
            ("web/index.html", brut(
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}",
                ".puce.file{color:var(--encre-pale)}\n"
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}")),
        ]),
    dict(
        nom="le cran de priorite lu par document.getElementById",
        banc="banc_page.py",
        imite="la MEME faute de banc une cinquieme fois : LECTURES_DU_MENU "
              "etait litteralement trois facons d'ecrire, et l'ecriture la "
              "plus banale du navigateur — document.getElementById — n'y "
              "figurait pas. Verifie avant correction : ce banc restait vert",
        rougit="aucun envoi ne renvoie le cran de priorite du menu",
        editions=[
            ("web/index.html", brut(
                '$("#go").onclick = () => lancerDemande(null);',
                '$("#go").onclick = () => '
                'lancerDemande(document.getElementById("priorite").value);')),
        ]),
]

# ──────────────────────────────────────────────────────────────────────
#  Les trous connus : ecrits, nommes, et PAS ENCORE fermes
# ──────────────────────────────────────────────────────────────────────
# Celle-ci DOIT rougir et passe au vert aujourd'hui. Ce n'est pas une
# hypothese : elle a ete jouee, et le banc vise est reste vert. L'ecrire ici
# plutot que dans un rapport est le seul moyen qu'elle reste mesuree — le
# premier trou de ce genre a ete decouvert des mois trop tard, dans un rapport
# que personne n'a relu.
#
# Quand le banc saura la voir, elle rougira : il le dira, et il suffira de la
# deplacer dans PAGE ou CONTENEUR ci-dessus. Les quatre qui visaient
# banc_page.py y sont passees ; celle-ci demande d'EVALUER un defaut calcule et
# non de generaliser un releve. Les trois de verifier_formulations.py sont
# parties dans FORMULATIONS le 2 septembre : elles tenaient toutes a la meme
# cause — le banc recopiait la sequence de serveur.py au lieu de l'emprunter —
# et il l'emprunte desormais.
TROUS_CONNUS = [
    dict(
        nom="un defaut du compose qui repete un defaut CALCULE par le code",
        banc="banc_conteneur.py",
        imite="deux maitres pour COMFY_MODELES, et la verification ecrite pour "
              "ce piege ne peut pas le voir : le defaut du code est "
              "« os.path.join(BASE_COMFY, \"models\") », que le banc lit sans "
              "l'evaluer. Rendre None est honnete, mais quatre chemins et un "
              "port restent hors de portee de « pas deux defauts »",
        rougit="pas deux defauts pour un meme reglage dans le compose",
        editions=[
            ("docker-compose.yml", brut(
                '      COMFY_MODELES: "${COMFY_MODELES:-}"',
                '      COMFY_MODELES: "${COMFY_MODELES:-/comfy/models}"')),
        ]),
]

# ──────────────────────────────────────────────────────────────────────
#  banc_repartition.py — le studio sans carte se choisissait lui-meme
# ──────────────────────────────────────────────────────────────────────
# Signale par l'utilisateur : « il m'affiche souvent moteur local, le studio
# n'en a pas, uniquement les noeuds, et du coup attend dans le vide ». Trois
# endroits supposaient que le studio pouvait calculer ; les trois sont ici.
_AVEC_TOLERANCE = '    return vram + tolerance_ram(e.get("ram") or 0)'
_SANS_CARTE = ('    if not vram:' + chr(10)
               + '        return 0.0' + chr(10))

REPARTITION = [
    dict(
        nom="la tolerance RAM accordee a une machine SANS carte",
        banc="banc_repartition.py",
        imite="un studio sans GPU se presente comme une carte de 2 a 5 Go "
              "selon sa RAM, et se fait retenir pour les petits moteurs",
        rougit="et la tolerance RAM ne lui invente pas une carte de 5 Go",
        editions=[("serveur.py", brut(
            _SANS_CARTE + _AVEC_TOLERANCE, _AVEC_TOLERANCE))]),
    dict(
        nom="une machine SANS carte redevient candidate au rendu",
        banc="banc_repartition.py",
        imite="depuis que le rendu prend la PLUS PETITE, une machine a zero "
              "gigaoctet serait choisie la premiere : elle est la plus petite "
              "de toutes, et elle ne rend rien",
        rougit="mais « pas de carte, pas de rendu » l'ecarte quand meme",
        editions=[("serveur.py", brut(
            '        if not (e.get("vram") or 0):' + chr(10)
            + "            continue" + chr(10), ""))]),
    dict(
        nom="le rendu reprend la PLUS GROSSE carte",
        banc="banc_repartition.py",
        imite="la regle d'avant, que l'utilisateur a inversee : la grosse carte "
              "part en rendu et n'est plus la pour le suivant",
        rougit="a cartes libres, le rendu prend la PLUS PETITE qui tient",
        editions=[("serveur.py", brut(
            'petite = min(dans, key=lambda x: vram_de(x["id"]))',
            'petite = max(dans, key=lambda x: vram_de(x["id"]))'))]),
    dict(
        nom="l'analyse reprend la plus PETITE carte",
        banc="banc_cerveaux.py",
        imite="l'autre moitie de la regle inversee : l'analyse traine sur la "
              "petite carte pendant que la grosse attend le rendu qu'elle "
              "n'a pas encore lu",
        rougit="a cartes libres, la PLUS GROSSE d'abord",
        editions=[("serveur.py", brut(
            "bons.append((0 if libre else 1, -taille, url, ident))",
            "bons.append((0 if libre else 1, taille, url, ident))"))]),
    dict(
        nom="le verrou de carte oublie la priorite",
        banc="banc_repartition.py",
        imite="une analyse de trois secondes patiente derriere deux rendus de "
              "quatre minutes — huit minutes sans que rien ne parte, pour une "
              "demande que le studio n'a meme pas encore lue",
        rougit="puis l'analyse passe devant, et les rendus gardent leur ordre",
        editions=[("serveur.py", brut(
            "        file = self._attente[0 if prioritaire else 1]",
            "        file = self._attente[1]"))]),
    dict(
        nom="le relais recu par une attente annulee est emporte avec elle",
        banc="banc_repartition.py",
        imite="la carte a DEJA ete donnee quand l'annulation reveille celui "
              "qui la recevait : ne rien faire ici la laisse prise pour "
              "toujours — la machine est fermee pour de bon, et celui qui "
              "attendait derriere n'est jamais servi. Le cas qui disait "
              "eprouver cette branche n'annulait que depuis la FILE : il "
              "passait meme quand le except ne faisait rien",
        rougit="un relais recu par une attente annulee est RENDU, pas emporte",
        editions=[("serveur.py", brut(
            "                self._en_vol = False" + chr(10)
            + "                self._rendre()" + chr(10)
            + "            raise" + chr(10),
            "                pass" + chr(10) + "            raise" + chr(10)))]),

    # ── Les quatre corrections de 1ad6c0d qui vivent dans ce banc ──────
    dict(
        nom="le garde-fou du verrou retire : release() sert toujours",
        banc="banc_repartition.py",
        imite="A tient, B et C attendent, A relache DEUX fois — et C obtient la "
              "carte pendant que B calcule dessus. Trois calculs sur les memes "
              "gigaoctets, en silence et sans retour",
        rougit="une carte que personne ne tenait reste libre, et se reprend "
               "normalement apres",
        editions=[("serveur.py", motif(
            r'        if not self._tenu or self._en_vol:\n.*?\n            return\n',
            ""))]),
    dict(
        nom="le PORTAGE NAIF du garde-fou : « if not _tenu » tout seul",
        banc="banc_repartition.py",
        imite="ce que asyncio.Lock aurait donne, et qui n'attrape RIEN du cas "
              "reel : le passage de relais ne repasse jamais par « libre », "
              "_tenu reste vrai d'un porteur au suivant, donc « est-elle "
              "tenue ? » ne distingue pas le second release() de A du premier "
              "de B. La carte que personne ne tenait, elle, reste attrapee — "
              "c'est ce qui rend ce demi-portage credible et le fait passer",
        rougit="un release() de trop ne donne pas la carte a un second titulaire",
        editions=[("serveur.py", brut(
            "        if not self._tenu or self._en_vol:" + chr(10),
            "        if not self._tenu:" + chr(10)))]),
    dict(
        nom="le vieillissement reprend la main au lieu d'un tour",
        banc="banc_repartition.py",
        imite="une fois le seuil franchi, la nouvelle tete de la file des "
              "rendus a forcement attendu longtemps elle aussi : la condition "
              "reste vraie et TOUS les rendus passent avant TOUTES les "
              "analyses. Trois rendus de quatre minutes, et le message qu'on "
              "vient de taper attend douze minutes avant d'etre seulement lu — "
              "le symptome exact que cette classe existe pour empecher",
        rougit="un rendu qui a trop attendu prend UN tour, pas la main",
        editions=[("serveur.py", brut(
            chr(10) + "                 and not self._vient_de_ceder)", ")"))]),
    # ── C2, ET LA DECOUPE QUI MANQUAIT ────────────────────────────────
    # La correction repare DEUX defauts distincts — « viser=grosse » retombe
    # sur la carte moyenne, et la reprise descend sur une carte ou le moteur ne
    # tient pas — et le banc porte une ligne pour chacun. Une seule mutation
    # les couvrait toutes les deux : elle rougit sur les deux lignes a la fois,
    # donc la seconde n'avait jamais ete vue mordre SEULE. L'agent qui l'a
    # posee ecrivait n'avoir trouve aucune decoupe ; elle existe, et la voici.
    #
    # Les deux defauts naissent du MEME geste — l'ordre du filtre de charge et
    # du filtre natif — mais ils n'en dependent pas de la meme facon : « grosse »
    # se tranche AVANT tout filtre dans choisir_noeud, la descente se joue APRES.
    # Reparer l'un dans la copie sans reparer l'autre est donc possible, et
    # chaque demi-copie ci-dessous ne fait rougir QUE sa ligne. Mesure : la
    # copie entiere rend 46/48, chaque moitie 47/48.
    #
    # La copie entiere reste, et ce n'est pas un doublon : elle seule restaure
    # le code tel qu'il etait, mot pour mot. Les deux moities sont des
    # demi-reparations ecrites pour l'occasion — credibles, comme « le portage
    # naif » plus haut, mais inventees. On garde le vrai defaut ET ce qui isole.
    dict(
        nom="la regle de reprise recopiee au lieu d'etre appelee",
        banc="banc_repartition.py",
        imite="les vingt lignes que soumettre_robuste gardait pour lui, mot "
              "pour mot : elles filtrent la charge AVANT le natif — l'inverse "
              "de choisir_noeud — ignorent debordement_acceptable, et leur "
              "« viser=grosse » retombe sur la plus petite des que le natif "
              "manque. La copie rendait la carte MOYENNE quand on demandait la "
              "grosse, et descendait sur une carte ou le moteur ne tient pas. "
              "Elle rougit sur les DEUX lignes ; les deux mutations suivantes "
              "les separent",
        rougit="la reprise choisit comme le premier choix : viser=grosse garde "
               "la grosse carte",
        editions=[("serveur.py", brut(
            '            neuf = choisir_noeud(cle, viser=viser, taille=taille,'
            + chr(10) + '                                 exclus=ecartes) or autres[0]'
            + chr(10),
            '            moindre_ = min(charge_noeud(x["id"]) for x in autres)' + chr(10)
            + '            autres = [x for x in autres'
            + ' if charge_noeud(x["id"]) == moindre_]' + chr(10)
            + '            natifs_ = [x for x in autres'
            + ' if tient_vraiment(cle, x["id"])]' + chr(10)
            + '            entre = natifs_ or autres' + chr(10)
            + '            if viser == "grosse" or not natifs_:' + chr(10)
            + '                neuf = max(entre, key=lambda x: vram_de(x["id"]))' + chr(10)
            + '            else:' + chr(10)
            + '                neuf = min(entre, key=lambda x: vram_de(x["id"]))'
            + chr(10)))]),
    dict(
        nom="la copie de reprise, MOITIE « grosse » seule",
        banc="banc_repartition.py",
        imite="le natif est filtre le premier, comme dans choisir_noeud — donc "
              "la reprise ne descend PLUS sur une carte ou le moteur ne tient "
              "pas — mais la plus grosse se cherche encore APRES le filtre de "
              "charge. Un rendu qui vise deja la geante l'ecarte, et « refaire "
              "sur la grosse carte, quitte a l'attendre » rend la carte "
              "MOYENNE sans rien dire. L'autre moitie de C2 est laissee "
              "reparee ici ; c'est la mutation suivante qui la porte",
        rougit="la reprise choisit comme le premier choix : viser=grosse garde "
               "la grosse carte",
        editions=[("serveur.py", brut(
            '            neuf = choisir_noeud(cle, viser=viser, taille=taille,'
            + chr(10) + '                                 exclus=ecartes) or autres[0]'
            + chr(10),
            '            natifs_ = [x for x in autres'
            + ' if tient_vraiment(cle, x["id"])]' + chr(10)
            + '            entre = natifs_ or autres' + chr(10)
            + '            moindre_ = min(charge_noeud(x["id"]) for x in entre)' + chr(10)
            + '            entre = [x for x in entre'
            + ' if charge_noeud(x["id"]) == moindre_]' + chr(10)
            + '            if viser == "grosse" or not natifs_:' + chr(10)
            + '                neuf = max(entre, key=lambda x: vram_de(x["id"]))' + chr(10)
            + '            else:' + chr(10)
            + '                neuf = min(entre, key=lambda x: vram_de(x["id"]))'
            + chr(10)))]),
    dict(
        nom="la copie de reprise, MOITIE « natif » seule",
        banc="banc_repartition.py",
        imite="« viser=grosse » est tranche avant tout filtre et garde donc la "
              "grosse carte — la moitie precedente est reparee — mais le reste "
              "filtre la charge AVANT le natif, l'inverse de choisir_noeud. Une "
              "carte libre trop petite bat alors une carte chargee ou le moteur "
              "tient : le debordement devient le choix par defaut au lieu du "
              "recours mesure qu'il doit rester",
        rougit="et la reprise ne descend pas sur une carte ou le moteur ne "
               "tient pas",
        editions=[("serveur.py", brut(
            '            neuf = choisir_noeud(cle, viser=viser, taille=taille,'
            + chr(10) + '                                 exclus=ecartes) or autres[0]'
            + chr(10),
            '            natifs_ = [x for x in autres'
            + ' if tient_vraiment(cle, x["id"])]' + chr(10)
            + '            if viser == "grosse":' + chr(10)
            + '                neuf = max(natifs_ or autres,'
            + ' key=lambda x: vram_de(x["id"]))' + chr(10)
            + '            else:' + chr(10)
            + '                moindre_ = min(charge_noeud(x["id"])'
            + ' for x in autres)' + chr(10)
            + '                proches_ = [x for x in autres' + chr(10)
            + '                            if charge_noeud(x["id"]) == moindre_]' + chr(10)
            + '                natifs_ = [x for x in proches_'
            + ' if tient_vraiment(cle, x["id"])]' + chr(10)
            + '                entre = natifs_ or proches_' + chr(10)
            + '                if natifs_:' + chr(10)
            + '                    neuf = min(entre,'
            + ' key=lambda x: vram_de(x["id"]))' + chr(10)
            + '                else:' + chr(10)
            + '                    neuf = max(entre,'
            + ' key=lambda x: vram_de(x["id"]))' + chr(10)))]),
]

# ──────────────────────────────────────────────────────────────────────
#  banc_variantes.py — six mutations, une par panne de 3cecca2
# ──────────────────────────────────────────────────────────────────────
# Ce banc porte 115 verifications et n'en avait aucune d'eprouvee : le commit
# qui l'a porte de 101 a 115 le dit lui-meme — « aucune mutation ajoutee pour
# ces vingt-deux cas ». Les six ci-dessous ne prennent pas les cas un par un,
# elles reprennent les QUATRE pannes que 3cecca2 nomme, plus les deux ecritures
# de la regle du rang qu'il a fusionnees.
#
# Chacune restaure le code d'AVANT le correctif, mot pour mot quand c'est
# possible : une mutation qui invente une manipulation prouve que le banc voit
# quelque chose, pas qu'il voit la panne.
#
# ET CES DEUX-LA NE SE DATENT PAS COMME LES QUATRE AUTRES. La diagonale les a
# trouvees encore ROUGES sur le banc de 3cecca2^ — « le choix fait a la main »
# et « le rang 1 tout court ». 3cecca2 a fusionne la regle du rang, il ne l'a
# pas ecrite : ses deux gardes, « et elle ne reprend pas la place donnee a la
# troisieme » et « le groupe designe quand meme une image », datent de cac8aa7.
# C'est contre le banc de cac8aa7^ qu'elles passent au vert, et c'est la leur
# preuve inverse. Une mutation datee du mauvais commit se serait declaree
# prouvee contre un filet qui la voyait deja.
VARIANTES = [
    dict(
        nom="la mediatheque ne sert ni le tour ni le groupe",
        banc="banc_variantes.py",
        imite="« tour=None, groupe=None » et un 404 — releve sur le studio en "
              "service : POST /api/variante reclame la conversation ET le "
              "tour, le geste n'etait donc pas appelable depuis la grille, "
              "c'est-a-dire partout sauf la ou l'on compare quatre images "
              "indiscernables",
        rougit="chaque piece dit de quel tour elle sort",
        editions=[("serveur.py", brut(
            '                    "tour": tour.get("id"),' + chr(10)
            + '                    "groupe": groupe,' + chr(10),
            '                    "tour": None,' + chr(10)
            + '                    "groupe": None,' + chr(10)))]),
    dict(
        nom="la mediatheque sert la marque BRUTE au lieu de la reponse calculee",
        banc="banc_variantes.py",
        imite="trois vues, trois reponses : le fil encadrait la premiere, la "
              "mediatheque n'en marquait AUCUNE, et « agrandis-la » suivait "
              "encore une troisieme regle. Le tour ne porte « choisie » "
              "qu'apres un geste humain ; le studio, lui, vise le plus petit "
              "rang abouti des la fin du rendu",
        rougit="sans aucun choix humain, la mediatheque marque la premiere",
        editions=[("serveur.py", brut(
            '"choisie": (retenues.get(groupe) == tour.get("id") if groupe'
            + chr(10)
            + '                                else bool(tour.get("choisie"))),',
            '"choisie": bool(tour.get("choisie")),'))]),
    dict(
        nom="le choix fait a la main ne prime plus sur le rang",
        banc="banc_variantes.py",
        imite="la troisieme est designee pendant que la premiere calcule "
              "encore ; celle-ci, en finissant, reprend la place que "
              "l'utilisateur venait de donner a une autre — l'inverse exact de "
              "ce que la garde protege, et un clic qu'on ne peut pas refaire",
        rougit="et elle ne reprend pas la place donnee a la troisieme",
        editions=[("serveur.py", brut(
            "    if designee:" + chr(10) + "        return designee" + chr(10),
            ""))]),
    dict(
        nom="le rang 1 tout court, et non le plus petit rang ABOUTI",
        banc="banc_variantes.py",
        imite="quand le premier tirage echoue ou qu'on le retire de la file, "
              "plus AUCUNE variante ne devient l'image courante et "
              "« agrandis-la » vise en silence l'image d'avant le groupe",
        rougit="le groupe designe quand meme une image",
        editions=[("serveur.py", brut(
            "    return min(aboutis)[1] if aboutis else None",
            "    return next((i for r, i in aboutis if r == 1), None)"))]),
    # « la phrase du devis repasse aux minutes des 90 s » ETAIT ICI, et elle
    # est partie avec ce qu'elle mesurait, le 2 septembre 2026 au soir. Elle
    # ramenait DEVIS_EN_SECONDES_JUSQUA a 90 pour faire rougir « la phrase ne
    # s'ecarte jamais du champ de plus de 10 % » — un ecart qui n'existait que
    # parce que la page relisait la PHRASE du journal pour en tirer le chiffre
    # de sa pastille. Elle lit le champ (MARQUE_DEVIS) : la phrase peut
    # arrondir comme elle veut, plus personne n'en tire de nombre, et le seuil
    # ne decide plus que de la lisibilite d'une ligne de journal. Le cas qu'elle
    # nommait a ete retire de banc_variantes.py comme son propre commentaire
    # l'annonçait ; garder la mutation l'aurait rendue « MUTATION PERIMEE », ce
    # qui est un echec et non un succes silencieux.
    #
    # Ce qui la remplace est dans PROSE, et vise le vrai contrat plutot que son
    # symptome : « le champ du devis renomme d'un seul cote ».
    dict(
        nom="le devis d'un essai precedent survit a la relance",
        banc="banc_variantes.py",
        imite="la tache garde son identifiant d'une relance a l'autre : une "
              "demande repartie en brouillon, ou relancee apres l'effacement "
              "de ses rendus comparables, promettait encore le chiffre que "
              "plus aucune mediane n'etayait. La phrase du journal, elle, ne "
              "ment jamais ainsi — elle n'est simplement pas reecrite",
        rougit="sans mediane, le devis d'avant est retire et non laisse la",
        editions=[("serveur.py", brut(
            '            TACHES.get(tid, {}).pop("devis", None)',
            "            pass"))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_cerveaux.py — le plafond de la REFLEXION, qui n'est pas celui du RENDU
# ──────────────────────────────────────────────────────────────────────
# Les sept cas que 3cecca2 a ajoutes sur plafond_cerveau n'etaient couverts par
# rien. La panne qu'ils gardent est un piege a deux etages : « cette machine
# n'a pas de carte » s'y lisait « on ne sait pas ce qu'elle tient », et un zero
# qui veut dire « elle ne rend rien » devenait « elle peut tout charger ».
# Mesure du 31 aout, rejouee sur un noeud a agent annoncant vram=0 et ram=63,8 :
# gemma4:26b, 18,6 Go, choisi sur une carte de 11 — cent soixante-cinq secondes
# par traduction.
#
# La troisieme mutation garde la porte d'en face, et c'est pour cela qu'elle
# est la : le correctif pouvait tres bien fermer le cas « machine inconnue » en
# fermant le cas « machine sans carte », et personne ne l'aurait vu.
#
# CES DEUX-LA SE RECOUVRENT DANS UN SEUL SENS, et c'est verifie : retirer le
# plafond RAM allume AUSSI la ligne du repli, parce qu'un plafond infini fait
# que plus rien n'est jamais ecarte et que le repli ne s'emprunte plus. Le
# contraire est faux — inverser le repli n'allume que sa ligne. Les deux
# mesurent donc bien deux gardes, et non deux fois la meme.
CERVEAUX = [
    dict(
        nom="la machine SANS carte reperd son plafond",
        banc="banc_cerveaux.py",
        imite="la branche morte reveillee par 38cb9d0 : sans carte, "
              "_vram_utile rend 0, zero est faux, et « sinon aucun plafond » "
              "l'emporte. Le plafond disparait la ou il devait etre le plus "
              "bas — 165 s par traduction, le chiffre ecrit juste au-dessus "
              "dans le code",
        rougit="et pour ecrire, elle reste plafonnee",
        editions=[("serveur.py", brut(
            '    if e.get("ram"):' + chr(10)
            + '        return tolerance_ram(e["ram"])' + chr(10), ""))]),
    dict(
        nom="quand aucun voyant ne tient, le repli reprend le PLUS GROS",
        banc="banc_cerveaux.py",
        imite="la seconde porte : « tenables or voyants » puis max() rendait "
              "precisement le modele que le plafond venait d'ecarter, et le "
              "plafond ne servait plus a rien des qu'il mordait sur tout le "
              "monde. Une image mal lue par un petit modele se corrige ; neuf "
              "cents secondes a ne pas rendre, non (GTX 1060, 31 aout)",
        rougit="meme quand aucun voyant ne tient, c'est le plus petit qui repond",
        editions=[("serveur.py", brut(
            '    return min(voyants, key=lambda m: m.get("size", 0))["name"]',
            '    return max(voyants, key=lambda m: m.get("size", 0))["name"]'))]),
    dict(
        nom="la machine INCONNUE herite du plafond des machines sans carte",
        banc="banc_cerveaux.py",
        imite="la porte d'en face, celle qu'on ferme par erreur en fermant "
              "l'autre : on ne devine pas ce qu'une machine dont on ignore "
              "tout peut charger, et lui refuser ses gros modeles la rendrait "
              "muette pour rien",
        rougit="d'une machine inconnue, on prend le plus gros",
        editions=[("serveur.py", brut(
            "    if not ident:" + chr(10) + '        return float("inf")'
            + chr(10),
            "    if not ident:" + chr(10) + "        return 0.0" + chr(10)))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_cout.py — l'argent qui sort, et la comptabilite qui le dit
# ──────────────────────────────────────────────────────────────────────
# Soixante-dix-neuf verifications, aucune eprouvee. Les trois ci-dessous visent
# les trois endroits ou une erreur ne se voit PAS : un depassement de plafond
# paye pour de bon, une ligne perdue en silence a l'arret, et une depense
# rangee sous un compte qui n'existe pas.
#
# Ce banc imprime « RATE » et non « NON » — voir MARQUE_ROUGE plus haut.
COUT = [
    dict(
        nom="le plafond ne regarde plus que les appels DEJA consignes",
        banc="banc_cout.py",
        imite="la course d'origine : le compteur n'est ecrit qu'au RETOUR du "
              "fournisseur, donc pendant l'aller-retour il reste immobile et "
              "les trois travailleurs partent tous. Un appel parti est un "
              "appel paye, meme sans reponse — c'est de l'argent, pas un "
              "compteur",
        rougit="appels lances ensemble : un seul part",
        editions=[("serveur.py", brut(
            "    return appels_du_mois(compte) + _EN_VOL_NUAGE.get(compte, 0)",
            "    return appels_du_mois(compte)"))]),
    dict(
        nom="la vidange recompte la file avec qsize()",
        banc="banc_cout.py",
        imite="qsize() ne compte pas la ligne deja SORTIE de la file, celle "
              "que le fil tient pendant que le disque ne repond plus : un "
              "appel distant consigne a l'instant de l'arret disparait sans "
              "un mot, et le compte plafonne se rembourse en redemarrant. "
              "Mesure : 39 annonces pour 40 lignes reellement perdues",
        rougit="mais la vidange la compte quand meme",
        editions=[("serveur.py", brut("    return _A_ECRIRE.unfinished_tasks",
                                      "    return _A_ECRIRE.qsize()"))]),
    dict(
        nom="le journal se relit avec errors=replace",
        banc="banc_cout.py",
        imite="le remede evident, et il etait PIRE que le mal : un octet "
              "abime au milieu d'une ligne complete donne un JSON valide au "
              "nom de compte corrompu. Le studio demarre, la depense quitte le "
              "compte plafonne pour un compte fantome, et rien ne le dit — "
              "c'est le remboursement par redemarrage sous une autre forme",
        rougit="une ligne abimee est JETEE, pas rangee sous un compte fantome",
        editions=[("serveur.py", brut(
            '                    l = brut.decode("utf-8").strip()',
            '                    l = brut.decode("utf-8", "replace").strip()'))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_catalogue.py — « ~0 Go a prendre », une ligne avant le telechargement
# ──────────────────────────────────────────────────────────────────────
# Le chiffre sur lequel quelqu'un decide d'attendre quarante minutes. Les deux
# premieres mutations reprennent les deux facons de le fausser que le banc
# raconte : un affichage arrondi a zero, et une somme qui compte deux fois les
# fichiers que deux moteurs partagent.
#
# Les deux mutations d'affichage se prouvent contre le banc de 3bb235d^, ou
# elles passent au vert. « poids() additionne les moteurs », non : ce banc est
# NE avec elle, au commit 02fdae6, et il n'y a pas de filet d'avant.
#
# LA QUATRIEME, elle, vient de la relecture adverse du 1er septembre, et le
# banc a du etre repare pour la voir. Voir son commentaire.
CATALOGUE = [
    dict(
        nom="l'affichage sous le demi-gigaoctet repasse aux gigaoctets",
        banc="banc_catalogue.py",
        imite="« fluidifier : ~0 Go a prendre » — le defaut d'origine, mais "
              "par l'AFFICHAGE et non par la table : detourer pese 0,44 Go "
              "releve et agrandir 0,07, et « ~0 Go » se lit « c'est gratuit »",
        rougit="sous le demi-gigaoctet on passe aux megaoctets",
        editions=[("catalogue.py", brut(
            '        quantite = f"{exact * 1000:.0f} Mo"',
            '        quantite = f"{exact:.0f} Go"'))]),
    dict(
        nom="poids() additionne les moteurs au lieu de les unir",
        banc="banc_catalogue.py",
        imite="deux moteurs partagent des fichiers, et les additionner "
              "surestime le telechargement : la raison d'etre de poids(), que "
              "rien ne verifiait avant ce banc",
        rougit="et poids() les compte une seule fois",
        editions=[("catalogue.py", brut(
            "    return round(sum(TAILLES.get(f, 0.0) "
            "for f in fichiers_requis(cles)), 1)",
            "    return round(sum(TAILLES.get(f, 0.0) "
            "for c in cles for f in fichiers_requis([c])), 1)"))]),
    dict(
        nom="une taille jamais relevee s'annonce « au moins 0 Mo »",
        banc="banc_catalogue.py",
        imite="un plancher annonce comme un total : quand TOUT ce qui manque "
              "est justement ce qu'on ne sait pas mesurer, « au moins 0 » "
              "n'annonce rien du tout — et c'est le cas de fluidifier, celui "
              "par lequel le defaut a ete trouve",
        rougit="une taille jamais relevee s'annonce comme telle",
        editions=[("catalogue.py", brut(
            '        return "taille inconnue" if exact < 0.05 '
            'else f"au moins {quantite}"',
            '        return f"au moins {quantite}"'))]),
    dict(
        nom="le total de la proposition remis en phrase a la main",
        banc="banc_catalogue.py",
        imite="le second des deux TOTAUX que 02fdae6 avait laisses faux, "
              "restaure mot pour mot depuis 3bb235d^ : « environ 0 Go » sur "
              "la proposition qu'on accepte en tapant entree. Le banc ne "
              "regardait que le TEXTE de installation.py, avec un releve qui "
              "cherchait « poids » entre accolades — donc aucune des trois "
              "lignes fautives reelles ; il ne lisait jamais ce que "
              "l'installeur IMPRIME, et restait vert dessus",
        rougit="et le total de la proposition aussi",
        editions=[("installation.py", brut(
            "        total = annonce_poids(conseil)   "
            "# union : deux moteurs partagent des fichiers" + chr(10)
            + "        print(f\"\\n  Proposition : {', '.join(conseil)}  "
              "({total})\")",
            "        total = poids(conseil)      "
            "# union : deux moteurs partagent des fichiers" + chr(10)
            + "        print(f\"\\n  Proposition : {', '.join(conseil)}  "
              "(environ {total:.0f} Go)\")"))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_attente.py — une demande gardee, et un chiffre qui ne ment pas
# ──────────────────────────────────────────────────────────────────────
# Soixante-quatre verifications, aucune eprouvee. Les deux mutations visent les
# deux reglages qui mentaient sur ce qu'ils faisaient — c'est la meme faute
# deux fois, et c'est celle que ce projet traite comme pire qu'un reglage
# absent : l'administrateur croit avoir agi et s'en va.
ATTENTE = [
    dict(
        nom="le plancher de quinze secondes s'applique aussi au clic",
        banc="banc_attente.py",
        imite="api_admin_pause annoncait « reveillees: 0 » pendant que les "
              "demandes repartaient trente secondes plus tard par le veilleur. "
              "Mesure du 1er septembre : trois demandes armees, reponse "
              "« 0 relancee », trois departs une fois le plancher passe. Un "
              "chiffre faux est pire que pas de chiffre",
        rougit="le clic, lui, la reveille tout de suite",
        editions=[("serveur.py", brut(
            '        if plancher and time.time() - a.get("quand", 0) < 15:',
            '        if time.time() - a.get("quand", 0) < 15:'))]),
    dict(
        nom="la revision d'echeance repart de maintenant et non de « depuis »",
        banc="banc_attente.py",
        imite="un simple passage dans /admin repousse alors l'attente de "
              "toutes les demandes en cours — le rearmement que « depuis » "
              "avait justement ete introduit pour empecher, et l'expiration "
              "n'arrive jamais",
        rougit="elle est deja passee, et l'on sait POURQUOI",
        editions=[("serveur.py", brut(
            '        neuve = a.get("depuis", 0) + heures * 3600',
            "        neuve = time.time() + heures * 3600"))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_durees.py — la mediane, et pourquoi ce n'est pas la moyenne
# ──────────────────────────────────────────────────────────────────────
# Dix verifications, aucune eprouvee. Une seule mutation suffit ici : le banc
# tient en une phrase, et cette phrase est un choix qu'un lecteur presse
# defera. « Simplifier » sum()/len() ne change rien sur les jeux reguliers du
# banc — 100/110/120 ont la meme moyenne que leur mediane — et ne se voit QUE
# sur le rendu qui a attendu une carte occupee.
#
# SA PREUVE INVERSE N'EXISTE PAS, et c'est le seul aveu de la diagonale avec
# ADULTE et le poids() de CATALOGUE : banc_durees.py est NE avec la mediane, au
# meme commit 717fb23. Il n'y a pas de filet d'avant contre lequel la rejouer,
# et la moyenne n'a jamais ete dans le depot. Elle rougit ; on ne sait pas ce
# qu'elle mesure d'autre.
DUREES = [
    dict(
        nom="la moyenne au lieu de la mediane",
        banc="banc_durees.py",
        imite="un rendu qui a attendu une demi-heure derriere une carte "
              "occupee tire la moyenne a 682 s pour un travail qui en prend "
              "110, et le devis annonce onze minutes au lieu de deux : il ne "
              "dit plus rien de ce qui va se passer maintenant",
        rougit="un rendu qui a attendu ne fausse pas le devis",
        editions=[("serveur.py", brut("            return v[len(v) // 2], len(v)",
                                      "            return sum(v) / len(v), len(v)"))]),
    dict(
        nom="une seule case de cache, clefee sur « qui »",
        banc="banc_durees.py",
        imite="deux lecteurs se croisent dans la MEME demande — le devis lit "
              "les rendus du proprietaire, la repartition ceux de tout le "
              "studio — et chacun chasse l'autre : _relever_durees reparcourt "
              "TOUTES les conversations a chaque appel, deux fois par tirage, "
              "et FRAICHEUR_DUREES ne sert jamais. Mesure : 2 / 2 / 2 / 8 "
              "relevees sur quatre demandes, contre 2 / 0 / 0 / 0",
        rougit="deux lecteurs dans la meme demande ne relisent les "
               "conversations qu'une fois chacun",
        editions=[("serveur.py", brut(
            '    if pid not in _DUREES["tables"]:' + chr(10),
            '    if _DUREES["tables"].get("qui") != pid:' + chr(10)
            + '        _DUREES["tables"].clear()' + chr(10)
            + '        _DUREES["tables"]["qui"] = pid' + chr(10)
            + '    if pid not in _DUREES["tables"]:' + chr(10)))]),
    dict(
        nom="le devis compte les rendus de tout le monde",
        banc="banc_durees.py",
        imite="« d'apres TES 3 rendus precedents » compte ceux du voisin : le "
              "chiffre est faux, et il revele au passage le volume d'activite "
              "de quelqu'un d'autre. Un chiffre annonce comme personnel qui ne "
              "l'est pas fait perdre la confiance des qu'il ne colle pas",
        rougit="le devis est personnel, la decision de placement ne l'est pas",
        editions=[("serveur.py", brut(
            '        if pid is not None and conv.get("proprietaire") != pid:'
            + chr(10) + "            continue" + chr(10), ""))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_refaire.py — les six defauts de 1ad6c0d, dont celui de surete
# ──────────────────────────────────────────────────────────────────────
# /api/refaire a pris trois defauts d'affilee en deux jours et n'etait eprouve
# par RIEN. Le banc est ne avec la correction, comme banc_durees et banc_adulte
# avant lui : il n'existe donc pas de « filet d'avant » a opposer a ces
# mutations. Leur preuve inverse a ete prise autrement, et elle a repondu —
# serveur.py de 1ad6c0d^ restaure, le banc NEUF rougit sur onze lignes, et ce
# sont exactement les lignes que ces mutations nomment. C'est la meme mesure
# que celle prise pour banc_catalogue.py au commit 3bb235d.
#
# LES DEUX GARDES DE LA SURETE SE RECOUVRENT, et la premiere suffit a elle
# seule : « modele_impose » coupe choix_distant sans rien savoir du contenu.
# Chacune est donc mutee a la place de l'autre, et c'est le BANC qui isole —
# le cas du classement retire « modele_impose » de l'entree de file, le cas de
# « modele_impose » emploie un tour d'AVANT, qui ne porte aucun classement.
# Sans cette isolation, muter le classement laisserait le banc vert.
REFAIRE = [
    dict(
        nom="LA SURETE : « modele_impose » retire du plan reconstruit",
        banc="banc_refaire.py",
        imite="executer rappelle choix_distant() sur le plan rejoue, et un "
              "rendu marque explicite dont le TEXTE ne mord pas sur le motif "
              "repart chez un fournisseur — contre la regle « ce qui est adulte "
              "ne sort pas de la maison ». C'est la garde qui sauve le PASSE : "
              "les tours ecrits avant le 1er septembre ne porteront jamais de "
              "classement, et adulte() n'a donc rien a y lire",
        rougit="et le rendu ne part pas chez un fournisseur",
        editions=[("serveur.py", brut(
            '    plan["modele_impose"] = True' + chr(10)
            + "    # « refaire » et non « esquisse »",
            "    # « refaire » et non « esquisse »"))]),
    dict(
        nom="LA SURETE : « classement » perdu par la reconstruction",
        banc="banc_refaire.py",
        imite="le plan reconstruit retombe sur « safe » : une autre image en "
              "silence sur Pony, dont la table de score RETIRE la balise au "
              "lieu d'en poser une — et adulte() perd le seul indice qu'il "
              "avait quand le texte est anodin",
        rougit="et sans « modele_impose », c'est le classement qui le retient ici",
        editions=[("serveur.py", brut('"paroles", "classement", "raison"',
                                      '"paroles", "raison"'))]),
    dict(
        nom="« paroles » perdues par la reconstruction",
        banc="banc_refaire.py",
        imite="ecrire_paroles() est rappele et la chanson repart sur d'AUTRES "
              "paroles — c'est-a-dire exactement le passage par l'analyse que "
              "la docstring promet d'eviter",
        rougit="ecrire_paroles() n'est PAS rappele",
        editions=[("serveur.py", brut('"negatif", "paroles", "classement"',
                                      '"negatif", "classement"'))]),
    dict(
        nom="« negatif » perdu par la reconstruction",
        banc="banc_refaire.py",
        imite="le negatif retombe sur NEG_DEFAUT, donc une autre image, alors "
              "que le bouton promet « meme prompt, meme moteur, meme taille »",
        rougit="le negatif du tour est celui qui part a la carte, pas NEG_DEFAUT",
        editions=[("serveur.py", brut('("negatif", "paroles",', '("paroles",'))]),
    dict(
        nom="un tour d'avant le 31 aout repart sans taille",
        banc="banc_refaire.py",
        imite="KeyError: 'largeur' sur tout tour anterieur au 31 aout — le "
              "champ « taille » n'existe que depuis, et une conversation en "
              "garde soixante. « ERREUR inattendue : 'largeur' », un plantage "
              "muet, sur ce qui est le cas le plus frequent du bouton",
        rougit="il rend une image, au lieu de « ERREUR inattendue : 'largeur' »",
        editions=[("serveur.py", brut("            sans_taille = True" + chr(10),
                                      "            pass" + chr(10)))]),
    dict(
        nom="la taille reprise n'est plus annoncee",
        banc="banc_refaire.py",
        imite="le bouton promet « meme taille » et en rend une autre sans le "
              "dire. Un ecart annonce se lit ; un ecart muet fait douter du "
              "reste — et c'est le prix a payer pour ne PAS refuser tout "
              "l'historique",
        rougit="et le studio ANNONCE la taille qu'il a reprise",
        # Le CORPS de l'annonce a deja change deux fois en deux jours — et sa
        # GARDE une fois de plus : on l'ancre sur sa premiere ligne et l'on
        # avale ce qui suit tant que l'indentation le rattache, plutot que de
        # recopier une phrase qui bougera encore.
        editions=[("serveur.py", motif(
            r'    if sans_taille and plan\.get\("intention"\) == "image":\n'
            r'        journal\(tid, f"la taille de ce tour'
            r'[^\n]*\n(?:[ ]{8,}[^\n]+\n)*', ""))]),
    dict(
        nom="un moteur retire du catalogue passe quand meme",
        banc="banc_refaire.py",
        imite="le KeyError part jusqu'au « except Exception » d'executer et "
              "s'affiche tel quel — « ERREUR : 'sdxl_vieux' » — un message qui "
              "n'apprend rien a personne, et surtout pas que le moteur a "
              "disparu du catalogue",
        rougit="refaire un tour dont le moteur a disparu repond 400",
        editions=[("serveur.py", motif(
            r'    if moteur_ not in CATALOGUE:\n.*?status=400\)\n', ""))]),
    dict(
        nom="un rendu confie a un fournisseur passe quand meme",
        banc="banc_refaire.py",
        imite="un tour rendu au loin porte le nom du FOURNISSEUR dans "
              "« modele », et ce bouton-ci demande une CARTE : le laisser "
              "passer menait au meme KeyError, « ERREUR : 'veo' », un cran plus "
              "loin. Le 400, lui, tombe quand meme : le controle du catalogue "
              "repond a sa place, en conseillant de « choisir un autre "
              "moteur » alors qu'il n'y a rien a choisir. C'est la PHRASE qui "
              "rougit, pas le code de retour — et c'est bien pour cela que le "
              "banc les verifie separement",
        rougit="et la phrase nomme le fournisseur, au lieu de « ERREUR : 'veo' »",
        editions=[("serveur.py", motif(
            r'    if moteur_ in MOTEURS_DISTANTS:\n.*?status=400\)\n', ""))]),
    dict(
        nom="le MEME trou, laisse ouvert dans api_au_propre",
        banc="banc_refaire.py",
        imite="les deux boutons rejouent un plan garde des semaines plus tot ; "
              "ils ont donc tous les deux besoin de la garde, et api_au_propre "
              "ne l'avait pas. Le meme « ERREUR : 'sdxl_vieux' », a l'autre "
              "bouton",
        rougit="passer au propre une esquisse au moteur disparu repond 400",
        editions=[("serveur.py", motif(
            r'    if moteur_ not in CATALOGUE and moteur_ not in '
            r'MOTEURS_DISTANTS:\n.*?status=400\)\n', ""))]),
    dict(
        nom="un refait qui echoue garde son bouton",
        banc="banc_refaire.py",
        imite="la marque est posee AVANT le rendu, contre le second onglet ; "
              "laissee la sur un echec, elle fait disparaitre le bouton pour "
              "toujours et repondre 409 a jamais — alors que ce geste EST la "
              "reparation d'un rendu rate",
        rougit="la marque est retiree du tour d'origine : le bouton revient",
        editions=[("serveur.py", motif(
            r'^    if etat == "erreur".*?\n        for t in conv\["tours"\]:\n'
            r'            if t\.get\("refait"\) == tid:\n'
            r'                t\.pop\("refait", None\)\n', ""))]),
    dict(
        nom="la marque « refait » effacee par une reecriture du tour",
        banc="banc_refaire.py",
        imite="toute reecriture du tour d'origine — rattacher_tardif, une "
              "reprise apres redemarrage — efface la marque et repropose le "
              "bouton, donc un second rendu sur la grosse carte, sans que rien "
              "ne le dise",
        rougit="et la marque est toujours la apres la reecriture",
        editions=[("serveur.py", brut(
            '            if ancien.get("refait"):' + chr(10)
            + '                tour["refait"] = ancien["refait"]' + chr(10), ""))]),
    dict(
        nom="ecoule_rendu compte de nouveau l'attente de la carte",
        banc="banc_refaire.py",
        imite="le chrono part avant le verrou, donc il compte la file de la "
              "carte — alors que le devis auquel la page le compare est la "
              "mediane de tour[\"secondes\"], dont le chrono demarre apres la "
              "prise. Sur un parc a une seule carte, le second rendu etait "
              "rouge avant sa premiere etape",
        rougit="le chrono est repose la carte EN MAIN, apres l'attente",
        # Le chrono n'est pas supprime, il est REMIS ou il etait : dans
        # executer, avant l'appel. Le supprimer imiterait « pas de chrono du
        # tout », qui n'est pas la panne — celle-ci est un chrono qui part trop
        # tot et compte la file de la carte.
        editions=[
            ("serveur.py", brut(
                '                        TACHES[tid]["debut_rendu"] = time.time()'
                + chr(10), "                        pass" + chr(10))),
            ("serveur.py", brut(
                "        sorties, secondes = await soumettre_robuste(" + chr(10),
                '        TACHES.setdefault(tid, {})["debut_rendu"] = time.time()'
                + chr(10)
                + "        sorties, secondes = await soumettre_robuste(" + chr(10))),
        ]),
    # ── LE PLAN ENTIER SUR LE TOUR, 2 septembre 2026 ───────────────────
    # Cinq gardes, cinq mutations, une par garde. Elles ne se recouvrent pas :
    # la premiere retire le plan, la deuxieme le repli, la troisieme fait
    # diverger les deux chemins, la quatrieme ouvre la porte a ce que le modele
    # a invente, la cinquieme reprend le defaut de la chanson par le nouveau
    # chemin. Chacune est nommee sur une ligne que les autres ne touchent pas.
    dict(
        nom="le plan redevient reserve aux esquisses",
        banc="banc_refaire.py",
        imite="l'etat d'avant le 2 septembre : « refaire » reconstruit de "
              "nouveau le plan champ par champ sur tout rendu ordinaire, et "
              "cette liste-la avait deja coute six defauts en deux jours, dont "
              "un de surete. Le suivant sera le septieme, et il ne se verra "
              "qu'au rendu",
        rougit="un tour ordinaire porte desormais son plan",
        editions=[("serveur.py", brut(
            '        "plan": plan_du_tour(plan, cle),',
            '        "plan": plan_du_tour(plan, cle) if ((plan or {}).get("priorite")'
            + chr(10) + '                                       == "brouillon"'
            + chr(10) + '                                       and (plan or {}).get("intention")'
            + chr(10) + "                                       in ESQUISSE_POSSIBLE) else None,"))]),
    dict(
        nom="le repli des tours d'avant supprime avec la reconstruction",
        banc="banc_refaire.py",
        imite="le bouton devient inoperant sur tout l'historique — une "
              "conversation garde soixante tours, et ceux d'avant le "
              "2 septembre 2026 n'ont pas de plan. C'est exactement le defaut "
              "de 0f0f3dc, qui exigeait deja le plan et repondait 400 sur tout "
              "rendu ordinaire ; le nettoyage qui suit une bonne migration le "
              "rejoue tel quel",
        rougit="refaire y est accepte quand meme",
        editions=[("serveur.py", brut(
            '    elif tour.get("prompt"):',
            '    elif tour.get("plan") and tour.get("prompt"):'))]),
    dict(
        nom="le plan et le repli cessent de rendre la meme image",
        banc="banc_refaire.py",
        imite="le bouton rend une image differente selon l'AGE du tour sur "
              "lequel on a clique, et rien ne le dit. Deux chemins pour un "
              "seul geste ne valent que tant qu'ils s'accordent",
        rougit="meme prompt, meme negatif, meme taille, memes etapes a la carte",
        editions=[("serveur.py", brut(
            "        plan = dict(plan_)" + chr(10),
            '        plan = {c: v for c, v in plan_.items() if c != "negatif"}'
            + chr(10)))]),
    dict(
        nom="le tour recopie le plan tel quel, sans liste nommee",
        banc="banc_refaire.py",
        imite="le plan sort de json.loads(reponse du modele) : tout ce que le "
              "modele a invente est ecrit sur le disque de l'utilisateur et "
              "relu a chaque ouverture de conversation. C'est la seule chose du "
              "tour qui grossisse sans borne — et les marques de geste "
              "recopiees avec, dont « enrichissement_rate », qui fait reposer "
              "une question a la place de l'image",
        rougit="le plan ecrit ne porte que la liste nommee",
        editions=[("serveur.py", brut(
            "    garde = {c: plan[c] for c in PLAN_SUR_LE_TOUR if c in plan}",
            "    garde = dict(plan)"))]),
    dict(
        nom="« langue » et « tonalite » retirees de ce que le plan emporte",
        banc="banc_refaire.py",
        imite="le meme defaut qu'avant la migration, par l'autre chemin : "
              "g_audio retombe sur « en » et « C minor », et une chanson "
              "francaise refaite repart en annoncant l'anglais a ACE-Step, avec "
              "ses paroles francaises, dans une autre tonalite",
        rougit="et dans la MEME langue et la meme tonalite",
        editions=[("serveur.py", brut(
            '    "paroles", "langue", "tonalite", "tags_audio", "cases", "raison",',
            '    "paroles", "tags_audio", "cases", "raison",'))]),
    dict(
        nom="un rendu confie au loin ecrit quand meme son plan",
        banc="banc_refaire.py",
        imite="sur le chemin distant, plan[\"modele\"] porte le repli LOCAL et "
              "c'est « cle » qui nomme le fournisseur. Le plan ecrit sur le "
              "tour, la page affiche « FLUX.2 klein 9B » sous une image rendue "
              "par Nano Banana — elle lit « plan.modele » en premier et ne "
              "retombe sur le champ du tour qu'a defaut. Le detail perd au "
              "passage la ligne « fournisseur », que le plan borne ne garde pas",
        rougit="un rendu confie au loin n'ecrit pas de plan sur son tour",
        editions=[("serveur.py", brut(
            "    if not isinstance(plan, dict) or cle in MOTEURS_DISTANTS:",
            "    if not isinstance(plan, dict):"))]),
    dict(
        nom="la phrase du fournisseur devient injoignable dans api_au_propre",
        banc="banc_refaire.py",
        imite="l'effet exact de la remettre APRES le controle du plan, depuis "
              "qu'un rendu confie au loin n'ecrit plus de plan sur son tour : "
              "le controle du plan tombe le premier et cette phrase-ci n'est "
              "plus jamais atteinte. Une esquisse rendue chez un fournisseur "
              "recoit alors « ce tour n'est pas une esquisse qu'on sache "
              "refaire » — vrai de nulle part et utile a personne",
        rougit="et la phrase nomme le fournisseur, sans plan a lire",
        editions=[("serveur.py", motif(
            r'    rendu_par = tour\.get\("modele"\)\n'
            r'    if rendu_par in MOTEURS_DISTANTS:\n.*?status=400\)\n', ""))]),
    # ── L'ANNONCE DE TAILLE, ET LES DEUX FOIS OU ELLE MENTAIT ─────────
    # Deux gardes posees le 2 septembre sur la meme phrase, et deux mutations :
    # elles ne mordent pas au meme endroit — la premiere sur le PLAN mis en
    # file, la seconde sur le seul journal.
    dict(
        nom="le repli de taille reprend aussi la planche",
        banc="banc_refaire.py",
        imite="caler_taille() n'est jamais appele pour une planche sur le "
              "chemin normal, et la branche planche d'executer n'en lit pas le "
              "resultat : elle plafonne la largeur a 960 et tire la hauteur "
              "d'un rapport A4. Le 1216x832 pose ici ressort en 960x1344, le "
              "journal se contredit a deux lignes d'intervalle, et ce 1216x832 "
              "ment ensuite dans tour[\"taille\"] — donc dans la mediatheque, "
              "et dans la table des durees sur laquelle "
              "debordement_acceptable(exact=True) tranche un debordement de "
              "carte. Une mesure fausse qui decide d'un placement",
        rougit="le repli de taille ne pose PAS 1216x832 sur une planche",
        editions=[("serveur.py", brut(
            '    if sans_taille and plan.get("intention") == "image":' + chr(10)
            + "        plan = caler_taille(plan, texte)",
            '    if sans_taille and plan.get("intention") in ("image", "planche"):'
            + chr(10) + "        plan = caler_taille(plan, texte)"))]),
    dict(
        nom="l'annonce de taille parle a qui n'a pas de taille",
        banc="banc_refaire.py",
        imite="une chanson, une video, un objet 3D n'ont pas de resolution : "
              "« sans_taille » y est vrai par nature, et la PREMIERE ligne que "
              "voit quelqu'un qui refait une chanson devient « la taille de ce "
              "tour n'avait pas ete conservee — on laisse le studio la "
              "choisir ». Rien n'a ete conserve ni choisi : il n'y a pas de "
              "taille",
        rougit="et le journal ne parle pas de taille a une chanson",
        editions=[("serveur.py", brut(
            '    if sans_taille and plan.get("intention") == "image":' + chr(10)
            + '        journal(tid, f"la taille de ce tour',
            "    if sans_taille:" + chr(10)
            + '        journal(tid, f"la taille de ce tour'))]),
    # ── LES TROIS DEFAUTS DE LA DIXIEME RELECTURE ─────────────────────
    # Ils etaient nommes et laisses ouverts : aucun n'etait dangereux ce
    # jour-la, les trois etaient des pieges poses pour plus tard.
    #
    # LA PREUVE INVERSE DES CINQ PREMIERES a ete prise comme pour les douze
    # d'avant, ce banc etant ne avec ses corrections : serveur.py et
    # web/index.html d'avant restaures, les bancs NEUFS lances dessus. Les cinq
    # lignes nommees y rougissent. La sixieme est d'une autre famille — c'est le
    # BANC qui a ete corrige, pas le code — et son sens inverse se prend en
    # remettant la garde d'avant : la mutation repasse alors au VERT sur la
    # ligne qu'elle nomme, ce qui est exactement ce qu'on lui reprochait.
    dict(
        nom="le refus « deja passe au propre » perd sa marque",
        banc="banc_refaire.py",
        imite="la page n'a plus, pour reconnaitre ce refus-la parmi les trois "
              "de la route, que le TEXTE francais du message. Elle retire le "
              "bouton et pose une coche verte « deja refait en soigne » ; un "
              "accent, une reformulation, et elle le fait sur les deux refus "
              "ou rien n'a ete rendu. C'est le mensonge que d24980a avait "
              "ferme, et il tenait sur un mot",
        rougit="le second clic est refuse en 409 ET porte la marque",
        # RE-ANCREE le 2 septembre 2026 au soir : la phrase francaise a
        # laisse la place a une cle du dictionnaire. Le champ, lui, n'a pas
        # bouge d'un caractere — c'est tout l'interet d'un champ, et la
        # traduction vient de le montrer une seconde fois.
        editions=[("serveur.py", brut(
            '            {"erreur": T("erreur.deja_au_propre", lg),'
            + chr(10) + '             "deja": True}, status=409)',
            '            {"erreur": T("erreur.deja_au_propre", lg)},'
            + chr(10) + "            status=409)"))]),
    dict(
        nom="la marque « deja » posee sur un second refus",
        banc="banc_refaire.py",
        imite="l'AUTRE moitie du contrat, celle qui manquait : le refus « deja "
              "fait » etait bon, ce sont les autres qui mentaient. Une esquisse "
              "encore en cours recoit la coche verte et perd son bouton, alors "
              "que son rendu soigne n'a meme pas commence — et il ne sera "
              "jamais repropose",
        rougit="et aucun des cinq autres refus ne la porte",
        editions=[("serveur.py", brut(
            '            {"erreur": T("erreur.esquisse_pas_finie", lg)}, status=409)',
            '            {"erreur": T("erreur.esquisse_pas_finie", lg),'
            + chr(10) + '             "deja": True}, status=409)'))]),
    dict(
        nom="la coche « deja refait » redevient un test sur le TEXTE",
        banc="banc_page.py",
        imite="le contrat d'avant, du cote de la page cette fois : "
              "« /deja/i.test(d.erreur) ». Il tenait sur un mot du serveur, et "
              "RIEN ne reliait ce test aux chaines de serveur.py — ni "
              "banc_page.py ni recette_chemin_page.py ne contenaient « 409 » ni "
              "« deja ». Le serveur peut poser sa marque : si la page ne la lit "
              "pas, le mensonge revient entier",
        rougit="et la coche se decide sur ce champ, jamais sur le texte du message",
        editions=[("web/index.html", brut(
            "      if (!r.ok && d[MARQUE_DEJA]) {",
            '      if (r.status === 409 && /deja/i.test(d.erreur || "")) {'))]),
    dict(
        nom="les deux boutons refusent le rendu distant avec deux codes",
        banc="banc_refaire.py",
        imite="l'etat d'avant : api_au_propre refuse un rendu confie au loin en "
              "400, api_refaire en 409 — la meme classe de refus, deux codes. "
              "409 promet « rejoue-le, l'etat te laissera passer », et aucun "
              "second clic ne donnera de graine a un fournisseur. Sans danger "
              "tant que la page n'a aucun cas particulier sur les 409 de "
              "/api/refaire ; le jour ou elle recoit celui que « au propre » "
              "avait, la coche verte ment par l'autre porte",
        rougit="les deux boutons refusent un rendu confie au loin avec le MEME code",
        editions=[("serveur.py", brut(
            '                         titre=MOTEURS_DISTANTS[moteur_]["titre"])},'
            + chr(10) + "            status=400)",
            '                         titre=MOTEURS_DISTANTS[moteur_]["titre"])},'
            + chr(10) + "            status=409)"))]),
    dict(
        nom="et un moteur sorti du catalogue, avec deux codes aussi",
        banc="banc_refaire.py",
        imite="la seconde moitie du meme desaccord : les deux boutons rejouent "
              "un plan ecrit il y a des semaines, et le catalogue a bouge "
              "depuis. Ce n'est pas une concurrence — c'est l'etat GARDE qui a "
              "change, et il ne rechangera pas au second clic",
        rougit="et un moteur sorti du catalogue, de meme : 400, pas un conflit",
        editions=[("serveur.py", brut(
            '            {"erreur": T("erreur.moteur_hors_catalogue", lg, moteur=moteur_)},'
            + chr(10) + "            status=400)",
            '            {"erreur": T("erreur.moteur_hors_catalogue", lg, moteur=moteur_)},'
            + chr(10) + "            status=409)"))]),
    dict(
        nom="le repli de taille REFUSE au lieu de reprendre",
        banc="banc_refaire.py",
        imite="le bouton devient inoperant sur tout tour anterieur au 31 aout — "
              "c'est la tentation que le commentaire du repli ecarte en toutes "
              "lettres, « refuser rendrait le bouton inoperant sur tout "
              "l'historique ». Mais ce que cette mutation-ci eprouve, c'est le "
              "BANC : l'assertion de la planche lisait S.EN_FILE.get(None), "
              "donc {}, et se comptait verte sur une demande que la route "
              "venait de refuser. Elle ne pouvait pas distinguer « la garde "
              "marche » de « rien ne s'est passe », et la ligne voisine portait "
              "deja la garde qui lui manquait",
        rougit="le repli de taille ne pose PAS 1216x832 sur une planche",
        editions=[("serveur.py", brut(
            "            sans_taille = True" + chr(10),
            '            return web.json_response(' + chr(10)
            + '                {"erreur": "taille inconnue"}, status=400)' + chr(10)))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_adulte.py — le seul garde-fou code en dur du projet
# ──────────────────────────────────────────────────────────────────────
# Ce banc n'a pas de dit() : il liste ses fautes indentees sous leur compte,
# d'ou son entree dans MARQUE_ROUGE. La ligne nommee existe bel et bien — elle
# cite la demande qui est passee au travers — et c'est elle qu'on exige.
#
# Une seule mutation, et c'est la deuxieme des deux erreurs du 31 aout, celle
# qui a fait passer « a child in a sexual pose » : le souligne est un caractere
# de mot, donc « \\b » ne separe pas « nude » de « _body », et les moteurs a
# etiquettes recoivent justement du danbooru colle par des soulignes.
#
# SA PREUVE INVERSE N'EXISTE PAS NON PLUS. banc_adulte.py est ne avec la
# correction, au commit f467e11, et le banc d'aujourd'hui ne sait meme pas lire
# le serveur.py d'avant : _BORD, _FIN et _motif n'y existent pas, il s'arrete
# sur « introuvable dans serveur.py ». Ce qui l'etaye n'est donc pas une
# diagonale mais la mesure de f467e11 lui-meme — « 26 fautes sur la version de
# ce matin, dont les 8 refus manques » — et le troisieme effet qu'il nomme est
# exactement celui que cette mutation rejoue.
ADULTE = [
    dict(
        nom="les frontieres du motif redeviennent des « \\b » ordinaires",
        banc="banc_adulte.py",
        imite="tout le pan des etiquettes collees repasse : « nude_body », "
              "« sex_scene », « explicit_content », « rating_explicit » ne "
              "sont plus reconnus adultes — et le prompt envoye a la carte est "
              "TOUJOURS traduit en anglais, donc c'est par la que tout sort de "
              "la maison",
        rougit="adulte NON reconnu : « 1girl, nude_body »",
        editions=[("serveur.py", brut(
            '_BORD = r"(?<![^\\W_])"' + chr(10) + '_FIN = r"(?![^\\W_])"',
            '_BORD = r"\\b"' + chr(10) + '_FIN = r"\\b"'))]),
]


# ──────────────────────────────────────────────────────────────────────
#  verifier_formulations.py — le dernier banc sans mutation
# ──────────────────────────────────────────────────────────────────────
# Le plus vieux banc du depot, 64 formulations, et le seul jamais eprouve. Ce
# qui l'en tenait ecarte est ecrit plus haut : il nomme ses fautes par le
# NUMERO DE LIGNE de banc_formulations.jsonl, si bien qu'une ancre posee dessus
# se perimerait au premier cas insere au milieu du fichier. On l'ancre donc sur
# LA FORMULATION elle-meme — le banc l'imprime entre guillemets a cote du
# numero — et l'ancre survit alors a toute insertion.
#
# Les sept ci-dessous ne sont pas des manipulations plausibles : ce sont sept
# fautes qui ONT EU LIEU, reprises dans le code d'avant leur correction. Les
# trois dernieres etaient dans TROUS_FORMULATIONS jusqu'au 2 septembre : le
# banc ne les voyait pas, et la premiere est celle qu'il existe pour empecher.
#
# LEUR SENS INVERSE, pris le 2 septembre :
#   - « detaille » et les verbes de _PAS_LIRE sont VERTES sur le banc de
#     c6bfacd^ (55 cas), qui tourne encore sur le serveur.py d'aujourd'hui et y
#     rend 55/55. Preuve inverse pleine.
#   - « l arriere-plan avec une espace » n'a pas de filet d'avant : le banc est
#     NE avec la correction, e149893, et il a trouve la faute a son premier
#     essai. Le sens inverse a donc ete pris comme pour banc_refaire — le banc
#     de e149893 (30 cas) lance sur le serveur.py d'aujourd'hui MUTE. Il rougit,
#     et il rougit sur le SYMPTOME d'origine : « attendu detourer, obtenu
#     retoucher_sujet », le sujet efface a la place du fond. Le banc
#     d'aujourd'hui, lui, ne dit que « obtenu aucun » — sa ligne 4 ne porte pas
#     de piece jointe, donc la retouche ne s'ouvre pas. Il voit la faute, plus
#     la panne.
#   - « la cible NOMMEE » n'est prouvable ni d'une facon ni de l'autre, et il
#     faut le dire : la garde vient de bb7ab72, plus vieille que le banc, et le
#     serveur.py d'alors n'a pas encore veut_zone_nommee — le banc
#     d'aujourd'hui s'arrete dessus sur AttributeError. C'est le cas de
#     banc_durees et banc_adulte, une troisieme fois : une mutation rouge dont
#     on ne sait pas ce qu'elle mesure d'autre.
#
# LES TROIS ANCIENS TROUS, sens inverse pris le 2 septembre. Meme filet
# d'avant pour les trois, parce qu'elles tenaient toutes a la meme cause : le
# banc de a0a078c — celui qui RECOPIAIT la sequence, 64 cas — lance sur le
# serveur.py d'aujourd'hui MUTE. Il rend 64/64 sur les trois mutations, donc le
# trou etait bien la ; le banc d'aujourd'hui rougit sur les trois. Preuve
# inverse pleine, et c'est l'emprunt de raccourci_ecrit() plus les deux cas
# munis de leur piece jointe qui la donnent.
#   - La premiere rougit sur LE SYMPTOME D'ORIGINE de 25ce7d2, mot pour mot :
#     « attendu detourer, obtenu retoucher_sujet » — le sujet efface a la place
#     du fond, ce que le commit decrit.
#   - La troisieme est ISOLEE, et c'etait tout l'enjeu : sur sa mutation le
#     banc ne rougit QUE sur « vire le fond ». « supprime le fond », la
#     formulation d'origine, reste verte — _PAS_LIRE l'arrete avant. La ligne
#     nommee mesure donc la garde d'ambiguite, et elle seule.
#   - CE QU'ON NE PEUT PLUS FAIRE, et il faut le dire : lancer le banc NEUF sur
#     un serveur.py d'AVANT. Il appelle serveur.raccourci_ecrit(), qui
#     n'existe dans aucune version anterieure au 2 septembre, et s'y arreterait
#     sur AttributeError — comme sur le bb7ab72 de « la cible NOMMEE ». C'est
#     le prix de l'emprunt ; il est paye par le filet d'avant ci-dessus, qui
#     lui est une mesure pleine.
FORMULATIONS = [
    dict(
        nom="le detourage reattend « l arriere-plan » avec une espace",
        banc="verifier_formulations.py",
        imite="la faute qui a fait naitre ce banc : sans_accents() enleve les "
              "accents, pas les apostrophes. « retire l'arriere-plan » — la "
              "forme que tout le monde ecrit, et celle du corpus — ne "
              "correspondait a rien. Benigne tant que la demande partait au "
              "modele de langage, elle tombait depuis l'arrivee des moteurs de "
              "retouche sur la retouche du SUJET : fond transparent demande, "
              "sujet efface obtenu",
        rougit="« retire l'arriere-plan »",
        editions=[("serveur.py", brut(
            'r".{0,12}(?:le fond|l.?arriere.?plan|le decor)|"',
            'r".{0,12}(?:le fond|l arriere.?plan|le decor)|"'))]),
    dict(
        nom="« detaille » revient dans le motif de lecture",
        banc="verifier_formulations.py",
        imite="avec une image jointe, « detaille davantage le visage » demande "
              "PLUS DE DETAIL, pas une description — et le raccourci rendait un "
              "paragraphe la ou l'on attendait une image. Un verbe ambigu dans "
              "un raccourci ecrit coute plus qu'il ne rapporte : ce qu'on ne "
              "reconnait pas part au modele, comme avant",
        rougit="« detaille davantage le visage »",
        editions=[("serveur.py", brut(
            r'r"\b(decri[st]|decrire|raconte|analyse|commente|explique)\b"',
            r'r"\b(decri[st]|decrire|raconte|analyse|commente|detaille|explique)\b"'))]),
    dict(
        nom="les verbes de transformation les plus courants quittent _PAS_LIRE",
        banc="verifier_formulations.py",
        imite="mesure de c6bfacd : « analyse cette photo et corrige les "
              "couleurs » partait en description. Le raccourci de lecture est "
              "place AVANT le detourage et l'agrandissement — ce qu'il avale, "
              "aucun autre ne le voit, et l'utilisateur recoit un paragraphe au "
              "lieu de l'image qu'il demandait",
        rougit="« analyse cette photo et corrige les couleurs »",
        editions=[("serveur.py", brut(
            r'    r"|\b(corrige|supprime|efface|recadre|eclairci[st]?|assombri[st]?|floute?s?|"'
            + chr(10)
            + r'    r"applique|rends|augmente|reduis|nettoie|repare|detoure|isole|recolore|"'
            + chr(10)
            + r'    r"agrandis|reduis|coupe|rogne)\b"' + chr(10),
            ""))]),
    dict(
        nom="la retouche localisee cesse d'exiger une cible NOMMEE",
        banc="verifier_formulations.py",
        imite="« enleve le sujet » et « efface la personne » ne nomment rien de "
              "plus que ce que BiRefNet sait deja trouver. Sans cette garde ils "
              "partent sur SAM 3.1 : un modele que l'utilisateur n'a peut-etre "
              "pas telecharge, une traduction de la cible, et quinze secondes "
              "de carte pour un masque qu'on avait deja gratuitement",
        rougit="« enleve le sujet »",
        editions=[("serveur.py", brut(
            "    return bool(apres) and not re.match(" + chr(10)
            + '        r"^(le|la|l.|les)?'
            + r'\s*(sujet|personnage|personne|fond|arriere)", apres, re.I)',
            "    return bool(apres)"))]),

    # ── Les trois qui etaient des TROUS, et qui mordent depuis le 2 septembre ──
    # Elles ont ete jouees et le banc est reste vert sur les trois. La premiere
    # est la pire de tout ce fichier : c'etait LA PANNE QUE CE BANC EXISTE POUR
    # EMPECHER, citee dans son propre en-tete. Le motif etait celui de
    # « priorite, » : aiguillage_ecrit() RECOPIAIT la sequence de serveur.py au
    # lieu de l'emprunter, tout en promettant « toute permutation la-bas doit
    # se voir ici ». Il eprouvait les predicats veut_*, jamais leur ORDRE ni
    # les gardes qui les entourent — tout ce que 25ce7d2 et 83e334d corrigent.
    #
    # Ce qui les a fermees : la sequence est sortie d'aiguiller() dans
    # serveur.raccourci_ecrit(), que les DEUX empruntent maintenant ; deux cas
    # du jsonl ont recu la piece jointe qui leur manquait ; et le troisieme a
    # recu une formulation que la SECONDE garde ne voit pas.
    dict(
        nom="le detourage cesse de passer AVANT la retouche localisee",
        banc="verifier_formulations.py",
        imite="la panne d'origine, mot pour mot : « enleve le fond », « retire "
              "l'arriere-plan », « mets-la sur fond transparent » contiennent "
              "les memes verbes que la retouche, et sans cette garde ils "
              "remplacent le SUJET",
        rougit="« enleve le fond »",
        editions=[("serveur.py", brut(
            '    if a_une_image == "image" and not modele_choisi'
            + " and not veut_detourer(texte):",
            '    if a_une_image == "image" and not modele_choisi:'))]),
    dict(
        nom="« que » revient dans le mot qui dit qu'on vise une zone",
        banc="verifier_formulations.py",
        imite="« je voudrais QUE tu changes le style » et « est-ce QUE tu peux "
              "refaire cette image » partaient en retouche localisee. Le banc "
              "portait les deux formulations SANS piece jointe, et la retouche "
              "localisee ne s'ouvre qu'avec une image : elles n'atteignaient "
              "jamais le motif qu'elles devaient garder. Les deux cas la "
              "portent desormais",
        rougit="« je voudrais que tu changes le style »",
        editions=[("serveur.py", brut(
            r'_SEULEMENT = re.compile(r"\b(seulement|uniquement|juste)\b", re.I)',
            r'_SEULEMENT = re.compile(r"\b(seulement|uniquement|juste|que)\b", re.I)'))]),
    dict(
        nom="le raccourci de lecture ne refuse plus une phrase ambigue",
        banc="verifier_formulations.py",
        imite="« decris cette image puis supprime le fond » declenchait la "
              "lecture ET le detourage, et la lecture etant placee avant, "
              "l'utilisateur recevait un paragraphe au lieu de son image "
              "detouree. Ce cas-la ne pouvait pas servir d'ancre : « supprime » "
              "figure aussi dans _PAS_LIRE, ajoute par le MEME commit, et la "
              "seconde garde le voit deja — le piege des gardes qui se "
              "recouvrent, pour la quatrieme fois. « vire » n'est dans aucune "
              "des deux listes de _PAS_LIRE : la phrase ne franchit alors QUE "
              "la garde d'ambiguite, et c'est elle seule qu'on mesure ici",
        rougit="« decris cette image puis vire le fond »",
        editions=[("serveur.py", brut(
            "    if not _LIRE.search(nu):" + chr(10)
            + "        return False" + chr(10)
            + "    return not (veut_detourer(texte) or veut_agrandir(texte)" + chr(10)
            + "                or veut_fluidifier(texte) or veut_ralenti(texte)" + chr(10)
            + "                or veut_zone_nommee(texte) or veut_retoucher_fond(texte)"
            + chr(10)
            + "                or veut_retoucher_sujet(texte))" + chr(10),
            "    return bool(_LIRE.search(nu))" + chr(10)))]),
]


# ── Ce que la couverture coute, et ou part le temps ───────────────────
# Mesure du 1er septembre, sur cette machine : 8,4 s pour 32 mutations sur
# quatre bancs, 52,8 s pour 51 sur dix, 54,6 s pour 54. Le sextuplement ne
# vient pas du nombre mais des DEUX bancs qui montent un studio complet —
# banc_variantes.py met 3,5 s par lancement et banc_cout.py 2,9, la ou
# banc_catalogue.py en met 0,07. Les six mutations de banc_variantes pesent a
# elles seules 22 s. Les trois mutations ajoutees le 1er septembre au soir
# n'ont coute que 1,8 s : elles visent banc_page, banc_repartition et
# banc_catalogue, les bancs bon marche, et c'est delibere.
#
# 72,8 s pour 72 le 2 septembre, contre 54,6 pour 54 : les dix-huit mutations
# de 1ad6c0d coutent 18 s, soit une seconde chacune. banc_refaire.py monte un
# studio complet comme banc_variantes, mais il ne relit pas la page et ne
# temporise que 0,4 s : 0,9 s par lancement contre 3,5. C'est le prix d'une
# route qui a pris trois defauts en deux jours, dont un de surete — et il reste
# nettement en dessous de ce que banc_variantes coute deja.
#
# C'est le prix qu'on accepte, et il vaut la peine d'etre relu avant d'ajouter
# une mutation de plus sur ces deux bancs-la : une couverture qui vaut vingt
# secondes de CI par panne finirait par se faire couper, et un filet coupe ne
# mesure plus rien. Sur les huit autres bancs, une mutation neuve coute moins
# d'une demi-seconde — c'est la qu'il reste de la place.
#
# Les six mutations ajoutees le 2 septembre au soir tiennent dans la place qui
# restait : verifier_formulations.py met 0,8 s par lancement — il n'ouvre aucun
# reseau et ne temporise pas — et banc_repartition.py autant. Dix lancements de
# plus au total : les quatre mutations, les trois trous, le sien sur le depot
# sain, et les deux moities de C2. 7,3 s mesurees, sur les bancs bon marche.
#
# Les trois trous devenus mutations le 2 septembre au soir ne coutent RIEN de
# plus : ils etaient deja lances, seule la liste qui les porte a change. Mesure
# apres bascule : 95,2 s pour 90 mutations et 1 trou connu, contre 103 s pour
# 87 et 4 — le meme travail, au bruit de la machine pres.
#
# Les SIX de la dixieme relecture coutent 104,5 s pour 96 mutations, soit
# 9,3 s : cinq lancements de banc_refaire a 1,6 s et un de banc_page a 0,3 s.
# C'est plus que la seconde par lancement mesuree la veille sur ce banc-la — il
# monte maintenant un studio de plus, celui du cas « deja refait », qui rend une
# image. On reste loin des 3,5 s de banc_variantes, et c'est le prix de la seule
# route du depot dont la page traduit une reponse.
#
# Les TROIS de la garde de couverture coutent 3,4 s de plus : 117,1 s pour 99
# mutations, contre 113,7 s pour 96. Trois lancements de banc_multilingue, plus
# le quatorzieme lancement du sens direct — chacun fait passer 460 demandes
# deux fois, sous deux politiques, et cela tient en 1,1 s. Le classifieur coute
# 0,04 ms par demande et la garde 0,008 ms : c'est le prix d'un banc qui
# n'appelle rien.
#
# On ne les lance pas en parallele, et ce n'est pas un oubli : banc_variantes
# ordonne ses tirages par des sommeils de 0,02 a 0,6 s pour eprouver « le
# premier fini n'est pas celui qui tient le rang ». Huit processus qui se
# disputent les coeurs reordonnent ces tirages, et le banc deviendrait
# capricieux — un banc qui rougit au hasard vaut moins qu'un banc lent.
#
# CE N'EST PAS L'ORDRE DES RESULTATS QUI L'INTERDIT — il se garde en collectant
# les verdicts dans une liste indexee et en n'imprimant qu'a la fin. C'est la
# mesure du 2 septembre : ce fichier met 77,4 s seul, et le meme lancement a
# depasse 300 s pendant que deux autres travaux occupaient les coeurs de cette
# machine. Un facteur quatre par la seule charge, sur des bancs qui temporisent,
# dit exactement ce que huit processus simultanes leur feraient. Le gain
# attendu — environ 38 s — s'achete au prix d'un banc capricieux.
# ── La garde de couverture, et ce qui la retirerait « pour simplifier » ──
# ELLE GARDE UNE REGLE DONT L'EFFET EST INVISIBLE EN FRANCAIS. Les douze autres
# bancs du depot ne bougent pas d'un seul cas quand on l'enleve — verifie : les
# treize sont verts avec la garde comme sans. C'est tout l'interet de ces trois
# mutations-ci, et c'est aussi ce qui la rendrait facile a retirer dans six
# mois, au motif qu'elle ne sert a rien.
#
# LE SENS INVERSE, pris sur le depot de 2f46396 — le commit d'avant la garde,
# avec le seul aiguilleur.py neuf pour que SEUIL_LANGUE existe : banc_multilingue
# neuf y rougit sur QUATRE lignes, dont les trois que ces mutations nomment.
#
# ET LA QUATRIEME EST UNE LEÇON DEJA APPRISE LE MEME JOUR. « chaque demande
# etrangere retenue par la garde le dit dans le journal » se lisait d'abord
# « dits >= etr_avant - etr_apres », et cette ligne-la etait VERTE sur le code
# d'avant : « 0 lignes de journal pour au moins 0 pannes evitees ». Zero est
# bien superieur ou egal a zero. Elle ne distinguait pas « la garde le dit » de
# « il n'y a pas de garde » — le defaut exact que treize assertions de
# banc_refaire.py portaient ce matin-la. « dits > 0 » l'a fermee, et c'est le
# sens inverse qui l'a trouvee : une mutation verte n'est pas la seule facon
# qu'un filet a d'avoir un trou.
MULTILINGUE = [
    dict(
        nom="la garde de couverture est retiree du court-circuit",
        banc="banc_multilingue.py",
        imite="l'etat d'avant le 2 septembre 2026. Bayes naif ne sait pas dire "
              "« je ne connais pas ces mots » : sur une demande dont presque "
              "aucun trait n'est au corpus, le lissage de Laplace et les "
              "probabilites a priori departagent les classes tout seuls, et la "
              "marge peut etre grande pour de mauvais motifs. 25 des 26 pannes "
              "SILENCIEUSES de l'etranger passaient par ces trois lignes — une "
              "demande executee de travers, et pas un mot pour le dire",
        rougit="avec elle, les pannes silencieuses sont divisees par cinq au moins",
        editions=[("serveur.py", brut(
            "        connu = AIGUILLEUR.connu(texte)",
            "        connu = True"))]),
    dict(
        nom="la garde mord, mais sans le dire",
        banc="banc_multilingue.py",
        imite="une demande qui part au modele de langage PARCE QU'ON NE LA "
              "COMPREND PAS est le seul cas du studio ou cela arrive. Sans "
              "cette ligne de journal, l'utilisateur voit un appel de plus, "
              "0,32 s en moyenne, et personne — lui, l'auteur, un rapport de "
              "bogue — ne saura jamais dire pourquoi. La garde marcherait, et "
              "serait indefendable",
        rougit="chaque demande etrangere retenue par la garde le dit dans le journal",
        editions=[("serveur.py", brut(
            "        if (propose in SANS_ECRITURE and marge >= _aiguilleur.MARGE_SURE",
            "        if (False and propose in SANS_ECRITURE "
            "and marge >= _aiguilleur.MARGE_SURE"))]),
    dict(
        nom="la moisson reapprend les demandes etrangeres",
        banc="banc_multilingue.py",
        imite="POIDS_REEL a ete regle sur des demandes francaises entrant dans "
              "un corpus francais. Sur une demande etrangere il s'inverse : "
              "onze demandes allemandes confirmees font passer les pannes "
              "allemandes de 17 a 44 %, et la justesse ne bouge presque pas — "
              "c'est la CONFIANCE qui monte, donc le court-circuit qui tire "
              "plus souvent. Sur le banc francais, l'ajout ne change rien du "
              "tout : la degradation est invisible depuis tous les autres "
              "bancs du depot",
        rougit="et aucune des deux allemandes",
        editions=[("entrainer_aiguilleur.py", brut(
            '        garde = [x for x in reels if connu.connu(x["texte"])]',
            "        garde = list(reels)"))]),
]


# ──────────────────────────────────────────────────────────────────────
#  Les quatre contrats en PROSE du 2 septembre 2026 au soir
# ──────────────────────────────────────────────────────────────────────
# Quatre defauts d'une seule famille, celle que MARQUE_DEJA a ouverte le matin
# meme : DU TEXTE ECRIT POUR ETRE LU PAR UN HUMAIN SERVAIT DE CONTRAT A DU
# CODE. Une phrase de journal, un libelle de menu, un debut de message
# d'erreur, une exception Python. Chacun se defait en reformulant quelque chose
# qu'on a parfaitement le droit de reformuler, et aucun ne leve d'erreur.
#
# SEPT MUTATIONS POUR QUATRE CORRECTIONS : trois d'entre elles ont deux
# moities, et une moitie qu'on n'a jamais vue rougir ne mesure rien. Le libelle
# court a la sienne pour la lecture et une pour l'attribut ; le devis, une pour
# la page qui relit la phrase et une pour le champ renomme d'un seul cote ;
# l'arret differe, une par fichier.
#
# LE SENS INVERSE a ete pris comme pour les douze de banc_refaire.py : ces cas
# sont NES avec la correction, il n'existe pas de filet d'avant a leur opposer.
# serveur.py et web/index.html ont donc ete REMIS DANS LEUR ETAT D'AVANT — les
# editions de la correction defaites une a une dans un dossier temporaire, sans
# jamais toucher au depot — et les bancs NEUFS lances dessus :
#
#     banc_page.py         15/23, 8 rouges
#     banc_variantes.py   113/118, 5 rouges
#     banc_refaire.py      83/85, 2 rouges
#
# Les sept lignes que ces mutations nomment y sont toutes, une par une. C'est
# mieux qu'une diagonale : chacune a ete vue rougir sur le VRAI defaut, pas
# seulement sur son imitation.
#
# ET L'ISOLEMENT, releve mutation par mutation. Aucune ne rougit ailleurs que
# sur son propre contrat : quatre n'allument qu'une ligne, et les trois autres
# n'allument que l'autre moitie du meme contrat — « la page reteste le TEXTE »
# allume aussi la condition du « if », « la page relit le devis » allume aussi
# la regle generale des expressions regulieres, « le champ renomme » allume les
# trois cas qui lisent ce champ-la au bout de la route. Aucune ne touche a un
# cas d'un autre sujet.
PROSE = [
    dict(
        nom="la page reteste le TEXTE de l'arret demande",
        banc="banc_page.py",
        imite="« /^arret demande a /.test(t.erreur) » sur un « t.erreur » que "
              "la page vient d'ecraser six lignes plus haut : le contrat "
              "traverse deux fichiers ET une substitution, et une ligne de "
              "journal de plus coupe la relecture differee en silence",
        rougit="aucune expression reguliere ne s'applique a un texte ecrit pour etre lu",
        editions=[
            ("web/index.html", brut(
                'if (t.etat === ETAT.erreur && t[MARQUE_ARRET_DIFFERE])',
                'if (t.etat === ETAT.erreur '
                '&& /^arret demande a /.test(t.erreur || ""))')),
        ]),
    dict(
        nom="le serveur ne pose plus la marque de l'arret differe",
        banc="banc_variantes.py",
        imite="la page ne peut plus savoir qu'un « arret demande » est une "
              "PROMESSE : elle ne relit pas huit secondes plus tard, et la "
              "bulle reste sur la promesse pendant que la carte s'arrete",
        rougit="et /api/etat dit que ce mot-la n'est encore qu'une promesse",
        # RE-ANCREE le 2 septembre 2026 au soir : la ligne porte desormais
        # une cle de panne a cote de sa marque, et l'ancre d'avant s'arretait
        # sur la parenthese fermante. On ne retire QUE « arret_differe » —
        # retirer les deux ferait rougir deux contrats a la fois, et une
        # mutation qui en allume deux ne dit plus lequel elle mesure.
        editions=[
            ("serveur.py", brut("                    arret_differe=True,\n", "")),
        ]),
    dict(
        nom="la pastille redecoupe le libelle visible d'une option",
        banc="banc_page.py",
        imite="« o.textContent.split(\" — \")[0] » : le tiret cadratin d'un "
              "texte d'interface redevient un contrat de code, et reformuler "
              "« rapide — moins d'étapes » fait afficher la phrase entiere "
              "dans la pastille, sans un mot",
        rougit="et aucun libelle visible n'est recoupe sur le tiret cadratin",
        editions=[
            ("web/index.html", brut(
                '  return (o && (o.dataset.court || o.textContent)) || "";',
                '  return (o && o.textContent.split(" — ")[0]) || "";')),
        ]),
    dict(
        nom="une option perd son libelle court",
        banc="banc_page.py",
        imite="l'autre moitie du meme contrat : le lecteur est bon, mais "
              "l'option n'a rien a lui donner. La pastille retombe sur le "
              "libelle entier — « taille 1024 × 1024 — carré » — et le repli "
              "de courtDe() rend la panne parfaitement muette",
        rougit="chaque option d'un menu de reglage porte son libelle court",
        editions=[
            ("web/index.html", brut(
                '<option value="1024x1024" data-court="1024 × 1024" '
                'data-t="page.taille.1024x1024">',
                '<option value="1024x1024" data-t="page.taille.1024x1024">')),
        ]),
    dict(
        nom="la page relit le devis dans la phrase du journal",
        banc="banc_page.py",
        imite="RE_DEVIS restaure : le chiffre de la pastille est tire d'une "
              "phrase française par expression reguliere, virgule decimale "
              "comprise. Muet a la premiere reformulation, et faux de "
              "naissance — la phrase arrondit, « 2 min » pour 90 s mesurees",
        rougit="et le devis affiche vient de ce champ, jamais du journal",
        editions=[
            ("web/index.html", brut(
                """function lireDevis(t) {
  const d = (t || {})[MARQUE_DEVIS];
  return d && d.secondes && d.mot ? d : null;
}""",
                """function lireDevis(etapes) {
  for (let i = (etapes || []).length - 1; i >= 0; i--) {
    const m = RE_DEVIS.exec(etapes[i].msg || "");
    if (!m) continue;
    const combien = parseFloat(m[1].replace(",", "."));
    return { secondes: combien * (m[2] === "min" ? 60 : 1),
             mot: `${m[1]} ${m[2]}`, mesures: "" };
  }
  return null;
}""")),
            ("web/index.html", brut("const devis = lireDevis(t);",
                                    "const devis = lireDevis(t.etapes);")),
        ]),
    dict(
        nom="le champ du devis renomme d'un seul cote",
        banc="banc_variantes.py",
        imite="la page lit « estimation », la route sert « devis » : la "
              "pastille disparait pour toujours, et rien dans la page ne "
              "paraît faux — c'est le mensonge de MARQUE_DEJA pris par "
              "l'autre bout, celui du champ qui ne repond a personne",
        rougit="/api/etat sert le devis en chiffres, SOUS LE NOM QUE LA PAGE LIT",
        editions=[
            ("web/index.html", brut('const MARQUE_DEVIS = "devis";',
                                    'const MARQUE_DEVIS = "estimation";')),
        ]),
    dict(
        nom="l'exception Python de /api/reprendre repart a l'ecran",
        banc="banc_refaire.py",
        imite="« str(e) » sur un « except Exception » nu, sur une route dont "
              "la page affiche l'erreur telle quelle : « [Errno 13] Permission "
              "denied: '/comfy/input/…' » dans le bandeau d'alerte. Le meme "
              "« ERREUR : 'sdxl_vieux' » que les deux autres boutons ont ferme",
        rougit="et il le DIT, au lieu de « [Errno 13] Permission denied: … »",
        editions=[
            ("serveur.py", motif(
                r"        journal\(None, f\"reprise impossible.*?status=502\)\n",
                """        return web.json_response({"erreur": str(e)}, status=502)\n""")),
        ]),
]


# ──────────────────────────────────────────────────────────────────────
#  Les langues — neuf mutations, 2 septembre 2026 au soir
# ──────────────────────────────────────────────────────────────────────
# UNE TRADUCTION NE PLANTE PAS, ELLE MENT — et c'est ce qui rend ce filet-ci
# different des autres. Toutes les pannes imitees ci-dessous laissent le studio
# rendre 200, la page s'afficher entiere, et le rendu se faire. Aucune ne leve,
# aucune ne se voit depuis une console : elles se voient depuis l'ecran d'un
# lecteur anglais, que personne au studio ne regarde.
#
# QUATRE FAMILLES, et les deux premieres coutent le plus cher :
#
#   1. UN SITE DE PANNE SANS CLE. Le journal ne se traduit pas, mais la page
#      affiche sa DERNIERE ligne quand un rendu echoue : ce que l'utilisateur
#      lit apres une panne n'est pas un refus d'API, c'est du journal. Le
#      remede est une cle POSEE A COTE du texte francais — et un site oublie
#      renvoie simplement la phrase francaise a l'ecran, ce qui a exactement
#      l'air de ce que le studio faisait avant.
#   2. LA CLE ET LA LIGNE QUI DERIVENT. Les deux moities existent, chacune est
#      juste, et elles ne disent plus la meme chose. C'est MARQUE_DEJA applique
#      au CONTENU et non au nom du champ : reformuler la phrase de serveur.py
#      ne casse rien, et le lecteur anglais recoit un message que plus personne
#      n'ecrit.
#   3. LA LANGUE QUI NE SE CHOISIT PLUS. « Accept-Language » dit la langue du
#      NAVIGATEUR, pas celle de la personne. Le cookie retire, un francophone
#      sur un Windows anglais est servi en anglais pour toujours, sans jamais
#      comprendre pourquoi — et le menu paraitra ne rien retenir.
#   4. LA ROUTE DES TEXTES. La page est servie en FileResponse : elle DEMANDE
#      ses textes, et si la route se ferme derriere exiger_compte, l'ecran de
#      connexion — le seul qu'un visiteur non connecte voie — reste francais
#      pour toujours.
#
# LE SENS INVERSE : ces cas sont NES avec la correction, il n'existe pas de
# filet d'avant a leur opposer. serveur.py, traductions.py et les deux bancs
# ont donc ete remis dans leur etat d'AVANT, edition par edition, dans un
# dossier temporaire — jamais dans le depot — et les bancs NEUFS lances dessus.
LANGUES = [
    dict(
        nom="un site de panne oublie sa cle",
        banc="banc_traductions.py",
        imite="« retiree de la file » repart a l'ecran en francais quel que "
              "soit le lecteur. Rien ne leve, la bulle se garnit, le bouton "
              "« relancer » est la : c'est exactement ce que le studio faisait "
              "avant qu'on traduise, et c'est pour cela que personne ne le "
              "verrait",
        rougit="chaque journal(..., etat=erreur) pose une cle a cote de sa phrase",
        editions=[
            ("serveur.py", brut(
                '''        journal(tid, "retiree de la file", etat="erreur",
                **marque_panne("panne.retiree_de_la_file"))''',
                '''        journal(tid, "retiree de la file", etat="erreur")''')),
        ]),
    dict(
        nom="echouer() appele sans la cle de sa phrase",
        banc="banc_traductions.py",
        imite="l'autre moitie de la meme famille, et la plus sournoise : le "
              "gabarit « ERREUR : {quoi} » est traduit, son contenu non. Le "
              "lecteur anglais recoit « ERROR: la machine n'est pas revenue a "
              "temps » — une DEMI-phrase traduite, qui se remarque moins "
              "qu'une phrase entierement francaise et trompe donc plus "
              "longtemps. Trois des cinq sites d'appel etaient dans cet etat",
        rougit="et chaque appel a echouer() nomme la phrase qu'il lui passe",
        editions=[
            ("serveur.py", brut(
                '''        echouer(tid, "la machine n'est pas revenue a temps",
                panne_de("panne.machine_pas_revenue"))''',
                '''        echouer(tid, "la machine n'est pas revenue a temps")''')),
        ]),
    dict(
        nom="une cle mal orthographiee au site d'appel",
        banc="banc_traductions.py",
        imite="T() rend la CLE quand elle est inconnue, et ne leve pas — c'est "
              "voulu, un studio qui rend 500 est pire. Mais alors la bulle "
              "affiche « panne.interompue » a la place du message, dans "
              "TOUTES les langues, francais compris. Une lettre",
        rougit="et toute cle citee par le serveur existe au dictionnaire",
        editions=[
            ("serveur.py", brut('**marque_panne("panne.interrompue")',
                                '**marque_panne("panne.interompue")')),
        ]),
    dict(
        nom="la cle et la ligne de journal derivent",
        banc="banc_refaire.py",
        imite="les deux moities existent, chacune est juste, et elles ne "
              "disent plus la meme chose. Le studio ecrit « ERREUR : … » dans "
              "son journal, le dictionnaire rend « ECHEC : … » : le francais "
              "de la page cesse d'etre celui du studio, et un rapport de bogue "
              "cite une phrase qu'aucun fichier ne contient",
        rougit="et cette cle, rendue en francais, EST la ligne du journal",
        editions=[
            ("traductions.py", brut(
                '''    "panne.echec": {
        "fr": "ERREUR : {quoi}",''',
                '''    "panne.echec": {
        "fr": "ECHEC : {quoi}",''')),
        ]),
    dict(
        nom="l'en-tete du navigateur decide de la langue",
        banc="banc_refaire.py",
        imite="le cookie n'est plus lu : « Accept-Language » ne sert plus de "
              "premiere valeur, il DECIDE. Un francophone sur un Windows "
              "anglais est servi en anglais pour toujours ; il ouvre le menu, "
              "choisit « francais », et la page revient en anglais sans qu'un "
              "mot le lui dise. C'est la panne que docs/plusieurs-langues.md "
              "refuse en toutes lettres",
        rougit="un francophone sur un Windows anglais revient au francais, et y reste",
        editions=[
            ("serveur.py", brut(
                '''    return traductions.langue_choisie(req.cookies.get(COOKIE_LANGUE) or "",
                                      req.headers.get("Accept-Language") or "")''',
                '''    return traductions.langue_choisie("",
                                      req.headers.get("Accept-Language") or "")''')),
        ]),
    dict(
        nom="un refus repart en francais, ecrit en dur",
        banc="banc_refaire.py",
        imite="la phrase d'avant, remise a sa place au fil d'une reecriture — "
              "le geste le plus banal du monde. Le refus est juste, le code de "
              "retour est juste, le francais est parfait : seul l'anglophone "
              "voit du francais, et il est seul a le voir",
        rougit="et l'anglais est de l'anglais, pas la meme phrase servie deux fois",
        editions=[
            ("serveur.py", brut(
                '''        return web.json_response(
            {"erreur": T("erreur.moteur_hors_catalogue", lg, moteur=moteur_)},
            status=400)''',
                '''        return web.json_response(
            {"erreur": f"le moteur de ce tour ({moteur_}) n'est plus au "
                       f"catalogue : relance la demande pour en choisir un autre"},
            status=400)''')),
        ]),
    dict(
        nom="la route des textes n'en sert qu'une partie",
        banc="banc_refaire.py",
        imite="les refus d'API sont servis, l'interface non : la page recoit "
              "un sous-ensemble et rend la CLE partout ou elle manque. Les "
              "boutons s'appellent « compte.echanges », et seulement chez "
              "celui qui a change de langue",
        rougit="GET /api/textes sert TOUTES les cles, jamais un sous-ensemble",
        editions=[
            ("serveur.py", brut(
                '''    rep_ = web.json_response({"langue": lg, "langues": list(traductions.LANGUES),
                              "textes": traductions.textes_de(lg)})''',
                '''    rep_ = web.json_response({"langue": lg, "langues": list(traductions.LANGUES),
                              "textes": {c: v for c, v
                                         in traductions.textes_de(lg).items()
                                         if c.startswith("erreur.")}})''')),
        ]),
    dict(
        nom="le choix de langue n'est plus pose en cookie",
        banc="banc_refaire.py",
        imite="la route repond dans la bonne langue, une fois. Au rechargement "
              "suivant, langue_choisie() retombe sur l'en-tete : le menu "
              "paraît ne rien retenir, et l'utilisateur rechoisit sa langue a "
              "chaque visite sans jamais comprendre pourquoi",
        rougit="et le choix est POSE en cookie : il survit au rechargement",
        editions=[
            ("serveur.py", motif(r'    if pose:\n.*?path="/"\)\n    return rep_\n',
                                 "    return rep_\n")),
        ]),
    dict(
        nom="la route des textes se ferme derriere la connexion",
        banc="banc_refaire.py",
        imite="en STUDIO_AUTH=obligatoire, le seul ecran qu'un visiteur non "
              "connecte voie est le formulaire de connexion — et c'est le seul "
              "qui reste francais. On traduit tout SAUF ce que lit celui a qui "
              "le studio n'a encore rien montre d'autre, y compris le refus "
              "« connexion requise » lui-meme",
        rougit="connexion obligatoire : tout est ferme, sauf les textes",
        editions=[
            ("serveur.py", brut('             or chemin == "/api/textes"\n', "")),
        ]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_page.py — la page en deux langues, seize mutations
# ──────────────────────────────────────────────────────────────────────
# Le point 6 de docs/plusieurs-langues.md, cote NAVIGATEUR : ~195 chaines, un
# T() avec sa propre copie de la regle du pluriel, le rendu des pannes, et le
# quatrieme des quatre chantiers qui « ne sont pas de la traduction » — les
# valeurs de protocole qui se confondaient avec les libelles.
#
# CE QUI PEUT CASSER SANS QUE RIEN NE LEVE, ET QUE CES QUINZE-LA IMITENT :
#
#   1. LE FRANCAIS QUI DERIVE D'UN SEUL COTE. C'est la plus importante, et
#      c'est MARQUE_DEJA applique a cent quatre-vingt-quinze chaines : la page
#      francaise reste juste, rien ne leve, et le lecteur anglais recoit une
#      traduction de la phrase d'AVANT. Personne au studio ne l'apprend.
#   2. UN ATTRIBUT QUI SE LIT ET QU'ON OUBLIE. Un aria-label ajoute sans cle
#      ne se VOIT pas — il s'entend, et seulement chez quelqu'un d'autre.
#   3. LA REGLE DU PLURIEL RECOPIEE. La page comptait « ${n} echange${n > 1 ?
#      "s" : ""} » : la regle FRANCAISE, dans du code d'interface, fausse en
#      anglais des zero.
#   4. LES VALEURS DE PROTOCOLE PRISES POUR DES LIBELLES. « en cours »,
#      « fini », « brouillons » voyagent jusqu'au serveur et sont ECRITES dans
#      les conversations deja enregistrees. Les traduire relit tout
#      l'historique de travers ; les laisser en clair a cote d'une etiquette
#      laisse une passe naive toucher les deux moities du meme litteral.
#   5. LA PANNE QUI NE SE LIT PLUS, OU QUI PERD SON REPLI. La bulle affiche la
#      derniere ligne de journal apres un echec — c'est le message le plus lu
#      du studio. Sans la marque, il reste francais ; sans le repli, une tache
#      relue apres redemarrage n'affiche RIEN.
#
# LE SENS INVERSE : ces seize cas sont NES avec la correction — banc_page.py
# ne relevait rien de tout cela avant, et lancer le banc NEUF sur la page
# d'AVANT ne rougirait pas, il MOURRAIT (« const PLURIELS » n'y existe pas,
# « <select id="langue"> » non plus : les releves rendent des listes vides et
# le banc s'arrete sur un IndexError). C'est le cas que CONTRIBUTING.md prevoit
# — « ecris-le quand tu ne peux ni l'un ni l'autre » — et l'on a mesure
# l'ISOLEMENT a la place : chaque mutation, SEULE, allume la ligne qu'elle
# nomme et elle seule, et le depot sain reste vert sur les trente-huit.
PAGE_LANGUES = [
    dict(
        nom="le francais de la page derive de celui du dictionnaire",
        banc="banc_page.py",
        imite="la page francaise reste juste, rien ne leve, et le lecteur "
              "anglais recoit la traduction de la phrase d'AVANT. C'est "
              "MARQUE_DEJA applique au CONTENU, sur cent quatre-vingt-quinze "
              "chaines : une reformulation d'un seul cote ne casse rien, elle "
              "ment",
        rougit="chaque texte francais du HTML est EXACTEMENT celui du dictionnaire",
        editions=[
            ("web/index.html", brut(
                'data-t="page.reglages">réglages</button>',
                'data-t="page.reglages">préférences</button>')),
        ]),
    dict(
        nom="un aria-label ajoute sans sa cle",
        banc="banc_page.py",
        imite="le defaut le plus silencieux de tous : il ne se voit pas, il "
              "s'entend — et pas par celui qui l'ecrit. Un lecteur d'ecran "
              "anglophone s'entend annoncer « Nouvelle conversation » au "
              "milieu d'une interface anglaise, et rien a l'ecran ne le montre",
        rougit="chaque titre, invite et aria-label du HTML passe par une cle",
        editions=[
            ("web/index.html", brut(
                '<button class="neuve" id="neuve" data-t="page.conv.neuve">',
                '<button class="neuve" id="neuve" aria-label="Nouvelle conversation"'
                ' data-t="page.conv.neuve">')),
        ]),
    dict(
        nom="une cle citee par la page n'existe pas au dictionnaire",
        banc="banc_page.py",
        imite="T() rend la CLE quand elle est inconnue, et ne leve pas — un "
              "studio qui rend une page blanche est pire. Mais le bouton "
              "s'appelle alors « page.reprise.imposible », et seulement chez "
              "celui qui a change de langue : le HTML, lui, garde son francais",
        rougit="et toute cle citee par la page existe au dictionnaire",
        editions=[
            ("web/index.html", brut('T("page.reprise.impossible")',
                                    'T("page.reprise.imposible")')),
        ]),
    dict(
        nom="une cle de page qu'aucun ecran ne pose",
        banc="banc_page.py",
        imite="le sens inverse : une entree que rien ne lit se perime sans "
              "bruit, et le dictionnaire donne l'impression de couvrir un "
              "ecran qui n'existe plus. C'est ce que banc_traductions.py tient "
              "deja pour les pannes du serveur",
        rougit="et aucune cle « page. » ne dort au dictionnaire",
        editions=[
            ("traductions.py", brut(
                '''    "page.source": {
        "fr": "source",''',
                '''    "page.ancien.bouton": {
        "fr": "réessayer",
        "en": "try again"},
    "page.source": {
        "fr": "source",''')),
        ]),
    dict(
        nom="la page perd la regle de pluriel d'une langue servie",
        banc="banc_page.py",
        imite="PLURIELS[langue] rend undefined, T() retombe sur le francais, "
              "et l'anglais ecrit « 0 exchange ». Un mot, sur un compte, une "
              "fois sur trois — le genre de faute qu'on relit sans la voir",
        rougit="la page porte une regle de pluriel par langue servie",
        editions=[
            ("web/index.html", brut("  en: n => (n !== 1 ? 1 : 0),\n", "")),
        ]),
    dict(
        nom="la regle francaise recopiee dans la colonne anglaise",
        banc="banc_page.py",
        imite="la faute exacte que cette table existe pour empecher, et la "
              "seule qui passe le cas precedent sans bruit : les deux langues "
              "ont leur ligne, les deux lignes sont la meme. Le francais ecrit "
              "« 0 echange », l'anglais « 0 exchanges » — et l'anglais dirait "
              "« 0 exchange »",
        rougit="et le francais met zero au singulier la ou l'anglais le met au pluriel",
        editions=[
            ("web/index.html", brut("  en: n => (n !== 1 ? 1 : 0),",
                                    "  en: n => (n > 1 ? 1 : 0),")),
        ]),
    dict(
        nom="le « s » recolle a la main revient dans la barre laterale",
        banc="banc_page.py",
        imite="l'etat d'avant, remis a sa place au fil d'une reecriture : "
              "« ${c.tours} échange${c.tours > 1 ? \"s\" : \"\"} ». La regle "
              "francaise, recopiee, dans du code d'interface — et il suffit "
              "d'un endroit sur vingt pour que la langue cesse de decider",
        rougit="et rien ne recolle plus un « s » ni n'ecrit « demande(s) »",
        editions=[
            ("web/index.html", brut(
                'ech(T("compte.echanges", { n: c.tours }))}</small>',
                '`${c.tours} échange${c.tours > 1 ? "s" : ""}`}</small>')),
        ]),
    dict(
        nom="une valeur de protocole traduite dans la table des etats",
        banc="banc_page.py",
        imite="« fini » devient « termine » DANS LE PROTOCOLE : la page "
              "n'attend plus l'etat que le serveur ecrit, le pouce en bas "
              "cesse de proposer « refaire sur la grosse carte », et toutes "
              "les conversations deja enregistrees se relisent de travers. "
              "Rien ne leve : la comparaison est simplement fausse pour "
              "toujours",
        rougit="la page declare les six etats que le serveur ECRIT, et pas d'autres",
        editions=[
            ("web/index.html", brut('cours: "en cours", fini: "fini",',
                                    'cours: "en cours", fini: "termine",')),
        ]),
    dict(
        nom="une comparaison d'etat repart en litteral",
        banc="banc_page.py",
        imite="l'etat est ecrit DEUX fois : la table, et cette comparaison-ci. "
              "Elle survit au jour ou la table bouge, et se tait. C'est la "
              "moitie du defaut que la separation ferme — l'autre moitie etant "
              "qu'une passe de traduction toucherait ce litteral-la en croyant "
              "toucher un libelle",
        rougit="et aucune comparaison d'etat ni de famille ne porte encore un litteral",
        editions=[
            ("web/index.html", brut("pose === -1 && t.etat === ETAT.fini",
                                    'pose === -1 && t.etat === "fini"')),
        ]),
    dict(
        nom="le filtre « brouillons » derive de la valeur du HTML",
        banc="banc_page.py",
        imite="la forme exacte du silence du 31 aout, sur une autre paire : la "
              "valeur est ecrite dans l'<option> et comparee dans le script a "
              "quinze cents lignes d'ecart. Le menu garde son libelle, le "
              "filtre ne garde plus rien — et « brouillons » n'affiche jamais "
              "que des images finies",
        rougit="le filtre « brouillons » compare la valeur que le HTML porte vraiment",
        editions=[
            ("web/index.html", brut('const SOIN_BROUILLONS = "brouillons";',
                                    'const SOIN_BROUILLONS = "esquisses";')),
        ]),
    dict(
        nom="la page ne nomme plus le champ de la panne",
        banc="banc_page.py",
        imite="le couplage page/serveur cesse d'etre mesure des DEUX cotes, "
              "comme pour MARQUE_DEJA : rien ne rougit, et le champ peut "
              "changer de nom cote serveur sans que la bulle s'en apercoive",
        rougit="la page NOMME le champ par lequel le serveur dit CE QUI a echoue",
        editions=[
            ("web/index.html", brut('const MARQUE_PANNE = "panne";',
                                    'const MARQUE_PANNE = "";')),
        ]),
    dict(
        nom="la bulle retombe sur la ligne de journal seule",
        banc="banc_page.py",
        imite="l'etat d'avant, exactement : « t.erreur = derniere.msg ». Le "
              "message le plus lu du studio redevient du JOURNAL, qui ne se "
              "traduit pas — le lecteur anglais lit « la machine n'est pas "
              "revenue a temps » apres chaque panne, et rien ne le signale",
        rougit="elle rend la marque en phrase, et retombe sur la ligne de journal",
        editions=[
            ("web/index.html", brut(
                """          t.erreur = rendrePanne(t[MARQUE_PANNE])
                  || (derniere && derniere.msg) || t.erreur;""",
                """          t.erreur = (derniere && derniere.msg) || t.erreur;""")),
        ]),
    dict(
        nom="le repli sur le journal disparait",
        banc="banc_page.py",
        imite="l'autre bout, et le plus grave des deux : une tache relue apres "
              "redemarrage n'a PAS de marque, et trois arguments de echouer() "
              "sur cinq n'en avaient pas le 2 septembre. La bulle affiche alors "
              "du VIDE la ou il y avait une phrase. Un studio qui repond en "
              "francais est genant, un studio qui ne repond rien est casse",
        rougit="elle rend la marque en phrase, et retombe sur la ligne de journal",
        editions=[
            ("web/index.html", brut(
                """          t.erreur = rendrePanne(t[MARQUE_PANNE])
                  || (derniere && derniere.msg) || t.erreur;""",
                """          t.erreur = rendrePanne(t[MARQUE_PANNE]);""")),
        ]),
    dict(
        nom="une valeur qui est une marque n'est plus rendue d'abord",
        banc="banc_page.py",
        imite="le seul cas d'imbrication du depot : « ERREUR : {quoi} » recoit "
              "une PHRASE du dictionnaire. Sans ce tour, l'anglophone lit "
              "« ERROR: la machine n'est pas revenue a temps » — une "
              "DEMI-phrase traduite, qui se remarque moins qu'une phrase "
              "entierement francaise et trompe donc plus longtemps. Ici, il "
              "lirait « ERROR: [object Object] »",
        rougit="et une valeur qui est elle-meme une marque est rendue d'abord",
        editions=[
            ("web/index.html", brut(
                """    valeurs[nom] = (v && typeof v === "object" && v.cle)
                 ? T(v.cle, v.valeurs || {}) : v;""",
                """    valeurs[nom] = v;""")),
        ]),
    dict(
        nom="la langue devient un reglage de conversation",
        banc="banc_page.py",
        imite="ce que docs/plusieurs-langues.md avait annonce puis refuse "
              "apres mesure : REGLAGES_CONV est PAR CONVERSATION, alors que "
              "l'en-tete, la mediatheque et le panneau de file ne le sont pas "
              "— la langue de l'ombrelle serait celle de la derniere "
              "conversation ouverte. Et le serveur ne lit pas cette cle : le "
              "menu poste dans le vide, et le murmure promis ne vient jamais",
        rougit="et il reste hors des reglages : le serveur ne le retient pas la",
        editions=[
            ("web/index.html", brut(
                'const MENU_REGLAGE = { modele: "#forcer", noeud: "#machine",',
                'const MENU_REGLAGE = { langue: "#langue", modele: "#forcer",'
                ' noeud: "#machine",')),
            ("web/index.html", brut(
                'const CLE_REGLAGE = { "#forcer": "modele", "#machine": "noeud",',
                'const CLE_REGLAGE = { "#langue": "langue", "#forcer": "modele",'
                ' "#machine": "noeud",')),
        ]),
    dict(
        nom="le menu de langue disparait de la page",
        banc="banc_page.py",
        imite="le studio sert deux langues et n'offre aucun moyen d'en "
              "changer : « Accept-Language » decide seul, et un francophone "
              "sur un Windows anglais reste en anglais pour toujours. Le "
              "serveur, lui, continue de poser le cookie que plus personne ne "
              "lui demande — tout marche, sauf qu'on ne peut pas choisir",
        rougit="la page offre le choix de la langue, et le poste au serveur",
        editions=[
            ("web/index.html", brut(
                '      <select id="langue" data-t-aria-label="page.langue.aria"'
                ' aria-label="Langue"></select>\n', "")),
        ]),
]


MUTATIONS = (CONTENEUR + PAGE + REPARTITION + VARIANTES + CERVEAUX + COUT
             + CATALOGUE + ATTENTE + DUREES + ADULTE + REFAIRE + FORMULATIONS
             + MULTILINGUE + PROSE + LANGUES + PAGE_LANGUES)


# ── Jouer une mutation ────────────────────────────────────────────────
_CACHE = {}


def source(banc):
    if banc not in _CACHE:
        _CACHE[banc] = {rel: lire(rel) for rel in BESOINS[banc]}
    return dict(_CACHE[banc])


# Au-dela, on considere que le banc mute ne rendra jamais la main. Voir le
# commentaire de lancer() : c'est une marge pour la CHARGE de la machine, pas
# pour le banc lui-meme.
DELAI_BANC = 90.0


def lancer(banc, fichiers, racine):
    """Ecrit les fichiers dans un dossier neuf, lance le banc, rend (code, sortie)."""
    dossier = tempfile.mkdtemp(dir=racine)
    for rel, texte in fichiers.items():
        chemin = os.path.join(dossier, *rel.split("/"))
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with io.open(chemin, "w", encoding="utf-8", newline="\n") as f:
            f.write(texte)
    # PYTHONIOENCODING : les bancs impriment des guillemets francais, et une
    # console Windows en cp1252 faisait mourir le fils sur son propre affichage
    # — un plantage qui ressemblait a une mutation attrapee.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    # UN DELAI, ET UN VERDICT NOMME QUAND IL EXPIRE. Sans lui, une mutation qui
    # fait PENDRE le banc au lieu de le faire rougir bloquait le lanceur pour
    # toujours — donc la CI, sans un message. Constate le 2 septembre : six
    # lancements empiles, deux depuis dix-sept minutes, sur une mutation qui
    # retirait un repli et faisait boucler banc_refaire.
    #
    # C'est la meme famille que l'exigence de la ligne NOMMEE, ecrite dans
    # l'en-tete : « une mutation qui casse le banc par une exception rend elle
    # aussi un code non nul, et se ferait passer pour une reussite ». Le
    # pendage est pire — il ne se declare pas du tout.
    #
    # QUATRE-VINGT-DIX SECONDES, et le premier chiffre etait faux. « Dix fois
    # la marge » se fondait sur banc_variantes (3,5 s) et banc_cout (2,9 s) —
    # mais banc_refaire MUTE met 5,07 s, parce que ses deux attentes de file
    # tirent a vide des que la route refuse, ce que sa propre docstring
    # annonce. Avec le facteur QUATRE que ce depot mesure sous charge, cela
    # fait vingt secondes : la marge reelle etait de 1,5x, pas de dix, et le
    # delai aurait rendu une CI ROUGE SANS DEFAUT — precisement ce qu'il
    # cherche a eviter.
    #
    # Ce delai n'est pas une assertion de performance, c'est un GARDE-FOU
    # contre un blocage infini. Le payer entier ne coute que sur une mutation
    # qui pend pour de bon, c'est-a-dire jamais quand tout va bien.
    try:
        fini = subprocess.run([sys.executable, os.path.join(dossier, banc)],
                              cwd=dossier, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=DELAI_BANC)
    except subprocess.TimeoutExpired:
        return None, ""
    return fini.returncode, fini.stdout.decode("utf-8", "replace")


def verdict(mut, racine):
    """Rend (etat, detail). etat : "rouge", "vert", "perimee" ou "casse"."""
    fichiers = source(mut["banc"])
    for rel, edition in mut["editions"]:
        if rel not in fichiers:
            return "perimee", f"{rel} n'est pas copie pour {mut['banc']}"
        neuf, souci = appliquer(fichiers[rel], edition)
        if neuf is None:
            return "perimee", f"{rel} : {souci}"
        fichiers[rel] = neuf
    code, sortie = lancer(mut["banc"], fichiers, racine)
    if code is None:
        # PENDRE N'EST PAS ROUGIR. Un banc qui ne rend jamais la main ne dit
        # rien du defaut qu'on lui presente, et il emporte la CI avec lui.
        return "casse", (f"la mutation fait PENDRE {mut['banc']} au lieu de le "
                         f"faire rougir — plus de {DELAI_BANC:.0f} s sans "
                         f"reponse")
    marque = MARQUE_ROUGE.get(mut["banc"], "  NON")
    lignes_non = [l for l in sortie.splitlines() if l.startswith(marque)]
    if any(mut["rougit"] in l for l in lignes_non):
        return "rouge", ""
    if code == 0:
        return "vert", "le banc n'a rien vu"
    if not lignes_non:
        return "casse", sortie.strip().splitlines()[-1][:120] if sortie.strip() else "sans sortie"
    return "casse", "rouge ailleurs : " + " / ".join(l.strip() for l in lignes_non)[:120]


depart = time.time()
racine = tempfile.mkdtemp(prefix="banc_mutations_")
try:
    # ── LE SENS INVERSE. Un banc qui rougit sur tout n'attrape rien : sans
    # cette verification, une mutation « rouge » ne prouverait pas que c'est
    # ELLE qui a fait rougir.
    for banc in sorted(BESOINS):
        code, sortie = lancer(banc, source(banc), racine)
        derniere = [l for l in sortie.splitlines() if l.strip()]
        dit(code == 0, f"{banc} est vert sur le depot sain",
            derniere[-1].strip() if derniere else "sans sortie")

    for mut in MUTATIONS:
        etat, detail = verdict(mut, racine)
        dit(etat == "rouge", f"{mut['banc']} rougit : {mut['nom']}",
            {"rouge": mut["rougit"],
             "vert": "LE FILET A UN TROU — " + mut["imite"],
             "perimee": "MUTATION PERIMEE, elle ne mesure plus rien — " + detail,
             "casse": "le banc s'est casse au lieu de rougir — " + detail}[etat])

    # Signales, jamais comptes en echec : voir TROUS_CONNUS plus haut.
    for mut in TROUS_CONNUS:
        etat, detail = verdict(mut, racine)
        if etat == "rouge":
            signales.append(f"FERME : {mut['nom']} — a deplacer dans PAGE")
        elif etat == "vert":
            signales.append(f"trou ouvert : {mut['nom']} — {mut['imite']}")
        else:
            # Une ancre perimee reste un echec, meme pour un trou connu : sans
            # elle, le trou cesse d'etre mesure et l'on croira l'avoir ferme.
            rate.append(mut["nom"])
            signales.append(f"A REGARDER : {mut['nom']} — {detail}")
finally:
    shutil.rmtree(racine, ignore_errors=True)

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees — "
      f"{len(MUTATIONS)} mutations, {len(TROUS_CONNUS)} trous connus, "
      f"{time.time() - depart:.1f} s")
for s in signales:
    print("    " + s)
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
