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
    # UNE SEULE CLE POUR LA CONVERSATION ET POUR LE TOUR, et c'est une
    # correction du 2 septembre 2026 au soir. Le dictionnaire en portait deux —
    # « unknown conversation » et « unknown turn » — la ou le serveur ecrit le
    # meme mot, « inconnue », aux deux endroits ET DELIBEREMENT : « 404 et non
    # 400 : un tour qui n'a rien produit n'est rien a designer, et distinguer
    # pas a toi de pas fini renseignerait un curieux » (api_variante_choisir,
    # serveur.py). La traduction anglaise reintroduisait donc exactement la
    # distinction que le francais cache : elle disait au curieux si la
    # conversation existe. Une cle, un mot, aucun aveu.
    "erreur.introuvable": {
        "fr": "inconnue",
        "en": "not found"},
    # Le masculin du meme refus, et sa seule autre occurrence : la sortie qu'on
    # redemande a /api/reprendre. Separee parce que le francais accorde, pas
    # parce qu'elle avoue quelque chose de plus.
    "erreur.fichier_introuvable": {
        "fr": "inconnu",
        "en": "not found"},
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
    # RELEVEE SUR LE CODE le 2 septembre 2026 au soir : le dictionnaire portait
    # « il n'a ni graine ni etapes. Relance la demande. » et le serveur ecrit
    # « il n'a ni graine ni etapes a reprendre. Relance la demande pour repartir
    # chez lui. » Le francais de la page n'aurait pas bouge — T() rend le
    # dictionnaire —, mais la phrase servie n'aurait plus ete celle que le code
    # dit servir, et c'est le contrat que banc_traductions.py existe pour tenir.
    "erreur.au_propre_distant": {
        "fr": "cette esquisse a ete rendue par {titre} : « en soigne » n'y "
              "veut rien dire, il n'a ni graine ni etapes a reprendre. "
              "Relance la demande pour repartir chez lui.",
        "en": "this sketch was rendered by {titre}: “cleanly” means nothing "
              "there — it has neither seed nor steps to reuse. Send the "
              "request again to go back there."},
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
    # LES TROIS SONT NOMMES ENSEMBLE, ET C'EST LA MEME RAISON QU'AVANT. Dire
    # « le mot de passe etait bon, c'est le code qui est faux » ferait de la
    # porte un oracle a mots de passe : on essaie un dictionnaire, on note ceux
    # qui font changer la phrase, et le second facteur ne garde plus qu'un
    # compte dont le mot de passe est desormais connu. Le code a rejoint la
    # liste le jour ou il est entre par cette route ; la phrase n'apprend
    # toujours rien.
    "erreur.identifiants_faux": {
        "fr": "nom, mot de passe ou code incorrect",
        "en": "wrong name, password or code"},
    # ── le second facteur ───────────────────────────────────────────
    # CELLE-CI N'EST PAS UN REFUS, c'est une demande : le mot de passe etait
    # bon. Elle voyage a cote du champ « mfa » que la page lit, et c'est LE
    # CHAMP qui decide d'afficher la case — jamais cette phrase, qui se
    # reformule et se traduit.
    "erreur.code_requis": {
        "fr": "code du second facteur requis",
        "en": "second-factor code required"},
    "erreur.code_faux": {
        "fr": "ce code ne correspond pas",
        "en": "this code does not match"},
    "erreur.mfa_deja_arme": {
        "fr": "le second facteur est déjà armé sur ce compte",
        "en": "the second factor is already armed on this account"},
    "erreur.mfa_sans_enrolement": {
        "fr": "aucun enrôlement en cours : recommence depuis le début",
        "en": "no enrolment under way: start again from the beginning"},
    "erreur.mfa_absent": {
        "fr": "aucun second facteur sur ce compte",
        "en": "no second factor on this account"},
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
    #
    # RELEVEE SUR LE CODE le 2 septembre 2026 au soir, et elle etait perimee :
    # le dictionnaire decrivait le remede tel qu'il avait ete IMAGINE — « le
    # journal du studio dit laquelle » — quand serveur.py, lui, NOMME deja la
    # machine dans la phrase. C'est la seule chose sur laquelle l'utilisateur
    # puisse agir, banc_refaire.py l'exige (« le titre de la machine est dans
    # le message »), et la traduction la lui aurait retiree. « {titre} » est
    # donc obligatoire ici, et le banc le mesure des deux cotes.
    "erreur.reprise_impossible": {
        "fr": "{titre} n'a pas rendu ce fichier : il a peut-etre ete efface, "
              "ou la machine ne repond plus. Reprends une autre sortie, ou "
              "reessaie plus tard.",
        "en": "{titre} did not hand this file back: it may have been deleted, "
              "or the machine no longer answers. Pick another output, or try "
              "again later."},
    # « sans extension » se pose DANS « {extension} » quand le fichier n'en a
    # pas. Deux mots francais au milieu d'une phrase anglaise, sinon — le meme
    # defaut que famille.* ferme deux entrees plus haut.
    "erreur.sans_extension": {
        "fr": "sans extension",
        "en": "no extension"},

    # ══ Les pannes ═════════════════════════════════════════════════════
    # CE QUE L'UTILISATEUR LIT QUAND UN RENDU ECHOUE. La page prend la DERNIERE
    # ligne du journal et la met dans le champ « erreur » du tour : ce ne sont
    # donc pas les refus ci-dessus qu'il voit apres une panne, ce sont
    # celles-ci — et c'est tout ce qui separe une page anglaise d'une page
    # anglaise qui ment.
    #
    # LE JOURNAL, LUI, RESTE FRANCAIS : il est ECRIT, garde sur la tache, relu
    # plus tard, parfois par quelqu'un d'autre que celui qui a lance la
    # demande. Ce que le serveur pose a cote de la ligne francaise, c'est une
    # CLE — serveur.MARQUE_PANNE — que /api/etat sert avec ses valeurs et que
    # la page met en phrase. Les deux moities du contrat : la ligne pour le
    # studio, la cle pour le lecteur.
    #
    # Treize phrases : les dix journal(..., etat="erreur") et les cinq
    # arguments de echouer(), moins les recoupements. Le compte est mesure —
    # banc_traductions.py releve les sites dans le TEXTE de serveur.py et
    # refuse qu'un seul soit sans cle.
    "panne.machine_pas_revenue": {
        "fr": "la machine n'est pas revenue a temps",
        "en": "the machine did not come back in time"},
    "panne.conversation_fermee": {
        "fr": "conversation fermee pendant l'attente",
        "en": "conversation closed while waiting"},
    # LA LIGNE DE JOURNAL QUI PRECEDE LA PRECEDENTE, et le dictionnaire ne
    # l'avait pas. Elle porte « etat="erreur" » elle aussi : elle n'est
    # aujourd'hui jamais la DERNIERE — echouer() en ecrit une apres —, mais
    # c'est un fait de l'ordre de deux appels, pas une regle. Le jour ou
    # quelqu'un deplace le echouer(), une phrase francaise revient a l'ecran
    # d'un lecteur anglais sans qu'une ligne n'ait l'air fausse.
    "panne.conversation_disparue": {
        "fr": "la conversation de cette demande a disparu pendant l'attente — "
              "elle est abandonnee",
        "en": "the conversation this request belonged to disappeared while "
              "waiting — it is abandoned"},
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

    # LES TROIS AUTRES ARGUMENTS DE echouer(), releves sur le code le
    # 2 septembre 2026 au soir. Le dictionnaire n'en portait que DEUX sur cinq,
    # et rien ne le disait : les trois manquantes seraient parties a l'ecran en
    # francais, sous « ERREUR : » traduit — une demi-phrase anglaise, ce qui se
    # remarque encore moins qu'une phrase entierement francaise. Le compte des
    # sites d'appel est desormais mesure dans banc_traductions.py, pour que la
    # sixieme ne s'ajoute pas en silence.
    "panne.machine_en_pause": {
        "fr": "{machines} pourrait faire ce travail, mais elle est en pause "
              "depuis plus de {minutes} minutes. Reactive-la dans /admin, ou "
              "demande quelque chose qu'une autre machine sait faire.",
        "en": "{machines} could do this work, but it has been paused for more "
              "than {minutes} minutes. Wake it up in /admin, or ask for "
              "something another machine can do."},
    "panne.delai_raccourci": {
        "fr": "le delai d'attente a ete raccourci dans /admin : ta demande a "
              "ete retiree de l'attente. Relance-la quand la machine sera la.",
        "en": "the waiting delay was shortened in /admin: your request was "
              "taken out of the queue. Send it again once the machine is back."},
    # « {heures} » est un entier deja arrondi au site d'appel : le studio compte
    # en heures des qu'il s'agit d'une demande armee, et c'est la seule unite ou
    # « 1 h » et « 20 h » se lisent pareil dans les deux langues.
    "panne.attente_expiree": {
        "fr": "{machines} n'est pas revenue en {heures} h : ta demande a ete "
              "retiree de l'attente. Relance-la quand la machine sera la.",
        "en": "{machines} did not come back within {heures} h: your request "
              "was taken out of the queue. Send it again once the machine is "
              "back."},

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

    # ══ LA PAGE ════════════════════════════════════════════════════════
    # LES ACCENTS SONT ICI, ET C'EST LA REGLE DU DEPOT — pas une entorse.
    # CONTRIBUTING.md interdit les accents dans les identifiants et les
    # commentaires, et les EXIGE partout ou ils sont la donnee : « les textes
    # affiches a l'utilisateur ». Les entrees « erreur. » et « panne. »
    # ci-dessus recopient serveur.py, qui n'en porte pas ; celles-ci
    # recopient web/index.html, qui en porte partout. Retirer un accent ici
    # ferait rougir banc_page.py, et c'est exactement ce qu'on lui demande.
    #
    # L'ESPACE AVANT « : » EST DANS LE TEXTE, PAS DANS LE CODE. Le francais
    # en met un, l'anglais pas. C'etait une des quatre choses que la page
    # figeait sur le francais (docs/plusieurs-langues.md) : recoller
    # « libelle » + « : » + valeur au site d'appel aurait mis l'espace
    # francais dans la phrase anglaise, sans qu'aucune ligne n'ait l'air
    # fausse. Chaque phrase est donc UNE entree, ponctuation comprise.
    #
    # CE QUI N'EST PAS ICI, ET NE PEUT PAS L'ETRE : ce que le serveur SERT a
    # la page — le titre d'un moteur, le libelle d'une modalite de nuage, le
    # nom d'une intention, le mot du devis (« 4 min »), la ligne de journal,
    # le murmure deja ecrit dans la conversation. Ce sont des donnees, pas
    # des etiquettes, et docs/plusieurs-langues.md tranche le journal
    # separement. La page les pose telles quelles.

    # ── l'entete ────────────────────────────────────────────────────
    "page.tiroir.aria": {
        "fr": "Afficher les conversations",
        "en": "Show conversations"},
    "page.moteurs.connexion": {
        "fr": "connexion…",
        "en": "connecting…"},
    "page.moteurs.prets": {
        "fr": "moteurs prêts",
        "en": "engines ready"},
    "page.serveur.injoignable": {
        "fr": "serveur injoignable",
        "en": "server unreachable"},
    # UNE SEULE CLE POUR LE BOUTON ET POUR LE TITRE DU PANNEAU. Le mot etait
    # ecrit deux fois dans la page — « médiathèque » en haut a droite, et
    # « médiathèque » en tete du panneau qu'il ouvre. Deux textes pour une
    # chose se reformulent separement a la premiere retouche.
    "page.media.nom": {
        "fr": "médiathèque",
        "en": "library"},
    "page.media.ouvrir.title": {
        "fr": "tout ce que tu as produit",
        "en": "everything you have made"},
    "page.admin": {
        "fr": "admin",
        "en": "admin"},
    "page.admin.title": {
        "fr": "administration : machines, comptes, clés",
        "en": "administration: machines, accounts, keys"},
    "page.source": {
        "fr": "source",
        "en": "source"},
    "page.source.title": {
        "fr": "ComfyStudio est sous licence AGPL-3.0 : le code source vous "
              "est dû, le voici",
        "en": "ComfyStudio is licensed under AGPL-3.0: the source code is "
              "owed to you, here it is"},

    # ── la mediatheque ──────────────────────────────────────────────
    "page.fermer.aria": {
        "fr": "fermer",
        "en": "close"},
    "page.media.chercher": {
        "fr": "chercher dans la demande, le prompt, le nom du fichier",
        "en": "search the request, the prompt, the file name"},
    "page.media.tri.aria": {
        "fr": "Trier",
        "en": "Sort"},
    "page.media.tri.recent": {
        "fr": "plus récent d'abord",
        "en": "newest first"},
    "page.media.tri.ancien": {
        "fr": "plus ancien d'abord",
        "en": "oldest first"},
    "page.media.tri.demande": {
        "fr": "demande (A→Z)",
        "en": "request (A→Z)"},
    "page.media.tri.long": {
        "fr": "le plus long d'abord",
        "en": "longest first"},
    "page.media.soin.aria": {
        "fr": "Brouillon ou fini",
        "en": "Draft or finished"},
    "page.media.soin.tout": {
        "fr": "brouillons et finies",
        "en": "drafts and finished"},
    "page.media.soin.finies": {
        "fr": "images finies",
        "en": "finished images"},
    "page.media.soin.brouillons": {
        "fr": "brouillons",
        "en": "drafts"},
    "page.media.moteur.aria": {
        "fr": "Moteur",
        "en": "Engine"},
    "page.media.machine.aria": {
        "fr": "Machine",
        "en": "Machine"},
    "page.media.qui.aria": {
        "fr": "Propriétaire",
        "en": "Owner"},
    "page.media.qui": {
        "fr": "propriétaire",
        "en": "owner"},
    "page.media.famille.image": {
        "fr": "images",
        "en": "images"},
    "page.media.famille.video": {
        "fr": "vidéos",
        "en": "videos"},
    "page.media.famille.audio": {
        "fr": "musiques",
        "en": "music"},
    "page.media.famille.objet3d": {
        "fr": "objets 3D",
        "en": "3D objects"},
    "page.media.indisponible": {
        "fr": "médiathèque indisponible : {quoi}",
        "en": "library unavailable: {quoi}"},
    "page.media.tous_moteurs": {
        "fr": "tous les moteurs",
        "en": "all engines"},
    "page.media.toutes_machines": {
        "fr": "toutes les machines",
        "en": "all machines"},
    "page.media.tout_le_monde": {
        "fr": "tout le monde",
        "en": "everyone"},
    "page.media.vue_admin": {
        "fr": "vue administrateur — tout ce que ce studio a produit",
        "en": "administrator view — everything this studio has made"},
    "page.media.sur": {
        "fr": "{n} sur {total}",
        "en": "{n} of {total}"},
    "page.media.vide": {
        "fr": "rien de ce type pour l'instant",
        "en": "nothing of this kind yet"},
    "page.media.retenue": {
        "fr": "✓ retenue",
        "en": "✓ chosen"},
    "page.media.retenue.court": {
        "fr": "retenue",
        "en": "chosen"},
    "page.media.prompt": {
        "fr": "prompt envoyé",
        "en": "prompt sent"},
    "page.media.rafraichir": {
        "fr": "c'est fait, mais la grille n'a pas pu se rafraîchir : {quoi}",
        "en": "done, but the grid could not refresh: {quoi}"},
    "page.reprendre": {
        "fr": "reprendre",
        "en": "reuse"},
    "page.reprendre.title": {
        "fr": "joindre ce fichier pour le retravailler",
        "en": "attach this file to work on it again"},
    "page.reprise.impossible": {
        "fr": "reprise impossible",
        "en": "cannot reuse this file"},

    # ── la barre laterale ───────────────────────────────────────────
    "page.conv.neuve": {
        "fr": "+ nouvelle conversation",
        "en": "+ new conversation"},
    "page.conv.jeter": {
        "fr": "Supprimer",
        "en": "Delete"},
    "page.conv.indisponible": {
        "fr": "liste indisponible",
        "en": "list unavailable"},
    "page.moteur.attente": {
        "fr": "ComfyUI…",
        "en": "ComfyUI…"},
    "page.comfy.demarrer": {
        "fr": "démarrer",
        "en": "start"},
    "page.comfy.arreter": {
        "fr": "arrêter",
        "en": "stop"},

    # ── la saisie ───────────────────────────────────────────────────
    "page.saisie.aria": {
        "fr": "Décris ce que tu veux",
        "en": "Describe what you want"},
    "page.saisie.exemple": {
        "fr": "un renard dans les hautes herbes au coucher du soleil…",
        "en": "a fox in the tall grass at sunset…"},
    "page.brouillon.title": {
        "fr": "Un rendu au quart des étapes : quelques secondes au lieu de "
              "quelques minutes. De quoi juger le prompt, le moteur et "
              "l'ambiance. Attention : la version soignée traitera le même "
              "sujet mais n'aura PAS le même cadrage — le nombre d'étapes "
              "change le calcul.",
        "en": "A render at a quarter of the steps: seconds instead of "
              "minutes. Enough to judge the prompt, the engine and the mood. "
              "Careful: the clean version will treat the same subject but "
              "will NOT have the same framing — the number of steps changes "
              "the computation."},
    "page.brouillon.aria": {
        "fr": "Brouillon",
        "en": "Draft"},
    "page.generer.title": {
        "fr": "Générer (Ctrl+Entrée)",
        "en": "Generate (Ctrl+Enter)"},
    "page.generer.aria": {
        "fr": "Générer",
        "en": "Generate"},
    "page.joindre": {
        "fr": "joindre un fichier",
        "en": "attach a file"},
    "page.joindre.echec": {
        "fr": "Fichier non joint : {quoi}",
        "en": "File not attached: {quoi}"},
    "page.televerser.echec": {
        "fr": "échec du téléversement",
        "en": "upload failed"},
    "page.apercu.alt": {
        "fr": "aperçu du fichier joint",
        "en": "preview of the attached file"},
    "page.reglages": {
        "fr": "réglages",
        "en": "settings"},
    # « retirer » ETAIT ECRIT TROIS FOIS : sous la piece jointe, dans le
    # panneau de file, et sur la bulle d'une demande armee. Trois textes pour
    # un geste divergent a la premiere retouche, et deux d'entre eux se
    # seraient traduits sans le troisieme.
    "page.retirer": {
        "fr": "retirer",
        "en": "remove"},
    "page.interrompre": {
        "fr": "interrompre",
        "en": "interrupt"},
    "page.annuler": {
        "fr": "annuler",
        "en": "cancel"},
    "page.envoyer": {
        "fr": "envoyer",
        "en": "send"},
    "page.envoi": {
        "fr": "envoi…",
        "en": "sending…"},

    # ── les menus de reglage ────────────────────────────────────────
    "page.moteur": {
        "fr": "moteur",
        "en": "engine"},
    "page.machine": {
        "fr": "machine",
        "en": "machine"},
    "page.forcer.aria": {
        "fr": "Forcer un moteur",
        "en": "Force an engine"},
    "page.forcer.auto": {
        "fr": "moteur : automatique",
        "en": "engine: automatic"},
    "page.machine.aria": {
        "fr": "Machine",
        "en": "Machine"},
    "page.machine.auto": {
        "fr": "machine : automatique",
        "en": "machine: automatic"},
    # « Go » N'EST PAS UNE UNITE INTERNATIONALE, c'est un mot francais :
    # gigaoctet. L'anglais ecrit « GB ». Les trois autres unites de la page —
    # min, h, s — s'ecrivent pareil dans les deux langues, et sont ici quand
    # meme pour que la quatrieme ne soit pas seule a passer par le
    # dictionnaire : une regle qui ne vaut qu'une fois se defait sans bruit.
    "page.machine.vram": {
        "fr": "{vram} Go",
        "en": "{vram} GB"},
    "page.machine.muette": {
        "fr": "(ne répond pas)",
        "en": "(not answering)"},
    "page.moteur.a_telecharger": {
        "fr": "(à télécharger)",
        "en": "(to download)"},
    "page.priorite.aria": {
        "fr": "Priorité",
        "en": "Priority"},
    "page.priorite.auto": {
        "fr": "priorité : équilibre",
        "en": "priority: balanced"},
    "page.priorite.rapide": {
        "fr": "rapide — moins d'étapes",
        "en": "fast — fewer steps"},
    "page.priorite.rapide.court": {
        "fr": "rapide",
        "en": "fast"},
    "page.priorite.soigne": {
        "fr": "soigné — plus d'étapes",
        "en": "clean — more steps"},
    "page.priorite.soigne.court": {
        "fr": "soigné",
        "en": "clean"},
    "page.taille.aria": {
        "fr": "Résolution",
        "en": "Resolution"},
    "page.taille.auto": {
        "fr": "taille : automatique",
        "en": "size: automatic"},
    # LE CHIFFRE EST DANS L'ENTREE, ET NON RECOLLE AU SITE D'APPEL. Une
    # <option> ecrite dans le HTML n'a pas de place ou poser une valeur : lui
    # en donner une demanderait un second mecanisme, pour huit lignes qui ne
    # changent jamais. Le « × » est le meme signe dans les deux langues.
    "page.taille.1920x1080": {
        "fr": "1920 × 1080 — paysage", "en": "1920 × 1080 — landscape"},
    "page.taille.1600x900": {
        "fr": "1600 × 900 — paysage", "en": "1600 × 900 — landscape"},
    "page.taille.1280x720": {
        "fr": "1280 × 720 — paysage", "en": "1280 × 720 — landscape"},
    "page.taille.1216x832": {
        "fr": "1216 × 832 — défaut", "en": "1216 × 832 — default"},
    "page.taille.1024x1024": {
        "fr": "1024 × 1024 — carré", "en": "1024 × 1024 — square"},
    "page.taille.832x1216": {
        "fr": "832 × 1216 — portrait", "en": "832 × 1216 — portrait"},
    "page.taille.1080x1350": {
        "fr": "1080 × 1350 — portrait", "en": "1080 × 1350 — portrait"},
    "page.taille.768x1344": {
        "fr": "768 × 1344 — portrait haut", "en": "768 × 1344 — tall portrait"},
    "page.taille.inerte": {
        "fr": "sans effet sur ce moteur : la taille vient de la source ou du "
              "format",
        "en": "no effect on this engine: the size comes from the source or "
              "the format"},
    "page.variantes.aria": {
        "fr": "Nombre de variantes",
        "en": "Number of variants"},
    "page.variantes.une": {
        "fr": "variantes : une seule",
        "en": "variants: just one"},
    "page.variantes.2": {
        "fr": "2 variantes — même prompt, autre graine",
        "en": "2 variants — same prompt, different seed"},
    "page.variantes.2.court": {
        "fr": "2 variantes",
        "en": "2 variants"},
    "page.variantes.3": {
        "fr": "3 variantes",
        "en": "3 variants"},
    "page.variantes.4": {
        "fr": "4 variantes",
        "en": "4 variants"},
    "page.actifs.oter": {
        "fr": "cliquer pour revenir à l'automatique",
        "en": "click to go back to automatic"},

    # ── le menu de langue ───────────────────────────────────────────
    # LES NOMS DE LANGUE NE SE TRADUISENT PAS, ILS SE LISENT. « French » dans
    # une interface anglaise est utile a l'anglophone ; « français » est utile
    # a CELUI QUI CHERCHE LE FRANCAIS, et c'est lui qui ouvre ce menu-la —
    # quelqu'un qui ne sait pas lire la page ou il se trouve. Chaque langue
    # s'ecrit donc dans la sienne, et identiquement dans toutes les colonnes.
    "page.langue.aria": {
        "fr": "Langue",
        "en": "Language"},
    "page.langue.fr": {
        "fr": "français",
        "en": "français"},
    "page.langue.en": {
        "fr": "English",
        "en": "English"},

    # ── le fil ──────────────────────────────────────────────────────
    "page.vide.titre": {
        "fr": "Dis ce que tu veux voir.",
        "en": "Say what you want to see."},
    "page.vide.texte": {
        "fr": "Une image, une vidéo, une musique, une retouche. Le moteur est "
              "choisi pour toi, et la conversation garde le fil : « la même "
              "mais en hiver » reprend ce qui précède.",
        "en": "An image, a video, a piece of music, a retouch. The engine is "
              "chosen for you, and the conversation keeps the thread: “the "
              "same but in winter” picks up what came before."},
    "page.telecharger": {
        "fr": "télécharger",
        "en": "download"},
    "page.telecharger.fichier": {
        "fr": "télécharger {nom}",
        "en": "download {nom}"},
    "page.plein_ecran": {
        "fr": "plein écran",
        "en": "full screen"},
    "page.echec.defaut": {
        "fr": "la génération a échoué",
        "en": "the render failed"},
    "page.relancer": {
        "fr": "relancer",
        "en": "send again"},
    "page.relancer.title": {
        "fr": "renvoyer exactement la même demande",
        "en": "send exactly the same request again"},
    "page.brouillon": {
        "fr": "brouillon",
        "en": "draft"},

    # ── les etiquettes d'etat ───────────────────────────────────────
    # CE SONT DES ETIQUETTES, ET LEURS CLES SONT DES VALEURS DE PROTOCOLE.
    # « en cours », « fini », « erreur » voyagent jusqu'au serveur et sont
    # ECRITES dans les conversations deja enregistrees : on ne les traduit
    # pas, on les separe. La page tient les valeurs dans ETAT et les
    # etiquettes ici, et banc_page.py exige que plus aucune comparaison
    # « .etat === "…" » ne porte un litteral (docs/plusieurs-langues.md,
    # quatrieme chantier).
    "page.etat.cours": {
        "fr": "en cours",
        "en": "running"},
    "page.etat.fini": {
        "fr": "terminé",
        "en": "finished"},
    "page.etat.echec": {
        "fr": "échec",
        "en": "failed"},
    "page.etat.question": {
        "fr": "précision demandée",
        "en": "question asked"},
    "page.etat.question.file": {
        "fr": "en attente de précision",
        "en": "waiting for an answer"},
    "page.etat.attente": {
        "fr": "en attente",
        "en": "waiting"},
    "page.etat.attente_carte": {
        "fr": "attend une carte",
        "en": "waiting for a card"},
    "page.etat.attente_machine": {
        "fr": "attend une machine en pause",
        "en": "waiting for a paused machine"},

    # ── le depliant des details ─────────────────────────────────────
    "page.detail.titre": {
        "fr": "détails",
        "en": "details"},
    "page.detail.reglages": {
        "fr": "réglages : {quoi}",
        "en": "settings: {quoi}"},
    "page.detail.choix": {
        "fr": "choix : {quoi}",
        "en": "choice: {quoi}"},
    "page.detail.rendu": {
        "fr": "rendu : {quoi}",
        "en": "render: {quoi}"},
    "page.detail.prompt": {
        "fr": "prompt envoyé :\n{quoi}",
        "en": "prompt sent:\n{quoi}"},
    "page.detail.negatif": {
        "fr": "\n\nécarté : {quoi}",
        "en": "\n\nexcluded: {quoi}"},
    "page.detail.paroles": {
        "fr": "paroles :\n{quoi}",
        "en": "lyrics:\n{quoi}"},
    "page.detail.fichiers": {
        "fr": "fichiers :\n{quoi}",
        "en": "files:\n{quoi}"},
    "page.detail.deroule": {
        "fr": "déroulé :\n{quoi}",
        "en": "steps:\n{quoi}"},

    # ── passer au propre ────────────────────────────────────────────
    "page.au_propre.bouton": {
        "fr": "refaire en soigné",
        "en": "redo cleanly"},
    "page.au_propre.title": {
        "fr": "Reprend le même prompt, le même moteur et la même taille, avec "
              "toutes les étapes. Le sujet et le style seront les mêmes ; le "
              "cadrage, non.",
        "en": "Reuses the same prompt, the same engine and the same size, "
              "with all the steps. The subject and the style will be the "
              "same; the framing will not."},
    "page.au_propre.fait": {
        "fr": "refait en soigné",
        "en": "redone cleanly"},
    "page.au_propre.deja": {
        "fr": "déjà refait en soigné",
        "en": "already redone cleanly"},
    "page.refus.reprise": {
        "fr": "le serveur a refusé la reprise",
        "en": "the server refused the redo"},
    # « le serveur a refusé » ETAIT ECRIT TROIS FOIS — la variante du fil,
    # celle de la mediatheque, et « refaire sur la grosse carte ».
    "page.refus.simple": {
        "fr": "le serveur a refusé",
        "en": "the server refused"},
    "page.refus.demande": {
        "fr": "le serveur a refusé la demande",
        "en": "the server refused the request"},
    "page.impossible": {
        "fr": "impossible : {quoi}",
        "en": "not possible: {quoi}"},

    # ── designer une variante ───────────────────────────────────────
    "page.variante.rang": {
        "fr": "variante {rang} sur {sur}",
        "en": "variant {rang} of {sur}"},
    "page.variante.retenue": {
        "fr": "✓ on repart de celle-ci",
        "en": "✓ we start again from this one"},
    # ECRITE DEUX FOIS, ELLE ET SON INFOBULLE DE TROIS LIGNES : une fois sous
    # la bulle du fil, une fois sous la vignette de la mediatheque. Le meme
    # geste, le meme mot, et deux textes a maintenir.
    "page.variante.repartir": {
        "fr": "repartir de celle-ci",
        "en": "start again from this one"},
    "page.variante.repartir.title": {
        "fr": "« agrandis-la », « rends-la fluide », « le même personnage » "
              "viseront cette image-là. Rien n'est supprimé : les autres "
              "variantes restent.",
        "en": "“upscale it”, “make it smooth”, “the same character” will aim "
              "at that image. Nothing is deleted: the other variants stay."},

    # ── l'avis, et le second geste ──────────────────────────────────
    "page.avis.haut": {
        "fr": "bonne réponse",
        "en": "good answer"},
    "page.avis.bas": {
        "fr": "à retravailler",
        "en": "needs work"},
    "page.avis.merci": {
        "fr": "noté, merci",
        "en": "noted, thanks"},
    "page.avis.note": {
        "fr": "noté",
        "en": "noted"},
    "page.avis.rate": {
        "fr": "avis non enregistré : {quoi}",
        "en": "rating not saved: {quoi}"},
    "page.avis.champ": {
        "fr": "ce qui n'allait pas (facultatif)",
        "en": "what went wrong (optional)"},
    # L'ESPACE INSECABLE AVANT « : » EST DANS LA DONNEE. Le francais en met
    # un, l'anglais aucun — et la page l'ecrivait « &nbsp; » dans du HTML
    # construit, c'est-a-dire au site d'appel, ou aucune langue ne peut
    # l'enlever.
    "page.avis.plutot": {
        "fr": "c’était plutôt :",
        "en": "it was rather:"},
    "page.avis.note_intention": {
        "fr": "✓ noté — {titre}",
        "en": "✓ noted — {titre}"},
    "page.refaire.bouton": {
        "fr": "refaire sur la grosse carte",
        "en": "redo on the big card"},
    "page.refaire.title": {
        "fr": "Même prompt, même moteur, même taille, mais sur la carte la "
              "plus grande — en l'attendant s'il le faut. Une autre graine, "
              "donc un autre tirage : le studio ne sait pas améliorer, il "
              "sait recommencer avec plus de carte.",
        "en": "Same prompt, same engine, same size, but on the largest card — "
              "waiting for it if need be. A different seed, so a different "
              "draw: the studio does not know how to improve, it knows how to "
              "start over with more card."},
    "page.refaire.fait": {
        "fr": "c'est reparti sur la grosse carte",
        "en": "off again on the big card"},
    "page.refaire.impossible": {
        "fr": "impossible de refaire : {quoi}",
        "en": "cannot redo: {quoi}"},

    # ── la precision demandee ───────────────────────────────────────
    "page.question.titre": {
        "fr": "Avant de lancer, j'ai besoin de savoir :",
        "en": "Before starting, I need to know:"},
    "page.question.champ": {
        "fr": "ta réponse…",
        "en": "your answer…"},
    "page.question.aria": {
        "fr": "Réponse à la précision demandée",
        "en": "Answer to the question asked"},
    "page.question.bouton": {
        "fr": "répondre",
        "en": "answer"},

    # ── les comptes ─────────────────────────────────────────────────
    "page.entree.invite": {
        "fr": "connecte-toi pour commencer…",
        "en": "sign in to start…"},
    "page.compte.sortir": {
        "fr": "sortir",
        "en": "sign out"},
    "page.compte.entrer": {
        "fr": "se connecter",
        "en": "sign in"},
    "page.entree.titre": {
        "fr": "Se connecter",
        "en": "Sign in"},
    "page.entree.nom": {
        "fr": "nom",
        "en": "name"},
    "page.entree.mdp": {
        "fr": "mot de passe",
        "en": "password"},
    "page.entree.valider": {
        "fr": "entrer",
        "en": "enter"},
    "page.entree.refus": {
        "fr": "connexion refusée",
        "en": "sign-in refused"},
    "page.entree.reprises": {
        "fr": ["{n} conversation de ce navigateur a été rattachée à ton "
               "compte.",
               "{n} conversations de ce navigateur ont été rattachées à ton "
               "compte."],
        "en": ["{n} conversation from this browser was attached to your "
               "account.",
               "{n} conversations from this browser were attached to your "
               "account."]},

    # ── le second facteur ───────────────────────────────────────────
    # PAS DE QR CODE, ET C'EST ECRIT DANS CES PHRASES. Le dessiner demanderait
    # une bibliotheque, et la page n'a aucune dependance — c'est une regle du
    # depot, pas une paresse. Restent les deux formes qu'une application sait
    # lire sans appareil photo : le secret recopie a la main, et le lien
    # « otpauth:// » que le telephone ouvre directement. Les textes disent donc
    # « recopie » et « ouvre », jamais « scanne ».
    "page.mfa.bouton": {
        "fr": "second facteur",
        "en": "second factor"},
    "page.mfa.titre": {
        "fr": "Second facteur",
        "en": "Second factor"},
    "page.mfa.pourquoi": {
        "fr": "Un code à six chiffres en plus du mot de passe, calculé hors "
              "ligne par ton application d'authentification.",
        "en": "A six-digit code on top of the password, computed offline by "
              "your authenticator app."},
    "page.mfa.preparer": {
        "fr": "commencer",
        "en": "start"},
    "page.mfa.recopie": {
        "fr": "Recopie ce secret dans ton application d'authentification. Les "
              "espaces sont là pour la lecture : ils ne comptent pas.",
        "en": "Copy this secret into your authenticator app. The spaces are "
              "there to make it readable: they do not count."},
    "page.mfa.lien": {
        "fr": "ou ouvrir dans l'application",
        "en": "or open in the app"},
    "page.mfa.code": {
        "fr": "code à six chiffres",
        "en": "six-digit code"},
    "page.mfa.confirmer": {
        "fr": "confirmer",
        "en": "confirm"},
    "page.mfa.arme": {
        "fr": "Le second facteur est armé.",
        "en": "The second factor is armed."},
    "page.mfa.retire": {
        "fr": "Le second facteur est désarmé, et son secret effacé.",
        "en": "The second factor is disarmed, and its secret erased."},
    "page.mfa.secours.titre": {
        "fr": "Tes codes de secours",
        "en": "Your backup codes"},
    # CETTE PHRASE-LA EST LA PLUS IMPORTANTE DE L'ECRAN, et elle est ecrite en
    # toutes lettres parce qu'un utilisateur qui ferme l'onglet en pensant les
    # retrouver dans ses réglages ne les retrouvera pas : seule leur empreinte
    # est gardée, comme un mot de passe.
    "page.mfa.secours.unique": {
        "fr": "Ils ne s'affichent qu'UNE fois. Note-les maintenant : ils ne "
              "sont pas conservés en clair, et personne ne peut te les "
              "redonner — pas même l'administrateur.",
        "en": "They are shown ONCE. Write them down now: they are not kept in "
              "clear, and nobody can hand them back — not even the "
              "administrator."},
    "page.mfa.secours.neufs": {
        "fr": "Voici un jeu neuf. Les anciens codes ne valent plus rien.",
        "en": "Here is a fresh set. The old codes are worthless now."},
    "page.mfa.secours.aussi": {
        "fr": "Un code de secours convient aussi.",
        "en": "A backup code works too."},
    # L'ATTENTE EST ANNONCEE PARCE QU'ELLE SE DEDUIT MAL. Le code qui vient de
    # CONFIRMER l'enrôlement est déjà consommé — sans cela, le rejeu rentrerait
    # par la porte de l'enrôlement — et quelqu'un qui le retape aussitôt, en le
    # lisant encore sur son écran, se voit refusé et croit avoir raté son
    # enrôlement. Trente secondes au plus, et c'est le pas de la RFC 6238.
    "page.mfa.attente": {
        "fr": "Le code que tu viens de taper est déjà consommé : attends le "
              "suivant, trente secondes au plus, avant de te reconnecter.",
        "en": "The code you just typed is already spent: wait for the next "
              "one, thirty seconds at most, before signing in again."},
    "page.mfa.attente_en_cours": {
        "fr": "Un enrôlement commencé n'a jamais été confirmé. Recommencer "
              "tire un secret neuf : efface l'ancienne entrée de ton "
              "application.",
        "en": "An enrolment was started and never confirmed. Starting again "
              "draws a fresh secret: delete the old entry from your app."},
    "page.mfa.fini": {
        "fr": "j'ai noté",
        "en": "noted"},
    # « SUR {total} » ET PAS SEULEMENT LE RESTE. « 2 codes de secours » ne dit
    # pas s'il en reste beaucoup ou presque plus ; « 2 sur 10 » le dit d'un
    # coup d'oeil, et c'est le seul signal qui pousse a en regénérer un jeu
    # avant d'être à court — être à court, c'est perdre le compte.
    "page.mfa.etat.arme": {
        "fr": ["armé · {n} code de secours restant sur {total}",
               "armé · {n} codes de secours restants sur {total}"],
        "en": ["armed · {n} backup code left out of {total}",
               "armed · {n} backup codes left out of {total}"]},
    "page.mfa.etat.absent": {
        "fr": "pas encore armé",
        "en": "not armed yet"},
    "page.mfa.regenerer": {
        "fr": "de nouveaux codes de secours",
        "en": "new backup codes"},
    "page.mfa.retirer": {
        "fr": "désarmer",
        "en": "disarm"},
    "page.mfa.retirer.sur": {
        "fr": "Désarmer le second facteur ? Son secret est effacé : il faudra "
              "recommencer l'enrôlement pour le remettre.",
        "en": "Disarm the second factor? Its secret is erased: you will have "
              "to enrol again to put it back."},

    # ── les interrupteurs de nuage ──────────────────────────────────
    "page.nuage.plafond.title": {
        "fr": "{libelle} : plafond du mois atteint ({faits} appels distants "
              "sur {limite}). Le studio reste sur cette machine jusqu'au mois "
              "prochain ; le plafond se règle dans /admin.",
        "en": "{libelle}: monthly cap reached ({faits} remote calls out of "
              "{limite}). The studio stays on this machine until next month; "
              "the cap is set in /admin."},
    "page.nuage.title": {
        "fr": "{libelle} : {ou}",
        "en": "{libelle}: {ou}"},
    "page.nuage.locale": {
        "fr": "cette machine",
        "en": "this machine"},
    "page.nuage.basculer": {
        "fr": "(cliquer pour {quoi})",
        "en": "(click to {quoi})"},
    "page.nuage.revenir": {
        "fr": "revenir en local",
        "en": "go back to local"},
    "page.nuage.passer": {
        "fr": "passer par {titre}",
        "en": "go through {titre}"},
    "page.nuage.atteint": {
        "fr": "plafond atteint · {faits}/{limite}",
        "en": "cap reached · {faits}/{limite}"},
    "page.nuage.compte": {
        "fr": "nuage {faits}/{limite}",
        "en": "cloud {faits}/{limite}"},
    # « appel(s) distant(s) » : la page ECRIVAIT les parentheses, faute de
    # savoir accorder. C'est le contournement que PLURIELS existe pour
    # supprimer — il ne se lit bien dans aucune langue, et n'existe pas dans
    # toutes.
    "page.nuage.mention.title": {
        "fr": ["{faits} appel distant ce mois-ci ({mois}) sur {limite} pour "
               "le compte {compte}.",
               "{faits} appels distants ce mois-ci ({mois}) sur {limite} pour "
               "le compte {compte}."],
        "en": ["{faits} remote call this month ({mois}) out of {limite} for "
               "the account {compte}.",
               "{faits} remote calls this month ({mois}) out of {limite} for "
               "the account {compte}."]},
    "page.nuage.mention.suite": {
        "fr": "Les demandes restent sur cette machine jusqu'au mois prochain.",
        "en": "Requests stay on this machine until next month."},

    # ── la file d'attente ───────────────────────────────────────────
    "page.file.titre": {
        "fr": "file d'attente",
        "en": "queue"},
    "page.file.rien": {
        "fr": "rien en cours",
        "en": "nothing running"},
    "page.file.vue_admin": {
        "fr": "vue administrateur",
        "en": "administrator view"},
    "page.file.compteur": {
        "fr": "{n} en file",
        "en": "{n} queued"},
    "page.file.a_moi": {
        "fr": "{n} à toi",
        "en": "{n} yours"},
    "page.file.position": {
        "fr": "en file — {n} devant",
        "en": "queued — {n} ahead"},
    "page.file.armees.title": {
        "fr": ["{n} demande attend le retour d'une machine en pause et "
               "repartira toute seule. Ouvrir la file pour la retirer.",
               "{n} demandes attendent le retour d'une machine en pause et "
               "repartiront toutes seules. Ouvrir la file pour les retirer."],
        "en": ["{n} request is waiting for a paused machine to come back and "
               "will start again on its own. Open the queue to remove it.",
               "{n} requests are waiting for a paused machine to come back "
               "and will start again on their own. Open the queue to remove "
               "them."]},
    "page.file.reste": {
        "fr": "encore {duree}",
        "en": "{duree} left"},
    # L'ESPACE AVANT « % » SUIT LA MEME REGLE QUE CELUI D'AVANT « : » : le
    # francais en met un, l'anglais colle le signe au chiffre. Recoller
    # « {pct} » + « % » au site d'appel figeait la regle francaise dans du
    # code d'interface, comme le faisait le pluriel avant PLURIELS.
    "page.pourcent": {
        "fr": "{n} %",
        "en": "{n}%"},
    "page.duree.min": {
        "fr": "{n} min",
        "en": "{n} min"},
    "page.duree.h": {
        "fr": "{n} h",
        "en": "{n} h"},
    "page.duree.s": {
        "fr": "{n} s",
        "en": "{n} s"},

    # ── le suivi d'une demande ──────────────────────────────────────
    "page.retirer_armee.title": {
        "fr": "retirer cette demande de l'attente : elle ne repartira pas "
              "toute seule au retour de la machine",
        "en": "take this request out of the queue: it will not start again on "
              "its own when the machine comes back"},
    "page.tache.inconnue": {
        "fr": "tâche inconnue — le serveur a-t-il redémarré ?",
        "en": "unknown task — did the server restart?"},
    "page.reponse.inattendue": {
        "fr": "réponse inattendue du serveur",
        "en": "unexpected answer from the server"},
    "page.armee.attend": {
        "fr": "⏸ attend le retour d'une machine en pause",
        "en": "⏸ waiting for a paused machine to come back"},
    "page.armee.reste": {
        "fr": "repart toute seule, encore {duree}",
        "en": "starts again on its own, {duree} left"},
    "page.devis.title": {
        "fr": ["médiane de ton {mesures} rendu comparable : {mot}. Une "
               "indication, pas une promesse.",
               "médiane de tes {mesures} rendus comparables : {mot}. Une "
               "indication, pas une promesse."],
        "en": ["median of your {mesures} comparable render: {mot}. An "
               "indication, not a promise.",
               "median of your {mesures} comparable renders: {mot}. An "
               "indication, not a promise."]},
    "page.devis.title.court": {
        "fr": "d'après tes rendus précédents : {mot}",
        "en": "based on your previous renders: {mot}"},
    "page.devis.depasse": {
        "fr": "plus long que d’habitude",
        "en": "longer than usual"},
    "page.devis.estime": {
        "fr": "≈ {mot}",
        "en": "≈ {mot}"},
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


def rendre(marque, langue="fr"):
    """Une MARQUE de panne — {"cle": ..., "valeurs": {...}} — mise en phrase.

    C'EST LA SPECIFICATION DE CE QUE LA PAGE DEVRA FAIRE, et elle est ici pour
    que le banc puisse l'exercer sans navigateur. Le serveur pose la marque sur
    la tache (serveur.MARQUE_PANNE) et /api/etat la sert ; la page rend la meme
    chose, dans la langue de son lecteur, a partir des memes donnees.

    UNE VALEUR PEUT ETRE UNE MARQUE, et c'est le seul cas d'imbrication : le
    gabarit « ERREUR : {quoi} » de echouer() recoit au site d'appel une PHRASE
    du dictionnaire, pas une valeur calculee. Sans ce tour, l'anglophone
    lisait « ERROR: la machine n'est pas revenue a temps » — une demi-phrase
    traduite, qui se remarque moins qu'une phrase entierement francaise et
    trompe donc plus longtemps. Une seule profondeur suffit : aucun site
    d'appel n'en demande deux, et une recursion sans borne sur des donnees
    servies par HTTP est une porte qu'on n'ouvre pas sans raison.
    """
    if not isinstance(marque, dict) or not marque.get("cle"):
        return ""
    valeurs = {}
    for nom, v in (marque.get("valeurs") or {}).items():
        valeurs[nom] = (T(v["cle"], langue, **(v.get("valeurs") or {}))
                        if isinstance(v, dict) and v.get("cle") else v)
    return T(marque["cle"], langue, **valeurs)


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
