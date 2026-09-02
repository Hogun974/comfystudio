# -*- coding: utf-8 -*-
"""Ce que le studio DIT, dans la langue de celui qui lit.

CE FICHIER NE TRADUIT PAS TOUT, ET C'EST UNE DECISION MESUREE. Le studio ecrit
trois familles de texte, et une seule se traduit :

  - LES MESSAGES D'ERREUR ET L'INTERFACE. Des etiquettes, constantes, courtes.
    Elles disent a l'utilisateur ce qui vient de se passer et ce qu'il peut
    faire. Elles sont ici.
  - LE JOURNAL. 163 messages, dont 110 interpolent une valeur calculee a
    l'execution — « RealVisXL demande 7,0 Go et la carte en offre 5,9 :
    debordement sur la RAM, plus lent ». Une phrase pareille porte deux mesures,
    une consequence et une raison ; la reduire a un gabarit la vide de ce qui la
    rend utile. Le journal ne se traduit pas, et docs/plusieurs-langues.md dit
    pourquoi en trois points.
  - LA DOCUMENTATION. 38 625 mots, dates et lies a une mesure. Une traduction
    fige la version du jour et vieillit sans le dire.

    L'EXCEPTION DU JOURNAL, ET ELLE COMPTE : la page affiche la DERNIERE ligne
    de journal comme message d'erreur quand un rendu echoue — « if (t.etat ===
    "erreur" && derniere) t.erreur = derniere.msg », web/index.html. Ce que
    l'utilisateur lit apres une panne n'est donc pas un message d'API, c'est du
    journal. Ces lignes-la sont peu nombreuses — celles qui portent
    « etat="erreur" » — et elles sont ici, sous « panne. ». Sans elles, on
    aurait traduit les REFUS, qui arrivent avant que rien ne commence, et laisse
    toutes les PANNES en francais.

LES CLES SONT DES IDENTIFIANTS, JAMAIS LE TEXTE SOURCE. Indexer sur le francais
paraissait plus simple, et c'est un piege mesure : la page ecrit « c’etait
plutot » avec une apostrophe typographique et « l'esquisse » avec une droite —
deux cles pour un meme mot, et une reformulation cote francais perd la
traduction sans rien dire.

LE FRANCAIS EST ICI AUSSI, meme si le studio est ecrit en francais. C'est la
moitie d'un contrat : banc_traductions.py exige que le texte francais de la
PAGE soit exactement celui du dictionnaire, comme banc_refaire.py exige que la
marque de la page soit celle du serveur. Sans cela, une phrase reformulee d'un
seul cote laisserait un utilisateur anglais devant une traduction devenue
fausse, et personne pour le voir.
"""

# Les langues servies. Le francais d'abord : c'est la langue source, celle qui
# fait foi quand une traduction manque.
#
# AJOUTER UNE LANGUE NE DEMANDE QUE DEUX CHOSES : l'ajouter ici, et remplir sa
# colonne. banc_traductions.py refusera tant qu'il manquera une seule cle —
# c'est voulu : une interface a moitie traduite est pire qu'une interface qui
# n'a jamais promis de l'etre.
LANGUES = ("fr", "en")

# ── Les pluriels ────────────────────────────────────────────────────────
# LA REGLE EST UNE DONNEE DE LA LANGUE, PAS DU SITE D'APPEL. La page ecrivait
# « ${n} echange${n > 1 ? "s" : ""} » a chaque endroit qui compte quelque
# chose : la regle FRANCAISE, recopiee, dans du code d'interface. Elle est
# fausse en anglais des zero — le francais ecrit « 0 echange », l'anglais
# « 0 exchanges » — et la recopier vingt fois garantit qu'une des vingt sera
# oubliee le jour ou l'on ajoutera une langue.
#
# Rend l'INDICE de la forme a prendre dans la liste des formes.
PLURIELS = {
    "fr": lambda n: 1 if n > 1 else 0,      # 0 et 1 au singulier
    "en": lambda n: 1 if n != 1 else 0,     # 1 seul au singulier
}


# ── Le dictionnaire ─────────────────────────────────────────────────────
# Une entree est soit une chaine par langue, soit une LISTE de formes par
# langue quand le texte compte quelque chose. Les valeurs interpolees s'ecrivent
# « {nom} » et doivent etre les MEMES dans toutes les langues : c'est ce que
# banc_traductions.py verifie en premier, parce qu'un « {n} » oublie dans la
# traduction fait disparaitre un chiffre a l'ecran sans lever la moindre erreur.
TEXTES = {

    # ══ Les refus d'API que la page AFFICHE ════════════════════════════
    # Vingt-cinq chaines sur les cinquante-deux du serveur. Les autres parlent
    # a l'administrateur (« acces refuse », « jeton invalide ») ou aux agents
    # des machines a carte (« jeton inconnu ») — deux publics qui lisent des
    # journaux, pas une interface —, ou bien la page les avale sans rien
    # montrer. Mesure du 2 septembre 2026 : 119 occurrences, 52 chaines
    # distinctes, 25 lues par un humain non administrateur.
    "erreur.corps_illisible": {
        "fr": "corps illisible",
        "en": "unreadable request body"},
    "erreur.conversation_inconnue": {
        "fr": "inconnue",
        "en": "unknown conversation"},
    "erreur.tour_inconnu": {
        "fr": "inconnu",
        "en": "unknown turn"},
    "erreur.demande_vide": {
        "fr": "demande vide",
        "en": "empty request"},
    "erreur.taille_non_prise": {
        "fr": "taille non prise en charge",
        "en": "unsupported size"},
    "erreur.moteur_inconnu": {
        "fr": "moteur inconnu",
        "en": "unknown engine"},
    "erreur.moteur_sans_cle": {
        "fr": "ce moteur demande une cle d API, a poser dans /admin",
        "en": "this engine needs an API key, set one in /admin"},
    "erreur.priorite_inconnue": {
        "fr": "priorite inconnue",
        "en": "unknown priority"},
    "erreur.variantes_illisible": {
        "fr": "nombre de variantes illisible",
        "en": "unreadable number of variants"},
    "erreur.variantes_bornes": {
        "fr": "de 1 a {plafond} variantes",
        "en": "1 to {plafond} variants"},
    "erreur.machine_inconnue": {
        "fr": "machine inconnue",
        "en": "unknown machine"},
    "erreur.image_inconnue": {
        "fr": "image inconnue",
        "en": "unknown image"},

    # Les deux boutons qui rejouent un plan garde. Leurs refus sont les seuls
    # du depot dont la page traduit un en coche verte — voir MARQUE_DEJA.
    "erreur.deja_au_propre": {
        "fr": "cette esquisse a deja ete passee au propre",
        "en": "this sketch has already been redrawn cleanly"},
    "erreur.pas_une_esquisse": {
        "fr": "ce tour n'est pas une esquisse qu'on sache refaire",
        "en": "this turn is not a sketch we know how to redo"},
    "erreur.esquisse_pas_finie": {
        "fr": "l'esquisse n'est pas terminee",
        "en": "the sketch is not finished yet"},
    "erreur.deja_refait": {
        "fr": "ce tour a deja ete refait",
        "en": "this turn has already been redone"},
    "erreur.tour_pas_termine": {
        "fr": "ce tour n'est pas termine",
        "en": "this turn is not finished yet"},
    "erreur.pas_de_prompt": {
        "fr": "ce tour n'a pas de prompt qu'on sache reprendre",
        "en": "this turn has no prompt we know how to reuse"},
    # « {titre} » est un nom propre servi par le catalogue : il ne se traduit
    # pas, il se place. L'anglais le met ailleurs dans la phrase, et c'est
    # exactement pour cela que la phrase entiere est ici et non recollee en
    # morceaux au site d'appel.
    "erreur.au_propre_distant": {
        "fr": "cette esquisse a ete rendue par {titre} : « en soigne » n'y "
              "veut rien dire, il n'a ni graine ni etapes. Relance la demande.",
        "en": "this sketch was rendered by {titre}: “cleanly” means nothing "
              "there — it has neither seed nor steps. Send the request again."},
    "erreur.refaire_distant": {
        "fr": "ce rendu a ete confie a {titre} : « refaire sur la grosse "
              "carte » demande une carte de la maison. Relance la demande pour "
              "repartir chez lui.",
        "en": "this render was handed to {titre}: “redo on the big card” "
              "needs a card of our own. Send the request again to go back "
              "there."},
    "erreur.moteur_hors_catalogue": {
        "fr": "le moteur de ce tour ({moteur}) n'est plus au catalogue : "
              "relance la demande pour en choisir un autre",
        "en": "this turn's engine ({moteur}) is no longer in the catalogue: "
              "send the request again to pick another one"},
    "erreur.moteur_esquisse_hors_catalogue": {
        "fr": "le moteur de cette esquisse ({moteur}) n'est plus au "
              "catalogue : relance la demande pour en choisir un autre",
        "en": "this sketch's engine ({moteur}) is no longer in the catalogue: "
              "send the request again to pick another one"},

    # Le pouce, et l'entree.
    "erreur.avis_attendu": {
        "fr": "avis attendu : -1, 0 ou 1",
        "en": "expected rating: -1, 0 or 1"},
    "erreur.intention_inconnue": {
        "fr": "intention inconnue",
        "en": "unknown intent"},
    "erreur.echange_inconnu": {
        "fr": "echange inconnu",
        "en": "unknown exchange"},
    "erreur.origine_refusee": {
        "fr": "origine refusee",
        "en": "origin refused"},
    "erreur.identifiants_faux": {
        "fr": "nom ou mot de passe incorrect",
        "en": "wrong name or password"},
    "erreur.trop_d_essais": {
        "fr": "trop d'essais — reessaie dans {secondes} s",
        "en": "too many attempts — try again in {secondes} s"},
    "erreur.connexion_requise": {
        "fr": "connexion requise",
        "en": "sign-in required"},

    # Les fichiers joints. « {famille} » vaut image, video ou audio : ce sont
    # des identifiants INTERNES, et les laisser au milieu d'une phrase traduite
    # ferait « file too heavy: video limited to 64 MB » avec un mot francais au
    # hasard le jour ou l'un d'eux changera. On les traduit donc aussi.
    "erreur.aucun_fichier": {
        "fr": "aucun fichier recu",
        "en": "no file received"},
    "erreur.fichier_vide": {
        "fr": "fichier vide",
        "en": "empty file"},
    "erreur.format_refuse": {
        "fr": "format non pris en charge ({extension}). Acceptes : {acceptes}",
        "en": "unsupported format ({extension}). Accepted: {acceptes}"},
    "erreur.fichier_trop_lourd": {
        "fr": "fichier trop lourd : {famille} limite a {mega} Mo",
        "en": "file too heavy: {famille} limited to {mega} MB"},
    "famille.image": {"fr": "image", "en": "image"},
    "famille.video": {"fr": "video", "en": "video"},
    "famille.audio": {"fr": "morceau", "en": "audio"},
    "famille.objet3d": {"fr": "objet 3D", "en": "3D object"},
    # UNE PHRASE, ET NON str(e). La route /api/reprendre rendait l'exception
    # Python telle quelle a l'ecran — « ERREUR : KeyError('sdxl_vieux') » —,
    # le meme message qui n'apprend rien a personne que ce depot chasse
    # partout ailleurs. Le detail technique va au journal du studio, ou il sert
    # a quelqu'un.
    "erreur.reprise_impossible": {
        "fr": "impossible de reprendre ce fichier depuis la machine qui l'a "
              "calcule — il a peut-etre ete efface. Le journal du studio dit "
              "laquelle et pourquoi.",
        "en": "this file could not be fetched back from the machine that "
              "computed it — it may have been deleted. The studio log says "
              "which machine, and why."},

    # ══ Les pannes ═════════════════════════════════════════════════════
    # CE QUE L'UTILISATEUR LIT QUAND UN RENDU ECHOUE. La page prend la DERNIERE
    # ligne du journal et la met dans le champ « erreur » du tour : ce ne sont
    # donc pas les refus ci-dessus qu'il voit apres une panne, ce sont
    # celles-ci. Neuf phrases — les journal(..., etat="erreur") — et c'est
    # tout ce qui separe une page anglaise d'une page anglaise qui ment.
    "panne.machine_pas_revenue": {
        "fr": "la machine n'est pas revenue a temps",
        "en": "the machine did not come back in time"},
    "panne.conversation_fermee": {
        "fr": "conversation fermee pendant l'attente",
        "en": "conversation closed while waiting"},
    "panne.abandon_delai": {
        "fr": "{machines} n'est pas revenue dans le delai prevu — la demande "
              "est abandonnee",
        "en": "{machines} did not come back within the expected delay — the "
              "request is abandoned"},
    "panne.retiree_de_la_file": {
        "fr": "retiree de la file",
        "en": "removed from the queue"},
    "panne.interrompue": {
        "fr": "interrompue",
        "en": "interrupted"},
    "panne.rendu_coupe": {
        "fr": "{machine} a coupe son rendu — {secondes} s de calcul jetees",
        "en": "{machine} cut its render short — {secondes} s of compute "
              "thrown away"},
    "panne.arret_demande": {
        "fr": "arret demande a {machine} — sa carte s'arrete des qu'elle nous "
              "rappelle",
        "en": "stop requested from {machine} — its card stops as soon as it "
              "calls us back"},
    # Les deux qui portaient une exception Python a l'ecran. Le gabarit reste
    # ouvert sur « {quoi} », parce que ce que echouer() recoit est deja une
    # phrase francaise ecrite au site d'appel — et ces sites-la sont, eux,
    # dans ce dictionnaire.
    "panne.echec": {
        "fr": "ERREUR : {quoi}",
        "en": "ERROR: {quoi}"},
    "panne.echec_inattendu": {
        "fr": "ERREUR inattendue : {quoi}",
        "en": "unexpected ERROR: {quoi}"},

    # ══ Ce qui COMPTE quelque chose ════════════════════════════════════
    # LA PAGE ECRIVAIT LA REGLE FRANCAISE A CHAQUE ENDROIT : « ${c.tours}
    # echange${c.tours > 1 ? "s" : ""} ». Recopiee, en francais, dans du code
    # d'interface — et fausse en anglais des zero. Ailleurs elle l'esquivait
    # avec « appel(s) », « demande(s) », « conversation(s) », ce qui ne se lit
    # bien dans aucune langue et n'existe pas dans toutes.
    #
    # Les formes sont dans l'ordre que PLURIELS rend : singulier d'abord.
    "compte.echanges": {
        "fr": ["{n} echange", "{n} echanges"],
        "en": ["{n} exchange", "{n} exchanges"]},
    "compte.pieces": {
        "fr": ["{n} piece", "{n} pieces"],
        "en": ["{n} file", "{n} files"]},
    "compte.appels": {
        "fr": ["{n} appel", "{n} appels"],
        "en": ["{n} call", "{n} calls"]},
    "compte.demandes": {
        "fr": ["{n} demande", "{n} demandes"],
        "en": ["{n} request", "{n} requests"]},
    "compte.conversations": {
        "fr": ["{n} conversation", "{n} conversations"],
        "en": ["{n} conversation", "{n} conversations"]},
    "compte.variantes": {
        "fr": ["{n} variante", "{n} variantes"],
        "en": ["{n} variant", "{n} variants"]},
    "compte.machines": {
        "fr": ["{n} machine", "{n} machines"],
        "en": ["{n} machine", "{n} machines"]},
}


# ── Lire une entree ─────────────────────────────────────────────────────
def T(cle, langue="fr", nombre=None, **valeurs):
    """Le texte de cette cle, dans cette langue, avec ses valeurs posees.

    LE REPLI EST LE FRANCAIS, ET IL EST SILENCIEUX ICI mais pas ailleurs :
    banc_traductions.py refuse qu'une cle manque dans une langue servie, donc
    ce repli ne devrait jamais servir en production. Il est la pour que le
    studio ne meure pas a cause d'un mot manquant — un studio qui repond en
    francais est genant, un studio qui rend 500 est casse.

    « nombre » choisit la forme quand l'entree en a plusieurs, selon la regle
    de la langue et non celle du site d'appel. Il est pose dans les valeurs
    sous le nom « n », parce qu'une forme plurielle veut presque toujours
    afficher le compte qu'elle accorde.
    """
    entree = TEXTES.get(cle)
    if entree is None:
        # UNE CLE INCONNUE REND SA PROPRE CLE, et ne leve pas. Le texte
        # « erreur.machin » a l'ecran est laid et se voit tout de suite ; une
        # exception, elle, remplacerait le message par une page blanche au
        # moment precis ou l'utilisateur avait besoin qu'on lui parle.
        return cle
    formes = entree.get(langue)
    if formes is None:
        formes = entree.get("fr", cle)
    if isinstance(formes, (list, tuple)):
        regle = PLURIELS.get(langue) or PLURIELS["fr"]
        formes = formes[regle(nombre or 0)]
    if nombre is not None:
        valeurs.setdefault("n", nombre)
    try:
        return formes.format(**valeurs)
    except (KeyError, IndexError):
        # UNE VALEUR MANQUANTE NE MANGE PAS LA PHRASE. Le gabarit brut, avec
        # ses accolades visibles, dit a celui qui le lit qu'il manque quelque
        # chose — et dit lequel. Une exception ici ferait disparaitre le
        # message entier.
        return formes


def textes_de(langue):
    """Toutes les cles dans cette langue, a plat. C'est ce que la page recoit.

    Les formes plurielles restent des LISTES : la page a sa propre copie de la
    regle, dans la meme langue, parce qu'elle compte des choses que le serveur
    ne voit pas — les pieces jointes qu'on vient de deposer, les conversations
    de la barre laterale.
    """
    rendu = {}
    for cle, entree in TEXTES.items():
        v = entree.get(langue)
        rendu[cle] = entree.get("fr") if v is None else v
    return rendu


def langue_choisie(cookie="", accept=""):
    """La langue a servir : le choix explicite d'abord, le navigateur ensuite.

    L'EN-TETE NE SERT QUE DE PREMIERE VALEUR, jamais de decision. Il dit la
    langue du NAVIGATEUR, pas celle de la personne : un francophone sur un
    Windows anglais serait servi en anglais pour toujours, sans jamais
    comprendre pourquoi. Des que quelqu'un choisit dans le menu, le cookie
    porte le choix et l'en-tete n'est plus lu.

    C'est AUSSI la raison pour laquelle il ne sert pas a aiguiller les
    demandes : docs/plusieurs-langues.md tranche ce point separement, et c'est
    la couverture du vocabulaire qui decide la-bas — la langue des MENUS et la
    langue de la DEMANDE sont deux questions, et quelqu'un peut tres bien lire
    une interface anglaise en tapant sa demande en francais.
    """
    if cookie in LANGUES:
        return cookie
    # « fr-CA,fr;q=0.9,en;q=0.8 » : on lit les etiquettes dans l'ordre ou le
    # navigateur les a mises, et on prend la premiere qu'on sait servir. Les
    # poids « q » ne sont pas relus : les navigateurs les ecrivent deja dans
    # l'ordre decroissant, et les trier a la main ferait du code sans mesure.
    for morceau in (accept or "").split(","):
        etiquette = morceau.split(";")[0].strip().lower()
        court = etiquette.split("-")[0]
        if court in LANGUES:
            return court
    return LANGUES[0]
