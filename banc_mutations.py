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

LES TROIS MOITIES SERVEUR, 3 septembre 2026. Une relecture adverse a trouve
trois assertions de banc_page.py qui ne mesuraient qu'une moitie — ou du
commentaire —, et les trois venaient du commit qui pretendait REPARER deux
filets de ce banc-la. Le detail est au-dessus de MOITIES_SERVEUR ; ce qu'il
faut retenir ici est la FORME, parce qu'elle a desormais quatre exemples dans
ce fichier : un banc qui relit UN seul fichier d'un contrat qui en compte deux
ne mesure que la moitie qui ne bouge pas. La variante creuse est pire encore —
« "no-cache" in SERVEUR » etait vraie du COMMENTAIRE qui explique la constante,
et l'en-tete pouvait valoir « max-age=604800, immutable » sans que rien ne
rougisse.

Le sens inverse se prend comme pour « le repli de taille REFUSE au lieu de
reprendre » : ce n'est pas le code qui a ete corrige, c'est le BANC. On remet
l'assertion creuse, et les trois mutations passent au vert. banc_page.py passe
de 65 a 66 verifications — la moitie serveur des etats est un cas de plus, les
deux autres se sont ajoutees a un cas qui existait deja.

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
    # ET « importlib.import_module("x") », depuis le 3 septembre 2026. Le motif
    # ci-dessous ne voit qu'un mot-clef ; serveur.py charge pourtant
    # « entrainer_aiguilleur » par un appel, pour le reentrainement depuis
    # /admin. Le module n'etait donc pas copie, banc_conteneur.py ne le trouvait
    # pas dans le dossier d'essai, et sa regle « aucun lecteur d'environnement
    # n'echappe au suivi » n'avait rien a mesurer : la mutation qui la vise
    # passait au VERT — non par un trou du filet, mais parce que le lanceur ne
    # lui donnait pas de quoi travailler. Le meme angle mort que celui qu'on
    # vient de fermer dans banc_conteneur.py, un cran plus loin.
    _APPEL = r'import_module\(\s*["\']([a-z_][a-z0-9_]*)["\']\s*\)'
    a_lire, vus = ["serveur.py"], {"serveur.py"}
    while a_lire:
        source = a_lire.pop()
        texte = lire(source)
        for mod in (re.findall(r'(?m)^\s*(?:import|from)\s+([a-z_][a-z0-9_]*)',
                               texte)
                    + re.findall(_APPEL, texte)):
            nom = mod + ".py"
            if nom in vus or not os.path.exists(os.path.join(ICI, nom)):
                continue
            vus.add(nom)
            a_lire.append(nom)
            if nom not in fichiers:
                fichiers.append(nom)
    return fichiers


BESOINS = {
    # ET paquet/comfystudio.spec, depuis le 4 septembre 2026 : banc_conteneur.py
    # confronte les DEUX empaquetages — ce que l'executable embarque, l'image
    # doit le copier. Sans ce fichier, le banc meurt sur un FileNotFoundError au
    # lieu de mesurer, et les DIX-HUIT mutations qui le visent se declarent « le
    # banc s'est casse au lieu de rougir ». C'est la troisieme fois qu'une
    # lecture neuve est ajoutee a un banc sans etre ajoutee ici — apres
    # aiguilleur.json pour banc_multilingue et web/index.html pour banc_refaire.
    # La regle tient en une phrase : un banc qui ouvre un fichier de plus doit
    # le declarer ici, sinon il ne mesure plus rien dans le dossier d'essai.
    "banc_conteneur.py": fichiers_du_conteneur() + ["paquet/comfystudio.spec"],
    # traductions.py DEPUIS LE 2 SEPTEMBRE 2026 AU SOIR : banc_page.py releve
    # le francais ecrit dans le HTML et exige qu'il soit exactement celui du
    # dictionnaire — la meme moitie de contrat que MARQUE_DEJA, mais sur cent
    # quatre-vingt-quinze chaines. Sans ce fichier, le banc meurt a l'import,
    # ce qui ressemblerait a une mutation attrapee.
    # serveur.py DEPUIS LE BRANCHEMENT DU SECOND FACTEUR : banc_page.py y releve
    # le NOM du champ « il manque le code » et exige que la page dise le meme
    # mot. C'est la moitie de contrat que MARQUE_DEJA devait aller chercher dans
    # un banc a studio ; ici le champ est une constante, donc les deux moities
    # se relevent au meme endroit. Sans ce fichier, le banc meurt a l'ouverture,
    # ce qui ressemblerait a une mutation attrapee.
    # web/demarrage.html DEPUIS L'ECRAN DE PREMIERE MISE EN ROUTE : c'est la
    # seconde page traduite du depot, et banc_page.py lui applique les memes
    # releves qu'a index.html plus deux couplages qui n'existent que pour elle
    # — la table des verdicts, ecrite des deux cotes, et la regle qui la tient
    # a cote de /admin (elle mesure, elle ne repose aucun reglage). Le fichier
    # est ouvert sous try la-bas : sans lui le banc ROUGIT sur un cas nomme au
    # lieu de mourir, et c'est ce qui rend mesurable le sens inverse.
    # web/admin.html DEPUIS LA LIBERATION DE LA VRAM : banc_page.py y releve
    # les noms de reglage que la console POSTe et exige qu'ils soient ceux de
    # BORNES_REGLAGES, dans les deux sens. La page n'est pas traduite — /admin
    # parle a celui qui heberge — mais c'est l'autre moitie de contrat, celle
    # de MENU_REGLAGE et CLE_REGLAGE, dont la derive a fait perdre un reglage
    # pendant des jours. Le fichier est ouvert sous try la-bas : sans lui le
    # banc ROUGIT sur un cas nomme au lieu de mourir.
    "banc_page.py": ["banc_page.py", "web/index.html", "web/demarrage.html",
                     "web/admin.html", "traductions.py", "serveur.py"],
    # LE SEUL BANC AVEC banc_page.py A LIRE DEUX MONDES : comptes.py qu'il
    # IMPORTE (et mfa.py avec lui, que comptes.py importe en tete), et
    # serveur.py qu'il LIT par l'arbre de syntaxe pour la derniere section — un
    # seul site d'appel a authentifier(), un seul compteur, cinq routes
    # branchees. Il n'a besoin d'aucune dependance : ni comptes.py ni mfa.py
    # n'importent autre chose que la bibliotheque standard.
    "banc_comptes.py": ["banc_comptes.py", "comptes.py", "mfa.py", "serveur.py"],
    # banc_console.py importe serveur.py : il lui faut donc tout ce que
    # serveur.py importe, comme banc_conteneur.py le calcule deja.
    "banc_console.py": ["banc_console.py"] + fichiers_du_conteneur(),
    # L'ENCODEUR QR ET SES ETALONS, et rien d'autre : qr.py n'importe que
    # « collections », etalons_qr.py n'importe rien du tout. mfa.py est la pour
    # la derniere section du banc, qui encode cinq URI d'enrolement REELLES —
    # celles que le studio produit, et pas seulement les quatre des etalons.
    # Sans lui, le banc meurt a l'import, ce qui ressemblerait a une mutation
    # attrapee.
    "banc_qr.py": ["banc_qr.py", "qr.py", "etalons_qr.py", "mfa.py"],
    # banc_mfa.py n'a eu AUCUNE mutation du 2 au 3 septembre 2026, et c'etait le
    # seul banc du depot dans ce cas — celui qui garde la seule porte du studio.
    # CONTRIBUTING l'exige pourtant en toutes lettres : « si tu ajoutes un banc,
    # ajoute-lui sa mutation ». Le prix de cet oubli est mesure : une saisie a UN
    # chiffre ouvrait la porte 27 fois sur 100, le banc rendait 41/0, et deux de
    # ses cas passaient PAR CHANCE au-dessus du trou.
    "banc_mfa.py": ["banc_mfa.py", "mfa.py"],
    # agent_noeud.py N'ETAIT COPIE PAR AUCUN BANC, et c'est ce qui rendait
    # PERIMEES les deux mutations qui le visaient — « MUTATION PERIMEE,
    # agent_noeud.py n'est pas copie pour banc_repartition.py ». Aucune de ses
    # lignes n'etait sous filet : « free_memory » coupe du corps de /free, et
    # les dix-sept bancs restaient verts.
    #
    # LUI SEUL, ET C'EST TOUT CE QU'IL FAUT : l'agent tourne sur la machine a
    # carte, n'importe pas serveur.py, et sa premiere page promet « aucune
    # dependance, seulement la bibliotheque standard ». banc_agent.py remplace
    # son unique porte sur le monde — appeler() — et fait tourner le VRAI code
    # contre un faux ComfyUI et un faux studio.
    "banc_agent.py": ["banc_agent.py", "agent_noeud.py"],
    # LES MEMES DEUX FICHIERS, et pour la meme raison : banc_boucle.py couvre
    # les six fonctions que banc_agent.py a nommees en les laissant dehors —
    # boucle(), insister(), servir_le_langage(), trouver_ollama(),
    # modeles_comfy() et main(). Il n'importe que agent_noeud.py, qui
    # n'importe que la bibliotheque standard.
    #
    # PAS DE TROISIEME FICHIER, ET C'EST VERIFIABLE : il n'ouvre rien d'autre
    # que ses propres bacs temporaires, et AGENT.CONFIG y est deplace le temps
    # de chaque appel a main() — sans quoi il ecrirait agent_noeud.json a cote
    # du vrai agent du depot. C'est la meme precaution que banc_agent.py prend
    # pour AGENT.__file__.
    "banc_boucle.py": ["banc_boucle.py", "agent_noeud.py"],
    # LE SEUL BANC QUI LANCE UN SCRIPT SHELL. Il n'importe rien du studio : il
    # fait tourner noeud.sh et maj_noeud.sh dans un bac a sable, contre un faux
    # curl et un faux nvidia-smi qu'il ecrit lui-meme. Il lui faut donc les deux
    # scripts, et le trio de l'installeur — installer.py, installation.py et le
    # catalogue que celui-ci importe — parce que sa derniere section demande
    # POUR DE VRAI, en sous-processus, quel interpreteur fera tourner le studio.
    # Les deux .bat sont la pour un releve de TEXTE, et le banc le dit : cmd.exe
    # n'existe pas sur les runners Ubuntu de la CI, et un cas qui ne tournerait
    # que sur une machine serait vert chez tout le monde sans avoir rien mesure.
    # Sans eux, ce releve mourrait a l'ouverture, ce qui ressemblerait a une
    # mutation attrapee.
    #
    # PAS agent_noeud.py : le banc sert son PROPRE agent, un temoin de trois
    # lignes qui ecrit ce qu'il a lu dans agent_noeud.json. Copier le vrai ne
    # mesurerait rien de plus et le ferait chercher un studio.
    "banc_noeud.py": ["banc_noeud.py", "noeud.sh", "maj_noeud.sh",
                      "maj_noeud.bat",
                      "installer.py", "installation.py", "catalogue.py",
                      "LANCER ComfyStudio.bat",
                      "paquet/construire_windows.bat"],
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
    # LE BANC QUI LIT LE PLUS DE MONDES A LA FOIS, et c'est dans sa nature : la
    # question « quelle version tourne ? » n'a pas la meme reponse selon le
    # chemin d'installation, et les quatre chemins vivent dans quatre fichiers
    # differents. Il lui faut donc, en plus du studio et de ce qu'il importe :
    #
    #   Dockerfile                        deja dans fichiers_du_conteneur()
    #   paquet/comfystudio.spec           l'executable, qui grave le meme nom
    #   paquet/construire_windows.bat     qui doit dire ce qu'il a grave
    #   web/admin.html                    la seconde place ou lire la valeur
    #   .github/ISSUE_TEMPLATE/bogue.md   la raison de tout ceci
    #
    # C'EST LA QUATRIEME FOIS qu'une lecture neuve doit etre declaree ici —
    # apres aiguilleur.json pour banc_multilingue, web/index.html pour
    # banc_refaire et paquet/comfystudio.spec pour banc_conteneur. Chaque oubli
    # a coute la meme chose : le banc meurt sur un FileNotFoundError dans le
    # dossier d'essai, et TOUTES les mutations qui le visent se declarent « le
    # banc s'est casse au lieu de rougir » d'un seul coup. Ici, la moitie
    # d'entre elles auraient survecu sans se faire remarquer, parce que
    # banc_version.py ouvre ses fichiers sous try et pose un cas nomme : elles
    # seraient devenues rouges POUR LA MAUVAISE RAISON, ce qui est pire.
    "banc_version.py": (["banc_version.py", "paquet/comfystudio.spec",
                         "paquet/construire_windows.bat", "web/admin.html",
                         ".github/ISSUE_TEMPLATE/bogue.md"]
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
# LA PLUPART des bancs impriment « NON » — c'est le defaut, et cette table ne
# nomme que les autres. Le compte est parti d'ici le 4 septembre 2026 : il
# disait « dix bancs sur quatorze » quand la table en connaissait sept et
# BESOINS vingt, et un nombre qu'aucune ligne ne recalcule est exactement
# l'enumeration que ce depot a vue rouiller quatre fois. On nomme le motif.
#
# banc_cout.py, banc_multilingue.py, banc_traductions.py, banc_comptes.py et
# banc_mfa.py impriment « RATE » ; banc_adulte.py comme verifier_formulations.py
# n'ont pas de dit() du tout —
# ils listent leurs fautes indentees sous leur compte. Sans cette table, TOUTE
# mutation qui les vise serait rendue « le banc s'est casse au lieu de
# rougir » alors qu'il l'a parfaitement attrapee : le faux positif que ce
# fichier existe pour interdire, retourne.
#
# L'exigence, elle, ne bouge pas — la ligne NOMMEE et pas un code de retour.
MARQUE_ROUGE = {"banc_cout.py": "  RATE ", "banc_adulte.py": "    ",
                "banc_multilingue.py": "  RATE ",
                "banc_traductions.py": "  RATE ",
                "banc_comptes.py": "  RATE ",
                # banc_mfa.py imprime « RATE », et il manquait ici parce qu'il
                # n'avait AUCUNE mutation jusqu'au 3 septembre 2026 : ses trois
                # premieres se sont declarees « le banc s'est casse au lieu de
                # rougir » alors qu'il rougissait parfaitement, sur la ligne
                # nommee. Un verdict faux dans le sens le moins dangereux —
                # mais qui aurait fait croire les mutations mal ecrites et
                # conduit a les affaiblir jusqu'a ce qu'elles « passent ».
                #
                # banc_qr.py, LUI, IMPRIME « NON » et n'a rien a faire ici. Je
                # l'y ai ajoute par symetrie, sur un « grep RATE » qui trouvait
                # le mot ailleurs dans le fichier, et ses DOUZE mutations sont
                # tombees d'un coup. Le releve d'un mot n'est pas le releve de
                # ce que la fonction imprime : c'est la faute que ce fichier
                # reproche aux bancs depuis le premier jour, commise dans le
                # fichier qui la reproche.
                "banc_mfa.py": "  RATE ",
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
        nom="un defaut du compose qui repete un defaut CALCULE par le code",
        banc="banc_conteneur.py",
        imite="DEUX MAITRES POUR COMFY_MODELES, et c'est le piege que ce banc "
              "existe pour attraper — il l'a laisse passer des semaines. Le "
              "defaut du code n'est pas litteral : « os.path.join(BASE_COMFY, "
              "\"models\") », qui vaut /comfy/models dans l'image. Le releve "
              "le lisait sans l'evaluer, donc il ne pouvait etre egal a rien. "
              "Le jour ou le code change de chemin, l'image garde l'ancien "
              "sans un mot",
        rougit="pas deux defauts pour un meme reglage dans le compose",
        editions=[
            ("docker-compose.yml", brut(
                '      COMFY_MODELES: "${COMFY_MODELES:-}"',
                '      COMFY_MODELES: "${COMFY_MODELES:-/comfy/models}"')),
        ]),
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
        # REECRITE LE 3 SEPTEMBRE 2026, ET LE DEFAUT QU'ELLE IMITAIT EST FERME.
        # Elle remplaçait un « import comptes » par un import_module au nom
        # LITTERAL, et cela suffisait a faire sortir le module du suivi : le
        # releve se faisait par motif de texte, qui ne voit pas un appel.
        # banc_conteneur lit desormais l'ARBRE DE SYNTAXE, et un import_module
        # litteral y est aussi visible qu'un import — la mutation d'avant
        # passait donc au vert, non parce que le filet a un trou mais parce
        # qu'elle a cesse d'imiter un defaut.
        #
        # Elle vise maintenant le seul angle mort qui reste, et que la docstring
        # de _modules_charges() nomme : un module dont le NOM EST CALCULE. Aucun
        # n'existe dans le depot, et l'on n'a pas voulu faire semblant de le
        # voir — un ast qui evaluerait des expressions serait un interpreteur.
        nom="un module suivi charge sous un nom CALCULE",
        banc="banc_conteneur.py",
        imite="l'angle mort assume du suivi. Le module sort de CODE, donc les "
              "variables d'environnement qu'il lit ne sont plus confrontees au "
              "compose — et c'est tout l'objet de ce banc. Ici comptes.py n'en "
              "lit aucune, donc le degat est nul aujourd'hui ; il ne le serait "
              "pas d'un module qui en lit",
        rougit="aucun fichier qui lit l'environnement n'echappe au suivi",
        editions=[
            ("serveur.py", brut(
                '    entrainer = importlib.import_module("entrainer_aiguilleur")',
                '    entrainer = importlib.import_module("entrainer_" '
                '+ "aiguilleur")')),
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
# VIDE DEPUIS LE 4 SEPTEMBRE 2026, et c'est la premiere fois. Le dernier —
# « un defaut du compose qui repete un defaut CALCULE par le code » — est parti
# dans CONTENEUR : banc_conteneur.py EVALUE desormais les defauts calcules au
# lieu de rendre None des qu'une expression n'est pas litterale. Il les evalue
# comme l'IMAGE les verrait — posixpath, et les lignes ENV du Dockerfile pour
# environnement — parce que le compose decrit un conteneur Linux et non la
# machine du contributeur.
#
# Cette liste doit pouvoir se remplir de nouveau sans que personne n'hesite :
# une mutation qu'on trouve et que le banc vise ne voit pas se met ICI, nommee,
# et le banc la signale sans compter d'echec. La cacher serait pire ; la
# compter en echec rendrait la CI rouge en permanence, et une CI qui rougit
# pour rien finit ignoree.
TROUS_CONNUS = []

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
# ── RENDRE LA CARTE QUAND PLUS RIEN NE LA DEMANDE ────────────────────
# LE SENS INVERSE, ET IL FAUT L'ECRIRE PLUTOT QUE DE LE MIMER. Ces quinze
# mutations gardent une regle qui N'EXISTAIT PAS avant elles : aucun /free
# nulle part, ni dans serveur.py ni dans agent_noeud.py, et « libre » arrivait
# a chaque battement sans qu'aucune route ne le rende. Il n'y a donc pas de
# filet d'avant a leur opposer, et CONTRIBUTING nomme exactement ce cas :
# « lance le banc NEUF sur le code d'AVANT et verifie que les lignes que ta
# mutation nomme y rougissent ».
#
# CE QUE ÇA A DONNE, RELEVE LE 3 SEPTEMBRE 2026 : le banc NEUF joue contre un
# serveur.py d'ou les seize morceaux de la liberation sont retires rend
# « 48 verifications passees, 1 echouee », code de retour 1 — les quarante-huit
# d'avant restent vertes, et la ligne rouge est « le studio sait rendre une
# carte laissee au repos ». Les vingt-sept cas de la section ne s'executent
# pas : elle est gardee par un hasattr, exactement comme banc_page.py garde
# web/demarrage.html — « sans lui le banc ROUGIT sur un cas nomme au lieu de
# mourir ». Un AttributeError aurait dit « le banc s'est casse », ce qui ne
# mesure rien. Sur le depot d'aujourd'hui le meme banc rend 76/0.
#
# La quatorzieme, celle de banc_page.py, est dans le meme cas pour une autre
# raison : le couplage /admin ↔ BORNES_REGLAGES qu'elle vise est un filet neuf,
# et il aurait ete VERT sur le depot d'avant — les trois reglages qui
# existaient s'accordaient deja. Ce n'est pas un defaut qu'on repare, c'est un
# filet qui manquait.
#
# On ne peut donc PAS montrer ces quatorze lignes-la rouges sur le code
# d'avant : elles n'ont rien a nommer la-bas. Ce qui est montre, et qui est
# tout ce qui peut l'etre, c'est que le banc neuf DISTINGUE les deux depots au
# lieu de se casser sur l'un des deux. Le reste de la preuve vient du sens
# ALLER, ou verdict() exige la ligne NOMMEE : une mutation qui ferait rougir
# ailleurs est rendue « casse », pas « rouge ».
LIBERATION = [
    dict(
        nom="« libre » absent relu comme une carte pleine",
        banc="banc_repartition.py",
        imite="le piege que l'utilisateur avait nomme : « float(d.get('libre') "
              "or 0) » lit l'agent d'avant — celui qui n'annonce pas ce champ — "
              "comme une carte entierement pleine, donc candidate, a chaque "
              "battement et pour toujours. Sur la machine precisement trop "
              "vieille pour comprendre la consigne",
        rougit="un agent qui ne dit pas sa VRAM libre n'est pas une carte pleine",
        editions=[("serveur.py", brut(
            '                    libre=(float(d["libre"])' + chr(10)
            + '                           if isinstance(d.get("libre"), (int, float))'
            + chr(10) + "                           else None),",
            '                    libre=float(d.get("libre") or 0),'))]),
    dict(
        nom="le delai ne repart pas de la fin du dernier travail",
        banc="banc_repartition.py",
        imite="le compteur de repos n'est jamais remis a zero : il se remplit "
              "pendant que la machine calcule, et la consigne part a la seconde "
              "ou le rendu finit — sur la carte qui vient tout juste de servir, "
              "et qui va probablement resservir",
        rougit="un travail en cours remet le compteur de repos a zero",
        editions=[("serveur.py", brut(
            '        e["repos_depuis"] = 0',
            '        e["repos_depuis"] = e.get("repos_depuis") or 0'))]),
    dict(
        nom="le studio redemande la carte sans fin",
        banc="banc_repartition.py",
        imite="une carte qui ne rend rien — un ComfyUI qui accepte /free sans "
              "liberer, un jeu qui tient la memoire — se voit reclamee toutes "
              "les dix secondes jusqu'a la fin des temps, et le journal en est "
              "noye",
        rougit="la consigne ne part qu'UNE fois, meme si la VRAM n'a pas bouge",
        editions=[("serveur.py", brut(
            ' or e.get("libere_demande")', ""))]),
    dict(
        nom="le refus de /free est oublie au battement suivant",
        banc="banc_repartition.py",
        imite="un ComfyUI trop ancien repond 404, et il repondra 404 six fois "
              "par minute : sans memoire du refus, la meme ligne de journal "
              "s'ecrit indefiniment — la facon exacte dont on cesse de lire un "
              "journal",
        rougit="puis on cesse de demander, et l'on cesse aussi de l'ecrire",
        editions=[("serveur.py", brut(
            ' or e.get("liberation_refusee")', ""))]),
    dict(
        nom="une demande ARMEE ne retient plus la carte",
        banc="banc_repartition.py",
        imite="on rend la carte d'une machine qu'une demande attend deja : elle "
              "repart des le reveil, et recharge le modele qu'on venait de "
              "decharger",
        rougit="et une demande ARMEE qui attend cette machine la retient aussi",
        editions=[("serveur.py", brut(
            "                or charge_noeud(ident)" + chr(10)
            + "                or any(ident in (a.get(\"noeuds\") or ())" + chr(10)
            + "                       for a in ARMEES.values()))",
            "                or charge_noeud(ident))"))]),
    dict(
        nom="l'INTENTION ne retient plus la carte, seule la file",
        banc="banc_repartition.py",
        imite="entre le choix d'une machine et le depot du travail il y a toute "
              "l'analyse et les telechargements — des minutes. Ne regarder que "
              "la file rend « au repos » une carte que trois demandes attendent "
              "deja : le meme aveuglement que « compter les verrous tenus "
              "revenait a croire libre une carte que trois demandes attendaient »",
        rougit="une demande qui a CHOISI cette machine la retient, avant meme "
               "d'avoir depose son travail",
        editions=[("serveur.py", brut(
            chr(10) + "                or charge_noeud(ident)", ""))]),
    dict(
        nom="le reglage a zero n'annule plus rien",
        banc="banc_repartition.py",
        imite="« 0 » est la sortie de secours promise a qui ne veut pas de ce "
              "defaut d'une minute. Sans cette garde, zero minute se lit "
              "« immediatement » et le reglage fait l'exact contraire de ce "
              "qu'il annonce",
        rougit="a zero, plus rien n'est jamais libere",
        editions=[("serveur.py", brut(
            '    if PREFERENCES["vram_repos_min"] <= 0:' + chr(10)
            + "        return False" + chr(10), ""))]),
    dict(
        nom="la pause empeche la liberation",
        banc="banc_repartition.py",
        imite="le reflexe : « une machine en pause, on n'y touche pas ». Or "
              "c'est LE cas pour lequel ce reglage existe — « je vais jouer un "
              "peu » — et une machine en pause ne recevra pas de travail, donc "
              "rien ne viendra reprendre la carte. La garder pleine la ferait "
              "tenir des heures pour personne",
        rougit="une machine en pause rend sa carte : c'est le cas pour lequel "
               "le reglage existe",
        editions=[("serveur.py", brut(
            "    if not _tient_quelque_chose(ident) or not _au_repos(ident):",
            "    if ((REGISTRE.get(ident) or {}).get(\"pause\")" + chr(10)
            + "            or not _tient_quelque_chose(ident)"
            + " or not _au_repos(ident)):"))]),
    dict(
        nom="le seuil tombe : une carte vide recoit la consigne",
        banc="banc_repartition.py",
        imite="une carte qui affiche un bureau tient deja un a deux gigaoctets "
              "sans rien avoir charge. Sans seuil, chaque repos lui vaut un "
              "/free qui ne rend rien — et un appel qui ne rend rien ne se "
              "distingue plus d'un echec le jour ou l'on lit le journal",
        rougit="sur une carte deja vide il ne se passe rien",
        editions=[("serveur.py", brut(
            '    return e["vram"] - e["libre"] >= SEUIL_TENU',
            '    return e["vram"] - e["libre"] > 0'))]),
    dict(
        nom="la consigne ne descend plus dans la reponse a l'annonce",
        banc="banc_repartition.py",
        imite="le studio decide et ne dit rien : la regle entiere tourne dans "
              "le vide. C'est le seul transport possible — le studio n'a pas "
              "l'adresse d'une machine a agent et n'en veut pas",
        rougit="au repos, la carte pleine, la consigne descend dans la reponse "
               "a l'annonce",
        editions=[("serveur.py", brut(
            '                              **({"liberer": True} if liberer else {}),'
            + chr(10), ""))]),
    dict(
        nom="le noeud local n'est plus traite du tout",
        banc="banc_repartition.py",
        imite="le studio a l'adresse de son propre ComfyUI et peut l'appeler : "
              "l'oublier laisserait la carte de la machine hote pleine pendant "
              "que celles des agents se vident, sans que rien ne le dise",
        rougit="et la ronde du veilleur l'appelle a chaque tour",
        editions=[("serveur.py", brut(
            "            await liberer_noeuds_a_url()" + chr(10), ""))]),
    dict(
        nom="le dechargement n'est fait qu'a moitie",
        banc="banc_repartition.py",
        imite="« unload_models » sans « free_memory » laisse le cache, soit "
              "plusieurs gigaoctets : exactement l'apparence d'un /free qui ne "
              "marche pas, et le diagnostic partirait chercher un ComfyUI trop "
              "ancien",
        rougit="et le studio le POSTe lui-meme, avec les DEUX moities du "
               "dechargement",
        editions=[("serveur.py", brut(
            'json={"unload_models": True,' + chr(10)
            + '                                        "free_memory": True}',
            'json={"unload_models": True}'))]),
    dict(
        nom="la VRAM libre cesse d'etre exposee",
        banc="banc_repartition.py",
        imite="l'etat d'avant : la donnee arrive toutes les dix secondes et "
              "aucune route ne la rend. La liberation serait alors a croire sur "
              "parole — on ne peut plus voir si elle marche",
        rougit="/api/admin/noeuds rend la VRAM libre de chaque machine",
        editions=[("serveur.py", brut(
            '                      "libre": e.get("libre"),' + chr(10), ""))]),
    dict(
        nom="un agent perime est diagnostique comme un ComfyUI fautif",
        banc="banc_repartition.py",
        imite="le jour de la mise a jour, c'est le cas le plus frequent : "
              "l'agent recoit la consigne et ne la lit pas. Sans cette "
              "distinction, le studio accuse un ComfyUI qui n'a jamais rien "
              "recu, et le diagnostic part chercher a l'autre bout de la "
              "machine — alors que l'empreinte, qu'on a deja sous la main, "
              "tranche",
        rougit="une carte qui n'a rien rendu sous un agent perime accuse "
               "l'AGENT, pas ComfyUI",
        editions=[("serveur.py", motif(
            r'    elif e\.get\("empreinte"\) and e\["empreinte"\] != empreinte_agent\(\):\n.*?              f"pas encore cette consigne — voir /admin", flush=True\)\n',
            ""))]),
    dict(
        nom="le nom du reglage derive entre /admin et le serveur",
        banc="banc_page.py",
        imite="la moitie de contrat qui a deja coute des jours a ce depot : la "
              "page ecrit un nom, le serveur en attend un autre, et rien ne "
              "leve. Le POST repond 400, le champ se remet a sa valeur d'avant "
              "au rafraichissement suivant, et l'administrateur croit "
              "simplement que son chiffre a ete refuse",
        rougit="aucun champ de /admin ne pose un reglage que le serveur ignore",
        editions=[("web/admin.html", brut(
            "{ vram_repos_min: Number(", "{ vram_repos: Number("))]),
]

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
# ── LE SECOND FACTEUR, ET LE BANC QUI N'AVAIT PAS DE FILET ────────────
# banc_mfa.py est ne le 2 septembre 2026 sans une seule mutation, et il est
# reste le seul banc du depot dans ce cas. Ce qu'il gardait, pourtant, c'est la
# porte : le prix de l'oubli est mesure a 27,4 % — la proportion de saisies a un
# chiffre que le studio acceptait.
FACTEUR_MFA = [
    dict(
        nom="la longueur du code se deduit de la SAISIE",
        banc="banc_mfa.py",
        imite="la porte telle qu'elle a ete livree, du 2 au 3 septembre 2026. "
              "verifie() comparait le code attendu TRONQUE a la longueur de ce "
              "qu'on tape : « 7 » etait donc confronte au code modulo dix, une "
              "chance sur dix par pas et trois pas dans la fenetre. Mesure : "
              "549 acceptations sur 2 000 instants au hasard, 25 sessions "
              "ouvertes sur 25 avec le seul mot de passe, 4,8 essais de "
              "moyenne — le freinage laisse trois essais gratuits puis 1, 2 et "
              "4 s, soit sept secondes pour 85 % de reussite. La garantie que "
              "tout le reste invoque, « six chiffres font un million », etait "
              "fausse : le studio en acceptait un",
        rougit="aucune longueur autre que six n'ouvre",
        editions=[
            ("mfa.py", brut(
                "    if not propre.isdigit() or len(propre) != chiffres:",
                "    if not propre.isdigit():")),
            ("mfa.py", brut(
                "        if hmac.compare_digest(code(secret, pas=p, chiffres=chiffres),",
                "        if hmac.compare_digest(code(secret, pas=p, "
                "chiffres=len(propre)),")),
        ]),
    dict(
        nom="le rejeu d'un code TOTP",
        banc="banc_mfa.py",
        imite="un second facteur qu'on peut rejouer ne protege plus contre "
              "quelqu'un qui a vu l'ecran ou relu un journal. Un code reste "
              "valable toute sa fenetre : sans memoire du dernier pas accepte, "
              "le meme code ouvre autant de sessions qu'on veut. C'est la faute "
              "la plus courante des implementations maison, parce qu'elles "
              "verifient le code — le facile — et s'arretent la",
        rougit="le meme code repasse avec ce pas en memoire est REFUSE",
        editions=[
            ("mfa.py", brut(
                "        if dernier_pas is not None and p <= dernier_pas:",
                "        if False:")),
        ]),
    dict(
        nom="la fenetre s'elargit a deux pas",
        banc="banc_mfa.py",
        imite="deux fois plus de codes valides a chaque instant, pour un "
              "confort que personne n'a demande : la RFC 6238 ecrit « at most "
              "one time step ». Rien ne se voit — les codes justes passent "
              "toujours, et ceux d'il y a deux minutes aussi",
        rougit="DEUX pas en arriere, non",
        editions=[
            ("mfa.py", brut("FENETRE = 1", "FENETRE = 2")),
        ]),
    dict(
        nom="un code de secours qui ressert",
        banc="banc_comptes.py",
        imite="un second mot de passe permanent, note sur un papier. Le code "
              "de secours est retire APRES avoir rendu vrai, au lieu d'avant : "
              "rien ne se voit tant qu'on ne le retape pas",
        rougit="LE MEME NE SERT PAS DEUX FOIS",
        editions=[
            ("comptes.py", brut(
                '                m["secours"].pop(i)\n'
                "                self.sauver()\n"
                "                return True",
                "                self.sauver()\n"
                "                return True")),
        ]),
]


# ══════════════════════════════════════════════════════════════════════
#  Desarmer le facteur d'un AUTRE — six mutations
# ══════════════════════════════════════════════════════════════════════
# CE QUE CETTE FAMILLE GARDE : une commodite qui ne doit pas rogner une
# promesse. Rouvrir un compte dont le telephone ET les codes de secours etaient
# perdus demandait, jusqu'au 4 septembre 2026, d'arreter le studio et d'editer
# _comptes.json a la main. /admin sait le faire — et la question n'est plus
# « est-ce que ca marche » mais « est-ce que ca coute encore la meme chose ».
FACTEUR_ADMIN = [
    dict(
        nom="le retrait s'ouvre a tout compte administrateur",
        banc="banc_comptes.py",
        imite="LA COMMODITE QUI MANGE LA PROMESSE, et elle se defend tres bien "
              "a l'ecrit : « c'est /admin, donc un administrateur suffit ». Un "
              "compte administrateur peut deja imposer un mot de passe a "
              "n'importe qui ; s'il peut AUSSI desarmer, il prend n'importe "
              "quel compte en deux gestes, et le second facteur ne protege "
              "plus que d'un mot de passe qui fuit. Le jeton, lui, ne se lit "
              "que sur la machine",
        rougit="admin_par_jeton() ne connait QUE le jeton",
        editions=[
            ("serveur.py", brut(
                '    jeton = (req.headers.get("X-Admin") or '
                'req.cookies.get("studio_admin") or "")\n'
                "    return bool(ADMIN_JETON) and secrets.compare_digest(jeton, "
                "ADMIN_JETON)\n\n\ndef _facteur_du_compte(nom):",
                '    nom_connecte = req.get("compte") or ""\n'
                "    if nom_connecte and COMPTES and COMPTES.est_admin(nom_connecte):\n"
                "        return True\n"
                '    jeton = (req.headers.get("X-Admin") or '
                'req.cookies.get("studio_admin") or "")\n'
                "    return bool(ADMIN_JETON) and secrets.compare_digest(jeton, "
                "ADMIN_JETON)\n\n\ndef _facteur_du_compte(nom):")),
        ]),
    dict(
        nom="le jeton est verifie APRES avoir desarme",
        banc="banc_comptes.py",
        imite="l'ordre inverse, qui se lit comme une garde et n'en est pas "
              "une : le facteur est deja tombe quand le refus part. La reponse "
              "dit « refuse », et le compte est ouvert",
        rougit="elle exige le JETON, et le verifie AVANT de desarmer",
        editions=[
            ("serveur.py", brut(
                "    if not admin_par_jeton(req):\n"
                "        return web.json_response(\n"
                '            {"erreur": "il faut le jeton d\'administration, pas '
                'seulement un "\n'
                '                       "compte administrateur : desarmer le facteur '
                'de "\n'
                '                       "quelqu\'un d\'autre demande la main sur la '
                'machine"},\n'
                "            status=403)\n",
                "")),
            # LE COMMENTAIRE EST DANS L'ANCRE, et ce n'est pas un ornement :
            # « COMPTES.mfa_retirer(nom) » seul apparait DEUX fois dans
            # serveur.py — ici, et dans la route du proprietaire, qui n'a rien
            # a voir. Une ancre en double rend « perimee » et la mutation ne
            # mesure plus rien.
            ("serveur.py", brut(
                "    COMPTES.mfa_retirer(nom)\n"
                "    # LA CONSOLE DU STUDIO EST LE JOURNAL.",
                "    COMPTES.mfa_retirer(nom)\n"
                "    if not admin_par_jeton(req):\n"
                '        return web.json_response({"erreur": "jeton"}, status=403)\n'
                "    # LA CONSOLE DU STUDIO EST LE JOURNAL.")),
        ]),
    dict(
        nom="la route qui desarme n'est plus branchee",
        banc="banc_comptes.py",
        imite="une fonctionnalite morte que rien ne signale : /admin montre le "
              "bouton, le clic rend 404, et le seul remede documente ne marche "
              "plus. C'est le defaut qui a fait naitre ce fichier",
        rougit="la route qui desarme pour autrui est branchee",
        editions=[
            ("serveur.py", brut(
                '    a.router.add_delete("/api/admin/comptes/{nom}/mfa", '
                "api_admin_mfa_retirer)\n",
                "")),
        ]),
    dict(
        nom="l'etat du facteur emmene le secret avec lui",
        banc="banc_comptes.py",
        imite="le secret TOTP sort par une route. Il est en clair dans "
              "_comptes.json — il ne peut pas en etre autrement, il faut le "
              "relire pour calculer le code attendu — et la seule chose qui "
              "l'empeche de sortir, c'est que personne ne le mette dans une "
              "reponse. Une ligne suffit",
        rougit="l'etat servi a /admin ne porte qu'un mot et un nombre",
        editions=[
            ("serveur.py", brut(
                '    return {"mfa": etat,\n',
                '    return {"mfa": etat,\n'
                '            "secret": (COMPTES.gens.get(nom.lower(), {})\n'
                '                       .get("mfa", {}).get("secret", "")),\n')),
        ]),
    dict(
        nom="le retrait laisse l'enrolement en attente",
        banc="banc_comptes.py",
        imite="le compte reste coince dans l'etat exact qu'on venait "
              "debloquer : « en attente » interdit de recommencer un "
              "enrolement, et il n'y a plus rien pour l'effacer. Celui qui a "
              "mal scanne son QR code n'a plus AUCUN chemin, ni le sien ni "
              "celui de l'administrateur",
        rougit="le retrait efface AUSSI l'attente",
        editions=[
            ("comptes.py", brut(
                '        c.pop("mfa", None)\n        c.pop("mfa_attente", None)\n',
                '        c.pop("mfa", None)\n')),
        ]),
    dict(
        nom="le retrait ne laisse plus de trace",
        banc="banc_comptes.py",
        imite="une protection posee par quelqu'un d'autre tombe en silence. "
              "docs/comptes.md promet la ligne de console ; sans elle, le "
              "proprietaire du studio n'a aucun moyen d'apprendre qu'on s'est "
              "servi de cette porte — et c'est le propre d'une trace de "
              "disparaitre sans que personne ne le remarque",
        rougit="le retrait laisse une trace dans la console",
        editions=[
            ("serveur.py", brut(
                '    print(f"  second facteur DESARME sur le compte « {nom} » "\n'
                '          f"depuis la console d\'administration", flush=True)\n',
                "")),
        ]),
]


PAGE_LANGUES = [
    dict(
        nom="la page repart sans en-tete de cache",
        banc="banc_page.py",
        imite="l'etat d'avant le 3 septembre 2026, et le defaut ne se voit pas "
              "au deploiement : il se voit chez celui qui avait deja ouvert la "
              "page. Sans « Cache-Control », le navigateur s'autorise a "
              "reutiliser une reponse pendant environ un dixieme de son age — "
              "une journee pour un fichier vieux de dix jours. Sa page continue "
              "de marcher, elle lit simplement des champs que le serveur ne "
              "pose plus, ou en ignore de nouveaux. Les cinq contrats que ce "
              "banc mesure sont alors vrais dans le depot et faux a l'ecran",
        rougit="et chacune dit au navigateur de REDEMANDER avant de servir",
        editions=[
            ("serveur.py", brut(
                '    return web.FileResponse(os.path.join(ICI, "web", "index.html"),\n'
                "                            headers=SANS_CACHE)",
                '    return web.FileResponse(os.path.join(ICI, "web", "index.html"))')),
        ]),
    dict(
        nom="le menu de langue retombe sous le bouton « reglages »",
        banc="banc_page.py",
        imite="l'endroit ou il a vecu une heure, et qui le rendait inutilisable "
              "par ceux a qui il sert. Le panneau du pied de page ne s'ouvre "
              "que pour changer de moteur ou de taille — la langue s'y cachait "
              "derriere un geste sans rapport — et surtout il ne s'ouvre PAS "
              "DU TOUT tant qu'on n'est pas connecte, alors que l'ecran de "
              "connexion est la premiere chose qu'un lecteur etranger doit "
              "pouvoir traduire. Le menu existe toujours, la page reste juste, "
              "et personne ne le trouve",
        rougit="et il est dans l'EN-TETE, visible sans ouvrir quoi que ce soit",
        # UN VRAI DEPLACEMENT, ET NON UNE SUPPRESSION. La premiere ecriture de
        # cette mutation retirait simplement le menu — ce que « le menu de
        # langue disparait de la page » fait deja, plus bas dans ce fichier.
        # Deux mutations pour un seul geste : la seconde n'aurait rien mesure
        # de plus, et le cas de POSITION serait reste non eprouve, puisqu'un
        # menu absent est absent de l'en-tete comme de partout ailleurs. On le
        # remet donc a l'endroit d'ou il vient, sous le bouton « reglages », et
        # c'est la seule facon de montrer que le banc lit la POSITION et pas la
        # presence.
        editions=[
            ("web/index.html", brut(
                '      <select id="langue" data-t-aria-label="page.langue.aria"\n'
                '              aria-label="Langue"></select>\n',
                "")),
            ("web/index.html", brut(
                '    <div class="jointe" id="jointe"',
                '      <select id="langue" data-t-aria-label="page.langue.aria"\n'
                '              aria-label="Langue"></select>\n'
                '    <div class="jointe" id="jointe"')),
        ]),
    dict(
        nom="le globe perd son « for »",
        banc="banc_page.py",
        imite="un caractere decoratif a cote d'un menu, au lieu de son "
              "etiquette. Le clic sur l'icone n'ouvre plus rien — il faut "
              "viser les onze pixels du menu lui-meme — et un lecteur d'ecran "
              "annonce un globe sans dire a quoi il sert. Rien ne se voit a "
              "l'oeil : le menu est toujours la, au bon endroit, et il marche "
              "encore pour qui vise juste",
        rougit="et le globe lui est attache par « for »",
        editions=[
            ("web/index.html", brut(
                '<label for="langue" aria-hidden="true"',
                '<label aria-hidden="true"')),
        ]),
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
        # REANCREE le 3 septembre 2026 : le menu a demenage du pied de page vers
        # l'en-tete, et cette ancre tenait sur son ancienne indentation.
        # banc_mutations l'a dit tout seul — « MUTATION PERIMEE, elle ne mesure
        # plus rien » — au lieu de se compter verte. C'est le comportement
        # voulu, et c'est la seule raison pour laquelle ce deplacement n'a pas
        # laisse un filet mort derriere lui.
        editions=[
            ("web/index.html", brut(
                '      <select id="langue" data-t-aria-label="page.langue.aria"\n'
                '              aria-label="Langue"></select>\n', "")),
        ]),
]


# ──────────────────────────────────────────────────────────────────────
#  Les trois moities serveur — 3 septembre 2026
# ──────────────────────────────────────────────────────────────────────
# TROIS ASSERTIONS DE banc_page.py NE MESURAIENT QU'UNE MOITIE, et les trois
# venaient du commit qui pretendait REPARER deux filets — ce qui les rend plus
# genantes que la moyenne : le fichier qui reproche aux bancs de ne pas voir ce
# qu'ils gardent en avait pose trois de plus. Elles ne mutent que serveur.py,
# et c'est tout leur sujet : la page etait relue, le serveur non.
#
#   1. « "no-cache" in SERVEUR ». Le mot est AUSSI dans le commentaire qui
#      explique la constante, et SERVEUR n'est jamais decommente — la page,
#      elle, l'est depuis le premier jour (CODE). Le cas ne mesurait donc que
#      de la prose : mesure du 3 septembre, l'en-tete remplace par
#      « max-age=604800, immutable » laissait le banc 65/65 VERT, et
#      « {"X-Studio": "1"} » aussi.
#   2. MARQUE_PANNE n'etait relevee que cote page. Renommer la constante dans
#      serveur.py laissait le banc VERT, et la bulle retombait en silence sur
#      la ligne de journal francaise — le defaut meme que la marque a ferme.
#   3. ETATS_DU_SERVEUR disait « les six etats que le serveur ECRIT » sans
#      jamais ouvrir serveur.py : la liste etait un souvenir recopie a la
#      main. Les quinze « en cours » du serveur renommes « en_cours »
#      laissaient le banc VERT, alors que toute bulle serait restee « en
#      cours », chronometre montant, indefiniment.
#
# LE SENS INVERSE se prend ici comme pour « le repli de taille REFUSE au lieu
# de reprendre » : ce n'est pas le code qui a ete corrige, c'est le BANC. On
# remet donc l'assertion creuse, et les trois mutations passent au VERT — les
# trois ont ete jouees ainsi avant la reparation, dans un dossier temporaire,
# et le banc rendait 65/65 sur chacune. Pour la troisieme, la ligne qu'elle
# nomme n'existait meme pas.
#
# ET L'ISOLEMENT : chacune, jouee seule sur le depot repare, allume SA ligne
# et une seule, 65/66. Les quatre mutations qui visaient deja ces trois
# sections par le cote PAGE — l'en-tete retire, « fini » traduit, MARQUE_PANNE
# videe, la comparaison en litteral — allument toujours la leur, et pas celles
# d'a cote : les deux moities se relevent separement, comme pour MARQUE_MFA.
#
# « attente machine » PLUTOT QUE « en cours » POUR LA TROISIEME, et il faut
# dire pourquoi : « en cours » s'ecrit a quinze endroits de serveur.py, donc
# quinze ancres, et appliquer() en exige une par edition. « attente machine »
# ne s'ecrit qu'a UN seul, et le defaut est le meme mot pour mot — la page
# compare a une valeur que le serveur n'ecrit plus. Il est meme deja arrive :
# le commentaire de la table des etats, dans la page, dit que sans cette
# entree la demande « s'affichait en attente, comme celles qui partent dans
# deux minutes », alors que c'est le seul etat dont l'attente se compte en
# HEURES. La variante a quinze sites a ete jouee a la main, et elle rougit sur
# la meme ligne.
MOITIES_SERVEUR = [
    dict(
        nom="l'en-tete de cache garde la page une semaine",
        banc="banc_page.py",
        imite="l'en-tete est bien la — le cas d'a cote reste vert — et il dit "
              "l'inverse de ce qu'il doit dire : le navigateur garde la page "
              "sept jours sans rien redemander. Les six contrats que ce banc "
              "mesure sont alors vrais dans le depot et faux a l'ecran, ce qui "
              "est exactement l'etat d'avant le 3 septembre, en pire : "
              "« immutable » supprime meme la revalidation au rafraichissement",
        rougit="et cet en-tete est bien « no-cache » : garder, mais revalider",
        editions=[
            ("serveur.py", brut('SANS_CACHE = {"Cache-Control": "no-cache"}',
                                'SANS_CACHE = {"Cache-Control": '
                                '"max-age=604800, immutable"}')),
        ]),
    dict(
        nom="MARQUE_PANNE renommee du seul cote serveur",
        banc="banc_page.py",
        imite="le mensonge de MARQUE_DEJA pris par l'autre bout : le serveur "
              "pose « echec », la page lit « panne », et rendrePanne ne recoit "
              "plus jamais rien. La bulle retombe sur la derniere ligne de "
              "JOURNAL — le repli, qui ne se traduit pas — et le lecteur "
              "anglais relit du francais apres chaque panne. Rien ne leve, "
              "rien ne manque a l'ecran : c'est le defaut que la marque a "
              "ferme, remis par le cote qu'aucun banc ne relisait",
        rougit="la page NOMME le champ par lequel le serveur dit CE QUI a echoue",
        editions=[
            ("serveur.py", brut('\nMARQUE_PANNE = "panne"\n',
                                '\nMARQUE_PANNE = "echec"\n')),
        ]),
    dict(
        nom="un etat de protocole renomme cote serveur",
        banc="banc_page.py",
        imite="la page compare a « attente machine », le serveur ecrit "
              "« attente_machine » : la ligne de file retombe sur son repli et "
              "affiche « en attente », comme une demande qui part dans deux "
              "minutes. C'est le seul etat dont l'attente se compte en HEURES "
              "— la machine est en pause, la demande repartira seule — et le "
              "commentaire de la page dit que c'est pour cela qu'il a fallu "
              "l'ecrire. Rien ne leve, et la file ment sur la seule attente "
              "qu'il faille nommer",
        rougit="et serveur.py n'ecrit toujours que ces etats-la",
        editions=[
            ("serveur.py", brut(
                '"etat": ("attente machine" if tid in ARMEES',
                '"etat": ("attente_machine" if tid in ARMEES')),
        ]),
]


# ──────────────────────────────────────────────────────────────────────
#  Le second facteur — onze mutations, sur DEUX bancs
# ──────────────────────────────────────────────────────────────────────
# La seule liste de ce fichier qui vise deux bancs a la fois, et c'est le sujet
# qui l'impose : la regle se coupe en deux moities qui vivent chacune de son
# cote. banc_comptes.py garde LA PORTE — un seul site d'appel a authentifier(),
# un seul compteur d'essais, cinq routes branchees — et banc_page.py garde LE
# CONTRAT AVEC L'ECRAN : le nom du champ, ce sur quoi la case du code s'ouvre,
# et les deux phrases que l'enrolement ne peut pas taire. Les separer en deux
# listes ferait croire a deux sujets.
#
# LE SENS INVERSE, ET IL FAUT LE DIRE ICI. Ces onze mutations naissent AVEC les
# deux bancs qu'elles eprouvent : ni banc_comptes.py ni banc_page.py ne
# mesuraient quoi que ce soit du second facteur avant ce travail — les routes
# n'existaient pas, l'ecran non plus. Il n'y a donc pas de « filet d'avant » a
# leur opposer, et CONTRIBUTING.md tranche ce cas : on lance le banc NEUF sur le
# code d'AVANT. Il y MEURT au lieu de rougir — les ancres qu'il releve
# (_ouvrir_porte, MARQUE_MFA, peindreSecours) n'existent pas encore, et le banc
# s'arrete a l'ouverture ou compte des zeros partout. Ce qui a ete mesure a la
# place, c'est l'ISOLEMENT : chaque mutation jouee seule sur le depot du jour
# allume SA ligne, et le releve nomme laquelle. C'est ce que ce fichier exige
# deja de toutes les autres — la ligne NOMMEE et pas un code de retour — mais
# cela ne dit pas ce qu'elles mesurent d'AUTRE, et il faut l'ecrire : ces onze
# restent des mutations rouges dont on ne sait pas ce qu'elles mesurent d'autre,
# comme les trois de banc_durees, banc_adulte et poids() plus haut.
FACTEUR = [
    dict(
        nom="le site d'appel oublie le code du second facteur",
        banc="banc_comptes.py",
        imite="le defaut que le sentinelle FAUX rend muet : la porte echoue "
              "FERME, donc plus personne n'entre sur un compte arme, et le "
              "studio a l'air de refuser un mot de passe juste. C'est mot pour "
              "mot ce que faisait le changement de mot de passe avant ce "
              "travail — « ancien mot de passe incorrect » sur le bon",
        rougit="UN SEUL site d'appel a authentifier() dans serveur.py, et il "
               "passe le code",
        editions=[
            ("serveur.py", brut(
                "    c = COMPTES.authentifier(nom, mdp, code)\n",
                "    c = COMPTES.authentifier(nom, mdp)\n")),
        ]),
    dict(
        nom="la demande de code remet le compteur d'essais a zero",
        banc="banc_comptes.py",
        imite="le forçage rouvert en grand : il suffit d'intercaler un appel "
              "SANS code entre deux essais de code pour effacer l'ardoise, et "
              "l'attente exponentielle ne mord plus jamais. Six chiffres se "
              "parcourent alors a pleine vitesse",
        rougit="et elle ne touche PAS au compteur",
        editions=[
            ("serveur.py", brut(
                "    if c is _comptes.BESOIN_MFA:\n"
                "        return None, web.json_response(\n",
                "    if c is _comptes.BESOIN_MFA:\n"
                "        _ECHECS.pop(cle, None)\n"
                "        return None, web.json_response(\n")),
        ]),
    dict(
        nom="le freinage vient APRES la verification",
        banc="banc_comptes.py",
        imite="chaque essai s'execute avant d'etre compte : le scrypt des dix "
              "codes de secours est paye a chaque saisie, et qui tape n'importe "
              "quoi occupe le studio sans jamais etre ralenti",
        rougit="et elle freine AVANT de verifier, jamais apres",
        editions=[
            ("serveur.py", brut(
                "    cle = _cle_freinage(req, nom)\n"
                "    reste = _freinage(cle)\n"
                "    if reste > 0:\n"
                "        return None, web.json_response(\n"
                '            {"erreur": T("erreur.trop_d_essais", lg, secondes=f"{reste:.0f}")},\n'
                "            status=429)\n"
                "    c = COMPTES.authentifier(nom, mdp, code)\n",
                "    cle = _cle_freinage(req, nom)\n"
                "    c = COMPTES.authentifier(nom, mdp, code)\n"
                "    reste = _freinage(cle)\n"
                "    if reste > 0:\n"
                "        return None, web.json_response(\n"
                '            {"erreur": T("erreur.trop_d_essais", lg, secondes=f"{reste:.0f}")},\n'
                "            status=429)\n")),
        ]),
    dict(
        nom="le compteur est indexe par la seule adresse",
        banc="banc_comptes.py",
        imite="derriere un reverse proxy qui n'ajoute pas « X-Forwarded-For », "
              "tout le monde arrive de la meme IP : le premier qui se trompe "
              "trois fois freine la maison entiere, et le studio parait tombe",
        rougit="le compteur est indexe par le COUPLE (compte, adresse)",
        editions=[
            ("serveur.py", brut(
                '    return ((nom or "").strip().lower(), hote)',
                '    return ("compte", hote)')),
        ]),
    dict(
        nom="une route desarme le facteur sans passer par la porte",
        banc="banc_comptes.py",
        imite="exactement ce que le middleware « origine_verifiee » a corrige "
              "ailleurs : la garde ecrite route par route s'oublie a la "
              "prochaine route ajoutee. Ici la route qui RETIRE le second "
              "facteur verifie le code elle-meme, donc sans compteur — un "
              "oracle a codes, a pleine vitesse, sur la porte de sortie",
        rougit="et aucune ne verifie un mot de passe ni un code a cote",
        editions=[
            ("serveur.py", brut(
                '    c, refus = _ouvrir_porte(req, nom, d.get("mdp"), d.get("code"), lg)\n'
                "    if refus is not None:\n"
                "        return refus\n"
                "    COMPTES.mfa_retirer(nom)\n",
                '    if not COMPTES.mfa_verifier(nom, d.get("code")):\n'
                '        return web.json_response({"erreur": "code refuse"},\n'
                "                                 status=403)\n"
                "    COMPTES.mfa_retirer(nom)\n")),
        ]),
    dict(
        nom="regenerer COMPLETE le jeu de codes au lieu de le remplacer",
        banc="banc_comptes.py",
        imite="on regenere justement parce qu'on a perdu de vue le papier "
              "d'avant : garder les anciens laisse valides les dix codes qu'on "
              "cherchait a annuler, et le geste ne sert plus a rien tout en "
              "ayant l'air de servir",
        rougit="AUCUN ancien code ne vaut plus",
        editions=[
            ("comptes.py", brut(
                '        m["secours"] = _empreintes_secours(secours)\n',
                '        m["secours"] = ((m.get("secours") or [])\n'
                "                        + _empreintes_secours(secours))\n")),
        ]),
    dict(
        nom="une des cinq routes du facteur n'est plus branchee",
        banc="banc_comptes.py",
        imite="une fonctionnalite morte que rien ne signale — le defaut qui a "
              "fait naitre ce fichier. Le bouton « desarmer » est la, il "
              "s'appuie, et il rend un 404 que la page affiche comme un refus",
        rougit="et les cinq routes du second facteur sont branchees",
        editions=[
            ("serveur.py", brut(
                '    a.router.add_post("/api/compte/mfa/retirer", api_mfa_retirer)\n',
                "")),
        ]),
    dict(
        nom="le nom du champ change du seul cote du serveur",
        banc="banc_page.py",
        imite="la case du code ne s'affiche plus jamais : l'utilisateur d'un "
              "compte arme tape son mot de passe JUSTE et lit « nom, mot de "
              "passe ou code incorrect », sans qu'une ligne de la page ni du "
              "serveur n'ait l'air fautive. C'est le degat de MARQUE_DEJA, sur "
              "la porte d'entree",
        rougit="porte le MEME nom dans la page et dans le serveur",
        editions=[
            ("serveur.py", brut('MARQUE_MFA = "mfa"',
                                'MARQUE_MFA = "code_attendu"')),
        ]),
    dict(
        nom="la page decide la case du code sur le TEXTE du refus",
        banc="banc_page.py",
        imite="le contrat de « deja refait » une troisieme fois : une "
              "reformulation cote serveur, un accent, une traduction — et la "
              "case du code cesse de s'ouvrir. Le refus se lit en anglais des "
              "que le navigateur le demande, donc le motif francais ne mord "
              "meme pas toujours",
        rougit="ouvre la case du code sur ce champ, jamais sur le texte du refus",
        editions=[
            ("web/index.html", brut(
                "      if (!r.ok && d[MARQUE_MFA]) { demanderCode(f, mal); return; }\n",
                '      if (!r.ok && /code/i.test(d.erreur || "")) '
                "{ demanderCode(f, mal); return; }\n")),
        ]),
    dict(
        nom="l'ecran ne dit plus que les codes de secours ne reviendront pas",
        banc="banc_page.py",
        imite="dix codes affiches comme un reglage qu'on retrouvera : l'onglet "
              "se ferme, et ils n'existent plus nulle part — ce qui est garde "
              "est leur empreinte scrypt, et personne ne peut les redonner, pas "
              "meme l'administrateur",
        rougit="dit qu'ils ne s'affichent QU'UNE fois",
        editions=[
            ("web/index.html", brut(
                '    corps.append(dire(cleMot), dire("page.mfa.secours.titre"), ul,\n'
                '                 dire("page.mfa.secours.unique", "avertit"));\n',
                '    corps.append(dire(cleMot), dire("page.mfa.secours.titre"), ul);\n')),
        ]),
    dict(
        nom="l'attente de trente secondes n'est plus annoncee",
        banc="banc_page.py",
        imite="le code qui vient de CONFIRMER l'enrolement est deja consomme, "
              "et rien ne le dit : celui qui le lit encore sur son telephone le "
              "retape, se voit refuse, et croit avoir rate son enrolement. Il "
              "desarme, recommence, et retombe sur le meme mur",
        rougit="annonce l'attente d'au plus trente secondes",
        editions=[
            ("web/index.html", brut(
                '    if (avecAttente) corps.append(dire("page.mfa.attente", "avertit"));\n',
                "")),
        ]),
]


# ──────────────────────────────────────────────────────────────────────
#  L'ECRAN DE PREMIERE MISE EN ROUTE — dix-huit mutations
# ──────────────────────────────────────────────────────────────────────
# web/demarrage.html MESURE ce qui manque a un studio neuf et RENVOIE vers
# /admin ; il ne repose aucun reglage. Toute sa valeur tient a cela : /admin
# sait deja tout poser, et un ecran d'accueil qui redemanderait l'un de ses
# reglages serait une SECONDE table du meme reglage. Les mutations ci-dessous
# defont, une par une, chaque regle qui l'y tient.
#
# LE SENS INVERSE, MESURE LE 3 SEPTEMBRE 2026. Ces sections de banc sont NEES
# avec l'ecran : il n'existe pas de « filet d'avant » a leur opposer, comme
# pour banc_durees.py, banc_adulte.py et les douze de banc_refaire.py. Il a
# donc ete pris comme pour banc_catalogue — le banc NEUF lance sur le code
# d'AVANT, reconstruit en retirant l'ecran, ses routes, sa famille du
# dictionnaire et le drapeau « origine » des comptes. Voici ce qu'il a rendu :
#
#   - banc_page.py NEUF sur le code d'AVANT : ROUGIT sur HUIT de ses dix
#     lignes neuves, et ne meurt pas. C'est la premiere mutation ci-dessous
#     qui rend ce chiffre possible : le releve ouvre web/demarrage.html sous
#     try et pose un cas NOMME, au lieu de lever a l'ouverture. Sans elle,
#     banc_mutations aurait rendu « le banc s'est casse au lieu de rougir »
#     pour les neuf autres, et le sens inverse n'aurait rien mesure du tout.
#     LES DEUX QUI RESTENT VERTES LE SONT A VIDE, et il faut le dire : « aucun
#     releve ne cite demarrage. nu » et « aucune cle demarrage. ne dort » sont
#     vraies d'un dictionnaire qui ne porte aucune cle de cette famille. Elles
#     ne mesurent quelque chose qu'a partir du moment ou l'ecran existe — leur
#     sens inverse a elles, c'est leur mutation et rien d'autre.
#   - banc_comptes.py NEUF sur le code d'AVANT : ROUGIT sur trois lignes, dont
#     « creer() sait marquer le mot de passe que le studio vient de tirer ».
#     Il MOURAIT d'abord, sur « TypeError: Comptes.creer() got an unexpected
#     keyword argument 'origine' », et emportait ses soixante verifications
#     avec lui — la section lit desormais la SIGNATURE avant d'appeler, et
#     garde le reste derriere. C'est la meme reparation que le try de
#     banc_page.py, et elle a sa mutation.
#   - banc_traductions.py NEUF sur le code d'AVANT : ROUGIT sur « une marque
#     qui compte accorde sa forme » — « 1 echange / 2 echange / 1 exchanges /
#     2 exchanges ». LE DEFAUT PREEXISTAIT : rendre() ne passait pas « nombre »
#     a T() depuis toujours, et personne ne pouvait le voir parce qu'aucune
#     marque ne comptait quoi que ce soit. L'autre ligne neuve — le nom de
#     valeur qui heurte un parametre de T() — y est verte a vide, pour la meme
#     raison : aucune entree d'avant ne heurtait.
DEMARRAGE = [
    dict(
        nom="l'ecran de premiere mise en route disparait",
        banc="banc_page.py",
        imite="le code d'AVANT : la page n'existe pas. Le releve qui l'ouvre "
              "doit ROUGIR sur un cas nomme, jamais mourir a l'ouverture — un "
              "banc qui se casse ne dit rien du defaut qu'on lui presente",
        rougit="l'ecran de premiere mise en route existe",
        editions=[
            ("web/demarrage.html", motif(r"\A[\s\S]+\Z", "")),
        ]),
    dict(
        nom="un texte de l'ecran reformule d'un seul cote",
        banc="banc_page.py",
        imite="la page francaise reste juste, le studio ne leve pas, et un "
              "lecteur anglais se retrouve devant une traduction devenue "
              "fausse sans que personne au studio ne l'apprenne jamais",
        rougit="chaque texte francais de l'ecran est EXACTEMENT celui du dictionnaire",
        editions=[
            ("web/demarrage.html", brut(
                'data-t="demarrage.retour">retour au studio</a>',
                'data-t="demarrage.retour">revenir au studio</a>')),
        ]),
    dict(
        nom="une invite de l'ecran ecrite sans cle",
        banc="banc_page.py",
        imite="le champ du jeton garde son invite FRANCAISE dans une interface "
              "anglaise — et c'est le seul champ que voie quelqu'un qui n'est "
              "pas encore entre",
        rougit="et chaque titre, invite et aria-label de l'ecran passe par une cle",
        editions=[
            ("web/demarrage.html", brut(
                '    <input id="jeton" type="password" data-t-placeholder="demarrage.jeton.invite"\n',
                '    <input id="jeton" type="password"\n')),
        ]),
    dict(
        nom="la page compose « demarrage. » nu",
        banc="banc_page.py",
        imite="le releve de citations lit alors un PREFIXE qui couvre la "
              "famille entiere : plus aucune cle ne peut y dormir, et la "
              "verification suivante devient verte parce qu'elle ne mesure "
              "plus rien — la faute corrigee treize fois d'un coup ailleurs",
        rougit="aucun releve ne cite « demarrage. » nu",
        editions=[
            ("web/demarrage.html", brut(
                'T("demarrage.verdict." + l.verdict)',
                'T("demarrage." + "verdict." + l.verdict)')),
        ]),
    dict(
        nom="le serveur cite une cle qui n'existe pas",
        banc="banc_page.py",
        imite="T() rend SA PROPRE CLE : la ligne affiche « demarrage.mdp.changee » "
              "a l'ecran, et seulement pour qui regarde",
        rougit="toute cle « demarrage. » citee par l'ecran ou par le serveur existe",
        editions=[
            ("serveur.py", brut('_marque("demarrage.mdp.change")',
                                '_marque("demarrage.mdp.changee")')),
        ]),
    dict(
        nom="une cle de l'ecran cesse d'etre posee",
        banc="banc_page.py",
        imite="une entree que plus aucun site ne pose : sa traduction se "
              "perime sans bruit, et le dictionnaire donne l'impression de "
              "couvrir un ecran qui n'existe plus",
        rougit="et aucune cle « demarrage. » ne dort au dictionnaire",
        editions=[
            ("serveur.py", brut('_marque("demarrage.cles.aucune")',
                                '_marque("demarrage.cles.posees", n=0, qui="")')),
        ]),
    dict(
        nom="la table des verdicts derive entre la page et le serveur",
        banc="banc_page.py",
        imite="MENU_REGLAGE et CLE_REGLAGE une seconde fois : un verdict connu "
              "du serveur et inconnu de la page donne une ligne sans couleur "
              "et sans etiquette, c'est-a-dire une ligne qu'on lit « tout va "
              "bien »",
        rougit="la page peint exactement les verdicts que le serveur nomme",
        editions=[
            ("web/demarrage.html", brut('option: "option" };',
                                        'absent: "option" };')),
        ]),
    dict(
        nom="une ligne pose un verdict absent de la table",
        banc="banc_page.py",
        imite="la table peut etre juste des DEUX cotes pendant qu'un site "
              "d'appel en ecrit un cinquieme a la main : la ligne des cles se "
              "peint alors sans couleur",
        rougit="et chaque verdict pose par une ligne figure dans cette table",
        editions=[
            ("serveur.py", brut('return _ligne("cles", "option",',
                                'return _ligne("cles", "neutre",')),
        ]),
    dict(
        nom="l'ecran se remet a poser un reglage de /admin",
        banc="banc_page.py",
        imite="la SECONDE table du meme reglage — et deux tables du meme "
              "reglage divergent, ce depot l'a mesure trois fois. C'est la "
              "regle qui fait tenir cet ecran a cote de /admin sans deriver",
        rougit="l'ecran n'appelle que la langue, sa propre mesure et la porte d'admin",
        editions=[
            ("web/demarrage.html", brut(
                '$("#remesurer").onclick = () => mesurer();',
                '$("#remesurer").onclick = () => fetch("/api/admin/cles",\n'
                '  { method: "POST", body: "{}" });')),
        ]),
    dict(
        nom="la mesure de l'ecran perd sa garde",
        banc="banc_page.py",
        imite="/api/demarrage est LIBRE de session — exiger_compte la laisse "
              "passer pour que l'amorçage d'une installation neuve reste "
              "possible. Sans admin_ok, elle dit a n'importe quel visiteur "
              "qu'un compte porte encore son mot de passe d'origine et "
              "qu'aucune carte ne repond : la meilleure page de reconnaissance "
              "qu'un studio puisse offrir",
        rougit="la mesure est libre de session mais gardee par le jeton d'administration",
        editions=[
            ("serveur.py", brut(
                '    if not admin_ok(req):\n'
                '        return web.json_response({"erreur": "acces refuse"}, status=403)\n'
                '    if req.method == "POST":\n'
                '        try:\n'
                '            d = await req.json()\n'
                '        except Exception:\n'
                '            return web.json_response(\n'
                '                {"erreur": T("erreur.corps_illisible", langue_de(req))}, status=400)\n'
                '        _ecrire_demarrage(bool(d.get("ferme")))',
                '    if req.method == "POST":\n'
                '        try:\n'
                '            d = await req.json()\n'
                '        except Exception:\n'
                '            return web.json_response(\n'
                '                {"erreur": T("erreur.corps_illisible", langue_de(req))}, status=400)\n'
                '        _ecrire_demarrage(bool(d.get("ferme")))')),
        ]),

    # ── le mot de passe d'origine, cote registre ──────────────────────
    dict(
        nom="creer() ne sait plus marquer un mot de passe d'origine",
        banc="banc_comptes.py",
        imite="le code d'AVANT, cote registre. Cette mutation-ci existe pour "
              "que le banc ROUGISSE au lieu de MOURIR : sans la ligne qui lit "
              "la signature, l'appel a creer(origine=True) levait un TypeError "
              "et emportait les soixante verifications suivantes — le banc "
              "s'est casse au lieu de rougir, et le sens inverse ne mesurait "
              "plus rien",
        rougit="creer() sait marquer le mot de passe que le studio vient de tirer",
        editions=[
            # LES DEUX, ET PAS SEULEMENT LE PARAMETRE. Retirer « origine=False »
            # seul laissait « if origine: » sur un nom qui n'existe plus : le
            # banc mourait sur un NameError au lieu de rougir, c'est-a-dire
            # exactement le defaut que cette mutation-ci vient mesurer, retourne
            # contre elle. Une mutation aussi s'eprouve.
            ("comptes.py", brut(", origine=False", "")),
            ("comptes.py", brut(
                "        if origine:\n"
                '            self.gens[nom.lower()]["origine"] = True\n', "")),
        ]),
    dict(
        nom="tout compte cree est marque « origine »",
        banc="banc_comptes.py",
        imite="l'ecran reclame un changement de mot de passe a chaque compte "
              "creee a la main — une ligne rouge qu'aucun geste n'eteint, "
              "c'est-a-dire une ligne qu'on apprend a ignorer",
        rougit="seul le compte cree avec « origine » porte la marque",
        editions=[
            ("comptes.py", brut("        if origine:\n", "        if True:\n")),
        ]),
    dict(
        nom="changer le mot de passe n'efface plus la marque",
        banc="banc_comptes.py",
        imite="l'ecran reclame indefiniment un changement DEJA FAIT : la facon "
              "la plus sure de le faire ignorer, et il ne rougirait plus le "
              "jour ou un vrai mot de passe d'origine trainerait",
        rougit="changer le mot de passe efface la marque, des deux cotes",
        editions=[
            ("comptes.py", brut('        c.pop("origine", None)\n', "")),
        ]),
    dict(
        nom="l'effacement de la marque n'atteint pas le disque",
        banc="banc_comptes.py",
        imite="la marque disparait en memoire et reste sur le disque : l'ecran "
              "est vert jusqu'au redemarrage, et rouge de nouveau apres — le "
              "genre de defaut qu'on met des semaines a croire",
        rougit="l'effacement est sur le DISQUE",
        editions=[
            ("comptes.py", brut(
                '        c.pop("origine", None)\n        self.sauver()\n',
                '        self.sauver()\n        c.pop("origine", None)\n')),
        ]),
    dict(
        nom="la marque s'efface a un second endroit",
        banc="banc_comptes.py",
        imite="deux ecritures du meme enchainement, et elles divergent : c'est "
              "la lecon que ce depot a payee trois fois. Le decoupage compte — "
              "cette mutation-ci laisse l'effacement en place, elle en AJOUTE "
              "un, et seule la ligne de l'unicite doit mordre",
        rougit="la marque n'est effacee qu'a UN endroit",
        editions=[
            ("comptes.py", brut(
                '        c["admin"] = bool(admin)\n',
                '        c["admin"] = bool(admin)\n        c.pop("origine", None)\n')),
        ]),
    dict(
        nom="le serveur marque aussi le mot de passe pose par l'hebergeur",
        banc="banc_comptes.py",
        imite="STUDIO_ADMIN_MDP est une DECISION de celui qui heberge : la "
              "marquer fait rougir pour toujours une ligne que personne ne "
              "peut eteindre autrement qu'en changeant un secret qu'il a choisi",
        rougit="le serveur ne marque « origine » que le mot de passe qu'il a TIRE",
        editions=[
            ("serveur.py", brut("origine=not ADMIN_MDP", "origine=True")),
        ]),

    # ── les deux pieges du dictionnaire, trouves en branchant l'ecran ──
    dict(
        nom="une valeur reprend le nom d'un parametre de T()",
        banc="banc_traductions.py",
        imite="rendre() LEVE — « got multiple values for argument 'langue' » — "
              "au moment precis ou l'on essayait de dire quelque chose a "
              "quelqu'un. Pas une phrase fausse : une exception. Deux entrees "
              "le faisaient le 3 septembre 2026, et rien ne l'aurait dit avant "
              "qu'un lecteur ne les atteigne",
        rougit="aucune valeur ne porte le nom d'un parametre de T()",
        editions=[
            ("traductions.py", brut(
                '    "demarrage.cles.posees": {\n'
                '        "fr": ["{n} clé posée : {qui}.",\n'
                '               "{n} clés posées : {qui}."],\n'
                '        "en": ["{n} key set: {qui}.",\n'
                '               "{n} keys set: {qui}."]},',
                '    "demarrage.cles.posees": {\n'
                '        "fr": ["{n} clé posée : {langue}.",\n'
                '               "{n} clés posées : {langue}."],\n'
                '        "en": ["{n} key set: {langue}.",\n'
                '               "{n} keys set: {langue}."]},')),
        ]),
    dict(
        nom="rendre() cesse de passer le nombre a T()",
        banc="banc_traductions.py",
        imite="toute marque plurielle prend la forme d'indice zero en francais "
              "et celle d'indice un en anglais, quel que soit le compte : "
              "« 1 accounts registered ». La page, elle, lit « v.n » et "
              "accorde juste — les deux moities du contrat divergent la ou "
              "rendre() se declare leur specification",
        rougit="une marque qui compte accorde sa forme, comme la page le fait",
        editions=[
            ("traductions.py", brut(
                'return T(marque["cle"], langue, nombre=valeurs.get("n"), **valeurs)',
                'return T(marque["cle"], langue, **valeurs)')),
        ]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_qr.py et banc_page.py — le QR code de l'enrolement, seize mutations
# ──────────────────────────────────────────────────────────────────────
# LES MUTATIONS D'UN ENCODEUR SONT FACILES A ECRIRE ET REDOUTABLES, et c'est
# exactement pour cela qu'elles sont ici. Aucune de ces seize ne fait LEVER quoi
# que ce soit : la matrice sort carree, les trois coins de reperage sont a leur
# place, l'image ressemble a un QR code dans tous les cas. Elles produisent
# simplement un code qu'aucun telephone ne lit — la panne la plus silencieuse
# qu'on puisse poser dans ce depot, puisque le seul symptome est un appareil
# photo qui n'affiche rien.
#
# Douze visent qr.py, quatre le dessin dans la page. Elles disent la PANNE et
# non la manipulation : « les octets de correction sont dans le mauvais ordre »
# se relit dans les deux lignes en dessous, « le code ne se corrige plus » non.
#
# LE SENS INVERSE, MENE LE 3 SEPTEMBRE 2026, ET IL SE PARTAGE EN DEUX.
#
#   - LES QUATRE DE banc_page.py SONT PROUVEES DANS LES DEUX SENS. La page
#     d'AVANT a ete reconstituee — la regle « .entree .qr », dessinerQR(), son
#     appel dans peindreEnrolement, le champ « qr » de la route et les deux cles
#     de traduction retires —, et le banc NEUF lance dessus rougit sur QUATRE
#     lignes et QUATRE seulement, exactement celles que ces mutations nomment :
#     54 vertes, 4 rouges. Chacune a donc ete vue rougir sur le vrai defaut, pas
#     seulement sur son imitation.
#   - LES DOUZE DE banc_qr.py NE SONT PAS PROUVABLES AINSI, et il faut le dire.
#     Le banc est NE avec qr.py, comme banc_durees.py et banc_adulte.py avant
#     lui : il n'existe pas de filet d'avant a leur opposer, et l'autre facon de
#     prendre le sens inverse — le banc neuf sur le code d'avant — ne donne rien
#     ici non plus, puisque le code d'avant n'a pas de qr.py du tout : le banc
#     MEURT sur « ModuleNotFoundError: No module named 'qr' » au lieu de rougir.
#     Mesure faite, et c'est un plantage, pas un verdict. Elles restent donc des
#     mutations rouges dont on ne sait pas ce qu'elles mesurent d'AUTRE.
#     CE QUI LIMITE LE DOUTE : chacune nomme une ligne DIFFERENTE, et elles ne
#     se recouvrent pas — les quatre etages du banc rougissent sur des cas
#     distincts, du bloc d'essai en Reed-Solomon jusqu'a l'invariant de
#     structure. Une mutation qui rougirait « pour une autre raison » rougirait
#     sur la ligne d'une autre, et verdict() refuse justement ce cas-la : il
#     exige la ligne NOMMEE, pas un code de retour non nul.
QR = [
    dict(
        # LA PANNE QUE L'EN-TETE DE banc_qr.py NOMME EN PREMIER — « un motif
        # d'alignement place a un pixel pres » — et elle etait INVISIBLE
        # jusqu'au 3 septembre 2026. Les quatre etalons couvraient les versions
        # 1, 4, 7 et 9 ; or toute URI d'enrolement reelle sort en version 8, et
        # elle seule : mesure du 3 septembre, les noms de compte « a »,
        # « jordan » et un nom de vingt-huit lettres donnent les trois 49x49.
        # La seule version que le studio emette n'etait donc comparee a segno
        # NULLE PART, et cette mutation-ci laissait le banc a 50/50 vert
        # pendant qu'aucun telephone ne lisait plus un enrolement.
        #
        # La cause etait dans outils_etalons_qr.py : son cas « reel » se donne
        # pour « exactement ce que mfa.uri() produit » et emploie le secret de
        # la RFC, long de SEIZE caracteres, quand mfa.secret_neuf() en rend
        # TRENTE-DEUX. Un etalon « emis » a ete ajoute, avec un secret de la
        # vraie longueur ; la mutation rougit desormais sur trois lignes, et les
        # trois nomment ce cas-la.
        nom="l'alignement de la version 8 decale d'un module",
        banc="banc_qr.py",
        imite="un motif d'alignement a un pixel pres sur la SEULE version que "
              "le studio emette. Rien ne leve, l'image ressemble a un QR code, "
              "et elle ne se lit plus. C'est la panne que ce banc nomme en "
              "premier, et celle qu'il ne voyait pas",
        rougit="« emis » (8-M) se refait module par module depuis son TEXTE",
        editions=[
            ("qr.py", brut(
                "7: (6, 22, 38), 8: (6, 24, 42), 9: (6, 26, 46), 10: (6, 28, 50),",
                "7: (6, 22, 38), 8: (6, 22, 42), 9: (6, 26, 46), 10: (6, 28, 50),")),
        ]),
    dict(
        nom="deux octets de correction sont echanges",
        banc="banc_qr.py",
        imite="le defaut qui ne se voit sur AUCUNE image : les mots de code sont "
              "tous la, a leur place, et le polynome n'est plus divisible par le "
              "generateur. Le lecteur eclaire le code, ne corrige rien, et "
              "n'affiche rien",
        rougit="un bloc juste a ses dix-huit syndromes nuls",
        editions=[
            ("qr.py", brut(
                "    return reste[len(donnees):]\n",
                "    sortie = reste[len(donnees):]\n"
                "    sortie[0], sortie[1] = sortie[1], sortie[0]\n"
                "    return sortie\n")),
        ]),
    dict(
        nom="un motif d'alignement est saute",
        banc="banc_qr.py",
        imite="le lecteur perd le quadrillage des que le code n'est pas "
              "parfaitement de face : les motifs d'alignement sont ce qui lui "
              "permet de redresser une photo prise de biais, et il n'y en a "
              "aucun avant la version 2",
        rougit="reperage, separateurs, synchronisation, module sombre, alignement",
        editions=[
            ("qr.py", brut(
                "    for l in centres:\n        for c in centres:\n",
                "    for l in centres[:-1]:\n        for c in centres:\n")),
        ]),
    dict(
        nom="le masque 0 est force au lieu d'etre choisi",
        banc="banc_qr.py",
        imite="un code parfaitement valide et moins lisible : les grandes "
              "plages uniformes et les faux motifs de reperage egarent les "
              "lecteurs, et c'est tout ce que les regles de penalite servent a "
              "eviter. Rien ne leve, et la comparaison aux etalons ne le voit "
              "pas non plus puisqu'elle force le masque",
        rougit="le masque rendu est celui de plus petite penalite parmi les huit",
        editions=[
            ("qr.py", brut(
                "    candidats = range(8) if masque is None else (masque,)\n",
                "    candidats = (0,) if masque is None else (masque,)\n")),
        ]),
    dict(
        nom="la colonne de synchronisation n'est plus sautee dans le zigzag",
        banc="banc_qr.py",
        imite="toute la moitie gauche du code decale d'une colonne. La matrice "
              "reste carree, les motifs sont a leur place, et rien ne se lit",
        rougit="se refait module par module depuis ses mots de code",
        editions=[
            ("qr.py", brut(
                "    while droite >= 1:\n"
                "        if droite == 6:\n"
                "            droite = 5\n"
                "        monte = ((droite + 1) & 2) == 0\n",
                "    while droite >= 1:\n"
                "        monte = ((droite + 1) & 2) == 0\n")),
        ]),
    dict(
        nom="le module sombre obligatoire n'est plus pose",
        banc="banc_qr.py",
        imite="un module clair la ou la norme en exige un sombre. Certains "
              "lecteurs acceptent quand meme, d'autres non : le defaut ne se "
              "reproduit pas d'un telephone a l'autre, ce qui est le pire cas "
              "pour qui cherche la panne",
        rougit="reperage, separateurs, synchronisation, module sombre, alignement",
        editions=[
            ("qr.py", brut(
                "    modules[taille - 8][8] = True\n"
                "    fixe[taille - 8][8] = True\n",
                "    modules[taille - 8][8] = False\n"
                "    fixe[taille - 8][8] = True\n")),
        ]),
    dict(
        nom="les blocs sont ecrits a la suite au lieu d'etre entrelaces",
        banc="banc_qr.py",
        imite="une eclaboussure locale abime alors dix octets du MEME bloc au "
              "lieu d'un octet dans chacun. La correction en supporte quelques-"
              "uns par bloc, pas dix : le code se lit tant qu'il est propre, et "
              "cesse de se lire des qu'il est un peu sali",
        rougit="se refait module par module depuis son TEXTE",
        editions=[
            ("qr.py", brut(
                "    flux = []\n"
                "    for i in range(max(len(d) for d, _ in parts)):\n"
                "        for d, _ in parts:\n"
                "            if i < len(d):\n"
                "                flux.append(d[i])\n",
                "    flux = []\n"
                "    for d, _ in parts:\n"
                "        flux.extend(d)\n")),
        ]),
    dict(
        nom="le remplissage revient a la lettre de la norme",
        banc="banc_qr.py",
        imite="l'ecart assume avec segno referme sans le dire. Le code reste "
              "parfaitement lisible — ces mots-la sont du remplissage —, mais "
              "les trois etalons en mode octet cessent tous de correspondre, et "
              "l'on ne saurait plus lequel des deux a raison",
        rougit="et le remplissage commence apres",
        editions=[
            ("qr.py", brut(
                "    bits += [0] * min(8 - len(bits) % 8, place - len(bits))\n",
                "    bits += [0] * min(-len(bits) % 8, place - len(bits))\n")),
        ]),
    dict(
        nom="la version choisie monte d'un cran",
        banc="banc_qr.py",
        imite="des codes plus gros que necessaire a chaque enrolement : plus de "
              "modules pour la meme surface d'ecran, donc moins de pixels par "
              "module, donc un code que les appareils photo lisent moins bien. "
              "Personne ne le remarque, tout continue de marcher — un peu moins",
        rougit="ni plus ni moins",
        editions=[
            ("qr.py", brut(
                "        if bits <= 8 * octets_utiles(version):\n"
                "            return version\n",
                "        if bits <= 8 * octets_utiles(version):\n"
                "            return min(version + 1, 40)\n")),
        ]),
    dict(
        nom="le format d'information n'est plus brouille",
        banc="banc_qr.py",
        imite="le format du niveau M avec le masque 0 vaut alors zero : quinze "
              "modules clairs d'affilee a cote du reperage, que le lecteur prend "
              "pour une zone vide. Et sur les autres masques, il defait le "
              "mauvais numero",
        rougit="les huit masques s'annoncent juste et se defont pour rendre les "
               "memes mots",
        editions=[
            ("qr.py", brut(
                "    return ((donnee << 10) | reste) ^ 0b101010000010010\n",
                "    return (donnee << 10) | reste\n")),
        ]),
    dict(
        nom="le bloc d'information de version n'est jamais ecrit",
        banc="banc_qr.py",
        imite="a partir de la version 7, le lecteur doit deviner la taille du "
              "code au lieu de la lire. Beaucoup y arrivent, certains non : le "
              "meme code marche sur un telephone et pas sur l'autre. Et il "
              "n'existe pas en dessous de la 7, donc les petits codes ne le "
              "montrent jamais",
        rougit="« reel » (7-M) se refait module par module depuis ses mots de code",
        # L'ANCRE NE PREND PAS LA LIGNE « def », ET C'EST UNE MESURE. Elle la
        # prenait ; le 3 septembre 2026, une docstring ajoutee a
        # _ecrire_version() a gliss'e entre la signature et le test, et le
        # passage suivant de ce banc a rendu « MUTATION PERIMEE, 0 occurrence ».
        # C'est le bon sens de l'erreur — mais la lecon est que l'ancre doit
        # tenir sur la DECISION (le seuil de version) et non sur ce qui
        # l'entoure, qui se commente et se reformule.
        editions=[
            ("qr.py", brut(
                "    if version < 7:\n"
                "        return\n",
                "    if version < 41:\n"
                "        return\n")),
        ]),
    dict(
        nom="la frontiere du champ de longueur passe de 9 a 10",
        banc="banc_qr.py",
        imite="a la version 10, le champ « combien d'octets » compte 8 bits au "
              "lieu de 16 : tout le flux decale de huit bits et le lecteur lit "
              "une longueur absurde. Aucun etalon ne va jusque-la — c'est le "
              "balayage des quarante versions qui l'attrape, et lui seul",
        rougit="ne devrait PAS prendre",
        editions=[
            ("qr.py", brut(
                "    return 8 if version <= 9 else 16\n",
                "    return 8 if version <= 10 else 16\n")),
        ]),
    dict(
        nom="la seconde copie du format d'information disparait",
        banc="banc_qr.py",
        imite="le format n'est plus ecrit qu'une fois. Le code se lit — jusqu'au "
              "jour ou le coin haut-gauche est sali, et ce jour-la il ne se lit "
              "plus du tout, alors que la redondance existe exactement pour ce "
              "cas",
        rougit="« ascii » (1-M) se refait module par module depuis ses mots de code",
        editions=[
            ("qr.py", brut(
                "    for i in range(8):\n"
                "        modules[8][taille - 1 - i] = bit(i)\n"
                "    for i in range(8, 15):\n"
                "        modules[taille - 15 + i][8] = bit(i)\n",
                "")),
        ]),
    dict(
        nom="les modules du QR prennent la couleur du theme",
        banc="banc_page.py",
        imite="LE PIEGE DU THEME SOMBRE, et c'est la panne la plus silencieuse "
              "de cet ecran. La page est sombre par defaut : dessiner les "
              "modules avec la couleur de texte INVERSE le code, et beaucoup de "
              "lecteurs echouent sur un code inverse sans rien afficher. En "
              "theme clair, tout marche — donc celui qui developpe ne le voit "
              "jamais",
        rougit="le QR code ne suit PAS le theme",
        editions=[
            ("web/index.html", brut(
                '<path d="${chemin}" fill="#000000"/>',
                '<path d="${chemin}" fill="var(--encre)"/>')),
        ]),
    dict(
        nom="la zone de silence tombe a zero module",
        banc="banc_page.py",
        imite="le code colle au fond de la boite. Un lecteur ne retrouve plus "
              "les trois coins de reperage sans les quatre modules clairs que la "
              "norme exige autour, et l'appareil photo reste ouvert sur l'ecran "
              "sans rien trouver",
        rougit="et sa zone de silence fait quatre modules, posee dans le viewBox",
        editions=[
            ("web/index.html", brut(
                "const MARGE_QR = 4;\n",
                "const MARGE_QR = 0;\n")),
        ]),
    dict(
        nom="le secret ecrit disparait sous le QR code",
        banc="banc_page.py",
        imite="il ne reste que le code a scanner. Quiconque enrole depuis la "
              "machine qui affiche l'ecran est enferme dehors — un telephone ne "
              "se photographie pas lui-meme — et rien a l'ecran ne le lui dit",
        rougit="l'ecran d'enrolement offre les TROIS chemins",
        editions=[
            ("web/index.html", brut(
                'corps.append(dire("page.mfa.recopie"), secret, lien);',
                "corps.append(secret, lien);")),
        ]),
    dict(
        nom="la route d'enrolement renomme le champ que la page dessine",
        banc="banc_page.py",
        imite="la meme derive que MARQUE_MFA, et la meme panne muette : "
              "dessinerQR() recoit « undefined », rend null, et le QR "
              "disparait de l'ecran sans qu'une ligne de la page ni du serveur "
              "ait l'air fautive",
        rougit="et la page dessine le champ « qr » que la route d'enrolement sert",
        editions=[
            ("serveur.py", brut(
                "                                  qr=matrice))",
                "                                  code_qr=matrice))")),
        ]),
]


# ──────────────────────────────────────────────────────────────────────
#  Les deux dernieres trouvailles de la relecture adverse — quatre mutations
# ──────────────────────────────────────────────────────────────────────
# DEUX DEFAUTS DE FILET, ET NON DEUX DEFAUTS DE CODE. Le premier est un cas
# ECRIT POUR CE COUPLAGE qui ne comparait que la moitie de ce qu'il nomme ; le
# second est un fichier entier hors de portee de ce banc-ci.
#
# ── 1. LES BORNES DE /admin, ET PAS SEULEMENT SES NOMS ────────────────
# banc_page.py releve depuis le 3 septembre que /admin et BORNES_REGLAGES
# nomment les memes reglages. Il ne relevait QUE les noms : les quatre paires
# « min/max » de la page sont recopiees a la main face au dictionnaire du
# serveur, et muter l'un ou l'autre cote laissait le banc VERT. Mesure du
# 3 septembre 2026, avant reparation : « max="1440" » passe a « max="720" » sur
# #vramReposMin, banc_page.py rend 66/0, pas une ligne rouge. Le cas ecrit pour
# ce couplage ne voyait pas ce couplage — la faute que ce fichier existe pour
# trouver, une fois de plus.
#
# LE SENS INVERSE, et il faut l'ecrire plutot que de le mimer : ce releve-la
# est un FILET NEUF, comme le couplage des noms avant lui. Sur le depot
# d'avant, les quatre paires s'accordaient deja — il aurait ete vert. Ce n'est
# pas un defaut qu'on repare, c'est une moitie de mesure qui manquait. Ce qui
# EST montre : la mutation rougit sur la page ET sur le serveur, dans les deux
# sens de la derive (0-720 contre 0-1440, puis l'inverse), et sur la ligne
# nommee.
#
# ── 2. UN POST REFUSE ETAIT SILENCIEUX ────────────────────────────────
# Celui-la est un vrai defaut de code, et le commentaire du cas de banc_page.py
# le decrivait DEJA sans que rien ne le mesure : « le POST repond 400, le champ
# se remet a sa valeur d'avant au rafraichissement suivant, et l'administrateur
# croit simplement que son chiffre a ete refuse ». C'etait pire : il ne croyait
# rien du tout, rien ne s'affichait. « poserPause » et « poserRepos »
# appelaient api() sans regarder ce qu'elle rendait ; seul « poserPlafond »
# lisait le refus.
#
# LA REPARATION EST CELLE DE raccourci_ecrit(), APPLIQUEE A LA PAGE : tant
# qu'il y avait trois ecritures du meme geste, deux avaient derive. Il n'y en a
# plus qu'une, poserReglages(corps, "#zone"), et les trois cartes l'empruntent.
# Le banc ne releve donc pas « chaque bouton regarde r.ok » — ce serait relever
# UNE facon d'ecrire la garde — mais qu'il n'y a qu'un seul ecrivain et qu'il
# lit le refus.
#
# LE SENS INVERSE, PRIS COMME POUR banc_refaire.py : les cinq cas sont nes avec
# la correction, donc pas de filet d'avant. banc_page.py NEUF lance sur la page
# d'AVANT — les trois cartes restaurees mot pour mot, sans poserReglages ni
# zones d'alerte — rend 66/5, et les deux lignes que ces mutations nomment y
# sont toutes les deux. Sur le depot du jour, 71/0.
#
# ── 3 et 4. agent_noeud.py, ENFIN SOUS FILET ──────────────────────────
# Voir BESOINS. Le sens inverse a ete pris comme pour banc_refaire.py :
# banc_agent.py NEUF lance sur un agent_noeud.py d'ou la liberation est retiree
# rend 4/9, et « ET la liberation du cache » y est rouge. La mutation du
# « not EN_COURS_ICI », elle, ne peut PAS s'y montrer rouge et il faut le dire :
# sur un agent qui ne libere jamais, « une machine qui CALCULE ne la rend pas »
# est vraie de rien. La ligne qui rougit la-bas pour cette regle est sa jumelle,
# « une machine au repos … la REND » — c'est pour cela que les deux sont
# relevees, l'une sans l'autre etant verte d'un agent qui libere toujours ou
# d'un agent qui ne libere jamais.
ADVERSE = [
    dict(
        nom="la borne de /admin derive de celle du serveur",
        banc="banc_page.py",
        imite="ce que le cas voisin ne voyait pas : les quatre « min/max » de "
              "la page sont recopies a la main face a BORNES_REGLAGES. Une "
              "page plus etroite que le serveur cache un reglage qu'il "
              "accepte ; plus large, elle laisse taper un chiffre que le POST "
              "refusera. Le nom, lui, reste juste des deux cotes — et c'est "
              "tout ce que le banc regardait",
        rougit="et les bornes de /admin sont CELLES du serveur, chiffre pour "
               "chiffre",
        editions=[("web/admin.html", brut(
            'id="vramReposMin" min="0" max="1440"',
            'id="vramReposMin" min="0" max="720"'))]),
    dict(
        nom="une carte repose son reglage toute seule, et redevient muette",
        banc="banc_page.py",
        imite="le code d'AVANT, mot pour mot : la carte du repos poste "
              "elle-meme et jette la reponse. Un 400 n'affiche RIEN, "
              "rafraichir() remet la valeur d'avant dans le champ, et "
              "l'administrateur lit son ancien chiffre en croyant que le "
              "nouveau a ete pris. C'est le symptome que le cas voisin decrit "
              "dans son propre commentaire depuis le premier jour",
        rougit="un seul endroit de /admin poste les reglages",
        editions=[("web/admin.html", brut(
            '$("#poserRepos").onclick = async () => {' + chr(10)
            + '  if (await poserReglages(' + chr(10)
            + '        { vram_repos_min: Number($("#vramReposMin").value) },'
            + ' "#alerteRepos"))' + chr(10)
            + '    rafraichir();' + chr(10) + '};',
            '$("#poserRepos").onclick = async () => {' + chr(10)
            + '  await api("/api/admin/reglages", "POST",' + chr(10)
            + '            { vram_repos_min:'
            + ' Number($("#vramReposMin").value) });' + chr(10)
            + '  rafraichir();' + chr(10) + '};'))]),
    dict(
        nom="l'ecrivain unique jette le refus du serveur",
        banc="banc_page.py",
        imite="la meme panne muette, mais posee la ou elle atteint les TROIS "
              "cartes d'un coup : l'unique fonction qui poste les reglages "
              "cesse de regarder ce que le serveur repond. Rien ne leve, rien "
              "ne s'affiche, et le studio a l'air d'accepter tout ce qu'on lui "
              "donne",
        rougit="et il MONTRE le refus du serveur au lieu de le jeter",
        editions=[("web/admin.html", brut(
            '  if (!r.ok) {' + chr(10)
            + '    if (zone) zone.textContent = (r.d && r.d.erreur)'
            + ' || "réglage refusé";' + chr(10)
            + '    return false;' + chr(10) + '  }' + chr(10)
            + '  return true;',
            '  return true;'))]),
    dict(
        nom="/free ne demande plus que la moitie de la memoire",
        banc="banc_agent.py",
        imite="la mutation qui revenait « PERIMEE » faute d'un banc qui copie "
              "agent_noeud.py. Le commentaire de liberer_carte() porte pourtant "
              "la mesure : « l'un sans l'autre laisse plusieurs gigaoctets, ce "
              "qui donne exactement l'apparence d'un /free qui ne marche pas ». "
              "La carte rend ses modeles et garde son cache, la colonne « carte "
              "» de /admin ne bouge presque pas, et l'on cherche le defaut du "
              "cote du studio",
        rougit="ET la liberation du cache : l'une sans l'autre laisse des "
               "gigaoctets",
        editions=[("agent_noeud.py", brut(
            'corps={"unload_models": True,' + chr(10)
            + '                                            "free_memory": True},'
            + ' secondes=20',
            'corps={"unload_models": True}, secondes=20'))]),
    dict(
        nom="l'agent libere la carte pendant qu'il calcule",
        banc="banc_agent.py",
        imite="l'autre mutation perimee, et c'est la moitie du garde-fou que "
              "le studio NE PEUT PAS tenir a sa place : il decide sur ce qu'il "
              "savait au debut du battement, et la boucle a pu prendre un "
              "travail entre sa decision et l'arrivee de sa reponse. Sans cette "
              "ligne, ComfyUI decharge un modele qu'il vient de charger et "
              "l'image part avec une minute de retard, sans que personne ne "
              "comprenne pourquoi",
        rougit="une machine qui CALCULE ne la rend pas, meme si le studio la "
               "reclame",
        editions=[("agent_noeud.py", brut(
            'if d.get("liberer") and not EN_COURS_ICI:',
            'if d.get("liberer"):'))]),
]


# ──────────────────────────────────────────────────────────────────────
#  agent_noeud.py, le reste du fichier — vingt-huit mutations
# ──────────────────────────────────────────────────────────────────────
# banc_agent.py ne couvrait que liberer_carte() et battre_annonce(). Le fichier
# fait onze cents lignes, et le RESTE n'avait aucun filet : la mise a jour, le
# rendu, le depot des entrees, le registre des sorties, la websocket de
# progression. Les mutations ci-dessous suivent l'ordre de la CONSEQUENCE.
#
# LE SENS INVERSE. Toutes ces gardes existaient avant le banc : la mutation EST
# la correction defaite, et « banc_agent.py est vert sur le depot sain » en tete
# de ce fichier tient l'autre moitie. Une seule exception, la derniere de la
# liste — la remise a zero du pourcentage, corrigee le 3 septembre 2026 en meme
# temps que le banc : elle n'a pas de filet d'avant, et le sens inverse a donc
# ete pris comme pour banc_refaire.py. banc_agent.py NEUF lance sur
# l'agent_noeud.py d'AVANT rend 83/1, rouge sur la ligne exacte que la mutation
# nomme, et 84/0 sur le depot du jour.
MAJ_AGENT = [
    dict(
        nom="l'empreinte epinglee n'est plus qu'un avertissement",
        banc="banc_agent.py",
        imite="le seul garde-fou dont dispose celui qui heberge contre un "
              "agent servi par autre chose que son studio. Il a releve le "
              "sha256 en SSH sur l'hote, l'a epingle par --empreinte, et la "
              "machine installe quand meme ce qu'on lui donne — en le lui "
              "DISANT, ce qui est pire : la ligne rassurante est la, et le "
              "code d'un autre tourne",
        rougit="une empreinte EPINGLEE qui ne correspond pas : rien n'est "
               "remplace",
        editions=[("agent_noeud.py", brut(
            '        print("  EMPREINTE INATTENDUE — rien n\'a ete remplace")'
            + chr(10)
            + '        print(f"    recue    : {recue}")' + chr(10)
            + '        print(f"    attendue : {attendue}")' + chr(10)
            + '        return 1' + chr(10),
            '        print("  EMPREINTE INATTENDUE")' + chr(10)))]),
    dict(
        nom="l'empreinte doit etre tapee exactement comme le sha256 sort",
        banc="banc_agent.py",
        imite="un sha256 qui se releve a la main. « sha256sum » rend des "
              "minuscules, « certutil -hashfile » et « Get-FileHash » de "
              "Windows rendent des MAJUSCULES, et un copier-coller ramene une "
              "espace. L'empreinte JUSTE est alors refusee : la machine reste "
              "sur sa vieille version en croyant se defendre, et l'on cherche "
              "l'erreur du cote du studio",
        rougit="l'empreinte relevee en MAJUSCULES, ou avec des espaces, reste "
               "la bonne",
        editions=[("agent_noeud.py", brut(
            'attendue = (empreinte or "").strip().lower()',
            'attendue = empreinte or ""'))]),
    dict(
        nom="on ne verifie plus que c'est du texte, pas que c'est du Python",
        banc="banc_agent.py",
        imite="le code d'avant le 31 aout, ou le fichier n'etait pas relu "
              "avant d'ecraser un agent qui fonctionnait. Anodin tant qu'un "
              "humain lançait « --maj » et voyait l'erreur au redemarrage ; "
              "depuis que la mise a jour est automatique, un telechargement "
              "tronque fait une brique sans personne pour le voir — et la "
              "machine ne redemarrera plus pour aller chercher la correction",
        rougit="un telechargement TRONQUE ne remplace pas un agent qui "
               "fonctionne",
        editions=[("agent_noeud.py", brut(
            "        ast.parse(octets.decode(\"utf-8\"))",
            "        octets.decode(\"utf-8\")"))]),
    dict(
        nom="le refus ne couvre plus que la syntaxe, pas l'encodage",
        banc="banc_agent.py",
        imite="la moitie oubliee du meme garde-fou. ast.parse() ne recoit pas "
              "du texte, il recoit ce que le reseau a rendu : des octets. Une "
              "image, une archive, une reponse binaire d'un proxy ne levent "
              "pas SyntaxError mais UnicodeDecodeError — qui traverse "
              "se_mettre_a_jour(), traverse se_mettre_a_jour_seul(), et "
              "emporte la boucle de travail de l'agent",
        rougit="ni des octets qui ne sont meme pas du texte",
        editions=[("agent_noeud.py", brut(
            "    except (UnicodeDecodeError, SyntaxError) as e:",
            "    except SyntaxError as e:"))]),
    dict(
        nom="la copie de secours n'est plus faite",
        banc="banc_agent.py",
        imite="l'agent remplace, et il ne reste rien a cote. Une version "
              "cassee est justement celle qui ne redemarrera pas pour aller "
              "en chercher une autre : sans .precedent, il faut aller "
              "physiquement sur la machine a carte, qui est souvent celle de "
              "quelqu'un d'autre",
        rougit="et il garde l'ancienne a cote, sous .precedent",
        editions=[("agent_noeud.py", brut(
            '        with open(moi + ".precedent", "wb") as f:' + chr(10)
            + '            f.write(open(moi, "rb").read())' + chr(10),
            ""))]),
    dict(
        nom="l'agent se reecrit meme quand rien n'a change",
        banc="banc_agent.py",
        imite="ce qui detruit la copie de secours a petit feu. La mise a jour "
              "est tentee a chaque battement : sans ce court-circuit, l'agent "
              "recopie son propre fichier dans .precedent au premier passage, "
              "et la version d'avant — la seule qui marchait — est perdue "
              "avant meme qu'on en ait besoin",
        rougit="et quand le studio sert le meme agent, rien n'est reecrit",
        editions=[("agent_noeud.py", brut(
            '    if octets == open(moi, "rb").read():' + chr(10)
            + '        print("  deja a jour.")' + chr(10)
            + '        return 0' + chr(10),
            ""))]),
    dict(
        nom="la mise a jour automatique ignore l'empreinte epinglee",
        banc="banc_agent.py",
        imite="l'epingle qui ne tient que sur « --maj » tape a la main, et pas "
              "sur le chemin qui compte : celui ou personne ne regarde. "
              "L'agent se remplace tout seul a chaque battement, et l'epingle "
              "de celui qui heberge ne sert plus a rien",
        rougit="une empreinte EPINGLEE arrete la mise a jour automatique",
        editions=[("agent_noeud.py", brut(
            "    if epinglee:" + chr(10)
            + '        print(f"  le studio sert un agent different (sha256 '
            + '{attendue[:12]}…), "' + chr(10)
            + '              f"mais une empreinte est epinglee : rien ne sera '
            + 'remplace",' + chr(10)
            + "              flush=True)" + chr(10)
            + "        return None" + chr(10),
            ""))]),
    dict(
        nom="le studio annonce une empreinte et en sert une autre",
        banc="banc_agent.py",
        imite="ce que la mise a jour automatique cesse de verifier quand elle "
              "ne repasse plus l'empreinte annoncee. Le studio dit servir X, "
              "sert Y — telechargement tronque, proxy qui reecrit les fins de "
              "ligne, studio mis a jour entre l'annonce et la demande — et la "
              "machine redemarre sur un fichier different de celui qu'elle "
              "croit avoir, en boucle puisque son empreinte ne correspondra "
              "jamais",
        rougit="un agent servi different de l'empreinte ANNONCEE n'est pas "
               "installe",
        editions=[("agent_noeud.py", brut(
            "    if se_mettre_a_jour(studio, attendue) != 0:",
            "    if se_mettre_a_jour(studio) != 0:"))]),
    dict(
        nom="le marqueur anti-boucle cloue la machine sur sa version",
        banc="banc_agent.py",
        imite="un marqueur qui arrete TOUTE mise a jour au lieu de la seule "
              "empreinte deja tentee. Une premiere tentative rate — le studio "
              "servait un fichier tronque — et la machine ne prendra plus "
              "jamais aucune version, y compris celle qui corrige justement le "
              "defaut. Elle est perdue jusqu'a ce que quelqu'un aille la "
              "relancer a la main",
        rougit="mais une AUTRE empreinte repart : le marqueur ne cloue pas la "
               "machine",
        editions=[("agent_noeud.py", brut(
            "    if os.environ.get(MARQUE_MAJ) == attendue:",
            "    if os.environ.get(MARQUE_MAJ):"))]),
    dict(
        nom="le marqueur n'est pas pose avant le redemarrage",
        banc="banc_agent.py",
        imite="l'autre moitie de l'anti-boucle. Le marqueur voyage par "
              "l'environnement, qui survit a os.execv ; pose apres, il ne "
              "serait pose par personne — le processus n'existe plus. Une "
              "empreinte qui ne correspondra jamais fait alors redemarrer la "
              "machine toutes les dix secondes, sans fin et sans qu'aucun "
              "message ne le dise",
        rougit="et il laisse sa trace dans l'environnement AVANT de se "
               "remplacer",
        editions=[("agent_noeud.py", brut(
            "    os.environ[MARQUE_MAJ] = attendue" + chr(10), ""))]),
    dict(
        nom="l'agent redemarre meme quand le remplacement a echoue",
        banc="banc_agent.py",
        imite="un redemarrage tire sur un fichier qui n'a pas ete remplace. "
              "L'agent repart sur le MEME code, retrouve la meme empreinte a "
              "l'annonce suivante, et recommence : une machine qui redemarre "
              "en rond au lieu de continuer a travailler avec la version "
              "qu'elle a",
        rougit="un agent casse servi par le studio : rien de pose, rien de "
               "redemarre, aucun marqueur",
        editions=[("agent_noeud.py", brut(
            "    if se_mettre_a_jour(studio, attendue) != 0:" + chr(10)
            + "        return None" + chr(10),
            "    se_mettre_a_jour(studio, attendue)" + chr(10)))]),
    dict(
        nom="les morceaux d'os.execv partent sans guillemets sous Windows",
        banc="banc_agent.py",
        imite="la mesure du 31 aout avec « C:/Program Files/Python314 ». "
              "os.execv y recolle les arguments en une seule ligne de commande "
              "SANS les proteger : l'enfant meurt sur « C:\\Program: can't "
              "open file », et le parent sort avec le code 0 — donc aucune "
              "OSError, donc le repli ne s'execute jamais et l'agent est mort "
              "pour de bon. La CI tourne sous Linux et ne le verrait jamais",
        rougit="sous Windows, l'interpreteur et le script a espaces partent "
               "proteges",
        editions=[("agent_noeud.py", brut(
            '        if os.name == "nt":' + chr(10)
            + '            morceaux = [f\'"{m}"\' if " " in m and not '
            + 'm.startswith(\'"\') else m' + chr(10)
            + "                        for m in morceaux]" + chr(10),
            ""))]),
]

RENDU_AGENT = [
    dict(
        nom="les deux client_id de l'agent divergent",
        banc="banc_agent.py",
        imite="le seul couplage de ce fichier qui ne leve jamais. executer() "
              "soumet le graphe sous un client_id, ecouter_progression() "
              "s'abonne a la websocket sous un autre — deux chaines "
              "litterales, dans deux fonctions, a trois cents lignes d'ecart. "
              "ComfyUI adresse la progression AU CLIENT QUI A SOUMIS : les "
              "rendus continuent de sortir, la barre de la file est morte, et "
              "rien ne le dit",
        rougit="et il s'abonne sous le MEME client_id que celui qui a soumis "
               "le graphe",
        editions=[("agent_noeud.py", brut(
            'f"GET /ws?clientId=agent HTTP/1.1' + chr(92) + 'r' + chr(92) + 'n"',
            'f"GET /ws?clientId=comfystudio HTTP/1.1' + chr(92) + 'r'
            + chr(92) + 'n"'))]),
    dict(
        nom="« dire » n'est appele que s'il y a un pourcentage a montrer",
        banc="banc_agent.py",
        imite="le trou que le commentaire d'executer() decrit lui-meme. C'est "
              "la REPONSE a cette annonce qui apporte l'annulation, et les "
              "premieres dizaines de secondes d'un rendu — le chargement du "
              "modele — n'ont aucun pourcentage. Annuler pendant ce trou-la ne "
              "coupe rien : l'utilisateur clique, l'interface dit annule, et "
              "la carte continue de calculer une image que personne ne verra",
        rougit="« dire » est appele des le premier tour, sans attendre un "
               "pourcentage",
        editions=[("agent_noeud.py", brut(
            '        if dire and dire(PROGRES["fait"], PROGRES["total"]):',
            '        if dire and PROGRES["total"] and dire(PROGRES["fait"],'
            + ' PROGRES["total"]):'))]),
    dict(
        nom="l'annulation tire sans regarder la file",
        banc="banc_agent.py",
        imite="POST /interrupt ne nomme pas le travail qu'il coupe : il coupe "
              "ce qui tourne. Sur une carte que son proprietaire fait aussi "
              "travailler depuis l'interface de ComfyUI, une annulation cote "
              "studio lui vole SON rendu a lui — et l'agent annonce « carte "
              "interrompue » comme si de rien n'etait",
        rougit="et un rendu qui n'est pas le notre n'est NI coupe NI retire de "
               "la file",
        editions=[("agent_noeud.py", brut(
            '    if _dedans("queue_pending"):' + chr(10)
            + '        appeler(f"{comfy}/queue", corps={"delete": [pid]},'
            + " secondes=10)" + chr(10)
            + '        return "retire de la file avant le GPU"' + chr(10)
            + '    if _dedans("queue_running"):' + chr(10)
            + '        appeler(f"{comfy}/interrupt", corps={}, secondes=10)'
            + chr(10)
            + '        return "carte interrompue"' + chr(10)
            + '    return "deja fini, rien a couper"',
            '    appeler(f"{comfy}/interrupt", corps={}, secondes=10)' + chr(10)
            + '    return "carte interrompue"'))]),
    dict(
        nom="tout ce qu'un noeud pose dans « outputs » est pris pour un fichier",
        banc="banc_agent.py",
        imite="un noeud qui rend un nombre, un texte ou une liste de rien a "
              "cote de ses images — il y en a. L'agent les prend pour des "
              "fichiers, lire_sortie() leve sur un « filename » absent au "
              "moment de livrer, et le rendu ECHOUE apres que la carte a "
              "travaille : le travail est fait, l'utilisateur lit « echec »",
        rougit="et ce qu'un noeud pose dans « outputs » sans etre un fichier "
               "est ecarte",
        editions=[("agent_noeud.py", brut(
            '                        sorties += [x for x in valeur' + chr(10)
            + '                                    if isinstance(x, dict) and '
            + '"filename" in x]',
            '                        sorties += [x for x in valeur' + chr(10)
            + '                                    if isinstance(x, dict)]'))]),
]

DISQUE_AGENT = [
    dict(
        nom="le fichier d'entree part en base64 au lieu de ses octets",
        banc="banc_agent.py",
        imite="une image d'entree ecrite sur la machine a carte sous une forme "
              "que ComfyUI ne sait pas lire. Le depot repond 200, le graphe "
              "est correct, et le rendu echoue sur un fichier illisible — sans "
              "que rien, du cote du studio, ne puisse distinguer ça d'un "
              "modele absent",
        rougit="et ce sont les octets decodes qui partent, pas le base64",
        editions=[("agent_noeud.py", brut(
            "        octets = base64.b64decode(donnees)",
            "        octets = donnees.encode()"))]),
    dict(
        nom="la frontiere du multipart est fixe",
        banc="banc_agent.py",
        imite="une frontiere constante dans un corps qui transporte des "
              "octets d'image bruts. Le jour ou la suite apparait dans "
              "l'image, le corps est coupe en plein milieu et ComfyUI retient "
              "un fichier tronque. C'est rare, ce n'est jamais reproductible, "
              "et c'est exactement pour ça que uuid4 est la",
        rougit="chaque fichier porte SA frontiere, tiree au hasard",
        editions=[("agent_noeud.py", brut(
            '        limite = "----" + uuid.uuid4().hex',
            '        limite = "----frontiere-comfystudio"'))]),
    dict(
        nom="seul le champ « image » du graphe est corrige",
        banc="banc_agent.py",
        imite="la moitie de CHAMPS_ENTREE, qui doit bouger avec "
              "entrees_du_graphe() de serveur.py. ComfyUI renomme en "
              "« x (1).png » quand le nom existe deja : les champs non "
              "corriges pointent alors sur un fichier qui n'est pas celui "
              "qu'on vient d'ecrire — le son, la video ou le fichier du "
              "rendu PRECEDENT, ou celui d'un autre utilisateur",
        rougit="quand ComfyUI renomme, les quatre champs d'entree du graphe "
               "suivent",
        editions=[("agent_noeud.py", brut(
            'CHAMPS_ENTREE = ("image", "file", "audio", "video")',
            'CHAMPS_ENTREE = ("image",)'))]),
    dict(
        nom="le registre des depots retourne vivre a cote du script",
        banc="banc_agent.py",
        imite="le demenagement defait. En conteneur, le script, les reglages "
              "et /tmp repartent a zero a chaque demarrage : le registre est "
              "perdu a chaque redemarrage, le menage ne trouve plus rien a "
              "effacer, et le disque de la machine a carte se remplit en "
              "silence — sans que personne ne s'en apercoive avant qu'il soit "
              "plein",
        rougit="le registre des depots vit DANS le dossier des sorties, pas a "
               "cote du script",
        editions=[("agent_noeud.py", brut(
            '    chemin = os.path.join(sorties or ICI,' + chr(10)
            + '                          "." + DEPOSEES if sorties else '
            + "DEPOSEES)",
            "    chemin = os.path.join(ICI, DEPOSEES)"))]),
    dict(
        nom="la garde n'est plus un delai",
        banc="banc_agent.py",
        imite="un menage qui efface une sortie a la seconde ou elle est "
              "deposee. Le studio en a bien une copie — mais le proprietaire "
              "de la machine a carte, lui, voit ses rendus disparaitre de son "
              "dossier output sous ses yeux, et --garder-heures ne sert plus a "
              "rien",
        rougit="ni une sortie deposee trop recemment — la garde est un delai, "
               "pas un drapeau",
        editions=[("agent_noeud.py", brut(
            "    limite = time.time() - garde_h * 3600",
            "    limite = time.time()"))]),
    dict(
        nom="un fichier qu'on n'a pas pu effacer est raye du registre",
        banc="banc_agent.py",
        imite="une sortie verrouillee au moment du menage — ouverte dans une "
              "visionneuse, un disque reseau qui repond mal. Rayee du "
              "registre, elle n'est plus surveillee par personne : elle "
              "restera la pour toujours, et le --garder-heures ne la reprendra "
              "jamais",
        rougit="ce qui a deja disparu est oublie, ce qu'on n'a pas pu effacer "
               "reste au registre",
        editions=[("agent_noeud.py", brut(
            '            print(f"  suppression impossible ({err}) — on garde '
            + 'la trace",' + chr(10)
            + "                  flush=True)" + chr(10)
            + "            restant.append(e)",
            '            print(f"  suppression impossible ({err})",'
            + chr(10) + "                  flush=True)"))]),
    dict(
        nom="a la reprise du registre, c'est la note la plus ancienne qui gagne",
        banc="banc_agent.py",
        imite="un fichier redepose entre les deux registres. La vieille note "
              "l'emporte, sa date est deja au-dela de la garde, et le menage "
              "efface une sortie que l'agent vient de reposer — celle que le "
              "studio est justement en train de venir chercher",
        rougit="et d'un fichier note deux fois, c'est la note la PLUS RECENTE "
               "qui compte",
        editions=[("agent_noeud.py", brut(
            '        if vue is None or e.get("quand", 0) >= vue.get("quand", 0):',
            "        if vue is None:"))]),
]

PROGRESSION_AGENT = [
    dict(
        nom="le pong n'est pas masque",
        banc="banc_agent.py",
        imite="une trame client vers serveur sans masque, ce que la RFC 6455 "
              "interdit. Le serveur ferme la connexion des le premier ping — "
              "toutes les minutes chez aiohttp — l'agent se reconnecte, et la "
              "barre de la file clignote sans que rien ne leve nulle part",
        rougit="et son second octet declare le masque et la longueur de la "
               "charge",
        editions=[("agent_noeud.py", brut(
            "                    sock.sendall(bytes([0x8A, 0x80 | "
            + "len(charge)]) + cle4 + charge)",
            "                    sock.sendall(bytes([0x8A, len(charge)]) + "
            + "cle4 + charge)"))]),
    dict(
        nom="la clef de masque du pong est constante",
        banc="banc_agent.py",
        imite="LE CAS QU'UN SEUL TIRAGE NE VOIT PAS. Un masque nul passe le "
              "round-trip — XOR par zero rend la charge intacte — et l'octet "
              "de tete declare toujours le masque : deux cas sur trois restent "
              "verts. La RFC exige une clef IMPREVISIBLE par trame, et c'est "
              "la seule chose qui empeche un cache intermediaire d'empoisonner "
              "la connexion. Il faut cinquante tirages pour la distinguer "
              "d'une clef tiree au hasard",
        rougit="avec une clef de masque TIREE A CHAQUE TRAME, comme l'exige la "
               "RFC 6455",
        editions=[("agent_noeud.py", brut(
            "                    cle4 = os.urandom(4)",
            '                    cle4 = b"' + chr(92) + "x00" + chr(92) + "x00"
            + chr(92) + "x00" + chr(92) + 'x00"'))]),
    dict(
        nom="les trames de plus de 125 octets ne sont plus lues",
        banc="banc_agent.py",
        imite="la longueur etendue de la websocket, oubliee. Au-dela de 125 "
              "octets la taille passe dans deux octets de plus, et un message "
              "de progression qui nomme le noeud en cours y arrive tout de "
              "suite. Sans cette branche, l'agent lit la taille comme un "
              "corps : il se desynchronise du flux et ne comprend plus une "
              "seule trame jusqu'a la reconnexion",
        rougit="une trame de plus de 125 octets est lue, longueur etendue "
               "comprise",
        editions=[("agent_noeud.py", brut(
            "    if taille == 126:" + chr(10)
            + '        t = lire(2)' + chr(10)
            + '        taille = int.from_bytes(t, "big") if t else 0' + chr(10)
            + "    elif taille == 127:",
            "    if taille == 127:"))]),
    dict(
        nom="une trame illisible emporte la connexion",
        banc="banc_agent.py",
        imite="un « continue » devenu « break ». ComfyUI emet des messages que "
              "l'agent ne connait pas et n'a pas a connaitre ; une seule trame "
              "que json refuse, et la connexion tombe. Elle se rattrape, mais "
              "le temps d'attente double a chaque fois jusqu'a trente "
              "secondes : la progression finit par ne plus arriver du tout",
        rougit="une trame illisible est sautee, et la suivante est lue quand "
               "meme",
        editions=[("agent_noeud.py", brut(
            "                except ValueError:" + chr(10)
            + "                    continue",
            "                except ValueError:" + chr(10)
            + "                    break"))]),
    dict(
        nom="le pourcentage reste fige quand la connexion tombe",
        banc="banc_agent.py",
        imite="LE DEFAUT CORRIGE LE 3 SEPTEMBRE 2026, remis en place. La "
              "remise a zero ne vivait que dans le « except », et les DEUX "
              "sorties les plus frequentes de la boucle de trames n'y passent "
              "pas : une fermeture propre (opcode 0x8, ce qu'envoie un ComfyUI "
              "qui redemarre) et un flux qui s'arrete net sortent par un "
              "« break ». Mesure au banc : 7/20 apres la fermeture, 7/20 apres "
              "la coupure, 0/0 apres une poignee de main refusee — pour trois "
              "pertes de connexion identiques. Le studio affichait 35 % sur un "
              "rendu mort jusqu'au delai d'executer(), soit une heure au pire, "
              "et le rendu SUIVANT demarrait a 35 %",
        rougit="une connexion fermee par ComfyUI ne laisse pas un pourcentage "
               "FIGE",
        editions=[("agent_noeud.py", motif(
            r"            # ICI ET PAS DANS LE SEUL .*?\n"
            r"            PROGRES\.update\(fait=0, total=0\)\n",
            ""))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_noeud.py — dix mutations, toutes verifiees rouges
# ──────────────────────────────────────────────────────────────────────
# CE BANC EST NE AVEC LES CORRECTIONS QU'IL GARDE, et CONTRIBUTING.md dit ce
# qu'il faut faire dans ce cas : « lance le banc NEUF sur le code d'AVANT et
# verifie que les lignes que ta mutation nomme y rougissent ». Fait le
# 4 septembre 2026 sur les fichiers d'avant correction : 18 cas rouges sur 34,
# et les dix lignes que ces mutations nomment y sont toutes. Les mutations
# ci-dessous rejouent chacune UNE de ces pannes, pour que le filet reste eprouve
# quand le defaut, lui, aura ete oublie.
#
# Elles visent le SEUL banc du depot qui lance un script shell : ce qu'il
# mesure ne se lit pas dans le texte des fichiers — c'est tout son propos — et
# une mutation qui deplacerait une ligne sans changer le comportement le
# laisserait vert a bon droit.
NOEUD = [
    dict(
        nom="ecrire_reglages n'existe plus au moment de l'appel",
        banc="banc_noeud.py",
        imite="LE DEFAUT D'ORIGINE : la fonction etait definie DANS le « if "
              "[ -z \"$JETON\" ] », donc absente des que --jeton est fourni — "
              "c'est-a-dire pour la commande exacte que /admin distribue. "
              "« command not found » ne tue rien (pas de set -e) et l'agent "
              "demarre sans configuration, puis sort sur « Il manque l'adresse "
              "du studio »",
        rougit="et l'agent trouve le jeton dans agent_noeud.json quand il demarre",
        editions=[
            ("noeud.sh", brut("ecrire_reglages() {",
                              "ecrire_reglages_jamais_definie() {"))]),
    dict(
        nom="le jeton repart sur la ligne de commande de l'agent",
        banc="banc_noeud.py",
        imite="le jeton d'un noeud redevient lisible par « ps » pour tout le "
              "monde sur la machine, ce qui annule le masquage de la saisie que "
              "le commentaire juste au-dessus reclame",
        rougit="le jeton ne passe jamais par la ligne de commande de l'agent",
        editions=[
            ("noeud.sh", brut('\nexec "$PY" "$AGENT"\nfi',
                              '\nexec "$PY" "$AGENT" --studio "$STUDIO"'
                              ' --jeton "$JETON"\nfi'))]),
    dict(
        nom="l'adresse d'Ollama n'est plus retenue dans les reglages",
        banc="banc_noeud.py",
        imite="une machine qui a bien un modele de langage cesse de le preter "
              "au studio des le SECOND lancement, celui ou l'on ne repasse plus "
              "--ollama",
        rougit="--ollama est retenu",
        editions=[
            ("noeud.sh", brut('if ollama:\n    c["ollama"] = ollama\n', ""))]),
    dict(
        nom="l'absence d'Ollama redevient un point bloquant",
        banc="banc_noeud.py",
        imite="une machine a carte sans Ollama ne peut plus s'enroler, alors "
              "que la ligne suivante dit « le studio le fera ailleurs » et que "
              "c'est le montage que le README recommande",
        rougit="une machine a carte SANS Ollama s'enrole quand meme",
        editions=[
            ("noeud.sh", brut('  remarque "aucun Ollama sur $OLLAMA_URL"',
                              '  souci "aucun Ollama sur $OLLAMA_URL"'))]),
    dict(
        nom="un ComfyUI introuvable redevient un point bloquant",
        banc="banc_noeud.py",
        imite="une machine dont le ComfyUI n'est pas encore installe, ou dont "
              "le COMFY_URL designe une autre machine, ne peut plus s'enroler — "
              "alors que l'agent attendrait qu'il reponde",
        rougit="un ComfyUI absent non plus : l'agent attendra qu'il reponde",
        editions=[
            ("noeud.sh", brut('    remarque "ComfyUI introuvable"',
                              '    souci "ComfyUI introuvable"'))]),
    dict(
        nom="les remarques sont recomptees avec les points bloquants",
        banc="banc_noeud.py",
        imite="les deux compteurs redeviennent un seul : n'importe quel "
              "avertissement consultatif interdit de nouveau la mise en "
              "service, et --verifier ne distingue plus ce qu'il faut regler de "
              "ce dont l'agent s'accommode",
        rougit="--verifier sort en 0 quand il ne reste que des remarques",
        editions=[
            ("noeud.sh", brut(
                'remarque() { jaune "$1"; REMARQUES=$((REMARQUES + 1)); }',
                'remarque() { jaune "$1"; ENNUIS=$((ENNUIS + 1)); }'))]),
    dict(
        nom="un studio injoignable devient une simple remarque",
        banc="banc_noeud.py",
        # LE SENS INVERSE DE LA PRECEDENTE, et il compte autant : un script qui
        # ne refuserait plus rien passerait tous les cas consultatifs sans rien
        # mesurer. Le partage doit tenir DES DEUX COTES.
        imite="l'adresse du studio fautive ou le pare-feu ferme ne sont plus "
              "signales que du coin de l'oeil, et la machine part en service "
              "vers un studio qu'elle n'atteint pas",
        rougit="il est compte comme un point a regler, jamais comme une remarque",
        editions=[
            ("noeud.sh", brut('  souci "studio injoignable sur $STUDIO"',
                              '  remarque "studio injoignable sur $STUDIO"'))]),
    dict(
        nom="maj_noeud.sh repasse le jeton sur la ligne de commande",
        banc="banc_noeud.py",
        imite="la mise a jour d'un parc contredit de nouveau la regle que "
              "noeud.sh ecrit en toutes lettres : l'argument de l'agent, lui, "
              "reste lisible dans « ps » tant que la machine sert",
        rougit="sans passer le jeton sur la ligne de commande, comme noeud.sh l'exige",
        editions=[
            ("maj_noeud.sh", brut('  exec "$PY" "$AGENT"\n',
                                  '  exec "$PY" "$AGENT" --studio "$STUDIO"'
                                  ' --jeton "$JETON"\n'))]),
    dict(
        nom="le lanceur Windows revient au seul chemin en dur",
        banc="banc_noeud.py",
        imite="« LANCER ComfyStudio.bat » sort de nouveau en 1 des que le "
              "ComfyUI portable n'est pas a cote, alors que l'installeur "
              "accepte huit emplacements et clone dans ../ComfyUI : suivre le "
              "README a la lettre sous Windows echoue",
        rougit="LANCER ComfyStudio.bat demande l'interpreteur a l'installeur",
        editions=[
            ("LANCER ComfyStudio.bat", brut(
                'for /f "delims=" %%p in (\'""%AMORCE%" installer.py'
                ' --python-du-studio"\') do set "PY=%%p"',
                "goto :sans_python"))]),
    dict(
        nom="STUDIO_PYTHON n'impose plus rien",
        banc="banc_noeud.py",
        imite="les lanceurs, qui SAVENT quel interpreteur ils emploient, ne "
              "peuvent plus le dire : l'installeur deduit a leur place, et un "
              "paquet pose dans le mauvais Python rend un « Successfully "
              "installed » suivi d'un ImportError au demarrage",
        rougit="STUDIO_PYTHON l'emporte",
        editions=[
            ("installation.py", brut(
                '    force = os.environ.get("STUDIO_PYTHON")\n    if force:',
                '    force = ""\n    if force:'))]),
    # LES DEUX SUIVANTES VISENT UN RELEVE DE TEXTE, ET C'EST ASSUME. Ailleurs
    # dans ce fichier une mutation qui ne change qu'un mot d'un fichier lu au
    # texte serait de la triche — elle prouverait que le banc sait lire, pas
    # qu'il garde quelque chose. Ici le releve EST la garde : cmd.exe n'existe
    # pas sur les runners, et la seule chose qu'on puisse tenir de maj_noeud.bat
    # sur une machine Linux, c'est ce qui y est ecrit. La mutation rejoue donc
    # exactement l'etat dans lequel le fichier a vecu jusqu'au 4 septembre 2026.
    dict(
        nom="le jeton repart sur la ligne de commande, cote Windows",
        banc="banc_noeud.py",
        imite="L'ETAT REEL DU DEPOT JUSQU'AU 4 SEPTEMBRE 2026 : maj_noeud.sh "
              "ecrivait le jeton dans agent_noeud.json, maj_noeud.bat le "
              "passait en clair a un processus qui tourne des semaines. "
              "« wmic process get commandline » suffit a le lire, sans droit "
              "particulier, et un jeton de noeud vaut droit de faire "
              "travailler la carte",
        rougit="maj_noeud.bat ne met pas le jeton sur la ligne de commande",
        editions=[
            ("maj_noeud.bat", brut(
                '"%PY%" agent_noeud.py',
                '"%PY%" agent_noeud.py --studio %STUDIO% --jeton %JETON%'))]),
    dict(
        nom="le jeton Windows passe par argv au lieu de l'environnement",
        banc="banc_noeud.py",
        imite="l'ecriture d'agent_noeud.json redevient un argv : le jeton est "
              "lisible le temps du python jetable, la ou un environnement "
              "n'appartient qu'a son proprietaire",
        rougit="il l'ecrit dans agent_noeud.json, en lisant le jeton dans "
               "l'environnement",
        editions=[
            ("maj_noeud.bat", brut("jeton=os.environ['JETON_A_ECRIRE']",
                                   "jeton=sys.argv[1]"))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_version.py — dix-neuf mutations, une par regle
# ──────────────────────────────────────────────────────────────────────
# « Le studio doit pouvoir dire ce qu'il est. » Il ne le disait nulle part, et
# .github/ISSUE_TEMPLATE demandait pourtant « Version du studio (commit, ou
# date) » — une question a laquelle DEUX chemins d'installation sur quatre ne
# pouvaient pas repondre.
#
# Le banc est ne avec la correction : pas de filet d'avant, donc pas de
# diagonale. Le sens inverse a ete pris par l'autre chemin — le banc NEUF sur
# le code d'AVANT — et il est ecrit dans docs/eprouver-les-bancs.md.
#
# Chaque mutation dit la PANNE et pas la manipulation, et la moitie d'entre
# elles imite la meme famille : ANNONCER QUELQUE CHOSE PLUTOT QUE DE DIRE
# « inconnue ». C'est la seule facon de se tromper qui soit pire que de se
# taire, parce que rien, dans une issue, ne dira que le chiffre est faux.
VERSION = [
    dict(
        nom="le studio n'a plus de mot pour son ignorance",
        banc="banc_version.py",
        imite="la banniere annonce « Version :  » suivi de rien, ce qui se lit "
              "comme une panne d'affichage et jamais comme une ignorance",
        rougit="le studio a de quoi dire ce qu'il est",
        editions=[("serveur.py", brut('VERSION_INCONNUE = "inconnue"',
                                      'VERSION_INCONNUE = ""'))]),
    dict(
        nom="une date du jour inventee a la place de « inconnue »",
        banc="banc_version.py",
        imite="le studio remplit le modele d'issue avec un nombre qui ne "
              "designe AUCUN code, et personne ne peut savoir qu'il est faux — "
              "exactement ce que « (commit, ou date) » obtenait deja",
        rougit="aucune source ne repond : le studio dit « inconnue »",
        editions=[("serveur.py", brut(
            '    return VERSION_INCONNUE, "aucune source"',
            '    return time.strftime("%Y-%m-%d"), "aucune source"'))]),
    dict(
        nom="l'ignorance rendue comme une chaine vide",
        banc="banc_version.py",
        imite="tout ce qui affiche l'identifiant affiche « » — et « la version "
              "est affichee » reste vrai, ce qui est l'assertion creuse que ce "
              "depot traque depuis le premier jour",
        rougit="et il ne rend JAMAIS une chaine vide",
        editions=[("serveur.py", brut(
            '    return VERSION_INCONNUE, "aucune source"',
            '    return "", "aucune source"'))]),
    dict(
        nom="un identifiant vide est accepte comme une valeur",
        banc="banc_version.py",
        imite="le cas REEL du conteneur construit sans --build-arg : le "
              "fichier grave ne porte qu'un retour a la ligne, et le studio "
              "l'annonce comme s'il savait",
        rougit="un identifiant vide est refuse, d'ou qu'il vienne",
        editions=[("serveur.py", brut(
            "    return 0 < len(valeur) <= VERSION_MAX",
            "    return len(valeur) <= VERSION_MAX"))]),
    dict(
        nom="plus aucune limite de longueur sur l'identifiant",
        banc="banc_version.py",
        imite="un fichier tombe par accident a la place du fichier grave "
              "devient la banniere, et se recopie dans une issue ou il ne "
              "designe rien",
        rougit="un identifiant demesure est refuse, et la limite tient",
        editions=[("serveur.py", brut(
            "    return 0 < len(valeur) <= VERSION_MAX",
            "    return 0 < len(valeur)"))]),
    dict(
        nom="le fichier grave par la construction n'est plus lu",
        banc="banc_version.py",
        imite="le conteneur et l'executable perdent leur SEULE source — ni "
              "l'un ni l'autre n'a de .git — et redisent « inconnue » pour "
              "toujours : les deux chemins que ce travail existe pour reparer",
        rougit="un identifiant grave normal repond, et se nomme",
        editions=[("serveur.py", brut(
            'SOURCES_VERSION = (("depot git", _version_du_depot),\n'
            '                   ("gravee a la construction", _version_gravee))',
            'SOURCES_VERSION = (("depot git", _version_du_depot),)'))]),
    dict(
        nom="git interroge meme quand le dossier n'est pas un clone",
        banc="banc_version.py",
        imite="GIT REMONTE LES DOSSIERS PARENTS : un studio pose dans un "
              "sous-dossier d'un AUTRE depot annonce le commit de cet autre "
              "depot, avec l'aplomb d'une valeur mesuree. Verifie le "
              "4 septembre 2026 depuis paquet/build, qui rend bd9fc88",
        rougit="git n'est pas interroge hors d'un clone",
        editions=[("serveur.py", brut(
            '    if not os.path.exists(os.path.join(racine, ".git")):\n'
            '        return ""\n',
            ""))]),
    dict(
        nom="git n'est plus dirige sur le dossier du code",
        banc="banc_version.py",
        imite="git resout depuis le REPERTOIRE COURANT, que le studio ne "
              "choisit pas : un service, ou un double-clic depuis "
              "l'explorateur, le posent sur C:\\Windows\\system32",
        rougit="dans un clone, git est interroge sur CE dossier",
        editions=[("serveur.py", brut(
            '["git", "-C", racine, "rev-parse", "--short", "HEAD"]',
            '["git", "rev-parse", "--short", "HEAD"]'))]),
    dict(
        nom="le fichier grave passe avant le depot",
        banc="banc_version.py",
        imite="un exe construit une fois, puis un « git pull » : le clone "
              "annonce l'identifiant de la vieille construction au lieu du "
              "sien, et il n'a aucune facon de se corriger",
        rougit="et le depot passe AVANT le fichier grave",
        editions=[("serveur.py", brut(
            'SOURCES_VERSION = (("depot git", _version_du_depot),\n'
            '                   ("gravee a la construction", _version_gravee))',
            'SOURCES_VERSION = (("gravee a la construction", _version_gravee),\n'
            '                   ("depot git", _version_du_depot))'))]),
    dict(
        nom="l'identifiant est recalcule a chaque appel",
        banc="banc_version.py",
        imite="un « git pull » pendant que le studio tourne lui fait annoncer "
              "un commit qu'il ne fait PAS tourner — et /api/admin/noeuds, "
              "interroge toutes les 5 s, lance un sous-processus git par "
              "battement pour une valeur qui ne peut pas bouger",
        rougit="l'identifiant annonce est fige pour la duree du processus",
        editions=[("serveur.py", brut(
            "    if not _VERSION_ANNONCEE:\n"
            "        _VERSION_ANNONCEE.extend(version_du_studio())\n"
            "    return _VERSION_ANNONCEE[0], _VERSION_ANNONCEE[1]",
            "    return version_du_studio()"))]),
    dict(
        nom="la banniere annonce l'identifiant sans sa source",
        banc="banc_version.py",
        imite="« bd9fc88 » seul ne dit pas si le studio l'a MESURE sur un "
              "depot ou recopie ce qu'on lui a grave : le premier se retrouve "
              "dans l'historique, le second depend de qui a construit",
        rougit="la banniere de demarrage annonce l'identifiant ET sa source",
        editions=[("serveur.py", brut(
            'print(f"  Version   : {_version}   ({_source_version})")',
            'print(f"  Version   : {_version}")'))]),
    dict(
        nom="/admin annonce une source ecrite en dur",
        banc="banc_version.py",
        imite="la console jure « depot git » a un conteneur qui n'a pas de "
              ".git : la source est justement ce qui devait dire si "
              "l'identifiant se retrouve quelque part",
        rougit="/api/admin/noeuds rend l'identifiant et sa source, calcules",
        editions=[("serveur.py", brut(
            '"version_source": version_annoncee()[1],',
            '"version_source": "depot git",'))]),
    dict(
        nom="la page lit une clef que le serveur ne rend pas",
        banc="banc_version.py",
        imite="le defaut que ce depot a paye trois fois : les deux cotes sont "
              "verts, la clef ne se rejoint pas, et /admin affiche « version "
              "bd9fc88 (undefined) »",
        rougit="la page /admin lit ces memes clefs, et a ou les poser",
        editions=[("web/admin.html", brut("d.version_source || ",
                                          "d.source_version || "))]),
    dict(
        nom="la page pose la valeur sans repli",
        banc="banc_version.py",
        imite="un studio plus ancien ne rend pas ces clefs : la page ecrit "
              "« version undefined (undefined) », ce qui se lit comme une "
              "panne de la page et non comme une ignorance du studio",
        rougit="et elle ne pose jamais un identifiant vide",
        editions=[("web/admin.html", brut(
            '`version ${d.version || "inconnue"} (${d.version_source || "source inconnue"})`',
            '`version ${d.version} (${d.version_source})`'))]),
    dict(
        nom="le conteneur ne grave plus rien",
        banc="banc_version.py",
        imite="l'image n'a aucun moyen de savoir ce qu'elle est — .git est "
              "dans .dockerignore — et le studio en conteneur redit "
              "« inconnue » a chaque demarrage, sans que la construction ait "
              "eu la moindre chance de le lui dire",
        rougit="le conteneur grave l'identifiant dans le fichier que le studio lit",
        editions=[("Dockerfile", brut(
            'RUN printf \'%s\\n\' "$VERSION" > /app/version.txt\n', ""))]),
    dict(
        nom="l'executable n'embarque plus l'identifiant grave",
        banc="banc_version.py",
        imite="la spec le calcule et l'ecrit, mais ne le met pas dans le "
              "paquet : le fichier reste dans build/ sur la machine qui a "
              "construit, et l'exe distribue dit « inconnue »",
        rougit="et l'executable embarque le meme, calcule a la construction",
        editions=[("paquet/comfystudio.spec",
                   brut('DONNEES.append((VERSION_GRAVEE, "."))\n', ""))]),
    dict(
        nom="la construction Windows ne dit plus ce qu'elle a grave",
        banc="banc_version.py",
        imite="celui qui construit l'exe ne sait pas ce qu'il distribue, et "
              "n'a aucune facon de s'apercevoir que git manquait sur sa "
              "machine et que l'exe dira « inconnue »",
        rougit="et la construction Windows dit ce qu'elle a grave",
        editions=[("paquet/construire_windows.bat", brut(
            "echo Version gravee : %VERSION%   "
            "(ligne \u00ab Version \u00bb de la banniere, et /admin)\n", ""))]),
    dict(
        nom="le modele d'issue redemande une valeur introuvable",
        banc="banc_version.py",
        imite="le point de depart, remis en place : « (commit, ou date) » est "
              "impossible a remplir pour qui a installe par executable ou par "
              "conteneur, c'est-a-dire deux chemins sur quatre",
        rougit="le modele d'issue ne demande plus une valeur introuvable",
        editions=[(".github/ISSUE_TEMPLATE/bogue.md",
                   brut("- **Version du studio** :",
                        "- **Version du studio** (commit, ou date) :"))]),
    dict(
        nom="le modele d'issue ne dit plus ou lire la valeur",
        banc="banc_version.py",
        imite="le studio SAIT sa version et l'affiche a deux endroits, et "
              "celui qui ouvre l'issue ne sait toujours pas ou regarder : "
              "l'identifiant existe, la question reste sans reponse",
        rougit="et il dit ou la lire, pour les quatre installations",
        editions=[(".github/ISSUE_TEMPLATE/bogue.md", brut(
            "       - en haut de <http://127.0.0.1:8199/admin>, "
            "\u00e0 c\u00f4t\u00e9 du titre.\n", ""))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_boucle.py — soixante-huit mutations, les six fonctions qui DECIDENT
# ──────────────────────────────────────────────────────────────────────
# banc_agent.py a ferme le trou du fichier agent_noeud.py, et son en-tete a
# nomme ce qu'il laissait dehors : « boucle(), qui ne rend jamais la main […]
# insister(), servir_le_langage(), trouver_ollama() et main() » — plus
# modeles_comfy(). Six fonctions, et ce sont celles qui decident : boucle()
# prend le travail, declare la machine occupee, livre les fichiers et choisit
# l'instant ou l'agent se remplace ; insister() est tout ce qui separe un rendu
# de trois minutes DEJA FAIT d'un « echec » affiche a l'utilisateur ; main() est
# la porte de l'enrolement.
#
# LE SENS INVERSE, ET IL A FALLU REPARER LE BANC POUR L'OBTENIR. Ces gardes
# sont toutes plus vieilles que banc_boucle.py : il n'y a pas de filet d'avant
# a rejouer, donc c'est le second chemin — le banc NEUF sur l'agent d'AVANT.
# Au premier essai, le banc MOURAIT sur cinq des six commits repris, en
# « AttributeError: module 'agent_noeud' has no attribute 'PREMIERE_ANNONCE' » :
# un banc qui meurt sur le code d'avant ne mesure pas le sens inverse, et
# banc_mutations aurait rendu « le banc s'est casse au lieu de rougir ». Chaque
# nom y est desormais lu par un accesseur tolerant et chaque absence pose un
# CAS NOMME — le meme tour que le « try » de banc_page.py sur
# web/demarrage.html. Releve le 4 septembre 2026, agent repris a neuf commits
# depuis le premier du depot :
#
#     811677b   115 lignes rouges, dont 54 que ces mutations nomment
#     b717f11^  111 lignes rouges, dont 53
#     ea06397^   95 lignes rouges, dont 45
#     aeee626^   83 lignes rouges, dont 36
#     f9b3051^   46 lignes rouges, dont 22
#     adca444^    8 lignes rouges, dont  5 — et le banc rend 130/8, il
#                 DISTINGUE les deux depots au lieu de mourir sur l'un
#
# CINQUANTE-SIX des soixante-huit lignes nommees rougissent ainsi sur au
# moins un agent d'avant. Les douze autres gardent des regles aussi vieilles
# que le depot — le refus d'un studio sans adresse, les dossiers de
# l'inventaire, le menage sans dossier de sorties : pour celles-la, la
# mutation EST la correction defaite, et « banc_boucle.py est vert sur le depot
# sain » en tete de ce fichier tient l'autre moitie.
#
# L'ISOLEMENT a ete releve mutation par mutation le 4 septembre 2026 :
# QUARANTE-CINQ des soixante-huit rougissent leur ligne et elle SEULE. Les
# vingt-trois autres en entrainent une a huit de plus, et c'est la meme
# distinction qu'a la liberation de la VRAM : couper un TRANSPORT fait tomber
# tout ce qui en depend, couper une GARDE ne fait tomber qu'elle. Les trois
# plus larges le montrent — « le delai de livraison est nul » (+8) coupe la
# reprise entiere d'insister(), « l'agent decharge la carte a chaque
# battement » (+7) coupe la LECTURE de la consigne, « un refus franc est repete
# pendant dix minutes » (+4) tient les cinq statuts du meme « if ».
#
# TROIS DE CES MUTATIONS ONT TROUVE UN TROU DANS LE BANC, et c'est pour cela
# qu'elles existent : « la boucle reclame du travail sans carte » et « ... a un
# studio qui l'a refusee » etaient VERTES — le faux reseau retirait de sa trace
# la demande qui l'arrete, si bien que « aucun travail reclame » restait vrai
# d'une boucle qui en reclamait un ; et « un fichier illisible interrompt le
# depot des suivants » l'etait aussi, parce que le fichier illisible etait
# ECRIT EN SECOND et que le break n'avait plus rien a couper. Le motif de
# « priorite, », trois fois, dans le banc qui vient le fermer.
# ══════════════════════════════════════════════════════════════════════
#  banc_console.py — les boutons de /admin, dix mutations
# ══════════════════════════════════════════════════════════════════════
# CE QU'ELLES GARDENT : sept routes que le releve du 5 septembre 2026 a
# trouvees muettes — vingt-deux sur soixante-quatre n'etaient nommees par aucun
# banc. Celles-ci AGISSENT sur le parc : elles mettent une carte au repos,
# ferment un jeton, retirent une machine, tuent un moteur.
#
# LA PAUSE EST LE CAS D'ECOLE. Son EFFET etait mesure depuis longtemps —
# banc_attente.py la nomme quarante-cinq fois — mais a partir d'un registre ou
# l'on avait pose « pause » a la main. Le GESTE, lui, n'etait mesure par
# personne : ni l'ecriture sur le disque, ni le reveil de ce qui attendait.
CONSOLE = [
    dict(
        nom="la pause n'est plus ecrite sur le disque",
        banc="banc_console.py",
        imite="la pause ne survit pas au redemarrage du studio. Elle tient tant "
              "que le processus vit, ce qui la rend PIRE qu'absente : celui qui "
              "l'a posee croit sa carte a lui, et le premier studio relance la "
              "redistribue pendant qu'il joue",
        rougit="elle est ECRITE dans _noeuds.json",
        editions=[
            ("serveur.py", brut(
                '    if d.get("pause"):\n'
                '        x["pause"] = time.time()\n'
                '    else:\n'
                '        x.pop("pause", None)\n'
                "    sauver_registre()\n",
                '    if d.get("pause"):\n'
                '        x["pause"] = time.time()\n'
                '    else:\n'
                '        x.pop("pause", None)\n')),
        ]),
    dict(
        nom="sortir de pause ne reveille plus ce qui attendait",
        banc="banc_console.py",
        imite="la machine est rendue au travail et la demande qui l'attendait "
              "reste armee : elle repartira au battement suivant du veilleur, "
              "trente secondes plus tard. L'administrateur voit son clic ne "
              "rien faire, et clique une seconde fois",
        rougit="sortir une machine de pause relance ce qui l'attendait",
        editions=[
            ("serveur.py", brut(
                "    reveillees = (0 if x.get(\"pause\")\n"
                "                  else await reveiller_armees(x[\"id\"], plancher=False))",
                "    reveillees = 0")),
        ]),
    dict(
        nom="le plancher de quinze secondes revient sur le clic",
        banc="banc_console.py",
        imite="LE DEFAUT EXACT QUE « plancher=False » REPARE : une demande armee "
              "depuis moins de quinze secondes est ecartee, la reponse annonce "
              "« 0 relancee » alors qu'elle repart au battement suivant. Le "
              "clic est deliberatif, pas un va-et-vient de machine",
        rougit="sans le plancher de quinze secondes",
        editions=[
            ("serveur.py", brut(
                'else await reveiller_armees(x["id"], plancher=False))',
                'else await reveiller_armees(x["id"]))')),
        ]),
    dict(
        nom="une pause devient un retrait",
        banc="banc_console.py",
        imite="mettre en pause efface l'etat de la machine. Elle disparait de "
              "la console au lieu d'y rester grisee, son inventaire est perdu, "
              "et il faut attendre qu'elle se reannonce pour la revoir — alors "
              "qu'une pause promet exactement le contraire",
        rougit="une pause n'est pas un retrait",
        editions=[
            ("serveur.py", brut(
                '    if d.get("pause"):\n        x["pause"] = time.time()\n',
                '    if d.get("pause"):\n        x["pause"] = time.time()\n'
                '        ETAT_NOEUDS.pop(req.match_info["ident"], None)\n')),
        ]),
    dict(
        nom="le jeton regenere ne ferme pas l'ancien",
        banc="banc_console.py",
        imite="LE PIRE DES DEUX ECHECS POSSIBLES. Le bouton rend un jeton neuf "
              "et l'ancien continue d'ouvrir : celui qui vient de regenerer "
              "parce que son jeton a fuite croit avoir ferme la porte, et ne "
              "cherchera plus. Un refus franc l'aurait au moins averti",
        rougit="ET L'ANCIEN NE VAUT PLUS RIEN",
        editions=[
            ("serveur.py", brut(
                '    jeton = secrets.token_urlsafe(24)\n'
                '    REGISTRE[ident]["jeton"] = jeton\n',
                "    jeton = secrets.token_urlsafe(24)\n")),
        ]),
    dict(
        nom="le jeton regenere n'est pas ecrit sur le disque",
        banc="banc_console.py",
        imite="l'ancien jeton revient au redemarrage du studio, et la machine "
              "dont on venait de fermer l'acces le rouvre toute seule. Le "
              "danger est le meme que ci-dessus, avec un delai",
        rougit="le neuf est ecrit sur le disque",
        editions=[
            ("serveur.py", brut(
                '    REGISTRE[ident]["jeton"] = jeton\n'
                "    sauver_registre()\n"
                "    ETAT_NOEUDS.pop(ident, None)\n"
                '    return web.json_response({"id": ident, "jeton": jeton})',
                '    REGISTRE[ident]["jeton"] = jeton\n'
                "    ETAT_NOEUDS.pop(ident, None)\n"
                '    return web.json_response({"id": ident, "jeton": jeton})')),
        ]),
    dict(
        nom="retirer une machine en laisse une trace",
        banc="banc_console.py",
        imite="une machine fantome : elle ne s'annonce plus, elle n'est plus "
              "dans le registre, et le studio compte encore ses travaux. C'est "
              "le genre de reste qui ne se voit qu'a la panne suivante",
        rougit="elle disparait des QUATRE tables",
        editions=[
            ("serveur.py", brut(
                "    ETAT_NOEUDS.pop(ident, None)\n"
                "    MODELES_NOEUD.pop(ident, None)\n"
                "    TRAVAUX.pop(ident, None)\n",
                "    ETAT_NOEUDS.pop(ident, None)\n"
                "    MODELES_NOEUD.pop(ident, None)\n")),
        ]),
    dict(
        nom="l'arret de ComfyUI ne regarde plus ce qui attend",
        banc="banc_console.py",
        imite="EN_VOL se vide entre deux taches. Ne tester que lui laisse "
              "passer l'arret dans cet intervalle : le moteur est tue pendant "
              "qu'une file entiere l'attend, et toutes les demandes echouent "
              "en cascade sans que personne n'ait rien demande de tel",
        rougit="l'arret est REFUSE tant qu'une demande ATTEND",
        editions=[
            ("serveur.py", brut("    if EN_VOL or ATTENTE:\n",
                                "    if EN_VOL:\n")),
        ]),
    dict(
        nom="l'arret ne tue plus l'arbre de processus, sous Windows",
        banc="banc_console.py",
        imite="« taskkill /PID <pid> /F » sans « /T » laisse les enfants du "
              "moteur en vie. Un exe onefile en a un, et c'est LUI qui tient le "
              "port : l'arret rend 200, le port reste pris, et la relance "
              "echoue sur une adresse deja utilisee",
        rougit="sur « nt », l'arret est exactement",
        editions=[
            ("serveur.py", brut(
                '            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],',
                '            subprocess.run(["taskkill", "/PID", str(pid), "/F"],')),
        ]),
    dict(
        nom="l'arret sous Unix vise le mauvais numero",
        banc="banc_console.py",
        imite="os.kill recoit autre chose que le pid du PORT : le moteur "
              "survit, et le studio a peut-etre tue quelqu'un d'autre",
        rougit="sur « posix », l'arret est exactement",
        editions=[
            ("serveur.py", brut("            os.kill(pid, 15)",
                                "            os.kill(1, 15)")),
        ]),
    dict(
        nom="le pilotage de ComfyUI s'ouvre au reseau",
        banc="banc_console.py",
        imite="n'importe qui sur le reseau local peut tuer et relancer le "
              "moteur du studio. Le pilotage lance un processus sur la machine "
              "hote : il n'a rien a faire au bout d'un cable",
        rougit="un appel venu d'une AUTRE machine est refuse",
        editions=[
            ("serveur.py", brut(
                "    if not local(req):\n"
                '        return web.json_response({"erreur": "pilotage reserve a la machine hote"}, status=403)\n'
                "    if await comfy_repond():",
                "    if await comfy_repond():")),
        ]),
    dict(
        nom="le pilotage perd la garde de l'origine",
        banc="banc_console.py",
        imite="local() ne suffit pas, et c'est tout l'objet de la seconde "
              "garde : un formulaire poste depuis un site piege part du "
              "navigateur de l'utilisateur, donc de 127.0.0.1. Sans "
              "origine_sure(), une page ouverte dans un autre onglet lance le "
              "moteur",
        rougit="un clic sur un site tiers l'est aussi",
        editions=[
            ("serveur.py", brut(
                "async def api_comfy_demarrer(req):\n"
                "    if not origine_sure(req):\n"
                '        return web.json_response({"erreur": "origine refusee"}, status=403)\n',
                "async def api_comfy_demarrer(req):\n")),
        ]),
]


BOUCLE_AGENT = [
    # ── LES DEUX DEFAUTS TROUVES EN COUVRANT, ET CORRIGES LE MEME JOUR ──
    # Ils vivaient tous les deux dans l'ecart entre une docstring et son code.
    # Ce n'est pas un hasard : une promesse ecrite au-dessus d'une condition est
    # ce qu'on relit, et la condition est ce qui s'execute.
    dict(
        nom="insister() reprend tout ce qui n'est ni 200 ni 4xx",
        banc="banc_boucle.py",
        imite="L'ETAT REEL DU DEPOT JUSQU'AU 4 SEPTEMBRE 2026, pendant que la "
              "docstring promettait « on ne recommence que sur un studio MUET "
              "ou en panne ». Un 204 — « recu, rien a dire », que le studio "
              "sert deja sur /api/noeud/question — repart VINGT-QUATRE fois "
              "sur dix minutes, puis le travail est declare perdu, en "
              "annoncant « studio muet (204) » d'une reponse qui disait oui",
        rougit="un 204 — « recu, rien a dire » — est une reponse",
        editions=[
            ("agent_noeud.py", brut(
                "        if st and not 500 <= st < 600:",
                "        if st == 200 or 400 <= st < 500:")),
        ]),
    dict(
        nom="trouver_ollama() se contente d'un Ollama joignable",
        banc="banc_boucle.py",
        imite="etat_ollama() rend {\"ok\": False, \"modeles\": []} pour un "
              "Ollama installe et VIDE : un dictionnaire non vide, donc vrai, "
              "et la recherche s'arrete dessus. En conteneur, OLLAMA_URL "
              "pointe souvent sur un Ollama qu'on vient d'installer et ou l'on "
              "n'a rien tire ; host.docker.internal, ou vivent les modeles de "
              "l'hote, n'est alors JAMAIS essaye, et la machine s'annonce avec "
              "« 0 modele(s) » sans que rien ne dise pourquoi",
        rougit="un Ollama joignable mais VIDE ne masque plus le voisin",
        editions=[
            ("agent_noeud.py", brut(
                '        if adresse and (etat_ollama(adresse.rstrip("/")) or {}).get("ok"):',
                '        if adresse and etat_ollama(adresse.rstrip("/")):')),
        ]),
    dict(
        nom='la boucle reclame du travail sans attendre le premier battement',
        banc="banc_boucle.py",
        imite="la machine prend un rendu avant de savoir si sa carte repond "
              "et si le studio l'accepte. Au demarrage d'un parc, chaque "
              "agent prend un travail qu'il ne peut pas faire et le rend en "
              "erreur",
        rougit="la boucle attend le premier battement AVANT de reclamer le "
               "moindre travail",
        editions=[
            ("agent_noeud.py", brut(
                '    PREMIERE_ANNONCE.wait(60)' + chr(10),
                '')),
        ]),
    dict(
        nom="le fil des questions n'est plus daemon",
        banc="banc_boucle.py",
        imite="ctrl+C rend la main a la boucle, et le processus attend un fil "
              "qui ne finit jamais. L'utilisateur tue la machine au lieu de "
              "l'arreter, et un rendu en cours part avec",
        rougit="et tous en daemon — sinon l'agent ne s'arreterait jamais",
        editions=[
            ("agent_noeud.py", brut(
                '        threading.Thread(target=servir_le_langage, args=(studio, jeton, ollama),' + chr(10)
                + '                         daemon=True).start()',
                '        threading.Thread(target=servir_le_langage, args=(studio, jeton, ollama),' + chr(10)
                + '                         daemon=False).start()')),
        ]),
    dict(
        nom="le fil d'annonce ne sait plus qu'il y a un Ollama ici",
        banc="banc_boucle.py",
        imite="la machine s'annonce sans son modele de langage. Le studio ne "
              "sait pas qu'elle peut servir de repli, et repond « aucun "
              "modele de langage » le jour ou le sien tombe — alors qu'une "
              "machine du parc en porte un",
        rougit="chaque fil recoit ce qu'il lui faut, et rien de plus",
        editions=[
            ("agent_noeud.py", brut(
                '    threading.Thread(target=battre_annonce, args=(studio, jeton, comfy, ollama),',
                '    threading.Thread(target=battre_annonce, args=(studio, jeton, comfy, ""),')),
        ]),
    dict(
        nom='le fil des questions part meme sans Ollama',
        banc="banc_boucle.py",
        imite="une machine sans modele de langage interroge quand meme le "
              "studio toutes les trois secondes pour des questions qu'elle ne "
              "saurait pas traiter — et si une lui est confiee, elle repond « "
              "ollama a repondu 0 » au lieu de laisser une autre la prendre",
        rougit="sans modele de langage local, le fil des questions ne part "
               "pas",
        editions=[
            ("agent_noeud.py", brut(
                '    if ollama:' + chr(10)
                + '        threading.Thread(target=servir_le_langage,',
                '    if True:' + chr(10)
                + '        threading.Thread(target=servir_le_langage,')),
        ]),
    dict(
        nom='la boucle reclame du travail sans carte',
        banc="banc_boucle.py",
        imite="une machine dont ComfyUI est arrete prend le rendu et le rate. "
              "Il aurait pu partir sur l'autre carte du parc ; l'utilisateur "
              "lit un echec la ou il aurait eu son image",
        rougit="une machine dont ComfyUI ne repond pas ne reclame aucun "
               "travail",
        editions=[
            ("agent_noeud.py", brut(
                '            if DEPUIS_L_ANNONCE["comfy"] is None or not DEPUIS_L_ANNONCE["studio"]:',
                '            if not DEPUIS_L_ANNONCE["studio"]:')),
        ]),
    dict(
        nom="la boucle reclame du travail a un studio qui l'a refusee",
        banc="banc_boucle.py",
        imite="jeton revoque, studio en panne : l'agent va quand meme "
              "reclamer du travail toutes les trois secondes au lieu de "
              "vingt. Une machine ecartee de l'administration continue de "
              "frapper a la porte mille fois par heure",
        rougit="un studio qui n'a pas repondu 200 au dernier battement non "
               "plus",
        editions=[
            ("agent_noeud.py", brut(
                '            if DEPUIS_L_ANNONCE["comfy"] is None or not DEPUIS_L_ANNONCE["studio"]:',
                '            if DEPUIS_L_ANNONCE["comfy"] is None:')),
        ]),
    dict(
        nom="la machine ne se declare occupee qu'apres le depot des entrees",
        banc="banc_boucle.py",
        imite="le fil d'annonce recopie EN_COURS_ICI a chaque battement. Pose "
              "trop tard, la machine s'annonce LIBRE pendant tout le depot "
              "des entrees — jusqu'a deux minutes pour une image lourde — et "
              "un studio qui redemarre dans cette fenetre relance une demande "
              "que cette carte va rendre : deux fois le meme travail",
        rougit="le travail est annonce EN COURS avant meme le depot des "
               "entrees",
        editions=[
            ("agent_noeud.py", brut(
                '            tid = travail["tid"]' + chr(10)
                + '            EN_COURS_ICI[:] = [tid]' + chr(10)
                + '            print(f"  travail {tid[:8]} recu", flush=True)' + chr(10)
                + '            erreur = deposer_entrees(comfy, travail.get("entrees"),' + chr(10)
                + '                                     travail["graphe"])',
                '            tid = travail["tid"]' + chr(10)
                + '            print(f"  travail {tid[:8]} recu", flush=True)' + chr(10)
                + '            erreur = deposer_entrees(comfy, travail.get("entrees"),' + chr(10)
                + '                                     travail["graphe"])' + chr(10)
                + '            EN_COURS_ICI[:] = [tid]')),
        ]),
    dict(
        nom="le nom du fichier n'est plus encode dans l'adresse du depot",
        banc="banc_boucle.py",
        imite="un « & » dans un nom de sortie coupe le parametre en deux : le "
              "studio enregistre un fichier qui n'a plus le nom que ComfyUI "
              "lui a donne, et le graphe qui le rappelle ne le retrouve pas. "
              "Une espace passe encore, une esperluette non",
        rougit="le tid et le NOM ENCODE voyagent dans l'adresse du depot",
        editions=[
            ("agent_noeud.py", brut(
                '                q = urllib.parse.urlencode({"tid": tid, "nom": f["filename"]})',
                '                q = f"tid={tid}&nom={f[\'filename\']}"')),
        ]),
    dict(
        nom="le registre note un depot qui n'est pas arrive",
        banc="banc_boucle.py",
        imite="le registre est la seule garantie qu'on n'effacera pas le "
              "travail personnel du proprietaire de la machine : on ne "
              "supprime que ce qui y figure. Y noter un envoi refuse fait "
              "effacer, vingt-quatre heures plus tard, un fichier que le "
              "studio n'a jamais recu — il n'existe alors nulle part",
        rougit="et rien n'entre au registre : on n'effacera pas ici ce qui "
               "n'est pas la-bas",
        editions=[
            ("agent_noeud.py", brut(
                '                st = insister(f"{studio}/api/noeud/fichier?{q}", jeton,' + chr(10)
                + '                              brut=octets, secondes=600)' + chr(10)
                + '                if st == 200:',
                '                st = insister(f"{studio}/api/noeud/fichier?{q}", jeton,' + chr(10)
                + '                              brut=octets, secondes=600)' + chr(10)
                + '                noter_depot(sorties, f, time.time())' + chr(10)
                + '                if st == 200:')),
        ]),
    dict(
        nom='un fichier illisible interrompt le depot des suivants',
        banc="banc_boucle.py",
        imite="une video rend dix images et la troisieme a ete effacee a la "
              "main : les sept dernieres ne partent jamais. L'utilisateur "
              "recoit deux images sur dix pour un rendu qui a bel et bien "
              "abouti, et rien ne dit que les autres existent encore ici",
        rougit="un fichier illisible sur le disque n'emporte pas les SUIVANTS",
        editions=[
            ("agent_noeud.py", brut(
                '                    erreur = erreur or f"fichier illisible : {f[\'filename\']}"' + chr(10)
                + '                    continue',
                '                    erreur = erreur or f"fichier illisible : {f[\'filename\']}"' + chr(10)
                + '                    break')),
        ]),
    dict(
        nom='la derniere erreur ecrase la premiere',
        banc="banc_boucle.py",
        imite="la cause est remplacee par sa consequence. Un disque plein "
              "donne d'abord « fichier illisible », puis dix « envoi refuse » "
              ": c'est le premier qui dit ou regarder, et c'est celui qu'on "
              "perd",
        rougit="deux echecs de suite : c'est le PREMIER qui remonte, pas le "
               "dernier",
        editions=[
            ("agent_noeud.py", brut(
                '                    erreur = erreur or f"fichier illisible : {f[\'filename\']}"',
                '                    erreur = f"fichier illisible : {f[\'filename\']}"')),
        ]),
    dict(
        nom="une entree refusee n'empeche plus le rendu",
        banc="banc_boucle.py",
        imite="ComfyUI n'a pas recu l'image de depart, et le graphe pointe "
              "sur un nom qu'il n'a pas retenu. La carte calcule quand meme, "
              "trois minutes, pour une erreur au dernier noeud — ou pire, "
              "pour une image sans rapport avec la demande",
        rougit="une entree qui n'a pas pu etre deposee n'envoie RIEN a la "
               "carte",
        editions=[
            ("agent_noeud.py", brut(
                '            if erreur:' + chr(10)
                + '                fichiers, secondes = [], 0' + chr(10)
                + '            else:',
                '            if False:' + chr(10)
                + '                fichiers, secondes = [], 0' + chr(10)
                + '            else:')),
        ]),
    dict(
        nom='une annulation est imputee a la machine comme une panne',
        banc="banc_boucle.py",
        imite="le studio compte les pannes par machine et ecarte celles qui "
              "en accumulent. Une salle ou l'on annule beaucoup viderait son "
              "parc d'elle-meme, pour des incidents qui ne sont pas les siens",
        rougit="un travail annule est rendu « annule », sans erreur a imputer "
               "a la machine",
        editions=[
            ("agent_noeud.py", brut(
                '                        {"tid": tid, "etat": "annule", "erreur": None,',
                '                        {"tid": tid, "etat": "erreur", "erreur": ANNULE,')),
        ]),
    dict(
        nom='la machine reste occupee apres une annulation',
        banc="banc_boucle.py",
        imite="EN_COURS_ICI garde un tid mort. La machine s'annonce occupee "
              "pour toujours, le repartiteur ne lui envoie plus rien, et la "
              "carte reste inutilisee jusqu'au redemarrage de l'agent",
        rougit="la machine se libere et fait remesurer sa carte, comme apres "
               "un rendu",
        editions=[
            ("agent_noeud.py", brut(
                '                print(f"  travail {tid[:8]} annule par le studio apres "' + chr(10)
                + '                      f"{secondes:.0f} s", flush=True)' + chr(10)
                + '                EN_COURS_ICI.clear()',
                '                print(f"  travail {tid[:8]} annule par le studio apres "' + chr(10)
                + '                      f"{secondes:.0f} s", flush=True)')),
        ]),
    dict(
        nom="la carte n'est pas remesuree apres un rendu",
        banc="banc_boucle.py",
        imite="le travail suivant est reclame sur un etat vieux de dix a "
              "trente secondes. Un ComfyUI mort en fin de rendu — l'OOM sur "
              "le dernier noeud, le cas classique — fait prendre PUIS rater "
              "le travail suivant, au lieu de le laisser partir sur l'autre "
              "carte",
        rougit="la carte est remesuree tout de suite, pas au prochain cache",
        editions=[
            ("agent_noeud.py", brut(
                '            print(f"  travail {tid[:8]} {\'echoue\' if erreur else \'rendu\'} "' + chr(10)
                + '                  f"en {secondes:.0f} s — {len(deposes)} fichier(s)", flush=True)' + chr(10)
                + '            EN_COURS_ICI.clear()' + chr(10)
                + '            # La carte est rendue : que le fil la remesure tout de' + chr(10)
                + '            # suite, pour que le travail suivant ne soit pas reclame' + chr(10)
                + '            # sur un etat vieux de trente secondes.' + chr(10)
                + '            DEPUIS_L_ANNONCE["remesurer"] = True',
                '            print(f"  travail {tid[:8]} {\'echoue\' if erreur else \'rendu\'} "' + chr(10)
                + '                  f"en {secondes:.0f} s — {len(deposes)} fichier(s)", flush=True)' + chr(10)
                + '            EN_COURS_ICI.clear()')),
        ]),
    dict(
        nom='un incident laisse la machine declaree occupee',
        banc="banc_boucle.py",
        imite="c'est la panne la plus silencieuse de l'agent : la carte est "
              "libre, la machine s'annonce en train de calculer, et le studio "
              "attend un resultat qui ne viendra jamais. Elle sort du "
              "repartiteur sans qu'une seule ligne le dise",
        rougit="et la liste des travaux est VIDEE",
        editions=[
            ("agent_noeud.py", brut(
                '            EN_COURS_ICI.clear()' + chr(10)
                + '            # La carte est rendue : que le fil la remesure tout de' + chr(10)
                + '            # suite, pour que le travail suivant ne soit pas reclame' + chr(10)
                + '            # sur un etat vieux de trente secondes.' + chr(10)
                + '            DEPUIS_L_ANNONCE["remesurer"] = True' + chr(10)
                + '            print(f"  incident : {type(e).__name__} {str(e)[:160]}", flush=True)',
                '            # La carte est rendue : que le fil la remesure tout de' + chr(10)
                + '            # suite, pour que le travail suivant ne soit pas reclame' + chr(10)
                + '            # sur un etat vieux de trente secondes.' + chr(10)
                + '            DEPUIS_L_ANNONCE["remesurer"] = True' + chr(10)
                + '            print(f"  incident : {type(e).__name__} {str(e)[:160]}", flush=True)')),
        ]),
    dict(
        nom='ctrl+C est avale comme un incident ordinaire',
        banc="banc_boucle.py",
        imite="l'agent ne s'arrete plus. Chaque ctrl+C est note « incident », "
              "l'agent dort vingt secondes et repart — il faut le tuer. Sur "
              "une machine de travail qu'on eteint le soir, c'est un rendu "
              "perdu a chaque fois",
        rougit="ctrl+C n'est PAS avale par le filet a incidents",
        editions=[
            ("agent_noeud.py", brut(
                '        except KeyboardInterrupt:' + chr(10)
                + '            raise',
                '        except KeyboardInterrupt:' + chr(10)
                + '            time.sleep(PAUSE_LONGUE)')),
        ]),
    dict(
        nom='le menage repasse a chaque tour de boucle',
        banc="banc_boucle.py",
        imite="le registre des sorties est relu et reecrit toutes les trois "
              "secondes, avec ses cinq mille entrees. Sur un disque lent, la "
              "boucle passe son temps a faire le menage au lieu de reclamer "
              "du travail",
        rougit="le menage passe entre deux travaux, au plus une fois par dix "
               "minutes",
        editions=[
            ("agent_noeud.py", brut(
                '            if sorties and maintenant - dernier_menage > PURGE_TOUS_LES:',
                '            if sorties:')),
        ]),
    dict(
        nom='le menage passe sans dossier de sorties',
        banc="banc_boucle.py",
        imite="l'agent efface sur une machine dont on ne lui a JAMAIS donne "
              "le dossier de sorties. Le registre s'y lit a cote du fichier "
              "de l'agent, et les chemins qu'il porte viennent d'ailleurs : "
              "c'est le seul garde-fou entre l'agent et le disque de "
              "quelqu'un d'autre",
        rougit="sans dossier de sorties, RIEN n'est efface sur la machine de "
               "l'utilisateur",
        editions=[
            ("agent_noeud.py", brut(
                '            if sorties and maintenant - dernier_menage > PURGE_TOUS_LES:',
                '            if maintenant - dernier_menage > PURGE_TOUS_LES:')),
        ]),
    dict(
        nom='la mise a jour est tentee a chaque tour de boucle',
        banc="banc_boucle.py",
        imite="le defaut exact que le compteur de battements a corrige : "
              "l'empreinte est relue toutes les trois secondes, et un studio "
              "qui sert un agent que l'on refuse — empreinte epinglee, "
              "telechargement tronque — noie la console sous deux lignes "
              "toutes les trois secondes",
        rougit="la mise a jour n'est tentee qu'UNE FOIS PAR BATTEMENT, pas a "
               "chaque tour",
        editions=[
            ("agent_noeud.py", brut(
                '            if maj_auto and battement != dernier_battement:',
                '            if maj_auto:')),
        ]),
    dict(
        nom='--sans-maj-auto est ignore par la boucle',
        banc="banc_boucle.py",
        imite="la machine se remplace toute seule alors qu'on le lui a "
              "explicitement interdit. C'est le drapeau que l'on pose sur une "
              "machine de production dont on veut figer la version — et un "
              "os.execv non voulu coupe le rendu en cours",
        rougit="--sans-maj-auto : la machine ne se remplace jamais toute "
               "seule",
        editions=[
            ("agent_noeud.py", brut(
                '            if maj_auto and battement != dernier_battement:',
                '            if battement != dernier_battement:')),
        ]),
    dict(
        nom='la mise a jour est tentee APRES avoir pris un travail',
        banc="banc_boucle.py",
        imite="se_mettre_a_jour_seul() finit par un os.execv, qui remplace le "
              "processus d'un bloc, sans deroulement ni fils survivants. Tire "
              "un travail deja pris, il emporte l'image avec le processus : "
              "l'utilisateur attend un rendu que plus personne ne fera, et le "
              "studio attend un resultat qui ne viendra pas",
        rougit="et jamais pendant un travail : aucun rendu en cours, rien "
               "encore reclame",
        editions=[
            ("agent_noeud.py", brut(
                '            battement = DEPUIS_L_ANNONCE["battements"]' + chr(10)
                + '            if maj_auto and battement != dernier_battement:' + chr(10)
                + '                dernier_battement = battement' + chr(10)
                + '                se_mettre_a_jour_seul(studio,' + chr(10)
                + '                                      DEPUIS_L_ANNONCE["empreinte_agent"],' + chr(10)
                + '                                      epinglee)' + chr(10),
                '')),
            ("agent_noeud.py", brut(
                '            EN_COURS_ICI[:] = [tid]' + chr(10),
                '            EN_COURS_ICI[:] = [tid]' + chr(10)
                + '            battement = DEPUIS_L_ANNONCE["battements"]' + chr(10)
                + '            if maj_auto and battement != dernier_battement:' + chr(10)
                + '                dernier_battement = battement' + chr(10)
                + '                se_mettre_a_jour_seul(studio,' + chr(10)
                + '                                      DEPUIS_L_ANNONCE["empreinte_agent"],' + chr(10)
                + '                                      epinglee)' + chr(10))),
        ]),
    dict(
        nom='le pourcentage part sans son tid',
        banc="banc_boucle.py",
        imite="le studio recoit un pourcentage qu'il ne peut rattacher a "
              "aucune demande. La barre de la file reste a zero pendant tout "
              "le rendu, et l'annulation — qui revient PAR CE MEME appel — "
              "n'a plus de chemin pour arriver",
        rougit="dire() rapporte au studio le tid, le fait et le total, sans "
               "attendre",
        editions=[
            ("agent_noeud.py", brut(
                '                                       {"tid": tid, "fait": fait, "total": total},',
                '                                       {"fait": fait, "total": total},')),
        ]),
    dict(
        nom='le frein du pourcentage saute',
        banc="banc_boucle.py",
        imite="une carte rapide poste un pourcentage a chaque pas de "
              "debruitage. Pour un rendu de cinquante pas, cinquante appels "
              "HTTP la ou trois suffisent — et le studio ecrit son parc a "
              "chacun",
        rougit="un frein de 1,5 s : une carte bavarde ne noie pas le studio "
               "de pourcentages",
        editions=[
            ("agent_noeud.py", brut(
                '                    if time.time() - dernier[0] < 1.5:',
                '                    if False:')),
        ]),
    dict(
        nom='un studio en panne suffit a annuler un rendu',
        banc="banc_boucle.py",
        imite="« on ne jette pas un rendu sur un doute ». Sans le controle du "
              "statut, une reponse d'erreur qui porte le mot « annule » — un "
              "cache de proxy, un studio qui repond 500 avec un corps ancien "
              "— jette un rendu de trois minutes deja fait aux deux tiers",
        rougit="un studio en panne dont le corps dirait « annule » ne vaut "
               "jamais « annule »",
        editions=[
            ("agent_noeud.py", brut(
                '                    return (st_ == 200 and isinstance(rep, dict)' + chr(10)
                + '                            and bool(rep.get("annule")))',
                '                    return (isinstance(rep, dict)' + chr(10)
                + '                            and bool(rep.get("annule")))')),
        ]),
    dict(
        nom="une reponse qui n'est pas un objet fait lever dire()",
        banc="banc_boucle.py",
        imite="appeler() rend une CHAINE quand le reseau echoue, et des "
              "OCTETS quand la reponse n'est pas du JSON. « .get » sur l'un "
              "ou l'autre leve, la levee remonte a travers executer(), et le "
              "rendu en cours devient un « incident » : la carte a tourne "
              "pour rien, et le message ne parle meme pas du bon defaut",
        rougit="une reponse qui n'est pas un objet ne vaut jamais « annule »",
        editions=[
            ("agent_noeud.py", brut(
                '                    return (st_ == 200 and isinstance(rep, dict)' + chr(10)
                + '                            and bool(rep.get("annule")))',
                '                    return (st_ == 200' + chr(10)
                + '                            and bool(rep.get("annule")))')),
        ]),
    dict(
        nom='toute reponse sans erreur vaut « annule »',
        banc="banc_boucle.py",
        imite="le studio n'a plus besoin de dire quoi que ce soit : le "
              "premier battement de progression qui aboutit arrete le rendu. "
              "Tous les rendus du parc s'interrompent au bout d'une seconde "
              "et demie, et le journal dit « annule par le studio »",
        rougit="un 200 sans le mot ne vaut jamais « annule »",
        editions=[
            ("agent_noeud.py", brut(
                '                            and bool(rep.get("annule")))',
                '                            and not rep.get("erreur"))')),
        ]),
    dict(
        nom="l'annulation ne parvient plus jusqu'a la carte",
        banc="banc_boucle.py",
        imite="le bouton « annuler » de la page n'a plus aucun effet sur une "
              "machine a agent : le studio marque la demande annulee, la "
              "carte continue jusqu'au bout, et le fichier arrive quand meme. "
              "C'est le SEUL chemin par lequel une annulation atteigne "
              "l'agent — le studio n'a pas son adresse",
        rougit="mais un « annule » franc du studio arrete bien le rendu",
        editions=[
            ("agent_noeud.py", brut(
                '                            and bool(rep.get("annule")))',
                '                            and False)')),
        ]),
    dict(
        nom='un refus franc est repete pendant dix minutes',
        banc="banc_boucle.py",
        imite="un fichier trop gros (413) ou une extension refusee (400) ne "
              "se repare pas en le repetant. La machine reste bloquee dix "
              "minutes sur un refus definitif, sans reclamer de travail, "
              "avant d'afficher l'erreur qu'elle connaissait au premier essai",
        rougit="un refus franc (400) rend la main tout de suite",
        editions=[
            ("agent_noeud.py", brut(
                "        if st and not 500 <= st < 600:",
                "        if st == 200:")),
        ]),
    dict(
        nom='le delai de livraison est nul : un hoquet perd le travail',
        banc="banc_boucle.py",
        imite="LE DEFAUT D'ORIGINE, remis en place : un seul appel, et si le "
              "studio ne repond pas, la carte a tourne pour rien. "
              "L'utilisateur lit « echec » pour un travail que sa machine a "
              "bel et bien mene a terme — parce que le studio redemarrait a "
              "la seconde ou l'on rendait",
        rougit="un studio MUET est rappele jusqu'a ce qu'il revienne — le "
               "travail est garde",
        editions=[
            ("agent_noeud.py", brut(
                '    fin = time.time() + LIVRAISON_MINUTES * 60',
                '    fin = time.time() - 1')),
        ]),
    dict(
        nom="l'attente entre deux essais ne plafonne plus",
        banc="banc_boucle.py",
        imite="la neuvieme attente fait huit minutes : on depasse le delai de "
              "livraison en ayant reessaye six fois au lieu de vingt-quatre. "
              "Un studio revenu au bout de deux minutes n'est retrouve "
              "qu'apres quatre, et le travail est declare perdu pendant qu'il "
              "repond",
        rougit="l'attente double a chaque essai, et plafonne a trente "
               "secondes",
        editions=[
            ("agent_noeud.py", brut(
                '            dit = True' + chr(10)
                + '        time.sleep(attente)' + chr(10)
                + '        attente = min(attente * 2, 30)',
                '            dit = True' + chr(10)
                + '        time.sleep(attente)' + chr(10)
                + '        attente = attente * 2')),
        ]),
    dict(
        nom='le studio muet est annonce a chaque essai',
        banc="banc_boucle.py",
        imite="vingt-quatre lignes identiques dans la console pour une seule "
              "coupure. Sur une machine ou l'on suit le journal, l'incident "
              "reel qui suit est pousse hors de l'ecran",
        rougit="le studio muet n'est annonce QU'UNE FOIS, pas a chaque essai",
        editions=[
            ("agent_noeud.py", brut(
                '        if not dit:' + chr(10)
                + '            print(f"  studio muet ({st}) — on garde le travail et l\'on insiste",' + chr(10)
                + '                  flush=True)' + chr(10)
                + '            dit = True',
                '        if True:' + chr(10)
                + '            print(f"  studio muet ({st}) — on garde le travail et l\'on insiste",' + chr(10)
                + '                  flush=True)' + chr(10)
                + '            dit = True')),
        ]),
    dict(
        nom="le retour du studio n'est plus annonce",
        banc="banc_boucle.py",
        imite="la console dit que le studio est muet et ne dit jamais qu'il "
              "est revenu. Celui qui regarde croit la livraison perdue alors "
              "qu'elle a abouti, et va chercher un defaut qui n'existe pas",
        rougit="et son retour est annonce, avec ce qui vient d'etre livre",
        editions=[
            # L'ANCRE S'ARRETE AVANT LE « elif », depuis que la correction du
            # 4 septembre 2026 a ajoute la ligne qui nomme une reponse ni 200
            # ni reessayee. Retirer seulement l'annonce du retour laisse le
            # reste en place : c'est bien ce defaut-la qu'on imite, et non un
            # bloc entier qu'on ampute.
            ("agent_noeud.py", brut(
                '            if dit:' + chr(10)
                + '                print(f"  studio revenu — {url.split(\'/\')[-1].split(\'?\')[0]} "' + chr(10)
                + '                      f"livre ({st})", flush=True)' + chr(10)
                + '            elif st != 200:',
                '            if False:' + chr(10)
                + '                pass' + chr(10)
                + '            elif st != 200:')),
        ]),
    dict(
        nom="la perte du travail n'est plus ecrite",
        banc="banc_boucle.py",
        imite="dix minutes de carte disparaissent en silence. C'est la seule "
              "ligne qui permette, apres coup, de distinguer « le studio "
              "etait tombe » de « la machine n'a jamais rien rendu » — et "
              "sans elle, on cherche du cote de la carte",
        rougit="la perte est ecrite en clair, avec la duree — sinon personne "
               "ne la voit",
        editions=[
            ("agent_noeud.py", brut(
                '            print(f"  studio injoignable depuis {LIVRAISON_MINUTES} min — "' + chr(10)
                + '                  f"travail perdu ({st})", flush=True)' + chr(10)
                + '            return st',
                '            return st')),
        ]),
    dict(
        nom='les octets ne repartent pas au deuxieme essai',
        banc="banc_boucle.py",
        imite="insister() rappelle le studio SANS le fichier. Les vingt- "
              "quatre essais deposent un corps vide, le studio enregistre une "
              "sortie de zero octet, et le travail est compte comme reussi",
        rougit="et l'on renvoie EXACTEMENT les memes octets, le meme jeton, "
               "le meme delai",
        editions=[
            ("agent_noeud.py", brut(
                '        st, _ = appeler(url, jeton, corps, brut=brut, secondes=secondes)',
                '        st, _ = appeler(url, jeton, corps, secondes=secondes)')),
        ]),
    dict(
        nom='le delai de livraison tombe a une minute',
        banc="banc_boucle.py",
        imite="un studio qui redemarre met plus d'une minute a revenir — le "
              "temps de relire son parc et ses conversations. Le travail est "
              "declare perdu juste avant qu'il ne reponde, a chaque "
              "redemarrage",
        rougit="et ce delai vaut dix minutes quand l'environnement ne dit "
               "rien",
        editions=[
            ("agent_noeud.py", brut(
                'LIVRAISON_MINUTES = int(os.environ.get("AGENT_LIVRAISON_MINUTES") or 10)',
                'LIVRAISON_MINUTES = int(os.environ.get("AGENT_LIVRAISON_MINUTES") or 1)')),
        ]),
    dict(
        nom="la question du studio est reecrite avant d'aller au modele",
        banc="banc_boucle.py",
        imite="le studio compose sa question entiere — modele, temperature, "
              "format attendu, « stream: false ». L'agent qui n'en relaie "
              "qu'une partie fait repondre un autre modele, a une autre "
              "temperature, en flux : le studio recoit du JSON tronque et "
              "l'aiguillage part de travers",
        rougit="la question du studio part TELLE QUELLE au modele local",
        editions=[
            ("agent_noeud.py", brut(
                '            corps = q.get("corps") or {}',
                '            corps = {"prompt": (q.get("corps") or {}).get("prompt", "")}')),
        ]),
    dict(
        nom='la reponse revient au studio sans son qid',
        banc="banc_boucle.py",
        imite="le studio garde un futur par qid. Sans lui, la reponse n'est "
              "rattachee a rien : la question reste en attente jusqu'a son "
              "delai, et l'utilisateur regarde une conversation qui ne repond "
              "pas — alors que le modele a repondu",
        rougit="et la reponse revient au studio sous le MEME qid — sinon elle "
               "est perdue",
        editions=[
            ("agent_noeud.py", brut(
                '                        {"qid": q["qid"], "reponse": d.get("response", "")},',
                '                        {"reponse": d.get("response", "")},')),
        ]),
    dict(
        nom='le jeton du noeud part chez Ollama',
        banc="banc_boucle.py",
        imite="la clef qui autorise cette machine a prendre du travail est "
              "postee a un Ollama — qui peut etre un conteneur voisin ou une "
              "machine du LAN. Elle se retrouve dans les journaux d'un "
              "service qui n'en a aucun besoin, et rien ne le dit",
        rougit="le jeton du noeud va au studio et JAMAIS a Ollama",
        editions=[
            ("agent_noeud.py", brut(
                '            st2, d = appeler(f"{ollama}/api/generate", corps=corps, secondes=900)',
                '            st2, d = appeler(f"{ollama}/api/generate", jeton, corps=corps,' + chr(10)
                + '                             secondes=900)')),
        ]),
    dict(
        nom="l'echec d'Ollama n'est plus rapporte au studio",
        banc="banc_boucle.py",
        imite="le studio attend son delai entier sur une question a laquelle "
              "personne ne repondra jamais. La machine, elle, reprend "
              "tranquillement la question suivante : rien ne dit que son "
              "modele est tombe, et le studio continue de lui en confier",
        rougit="un Ollama en panne est RAPPORTE au studio, qui n'attend pas "
               "pour rien",
        editions=[
            ("agent_noeud.py", brut(
                '            else:' + chr(10)
                + '                appeler(f"{studio}/api/noeud/reponse", jeton,' + chr(10)
                + '                        {"qid": q["qid"],' + chr(10)
                + '                         "erreur": f"ollama a repondu {st2}"}, secondes=60)',
                '            else:' + chr(10)
                + '                pass')),
        ]),
    dict(
        nom="l'espacement ne se remet pas a zero apres une reprise",
        banc="banc_boucle.py",
        imite="le studio revient et le fil continue de l'interroger toutes "
              "les vingt secondes, pour toujours. Une question posee juste "
              "apres une coupure attend vingt secondes de plus que "
              "necessaire, a chaque fois",
        rougit="et l'espacement est remis a zero des que le studio repond",
        editions=[
            ("agent_noeud.py", brut(
                '            attente = PAUSE_COURTE' + chr(10)
                + '            if not isinstance(q, dict) or "qid" not in q:',
                '            if not isinstance(q, dict) or "qid" not in q:')),
        ]),
    dict(
        nom="l'espacement du fil des questions ne plafonne plus",
        banc="banc_boucle.py",
        imite="apres une heure de studio absent, le fil ne repasse plus "
              "qu'une fois par jour. Le studio revient, et cette machine ne "
              "sert plus aucune question jusqu'au redemarrage de l'agent",
        rougit="un jeton refuse espace les demandes, en doublant, jusqu'a "
               "vingt secondes",
        editions=[
            ("agent_noeud.py", brut(
                '                attente = min(attente * 2, PAUSE_LONGUE)',
                '                attente = attente * 2')),
        ]),
    dict(
        nom='une file de questions vide est prise pour une panne',
        banc="banc_boucle.py",
        imite="204 est ce que le studio repond quand sa file est vide, c'est- "
              "a-dire presque toujours. Le compter comme une panne espace le "
              "fil jusqu'a vingt secondes en une minute : la premiere "
              "question posee apres un calme attend vingt secondes avant meme "
              "d'etre vue",
        rougit="pas de question (204) : on repasse dans trois secondes, sans "
               "s'espacer",
        editions=[
            ("agent_noeud.py", brut(
                '            if st not in (200, 204):',
                '            if st != 200:')),
        ]),
    dict(
        nom='le fil des questions meurt sur la premiere exception',
        banc="banc_boucle.py",
        imite="la machine cesse silencieusement de servir le langage, et "
              "continue de s'annoncer capable de le faire. Le studio lui "
              "confie des questions qui expirent une par une, et rien nulle "
              "part ne dit que le fil est mort",
        rougit="une exception au milieu ne tue pas le fil : il revient au "
               "tour suivant",
        editions=[
            ("agent_noeud.py", brut(
                '        except Exception:' + chr(10)
                + "            # Ce fil ne doit jamais emporter l'agent : au pire le studio se" + chr(10)
                + '            # passe de cette machine pour ses questions.' + chr(10)
                + '            time.sleep(PAUSE_LONGUE)',
                '        except Exception:' + chr(10)
                + '            raise')),
        ]),
    dict(
        nom="le delai de generation tombe a celui d'une demande",
        banc="banc_boucle.py",
        imite="un modele de sept milliards de parametres sur une carte "
              "occupee met plusieurs minutes a repondre. Trente secondes, et "
              "CHAQUE question est rapportee au studio comme « ollama a "
              "repondu 0 » — alors que le modele repond, plus tard, dans le "
              "vide",
        rougit="quinze minutes pour generer, trente secondes pour demander, "
               "une pour rendre",
        editions=[
            ("agent_noeud.py", brut(
                'appeler(f"{ollama}/api/generate", corps=corps, secondes=900)',
                'appeler(f"{ollama}/api/generate", corps=corps, secondes=30)')),
        ]),
    dict(
        nom='les voisins de conteneur sont essayes avant le reglage',
        banc="banc_boucle.py",
        imite="une faute de frappe dans OLLAMA_URL devient invisible : la "
              "machine marche, par le voisin, et le reglage est mort sans que "
              "personne ne l'apprenne. Le jour ou le voisin disparait, le "
              "langage tombe et le reglage qu'on relit a l'air juste",
        rougit="le reglage est essaye AVANT les voisins de conteneur, et seul "
               "s'il repond",
        editions=[
            ("agent_noeud.py", brut(
                '    for adresse in (prefere,) + VOISINS_OLLAMA:',
                '    for adresse in VOISINS_OLLAMA + (prefere,):')),
        ]),
    dict(
        nom='les voisins de conteneur disparaissent',
        banc="banc_boucle.py",
        imite="en conteneur, l'Ollama de l'hote se joint par "
              "host.docker.internal ou par 172.17.0.1, et par rien d'autre. "
              "Sans ce repli, une machine a agent en conteneur ne trouve "
              "jamais le modele qui tourne pourtant sur son hote",
        rougit="puis les deux voisins de conteneur, dans l'ordre, en dernier "
               "recours",
        editions=[
            ("agent_noeud.py", brut(
                '    for adresse in (prefere,) + VOISINS_OLLAMA:',
                '    for adresse in (prefere,):')),
        ]),
    dict(
        nom='un reglage vide est quand meme interroge',
        banc="banc_boucle.py",
        imite="l'agent demande « /api/tags » a l'adresse vide. Selon la "
              "machine, cela leve ou attend le delai complet avant de passer "
              "au voisin — huit secondes de demarrage pour rien, a chaque "
              "lancement",
        rougit="un reglage vide n'est pas interroge — on ne demande pas a « "
               "/api/tags »",
        editions=[
            ("agent_noeud.py", brut(
                '        if adresse and (etat_ollama(adresse.rstrip("/")) or {}).get("ok"):',
                '        if (etat_ollama(adresse.rstrip("/")) or {}).get("ok"):')),
        ]),
    dict(
        nom="la barre finale reste sur l'adresse rendue",
        banc="banc_boucle.py",
        imite="l'adresse est essayee sans sa barre et rendue AVEC : toutes "
              "les requetes suivantes portent un double slash — « "
              "http://x//api/generate ». Certains serveurs l'acceptent, "
              "d'autres rendent 404, et l'essai qui a reussi ne ressemble "
              "plus a ce qu'on envoie ensuite",
        rougit="la barre finale du reglage est retiree, a l'essai comme au "
               "retour",
        editions=[
            ("agent_noeud.py", brut(
                '            return adresse.rstrip("/")' + chr(10)
                + '    return ""',
                '            return adresse' + chr(10)
                + '    return ""')),
        ]),
    dict(
        nom="les trois moteurs ajoutes apres coup quittent l'inventaire",
        banc="banc_boucle.py",
        imite="le defaut d'origine, remis en place : une machine distante ne "
              "peut jamais servir l'agrandissement, le detourage ni la "
              "fluidite video, MEME avec les fichiers sur son disque. Le "
              "studio ne les voit pas, donc il ne lui envoie rien, et rien ne "
              "le dit",
        rougit="y compris les trois moteurs ajoutes apres coup",
        editions=[
            ("agent_noeud.py", brut(
                '            "upscale_models", "background_removal", "frame_interpolation"]',
                '            ]')),
        ]),
    dict(
        nom="les dossiers virtuels du noeud GGUF quittent l'inventaire",
        banc="banc_boucle.py",
        imite="les .gguf n'apparaissent QUE dans unet_gguf et clip_gguf. Une "
              "machine qui ne sert que du GGUF — le montage courant sur une "
              "carte de huit gigaoctets — est declaree sans aucun modele, et "
              "le studio ne lui confie plus rien",
        rougit="et les deux dossiers virtuels du noeud GGUF",
        editions=[
            ("agent_noeud.py", brut(
                '            "unet_gguf", "clip_gguf",' + chr(10),
                '')),
        ]),
    dict(
        nom="une reponse qui n'est pas une liste entre dans l'inventaire",
        banc="banc_boucle.py",
        imite="ComfyUI repond parfois un objet d'erreur avec un 200, et un "
              "portail captif repond du HTML. L'agent annonce alors au studio "
              "un dossier dont le contenu est une page web, et manquants() en "
              "tire n'importe quoi — la machine passe pour porter des modeles "
              "qui n'existent pas",
        rougit="une reponse 200 qui n'est pas une liste n'entre pas dans "
               "l'inventaire",
        editions=[
            ("agent_noeud.py", brut(
                '        if st == 200 and isinstance(liste, list):',
                '        if st == 200:')),
        ]),
    dict(
        nom="un dossier vide est retire de l'inventaire",
        banc="banc_boucle.py",
        imite="le studio ne distingue plus « cette machine a le dossier et il "
              "est vide » de « je ne sais rien de ce dossier ». Les deux se "
              "lisent « clef absente », et manquants() croit l'inventaire "
              "incomplet la ou il est complet et vide",
        rougit="un dossier VIDE reste dans l'inventaire",
        editions=[
            ("agent_noeud.py", brut(
                '            trouve[d] = liste',
                '            if liste:' + chr(10)
                + '                trouve[d] = liste')),
        ]),
    dict(
        nom="l'adresse du studio manquante n'arrete plus rien",
        banc="banc_boucle.py",
        imite="l'agent demarre sans studio et va battre contre l'adresse "
              "vide, sans un mot d'explication. Celui qui installe une "
              "machine voit une banniere, puis rien — et cherche du cote du "
              "reseau",
        rougit="sans adresse de studio, rien ne demarre — et l'on dit quoi "
               "taper",
        editions=[
            ("agent_noeud.py", brut(
                '    if not studio:' + chr(10)
                + '        print("  Il manque l\'adresse du studio : --studio http://...:8199")' + chr(10)
                + '        return 1' + chr(10),
                '')),
        ]),
    dict(
        nom="le jeton manquant n'arrete plus rien",
        banc="banc_boucle.py",
        imite="l'agent ecrit ses reglages avec un jeton VIDE, puis bat contre "
              "un studio qui le refuse toutes les trente secondes. Le fichier "
              "de reglages fautif survit au lancement suivant, qui ne demande "
              "donc plus rien : la machine est enrolee de travers, "
              "durablement",
        rougit="sans jeton non plus, et AUCUN reglage n'est ecrit sur cette "
               "machine",
        editions=[
            ("agent_noeud.py", brut(
                '    if not args.jeton:' + chr(10)
                + '        print("  Il manque le jeton : --jeton XXXX (cree dans /admin du studio)")' + chr(10)
                + '        return 1' + chr(10),
                '')),
        ]),
    dict(
        nom='--maj enchaine sur la boucle',
        banc="banc_boucle.py",
        imite="« python agent_noeud.py --maj » ne rend plus la main : il "
              "telecharge, puis se met en service. Le script de mise a jour "
              "qui l'appelle ne se termine jamais, et sur une machine ou "
              "l'agent tourne deja, deux agents reclament du travail avec le "
              "meme jeton",
        rougit="--maj se passe de jeton, rend le code de la mise a jour, et "
               "ne lance rien",
        editions=[
            ("agent_noeud.py", brut(
                '    if args.maj:' + chr(10)
                + '        return se_mettre_a_jour(studio, args.empreinte)',
                '    if args.maj:' + chr(10)
                + '        se_mettre_a_jour(studio, args.empreinte)')),
        ]),
    dict(
        nom="la barre finale du studio n'est plus retiree",
        banc="banc_boucle.py",
        imite="l'adresse collee depuis /admin porte souvent une barre finale. "
              "Toutes les routes deviennent alors « http://s:8199//api/noeud/ "
              "annonce » — et le jour ou un proxy les refuse, la machine est "
              "invisible sans qu'aucun reglage n'ait l'air faux",
        rougit="la barre finale du studio ET celle de ComfyUI sont retirees "
               "avant la boucle",
        editions=[
            ("agent_noeud.py", brut(
                '    studio = args.studio.rstrip("/")',
                '    studio = args.studio')),
        ]),
    dict(
        nom="le fichier de reglages passe avant l'environnement",
        banc="banc_boucle.py",
        imite="en conteneur, STUDIO_URL ne peut plus rien contre un "
              "agent_noeud.json reste dans le volume. La machine repart sur "
              "l'adresse d'hier a chaque redemarrage, et le compose qu'on "
              "vient de corriger n'a aucun effet",
        rougit="l'environnement passe AVANT le fichier de reglages, pour le "
               "conteneur",
        editions=[
            ("agent_noeud.py", brut(
                '    cfg = {"studio": os.environ.get("STUDIO_URL") or cfg.get("studio", ""),',
                '    cfg = {"studio": cfg.get("studio", "") or os.environ.get("STUDIO_URL", ""),')),
        ]),
    dict(
        nom="un dossier de sorties introuvable n'est plus refuse",
        banc="banc_boucle.py",
        imite="l'agent annonce au demarrage qu'il effacera les sorties, et "
              "n'efface jamais rien : le chemin n'existe pas. Le disque de la "
              "machine a carte se remplit pendant des semaines, sous une "
              "ligne qui affirme le contraire",
        rougit="un dossier de sorties introuvable est refuse TOUT DE SUITE",
        editions=[
            ("agent_noeud.py", brut(
                '    if sorties and not os.path.isdir(sorties):',
                '    if False:')),
        ]),
    dict(
        nom='les reglages ne sont plus enregistres',
        banc="banc_boucle.py",
        imite="chaque lancement redemande studio, jeton, ComfyUI et sorties. "
              "Le service Windows et l'unite systemd, qui lancent l'agent "
              "sans aucun argument, ne demarrent plus du tout apres le "
              "premier redemarrage de la machine",
        rougit="les reglages sont ecrits pour le prochain lancement, sans "
               "arguments",
        editions=[
            ("agent_noeud.py", brut(
                '    ecrire_config({"studio": studio, "jeton": args.jeton, "comfy": args.comfy,' + chr(10)
                + '                   "sorties": sorties, "garder_heures": args.garder,' + chr(10)
                + '                   "ollama": args.ollama})' + chr(10),
                '')),
        ]),
    dict(
        nom="c'est le reglage demande qui part a la boucle, pas l'Ollama trouve",
        banc="banc_boucle.py",
        imite="la boucle demarre le fil des questions sur une adresse dont on "
              "vient de mesurer qu'elle ne repond pas, et le voisin de "
              "conteneur qu'on avait trouve est jete. Le fil interroge un "
              "Ollama mort pour toujours, en rapportant au studio « ollama a "
              "repondu 0 » a chaque question",
        rougit="aucun Ollama joignable : la boucle demarre quand meme, sans "
               "fil de langage",
        editions=[
            ("agent_noeud.py", brut(
                '           ollama, args.empreinte, not args.sans_maj_auto)',
                '           args.ollama, args.empreinte, not args.sans_maj_auto)')),
        ]),
    dict(
        nom="--sans-maj-auto n'arrive pas jusqu'a la boucle",
        banc="banc_boucle.py",
        imite="le drapeau est accepte sur la ligne de commande, affiche dans "
              "l'aide, et sans aucun effet. La machine qu'on voulait figer se "
              "remplace a la premiere version servie — c'est le pire des cas "
              ": un garde-fou qui a l'air pose",
        rougit="--sans-maj-auto arrive jusqu'a la boucle, qui ne se "
               "remplacera pas",
        editions=[
            ("agent_noeud.py", brut(
                '           ollama, args.empreinte, not args.sans_maj_auto)',
                '           ollama, args.empreinte, True)')),
        ]),
    dict(
        nom="l'empreinte epinglee n'arrive pas jusqu'a la boucle",
        banc="banc_boucle.py",
        imite="--empreinte ne protege que le « --maj » lance a la main, et "
              "pas la mise a jour AUTOMATIQUE — la seule qui tourne sans "
              "personne pour regarder. Le seul garde-fou de celui qui heberge "
              "contre un agent servi par autre chose que son studio devient "
              "decoratif",
        rougit="l'empreinte epinglee descend jusqu'a la boucle, qui la "
               "passera a la maj",
        editions=[
            ("agent_noeud.py", brut(
                '           ollama, args.empreinte, not args.sans_maj_auto)',
                '           ollama, "", not args.sans_maj_auto)')),
        ]),
    dict(
        nom="l'agent avale l'echec du /free au lieu de le rapporter",
        banc="banc_boucle.py",
        imite="le studio ne remplit plus liberation_refusee, et ne distingue "
              "plus « ComfyUI trop ancien » de « la carte etait deja vide ». "
              "C'est exactement le diagnostic pour lequel ce rapport existe, "
              "et il ne remonte plus que quand tout va bien",
        rougit="un ComfyUI qui REFUSE le /free est rapporte au studio, avec "
               "son statut",
        editions=[
            ("agent_noeud.py", brut(
                '                rapport_liberation = {"ok": abouti, "statut": statut}',
                '                rapport_liberation = ({"ok": abouti, "statut": statut}' + chr(10)
                + '                                      if abouti else None)')),
        ]),
    dict(
        nom="le diagnostic de liberation est jete avant d'etre recu",
        banc="banc_boucle.py",
        imite="un studio qui redemarre a la seconde ou l'on rapporte fait "
              "perdre le diagnostic pour toujours : la consigne a ete suivie, "
              "le refus a eu lieu, et plus rien nulle part ne le dit. Le "
              "studio reclamera la carte au battement suivant, et au suivant",
        rougit="un studio muet ne fait pas perdre le diagnostic : il est "
               "GARDE et repropose",
        editions=[
            ("agent_noeud.py", brut(
                '            if rapport_liberation is not None:' + chr(10)
                + '                corps["libere"] = rapport_liberation' + chr(10)
                + '            st, d = appeler(f"{studio}/api/noeud/annonce", jeton, corps)',
                '            if rapport_liberation is not None:' + chr(10)
                + '                corps["libere"] = rapport_liberation' + chr(10)
                + '            rapport_liberation = None' + chr(10)
                + '            st, d = appeler(f"{studio}/api/noeud/annonce", jeton, corps)')),
        ]),
    dict(
        nom="la carte n'est pas remesuree apres avoir ete rendue",
        banc="banc_boucle.py",
        imite="la VRAM annoncee au battement suivant est celle d'AVANT la "
              "liberation, prise dans le cache d'une minute. Le studio lit "
              "que le /free n'a rien rendu, et va chercher le defaut du cote "
              "de ComfyUI — alors que la carte est vide",
        rougit="la carte est remesuree au battement SUIVANT, et une seule "
               "fois",
        editions=[
            ("agent_noeud.py", brut(
                "                # Remesurer tout de suite : c'est la VRAM du battement SUIVANT" + chr(10)
                + '                # qui dit au studio ce que la liberation a rendu, et sans cela' + chr(10)
                + "                # elle serait celle d'avant, prise dans le cache d'une minute." + chr(10)
                + '                DEPUIS_L_ANNONCE["remesurer"] = True',
                "                # Remesurer tout de suite : c'est la VRAM du battement SUIVANT" + chr(10)
                + '                # qui dit au studio ce que la liberation a rendu, et sans cela' + chr(10)
                + "                # elle serait celle d'avant, prise dans le cache d'une minute.")),
        ]),
    dict(
        nom="l'agent decharge la carte a chaque battement",
        banc="banc_boucle.py",
        imite="la consigne du studio n'est plus lue : l'agent rend la carte "
              "toutes les dix secondes des qu'il est au repos. Chaque rendu "
              "recommence par un rechargement complet du modele — dix a "
              "trente secondes de carte, a chaque image",
        rougit="et une seule fois : un ordre unique ne vaut pas une "
               "liberation par battement",
        editions=[
            ("agent_noeud.py", brut(
                '            if d.get("liberer") and not EN_COURS_ICI:',
                '            if not EN_COURS_ICI:')),
        ]),
    dict(
        nom="le refus du /free n'est plus nomme dans la console",
        banc="banc_boucle.py",
        imite="la console annonce « carte rendue au systeme » alors que "
              "ComfyUI a repondu 404. Celui qui heberge lit que tout va bien, "
              "et le seul endroit ou le chiffre apparaissait disparait",
        rougit="et la console nomme le refus, avec le chiffre qui dit ou "
               "regarder",
        editions=[
            ("agent_noeud.py", brut(
                '                print("  carte rendue au systeme" if abouti' + chr(10)
                + '                      else f"  ComfyUI a refuse /free ({statut}) — version trop "' + chr(10)
                + '                           f"ancienne ?", flush=True)',
                '                print("  carte rendue au systeme", flush=True)')),
        ]),
]


MUTATIONS = (CONSOLE + FACTEUR_ADMIN + CONTENEUR + PAGE + REPARTITION + LIBERATION + VARIANTES + CERVEAUX + COUT
             + CATALOGUE + ATTENTE + DUREES + ADULTE + REFAIRE + FORMULATIONS
             + MULTILINGUE + PROSE + LANGUES + PAGE_LANGUES + MOITIES_SERVEUR
             + FACTEUR + FACTEUR_MFA + DEMARRAGE + QR + ADVERSE
             + MAJ_AGENT + RENDU_AGENT + DISQUE_AGENT + PROGRESSION_AGENT
             + NOEUD + VERSION + BOUCLE_AGENT)


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

    # ── « CASSE » SE REJOUE UNE FOIS, « VERT » JAMAIS ───────────────────
    # Les quatre verdicts ne se valent pas devant le hasard. « vert » dit que le
    # filet a un trou : le rejouer serait chercher un tour ou le trou se referme,
    # et c'est exactement la facon dont on finit par ne plus rien mesurer.
    # « perimee » ne depend d'aucune execution : l'ancre est la ou elle n'y est
    # pas. Mais « casse » melange deux choses tres differentes — une mutation qui
    # fait vraiment planter le banc, et un processus que la machine a tue.
    #
    # MESURE DU 4 SEPTEMBRE 2026, ET C'EST ELLE QUI A DECIDE : un tour a rendu
    # TROIS echecs — deux « sans sortie », c'est-a-dire un banc mort avant sa
    # premiere ligne, et un « TypeError: 'str' object is not an iterator » dans
    # ast.iter_fields — et le tour suivant ZERO sur 244 mutations, sans qu'une
    # ligne du depot ne bouge. Un troisieme avait rendu « SystemError: Negative
    # size passed to PyBytes_FromStringAndSize ». Trois signatures differentes,
    # dont deux erreurs INTERNES de CPython, sur trois bancs differents : c'est
    # la machine sous charge, pas le filet.
    #
    # ON NE LISSE PAS POUR AUTANT. Un second essai qui reussit est SIGNALE, avec
    # ce que le premier avait rendu : une instabilite qu'on efface est une
    # instabilite qui grandit, et le jour ou un banc plantera vraiment un tour
    # sur deux, la ligne sera la pour le dire. C'est le meme raisonnement que
    # TROUS_CONNUS, pris a l'envers : on ne compte pas en echec ce qu'on ne sait
    # pas reproduire, mais on l'ecrit.
    for mut in MUTATIONS:
        etat, detail = verdict(mut, racine)
        if etat == "casse":
            second, detail2 = verdict(mut, racine)
            if second == "rouge":
                signales.append(
                    f"DEUX ESSAIS : {mut['banc']} / {mut['nom']} — le premier a "
                    f"rendu « {detail} », le second a rougi")
                etat, detail = second, detail2
            else:
                detail = f"{detail} (deux essais, second : {detail2})"
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
