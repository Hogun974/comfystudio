#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les cles d'acces : ce qu'un programme presente pour agir au nom d'un compte.

CE QUE CE BANC GARDE, DANS L'ORDRE DES DEGATS :

  1. UNE CLE FAUSSE QUI PASSE. Tronquee, un caractere change, l'identifiant
     d'une cle avec le secret d'une autre, une cle revoquee, une cle d'un
     compte supprime : chacune ouvrirait le studio a qui ne devrait pas y
     entrer. reconnaitre() doit rendre None, et ne jamais lever.
  2. UNE CLE QUI SURVIT AU CHANGEMENT DE MOT DE PASSE. La generation du compte
     est ce qui ferme les sessions quand le proprietaire chasse un voleur ; une
     cle qui l'ignore est la porte de derriere qu'il n'a pas fermee.
  3. LA CLE OU SON SECRET SUR LE DISQUE, OU DANS UNE FICHE PUBLIQUE. Le fichier
     se sauvegarde, se copie, se lit par un administrateur : il ne doit porter
     que l'empreinte. Le secret de rappel, lui, est sur le disque (il faut le
     relire pour signer) mais ne sort jamais par liste() ni par une fiche.
  4. LA CLE D'UN AUTRE COUPEE. revoquer() avec un compte ne touche qu'a SES
     cles ; revoquer_compte() tue toutes celles du compte, et seulement elles.
  5. UN FICHIER ILLISIBLE ECRASE. Il porte les cles de tous les comptes : le
     reecrire vide au premier creer() les tuerait toutes, sans trace.
  6. UN LIEN SIGNE QU'ON PEUT ALTERER OU QUI N'EXPIRE PAS.
  7. LES BORNES : nom, nombre de cles, hotes de rappel, file, plafond du jour.
  8. LA DATE DE DERNIER USAGE, ecrite au plus une fois par dix minutes et par
     cle — sinon un n8n qui interroge chaque seconde reecrit le fichier chaque
     seconde.

    python banc_acces.py

Aucun reseau, aucun studio : ce banc n'importe qu'acces.py, qui n'importe que
la bibliotheque standard.

CE QU'IL NE VOIT PAS.

  - LE CHRONOMETRE. reconnaitre() calcule une empreinte meme pour un
    identifiant inconnu ; le banc verifie qu'elle est CALCULEE (il compte les
    appels), pas que les deux chemins durent le meme temps — une mesure de
    temps sur une machine partagee ne prouve rien en une seconde.
  - LE PERIMETRE. Qu'une cle ne vaille jamais administration, que « en_file »,
    « par_jour » et « nuage » soient appliques : c'est serveur.py qui le fait,
    et c'est son banc qui doit le voir.
  - LES RAPPELS. Que l'hote d'une URL de rappel soit compare a la liste
    declaree, et que la signature parte avec : rappels.py.
  - LA MORT D'UN LIEN AVEC SA CLE. lien_valide() ne connait que le secret ;
    c'est au studio de verifier que la cle existe encore.
  - L'ATOMICITE SOUS COUPURE. Le banc voit que l'ecriture passe par un .tmp
    remplace d'un coup ; il ne coupe pas le courant au milieu.
"""
import json
import os
import shutil
import sys
import tempfile
import time

# LA CONSOLE WINDOWS ECRIT EN cp1252, et ce banc n'importe pas serveur.py —
# c'est serveur.py qui reconfigure la sortie pour le reste du depot. Sans ces
# lignes, le banc meurt sur son propre affichage au premier titre de section,
# lance a la main depuis une console Windows (voir banc_mfa.py).
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import acces  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


def leve(fonction, *args, **kwargs):
    """Le message de l'ErreurAcces levee, ou None si rien n'a leve. Une autre
    exception remonte : elle dirait une panne, pas un refus explicable."""
    try:
        fonction(*args, **kwargs)
    except acces.ErreurAcces as e:
        return str(e) or "(sans message)"
    return None


def brut_du_disque(chemin):
    with open(chemin, encoding="utf-8") as f:
        return f.read()


# La generation des comptes du banc, comme comptes.py la tiendrait. Un compte
# absent rend None : il a ete supprime.
GENS = {"jordan": 0, "camille": 3}


def generation_de(compte):
    return GENS.get(compte)


T0 = 1_800_000_000.0
dossier = tempfile.mkdtemp(prefix="banc_acces_")
try:
    chemin = os.path.join(dossier, "_acces.json")
    a = acces.Acces(chemin)

    print("\n  ── la forme de la cle ──")
    r = a.creer("jordan", "n8n maison", 0, maintenant=T0)
    cle, secret = r["cle"], r["secret_rappel"]
    ident = r["fiche"]["id"]
    dit(cle.startswith(acces.PREFIXE) and acces.PREFIXE == "cs_",
        "la cle commence par « cs_ »", cle[:12] + "…")
    morceaux = cle.split("_", 2)
    dit(len(cle) == 3 + 8 + 1 + 43 and len(morceaux) == 3
        and len(morceaux[2]) == 43,
        "trois morceaux : cs, 8 hex, 43 caracteres de secret",
        f"{len(cle)} caracteres")
    dit(len(ident) == 8 and all(c in "0123456789abcdef" for c in ident)
        and morceaux[1] == ident,
        "l'identifiant public est fait de 8 hex minuscules, ceux de la cle",
        ident)
    dit(acces.identifiant_de(cle) == ident,
        "identifiant_de() relit cet identifiant dans la cle")

    # DEUX CENTS CLES, DEUX CENTS VALEURS. Dans un magasin a part : vingt cles
    # par compte, donc dix comptes.
    lot_chemin = os.path.join(dossier, "lot.json")
    lot = acces.Acces(lot_chemin)
    cles_lot = [lot.creer(f"c{i % 10}", f"cle {i}", 0)["cle"] for i in range(200)]
    dit(len(set(cles_lot)) == 200
        and len({acces.identifiant_de(c) for c in cles_lot}) == 200,
        "deux cents creations, deux cents cles et deux cents identifiants",
        f"{len(set(cles_lot))}/200")
    dit(all(acces.identifiant_de(c) for c in cles_lot),
        "et toutes ont la forme exacte", f"{len(cles_lot)} relues")

    print("\n  ── identifiant_de refuse une forme inexacte ──")
    secret_43 = morceaux[2]
    formes = [
        cle[:-1], cle + "x", cle + "\n", " " + cle,
        "cs_" + ident.upper() + "_" + secret_43,
        "CS_" + ident + "_" + secret_43,
        "cs_" + ident[:7] + "_" + secret_43,
        "cs_" + ident + "_" + secret_43[:40],
        "cs_" + ident + "-" + secret_43,
        "cs_" + ident + "_" + secret_43[:-1] + "=",
        "", None, 12, b"cs_", ["cs_"],
    ]
    mal = [repr(f)[:30] for f in formes if acces.identifiant_de(f) is not None]
    dit(not mal and len(formes) >= 10,
        "identifiant_de refuse une forme inexacte, sans lever",
        ", ".join(mal) or f"{len(formes)} formes fautives, toutes None")

    print("\n  ── reconnaitre ──")
    f = a.reconnaitre(cle, generation_de, maintenant=T0 + 1)
    dit(f is not None and f["id"] == ident and f["compte"] == "jordan",
        "la vraie cle rend sa fiche", str(f and f["nom"]))
    # « generation » n'est plus interdite ici : elle est publique depuis que
    # la page doit dire quelles cles se sont eteintes (voir les quatorze champs).
    dit(f is not None and "empreinte" not in f and "secret_rappel" not in f,
        "reconnaitre rend une fiche publique sans empreinte ni secret",
        ", ".join(sorted(f or {})))
    autre = a.creer("jordan", "agent du salon", 0, maintenant=T0 + 2)
    cle_b, ident_b = autre["cle"], autre["fiche"]["id"]
    change = cle[:-1] + ("A" if cle[-1] != "A" else "B")
    croisee = f"cs_{ident_b}_{secret_43}"
    fausses = [("tronquee", cle[:-1]), ("un caractere change", change),
               ("l'identifiant d'une autre cle avec ce secret", croisee),
               ("non-str", 12345), ("None", None), ("chaine vide", ""),
               ("des octets", cle.encode())]
    for quoi, fausse in fausses:
        try:
            rendu = a.reconnaitre(fausse, generation_de, maintenant=T0 + 3)
        except Exception as e:
            rendu = f"LEVE {type(e).__name__}"
        dit(rendu is None, f"une cle {quoi} ne passe pas", repr(rendu)[:40])
    dit(a.reconnaitre(cle_b, generation_de) is not None,
        "temoin : la seconde cle, elle, passe — le croisement n'est pas un "
        "faux negatif")

    # UN IDENTIFIANT INCONNU COUTE UNE EMPREINTE. On compte les appels a
    # empreinte_de() : rendre None avant de la calculer distinguerait au
    # chronometre « identifiant inconnu » de « secret faux ».
    vraie_empreinte = acces.empreinte_de
    appels = []

    def comptee(c):
        appels.append(c)
        return vraie_empreinte(c)

    acces.empreinte_de = comptee
    try:
        inconnue = "cs_" + ("0" * 8 if ident != "0" * 8 else "1" * 8) + "_" + secret_43
        rendu = a.reconnaitre(inconnue, generation_de)
        n_inconnu = len(appels)
        a.reconnaitre(change, generation_de)
        n_faux = len(appels) - n_inconnu
    finally:
        acces.empreinte_de = vraie_empreinte
    dit(rendu is None and n_inconnu == 1 and n_faux == 1,
        "un identifiant inconnu coute une empreinte comme un secret faux",
        f"inconnu : {n_inconnu} empreinte(s), secret faux : {n_faux}")

    print("\n  ── la generation du compte ──")
    c_cam = a.creer("Camille", "script", 3, maintenant=T0 + 4)
    dit(a.reconnaitre(c_cam["cle"], generation_de) is not None,
        "temoin : la cle de camille, nee a la generation 3, passe")
    GENS["camille"] = 4
    dit(a.reconnaitre(c_cam["cle"], generation_de) is None,
        "generation changee (mot de passe, second facteur) : la cle ne passe plus")
    GENS["camille"] = 3
    dit(a.reconnaitre(c_cam["cle"], generation_de) is not None,
        "temoin : revenue a 3, elle repasse — c'est bien la generation qui "
        "refusait")
    del GENS["camille"]
    dit(a.reconnaitre(c_cam["cle"], generation_de) is None,
        "compte disparu (generation None) : la cle ne passe plus")
    GENS["camille"] = 3

    def explose(_compte):
        raise RuntimeError("comptes.py en panne")
    try:
        rendu = a.reconnaitre(cle, explose)
    except Exception as e:
        rendu = f"LEVE {type(e).__name__}"
    dit(rendu is None, "une generation_de qui leve rend None, sans lever",
        repr(rendu))
    dit(c_cam["fiche"]["compte"] == "camille"
        and a.fiche(c_cam["fiche"]["id"])["compte"] == "camille",
        "le compte est garde en minuscules, comme comptes.py l'indexe",
        c_cam["fiche"]["compte"])
    dit(leve(a.creer, "jordan", "x", "0") is not None
        and leve(a.creer, "jordan", "x", True) is not None,
        "une generation qui n'est pas un entier est refusee")

    print("\n  ── ce qui est sur le disque ──")
    disque = brut_du_disque(chemin)
    cles_vues = [cle, cle_b, c_cam["cle"]]
    secrets_vus = [c.split("_", 2)[2] for c in cles_vues]
    fuites = [c[:12] for c in cles_vues + secrets_vus if c in disque]
    dit(not fuites and len(cles_vues) == 3 and len(disque) > 200,
        "la cle en clair n'est jamais sur disque, ni son secret de 43 caracteres",
        ", ".join(fuites) or f"{len(cles_vues)} cles cherchees dans "
        f"{len(disque)} octets")
    dit(acces.empreinte_de(cle) in disque,
        "temoin : son empreinte, elle, y est — on cherchait au bon endroit")
    dit(secret in disque,
        "le secret de rappel est sur le disque (il faut le relire pour signer)")
    publiques = a.liste() + [a.fiche(ident), r["fiche"], autre["fiche"]]
    texte_public = json.dumps(publiques, ensure_ascii=False)
    tous_secrets = [secret, autre["secret_rappel"], c_cam["secret_rappel"]]
    dit(not any(s in texte_public for s in tous_secrets)
        and not any(acces.empreinte_de(c) in texte_public for c in cles_vues)
        and not any("secret_rappel" in p or "empreinte" in p for p in publiques)
        and len(publiques) >= 5,
        "le secret de rappel n'est jamais dans une fiche publique ni dans liste()",
        f"{len(publiques)} fiches relues")
    dit(a.secret_rappel(ident) == secret and a.secret_rappel("zzzzzzzz") is None,
        "secret_rappel() le rend a qui doit signer, et rien pour un inconnu")
    # ONZE CHAMPS, dont « generation » : un entier, pas un secret, mais le seul
    # moyen pour la page de dire qu'une cle s'est eteinte avec le changement
    # de mot de passe au lieu de la montrer vivante.
    dit(set(r["fiche"]) == {"id", "compte", "nom", "apercu", "cree", "vu",
                            "nuage", "hotes", "en_file", "par_jour",
                            "generation", "expire", "ancienne_jusqu",
                            "operations"},
        "la fiche publique porte exactement les quatorze champs du contrat",
        ", ".join(sorted(r["fiche"])))
    dit(r["fiche"]["apercu"] == f"cs_{ident}_…",
        "l'apercu ne montre rien du secret", r["fiche"]["apercu"])
    noms = [x["nom"] for x in a.liste("jordan")]
    dit(noms == ["n8n maison", "agent du salon"],
        "liste(compte) rend ses cles, de la plus ancienne a la plus recente",
        ", ".join(noms))
    dit(len(a.liste()) == 3 and a.liste("JORDAN") == a.liste("jordan"),
        "liste() sans compte les rend toutes, et le compte se lit sans casse")

    print("\n  ── la persistance ──")
    neuve = acces.Acces(chemin)
    dit(neuve.reconnaitre(cle, generation_de) is not None
        and neuve.secret_rappel(ident) == secret,
        "une instance neuve relue du disque reconnait la cle et son secret")
    dit(not os.path.exists(chemin + ".tmp")
        and not [n for n in os.listdir(dossier) if n.endswith(".tmp")],
        "pas de .tmp qui traine apres sauver")
    vraie_replace = os.replace
    remplacements = []

    def note_replace(src, dst):
        remplacements.append((src, dst))
        return vraie_replace(src, dst)

    acces.os.replace = note_replace
    try:
        neuve.creer("jordan", "atomique", 0)
    finally:
        acces.os.replace = vraie_replace
    dit(remplacements == [(chemin + ".tmp", chemin)],
        "l'ecriture passe par un .tmp remplace d'un coup",
        repr([(os.path.basename(s), os.path.basename(d))
              for s, d in remplacements]))

    print("\n  ── revoquer ──")
    sacha = a.creer("sacha", "a sacha", 0)
    GENS["sacha"] = 0
    dit(a.revoquer(sacha["fiche"]["id"], compte="jordan") is False
        and a.reconnaitre(sacha["cle"], generation_de) is not None,
        "revoquer avec un autre compte ne touche pas la cle d'un autre")
    dit(a.revoquer(sacha["fiche"]["id"], compte="SACHA") is True
        and a.reconnaitre(sacha["cle"], generation_de) is None,
        "revoquer par son proprietaire la tue : une cle revoquee ne passe plus")
    dit(a.revoquer("zzzzzzzz") is False and a.revoquer(None) is False,
        "revoquer un inconnu rend False sans lever")
    dit(acces.Acces(chemin).fiche(sacha["fiche"]["id"]) is None,
        "et la revocation est ecrite sur le disque")

    print("\n  ── revoquer_compte ──")
    s2 = [a.creer("sacha", f"s{i}", 0)["cle"] for i in range(3)]
    avant_jordan = len(a.liste("jordan"))
    n = a.revoquer_compte("SACHA")
    dit(n == 3 and not a.liste("sacha")
        and all(a.reconnaitre(c, generation_de) is None for c in s2),
        "revoquer_compte tue toutes les cles du compte", f"{n} revoquee(s)")
    dit(len(a.liste("jordan")) == avant_jordan >= 2
        and a.reconnaitre(cle, generation_de) is not None,
        "et seulement les siennes", f"jordan garde {avant_jordan} cle(s)")
    dit(a.revoquer_compte("personne") == 0, "un compte sans cle : zero")

    print("\n  ── les bornes ──")
    b = acces.Acces(os.path.join(dossier, "bornes.json"))
    refus = {
        "nom vide": leve(b.creer, "jordan", "", 0),
        "nom fait d'espaces": leve(b.creer, "jordan", "   ", 0),
        "nom trop long": leve(b.creer, "jordan", "x" * (acces.NOM_MAX + 1), 0),
        "nom a saut de ligne": leve(b.creer, "jordan", "a\nb", 0),
        "compte vide": leve(b.creer, "", "x", 0),
        "en_file a zero": leve(b.creer, "jordan", "x", 0, en_file=0),
        "en_file au-dela": leve(b.creer, "jordan", "x", 0,
                                en_file=acces.EN_FILE_MAX + 1),
        "en_file non entier": leve(b.creer, "jordan", "x", 0, en_file="4"),
        "par_jour negatif": leve(b.creer, "jordan", "x", 0, par_jour=-1),
        "par_jour au-dela": leve(b.creer, "jordan", "x", 0,
                                 par_jour=acces.PAR_JOUR_MAX + 1),
        "trop d'hotes": leve(b.creer, "jordan", "x", 0,
                             hotes=[f"h{i}.maison" for i in
                                    range(acces.HOTES_MAX + 1)]),
        "hotes en chaine": leve(b.creer, "jordan", "x", 0, hotes="n8n.maison"),
        "hote invalide": leve(b.creer, "jordan", "x", 0,
                              hotes=["n8n.maison", "http://n8n.maison"]),
    }
    for quoi, message in refus.items():
        dit(message is not None, f"refuse : {quoi}", message or "accepte")
    dit(not b.fiches and not os.path.exists(b.chemin),
        "et aucun refus n'a laisse de cle derriere lui")
    dit(leve(b.creer, "jordan", "x" * acces.NOM_MAX, 0, hotes=[],
             en_file=acces.EN_FILE_MAX, par_jour=acces.PAR_JOUR_MAX) is None
        and leve(b.creer, "jordan", "y", 0, en_file=1, par_jour=0) is None,
        "temoin : les bornes elles-memes sont acceptees")
    pleine = acces.Acces(os.path.join(dossier, "pleine.json"))
    for i in range(acces.CLES_PAR_COMPTE):
        pleine.creer("jordan", f"cle {i}", 0)
    dit(len(pleine.liste("jordan")) == 20
        and leve(pleine.creer, "Jordan", "la 21e", 0) is not None,
        "la 21e cle d'un compte est refusee", f"{len(pleine.liste())} creees")
    dit(leve(pleine.creer, "camille", "la sienne", 3) is None,
        "temoin : un autre compte en cree encore")
    h = b.creer("jordan", "rappels", 0, nuage=True,
                hotes=["N8N.Maison", "n8n.maison", "172.20.1.50:5678",
                       "[0:0::1]:5678"])["fiche"]
    dit(h["hotes"] == ["n8n.maison", "172.20.1.50:5678", "[::1]:5678"]
        and h["nuage"] is True and h["en_file"] == acces.EN_FILE_DEFAUT == 4
        and h["par_jour"] == 0,
        "les hotes sont normalises et dedoublonnes, les defauts poses",
        ", ".join(h["hotes"]))

    print("\n  ── hote_valide, cas par cas ──")
    bons = {"n8n.maison": "n8n.maison", "N8N.Maison": "n8n.maison",
            "172.20.1.50:5678": "172.20.1.50:5678", "[::1]:5678": "[::1]:5678",
            "[::1]": "[::1]", "localhost:1": "localhost:1",
            "n8n_main:65535": "n8n_main:65535", "a" * 63: "a" * 63}
    for texte, attendu in bons.items():
        dit(acces.hote_valide(texte) == attendu, f"hote accepte : {texte[:20]}",
            repr(acces.hote_valide(texte)))
    mauvais = {
        "vide": "", "schema": "http://n8n.maison", "schema sans //": "http:n8n",
        "chemin": "n8n.maison/rappel", "barre seule": "/",
        "identifiants": "user@n8n.maison", "identifiants et mot de passe":
            "u:p@n8n.maison", "espace": "n8n maison",
        "espace en tete": " n8n.maison", "tabulation": "n8n.maison\t",
        "port zero": "n8n.maison:0", "port hors bornes": "n8n.maison:65536",
        "port vide": "n8n.maison:", "port non numerique": "n8n.maison:abc",
        "plus de 253 caracteres": ".".join(["a" * 50] * 5),
        "etiquette vide": "n8n..maison", "point final": "n8n.maison.",
        "IPv6 sans crochets": "::1", "IPv6 fausse": "[::g]",
        "requete": "n8n.maison?x=1", "non-ASCII": "n8n.maKison",
        "non-str": None,
    }
    for quoi, texte in mauvais.items():
        try:
            rendu = acces.hote_valide(texte)
        except Exception as e:
            rendu = f"LEVE {type(e).__name__}"
        dit(rendu is None, f"hote refuse : {quoi}", repr(rendu)[:40])
    dit(len(".".join(["a" * 50] * 5)) == 254
        and acces.hote_valide(".".join(["a" * 50] * 5)[:253]) is not None,
        "temoin : 253 caracteres passent, 254 non")

    print("\n  ── la date de dernier usage ──")
    v_chemin = os.path.join(dossier, "vu.json")
    v = acces.Acces(v_chemin)
    vc = v.creer("jordan", "vu", 0, maintenant=T0)
    vid = vc["fiche"]["id"]

    def vu_disque():
        return {x["id"]: x["vu"] for x in json.load(open(v_chemin,
                                                         encoding="utf-8"))}[vid]

    dit(vc["fiche"]["vu"] is None and vu_disque() is None,
        "une cle neuve n'a jamais servi")
    v.reconnaitre(vc["cle"], generation_de, maintenant=T0 + 100)
    dit(vu_disque() == T0 + 100, "le premier usage est ecrit tout de suite",
        str(vu_disque()))
    v.reconnaitre(vc["cle"], generation_de, maintenant=T0 + 400)
    dit(v.fiche(vid)["vu"] == T0 + 400,
        "vu est mis a jour en memoire a chaque reconnaissance",
        str(v.fiche(vid)["vu"]))
    dit(vu_disque() == T0 + 100,
        "vu ecrit au plus une fois par 600 s : 300 s apres, le disque n'a "
        "pas bouge", str(vu_disque()))
    v.reconnaitre(vc["cle"], generation_de, maintenant=T0 + 699)
    dit(vu_disque() == T0 + 100, "599 s apres, toujours pas", str(vu_disque()))
    v.reconnaitre(vc["cle"], generation_de, maintenant=T0 + 700)
    dit(vu_disque() == T0 + 700, "600 s apres le dernier ecrit, il l'est",
        str(vu_disque()))
    v2 = acces.Acces(v_chemin)
    v2.reconnaitre(vc["cle"], generation_de, maintenant=T0 + 800)
    dit(vu_disque() == T0 + 700,
        "une instance relue mesure l'intervalle depuis ce qu'elle a lu",
        str(vu_disque()))

    print("\n  ── un fichier corrompu ──")
    for quoi, contenu in (("JSON tronque", brut_du_disque(chemin)[:120]),
                          ("une fiche sans empreinte",
                           json.dumps([{"id": ident, "compte": "jordan",
                                        "secret_rappel": "s", "generation": 0,
                                        "hotes": []}])),
                          ("un objet au lieu d'une liste",
                           json.dumps({"cles": []}))):
        c_chemin = os.path.join(dossier, f"corrompu_{len(contenu)}.json")
        with open(c_chemin, "w", encoding="utf-8") as fic:
            fic.write(contenu)
        cor = acces.Acces(c_chemin)
        refuse = leve(cor.creer, "jordan", "neuve", 0)
        dit(cor.illisible and refuse is not None,
            f"{quoi} : creer() refuse", refuse or "accepte")
        dit(cor.reconnaitre(cle, generation_de) is None,
            f"{quoi} : reconnaitre() rend None")
        cor.revoquer(ident)
        cor.revoquer_compte("jordan")
        dit(leve(cor.sauver) is not None, f"{quoi} : sauver() lui-meme refuse")
        dit(brut_du_disque(c_chemin) == contenu
            and not os.path.exists(c_chemin + ".tmp"),
            f"{quoi} : rien n'est ecrase")
    absent = acces.Acces(os.path.join(dossier, "absent.json"))
    dit(not absent.illisible and absent.liste() == [],
        "fichier absent : magasin vide, et ce n'est pas une erreur")
    dit(leve(absent.creer, "jordan", "premiere", 0) is None
        and os.path.exists(absent.chemin),
        "fichier absent : creer() marche et l'ecrit")

    print("\n  ── les liens signes ──")
    tid = "0123456789abcdef0123456789abcdef"
    fin = int(T0) + 3600
    jeton = acces.signer_lien(secret, ident, tid, 2, fin)
    dit(acces.lien_valide(secret, jeton, maintenant=T0) == (ident, tid, 2),
        "aller-retour : le lien se relit", jeton[:24] + "…")
    dit(acces.lien_valide(secret, jeton, maintenant=fin) is not None
        and acces.lien_valide(secret, jeton, maintenant=fin + 1) is None,
        "un lien expire ne passe plus, et vaut jusqu'a sa fin incluse")
    _now = int(time.time())
    dit(acces.lien_valide(secret, acces.signer_lien(secret, ident, tid, 1,
                                                    _now + 3600)) is not None
        and acces.lien_valide(secret, acces.signer_lien(secret, ident, tid, 1,
                                                        _now - 10)) is None,
        "sans instant donne, c'est l'heure du studio qui juge l'expiration")
    tete, sig = jeton.rsplit(".", 1)
    sig_alteree = sig[:-1] + ("0" if sig[-1] != "0" else "1")
    rang_altere = jeton.replace(f".2.{fin}.", f".3.{fin}.")
    tid_altere = jeton.replace(tid, tid[::-1])
    fin_alteree = jeton.replace(f".{fin}.", f".{fin + 86400}.")
    ident_altere = jeton.replace(ident, ident_b, 1)
    alterations = {"signature alteree": tete + "." + sig_alteree,
                   "rang altere": rang_altere, "tid altere": tid_altere,
                   "fin repoussee": fin_alteree,
                   "identifiant altere": ident_altere}
    for quoi, j in alterations.items():
        dit(j != jeton and acces.lien_valide(secret, j, maintenant=T0) is None,
            f"lien refuse : {quoi}")
    dit(acces.lien_valide(autre["secret_rappel"], jeton, maintenant=T0) is None,
        "lien refuse : signe avec le secret d'une autre cle")
    formes_lien = [
        "", None, 42, jeton + ".", "." + jeton, jeton.upper(),
        jeton.replace(f".2.{fin}.", f".02.{fin}."),
        jeton.replace(f".2.{fin}.", f".100.{fin}."),
        jeton.replace(f".2.{fin}.", f".-1.{fin}."),
        jeton.replace(f".{fin}.", ".abc."),
        jeton.replace(tid, tid[:31]), jeton.replace(ident, ident[:7], 1),
        tete, jeton + "\n",
    ]
    mal = []
    for j in formes_lien:
        try:
            if acces.lien_valide(secret, j, maintenant=T0) is not None:
                mal.append(repr(j)[:30])
        except Exception as e:
            mal.append(f"LEVE {type(e).__name__}")
    dit(not mal and len(formes_lien) >= 10,
        "lien refuse : forme invalide, sans lever",
        ", ".join(mal) or f"{len(formes_lien)} formes fautives")
    dit(acces.lien_valide("", jeton, maintenant=T0) is None
        and acces.lien_valide(None, jeton, maintenant=T0) is None,
        "lien refuse : secret vide ou absent")
    dit(acces.lien_valide(secret, acces.signer_lien(secret, ident, tid, 0, fin),
                          maintenant=T0) == (ident, tid, 0)
        and acces.lien_valide(secret, acces.signer_lien(secret, ident, tid, 99,
                                                        fin),
                              maintenant=T0) == (ident, tid, 99),
        "temoin : les rangs 0 et 99 se signent et se relisent")
    dit(leve(acces.signer_lien, secret, ident, tid, 100, fin) is not None
        and leve(acces.signer_lien, secret, "xyz", tid, 1, fin) is not None
        and leve(acces.signer_lien, "", ident, tid, 1, fin) is not None,
        "signer_lien refuse ce que lien_valide refuserait")

    # ══════════════════════════════════════════════════════════════════
    #  LA DATE DE FIN. Une cle donnee a un essai, une demonstration,
    #  l'assistant d'un invite se ferme seule. Sans fin par defaut : une cle
    #  qui meurt en silence casse le workflow qu'elle servait.
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── la date de fin ──")
    fin_chemin = os.path.join(dossier, "fin.json")
    m = acces.Acces(fin_chemin)
    JOUR = 86400
    rf = m.creer("jordan", "essai d'une semaine", 0, expire_jours=7, maintenant=T0)
    cle_f, id_f = rf["cle"], rf["fiche"]["id"]
    dit(rf["fiche"]["expire"] == T0 + 7 * JOUR,
        "une cle de sept jours porte sa date de fin, sept jours apres sa creation",
        str(rf["fiche"]["expire"]))
    rs = m.creer("jordan", "sans fin", 0, maintenant=T0)
    dit(rs["fiche"]["expire"] is None
        and m.reconnaitre(rs["cle"], generation_de, maintenant=T0 + 3650 * JOUR) is not None,
        "sans duree de vie, la cle n'a pas de date de fin, et vaut encore dix ans "
        "plus tard", str(rs["fiche"]["expire"]))
    dit(m.reconnaitre(cle_f, generation_de, maintenant=T0 + 7 * JOUR - 1) is not None,
        "une seconde avant sa date de fin, la cle est reconnue")
    dit(m.reconnaitre(cle_f, generation_de, maintenant=T0 + 7 * JOUR) is None,
        "a sa date de fin, la cle n'est plus reconnue")
    dit(m.expiree_pour(cle_f, maintenant=T0 + 7 * JOUR)
        and not m.expiree_pour(cle_f, maintenant=T0 + 7 * JOUR - 1),
        "expiree_pour() dit « expiree » a partir de la date de fin, pas avant")
    faux_f = cle_f[:-1] + ("A" if cle_f[-1] != "A" else "B")
    dit(not m.expiree_pour(faux_f, maintenant=T0 + 30 * JOUR),
        "un secret faux n'apprend pas que la cle a expire : la reponse ne doit "
        "rien dire a qui n'a pas la cle")
    dit(not m.expiree_pour(rs["cle"], maintenant=T0 + 30 * JOUR)
        and not m.expiree_pour("cs_00000000_" + "x" * 43, maintenant=T0 + 30 * JOUR),
        "une cle sans fin, ou inconnue, n'est jamais « expiree »")
    mal_f = []
    for forme in (None, 12, "", "n'importe quoi", b"cs_", ["cs_"]):
        try:
            if m.expiree_pour(forme, maintenant=T0 + 30 * JOUR):
                mal_f.append(repr(forme))
        except Exception as e:
            mal_f.append(f"{forme!r} LEVE {type(e).__name__}")
    dit(not mal_f, "expiree_pour() ne leve pas sur une forme quelconque",
        ", ".join(mal_f) or "6 formes")
    dit(not acces.expiree(None) and not acces.expiree({})
        and acces.expiree({"expire": T0}, maintenant=T0)
        and not acces.expiree({"expire": T0}, maintenant=T0 - 1),
        "expiree() : rien n'expire sans date ; la date elle-meme est la fin")
    bornes_f = []
    for v in (-1, acces.EXPIRE_JOURS_MAX + 1, True, "7", 1.5, None):
        try:
            m.creer("jordan", "borne", 0, expire_jours=v, maintenant=T0)
            bornes_f.append(f"{v!r} accepte")
        except acces.ErreurAcces as e:
            if e.cle != "erreur.acces_expire":
                bornes_f.append(f"{v!r} : {e.cle}")
    dit(not bornes_f, "une duree hors de 0 a 365 jours, ou qui n'est pas un "
        "entier, est refusee avec sa propre phrase", ", ".join(bornes_f) or "6 refus")
    dit(m.creer("jordan", "un an", 0, expire_jours=acces.EXPIRE_JOURS_MAX,
                maintenant=T0)["fiche"]["expire"] == T0 + 365 * JOUR,
        "un an pile est accepte")
    dit(all(isinstance(j, int) and 0 <= j <= acces.EXPIRE_JOURS_MAX
            for j in acces.EXPIRATIONS) and acces.EXPIRATIONS[0] == 0,
        "les durees proposees sont dans les bornes, « sans fin » en tete",
        str(acces.EXPIRATIONS))
    # Le disque : la date survit, et une fiche d'avant (sans le champ) reste
    # une cle sans fin.
    m2 = acces.Acces(fin_chemin)
    m2.charger()
    dit(not m2.illisible and m2.fiche(id_f)["expire"] == T0 + 7 * JOUR
        and m2.reconnaitre(cle_f, generation_de, maintenant=T0 + 8 * JOUR) is None,
        "relue du disque, la date de fin tient toujours")
    brut_f = json.loads(brut_du_disque(fin_chemin))
    for x in brut_f:
        x.pop("expire", None)
    with open(fin_chemin, "w", encoding="utf-8") as fh:
        json.dump(brut_f, fh)
    m3 = acces.Acces(fin_chemin)
    m3.charger()
    dit(not m3.illisible and m3.fiche(id_f)["expire"] is None
        if m3.fiche(id_f) else False,
        "une fiche ecrite avant la date de fin se relit, et vaut « sans fin »")
    for x in brut_f:
        x["expire"] = "dans une semaine"
    with open(fin_chemin, "w", encoding="utf-8") as fh:
        json.dump(brut_f, fh)
    m4 = acces.Acces(fin_chemin)
    m4.charger()
    dit(m4.illisible and not m4.fiches,
        "une date de fin illisible rend le fichier illisible, comme tout champ "
        "mal forme : on ne devine pas une date")

    # ══════════════════════════════════════════════════════════════════
    #  RENOUVELER. Un secret neuf, le meme identifiant ; l'ancien secret vaut
    #  encore GRACE_RENOUVELLEMENT, le temps de recopier le neuf.
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── renouveler ──")
    GRACE = acces.GRACE_RENOUVELLEMENT
    ren_chemin = os.path.join(dossier, "renouveler.json")
    rv = acces.Acces(ren_chemin)
    r0 = rv.creer("jordan", "n8n", 0, hotes=["n8n.maison"], maintenant=T0)
    k0, id0, sec0 = r0["cle"], r0["fiche"]["id"], r0["secret_rappel"]
    r1 = rv.renouveler(id0, compte="jordan", maintenant=T0 + 10)
    k1 = r1["cle"]
    dit(k1 != k0 and acces.identifiant_de(k1) == id0 and r1["fiche"]["id"] == id0,
        "le renouvellement rend un secret neuf sous le MEME identifiant")
    dit(rv.reconnaitre(k1, generation_de, maintenant=T0 + 20) is not None
        and rv.reconnaitre(k0, generation_de, maintenant=T0 + 20) is not None,
        "le neuf vaut tout de suite, et l'ancien encore")
    dit(rv.reconnaitre(k0, generation_de, maintenant=T0 + 10 + GRACE - 1) is not None
        and rv.reconnaitre(k0, generation_de, maintenant=T0 + 10 + GRACE) is None
        and rv.reconnaitre(k1, generation_de, maintenant=T0 + 10 + GRACE) is not None,
        "l'ancien secret meurt a la fin de sa grace, pas avant ; le neuf continue")
    dit(r1["fiche"]["ancienne_jusqu"] == T0 + 10 + GRACE
        and "secret_rappel" not in r1 and rv.secret_rappel(id0) == sec0
        and r1["fiche"]["hotes"] == ["n8n.maison"],
        "la fiche dit jusqu'a quand l'ancien vaut ; le secret de rappel et les "
        "reglages ne changent pas, et le secret de rappel n'est pas remontre")
    dit(not any("empreinte" in k for k in r1["fiche"]),
        "aucune empreinte, neuve ou ancienne, ne sort dans la fiche publique")
    r2 = rv.renouveler(id0, maintenant=T0 + 100)
    dit(rv.reconnaitre(k0, generation_de, maintenant=T0 + 110) is None
        and rv.reconnaitre(k1, generation_de, maintenant=T0 + 110) is not None
        and rv.reconnaitre(r2["cle"], generation_de, maintenant=T0 + 110) is not None,
        "un second renouvellement ferme aussitot le premier secret : un seul "
        "secret d'avance")
    rv2 = acces.Acces(ren_chemin)
    rv2.charger()
    dit(not rv2.illisible
        and rv2.reconnaitre(k1, generation_de, maintenant=T0 + 120) is not None
        and rv2.reconnaitre(r2["cle"], generation_de, maintenant=T0 + 120) is not None,
        "relu du disque, l'ancien secret et sa grace tiennent toujours")
    refus_r = []
    try:
        rv.renouveler(id0, compte="camille", maintenant=T0 + 200)
        refus_r.append("celle d'un autre compte renouvelee")
    except acces.ErreurAcces as e:
        if e.cle != "erreur.cle_inconnue":
            refus_r.append(f"autre compte : {e.cle}")
    try:
        rv.renouveler("zzzzzzzz", maintenant=T0 + 200)
        refus_r.append("une cle inconnue renouvelee")
    except acces.ErreurAcces as e:
        if e.cle != "erreur.cle_inconnue":
            refus_r.append(f"inconnue : {e.cle}")
    rx = rv.creer("jordan", "courte", 0, expire_jours=1, maintenant=T0)
    try:
        rv.renouveler(rx["fiche"]["id"], maintenant=T0 + 2 * 86400)
        refus_r.append("une cle expiree renouvelee")
    except acces.ErreurAcces as e:
        if e.cle != "erreur.acces_renouveler_expiree":
            refus_r.append(f"expiree : {e.cle}")
    dit(not refus_r, "on ne renouvelle ni la cle d'un autre compte, ni une cle "
        "inconnue, ni une cle expiree — chacune avec sa raison",
        ", ".join(refus_r) or "3 refus")
    # Un renouvellement qui ne s'ecrit pas ne change rien : la cle montree
    # mourrait au redemarrage, et l'ancienne reviendrait seule.
    rv.illisible = True
    try:
        rv.renouveler(id0, maintenant=T0 + 300)
        ecrit = "le renouvellement est passe sans s'ecrire"
    except acces.ErreurAcces:
        ecrit = ""
    rv.illisible = False
    dit(not ecrit and rv.reconnaitre(r2["cle"], generation_de, maintenant=T0 + 310) is not None
        and rv.fiche(id0)["ancienne_jusqu"] == T0 + 100 + GRACE,
        "un renouvellement qui ne s'ecrit pas est defait : la cle d'avant vaut "
        "toujours, rien n'a bouge", ecrit)
    brut_r = json.loads(brut_du_disque(ren_chemin))
    for x in brut_r:
        if x["id"] == id0:
            x["ancienne_jusqu"] = "demain"
    with open(ren_chemin, "w", encoding="utf-8") as fh:
        json.dump(brut_r, fh)
    rv3 = acces.Acces(ren_chemin)
    rv3.charger()
    dit(rv3.illisible, "une fin de grace illisible rend le fichier illisible")

    # VOLE, ET NON SEULEMENT VU : sans grace, l'ancien secret meurt a la
    # reponse — et celui d'un renouvellement precedent aussi.
    sg = acces.Acces(os.path.join(dossier, "sans_grace.json"))
    a0 = sg.creer("jordan", "volee", 0, maintenant=T0)
    a1 = sg.renouveler(a0["fiche"]["id"], maintenant=T0 + 10)
    a2 = sg.renouveler(a0["fiche"]["id"], grace=0, maintenant=T0 + 20)
    dit(sg.reconnaitre(a0["cle"], generation_de, maintenant=T0 + 21) is None
        and sg.reconnaitre(a1["cle"], generation_de, maintenant=T0 + 21) is None
        and sg.reconnaitre(a2["cle"], generation_de, maintenant=T0 + 21) is not None
        and a2["fiche"]["ancienne_jusqu"] is None
        and "empreinte_ancienne" not in sg.fiches[a0["fiche"]["id"]],
        "sans grace, tous les secrets d'avant meurent a la reponse, et leur "
        "empreinte ne reste pas au fichier")
    # LA GRACE PASSEE, la fiche ne dit plus de date (un client qui teste
    # « if ancienne_jusqu » croirait l'ancien vivant), et la relecture du
    # fichier en efface l'empreinte.
    pg = os.path.join(dossier, "grace_passee.json")
    gp = acces.Acces(pg)
    b0 = gp.creer("jordan", "vieille grace", 0)
    passe = time.time() - acces.GRACE_RENOUVELLEMENT - 60
    gp.renouveler(b0["fiche"]["id"], maintenant=passe)
    gp2 = acces.Acces(pg)
    gp2.charger()
    dit(gp.fiche(b0["fiche"]["id"])["ancienne_jusqu"] is None
        and "empreinte_ancienne" not in gp2.fiches[b0["fiche"]["id"]]
        and not gp2.illisible,
        "la grace passee, ancienne_jusqu redevient null, et le chargement "
        "oublie l'empreinte de l'ancien secret")

    # ══════════════════════════════════════════════════════════════════
    #  CE QUE LA CLE PEUT FAIRE. Une liste de familles ; vide : tout. Une cle
    #  de detourage volee ne doit pas lancer de video.
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── operations ──")
    po = os.path.join(dossier, "operations.json")
    op = acces.Acces(po)
    o_tout = op.creer("jordan", "tout", 0)
    dit(o_tout["fiche"]["operations"] == [] and op.fiches[o_tout["fiche"]["id"]]["operations"] == [],
        "sans « operations », la cle peut tout : liste vide, sur la fiche et au fichier",
        repr(o_tout["fiche"]["operations"]))
    o_det = op.creer("jordan", "detourage", 0,
                     operations=["detourer", "agrandir", "detourer"])
    dit(o_det["fiche"]["operations"] == ["agrandir", "detourer"],
        "les familles sont rangees dans l'ordre d'OPERATIONS, sans doublon",
        repr(o_det["fiche"]["operations"]))
    mauvaises = {"une chaine seule": "video", "une famille inconnue": ["peindre"],
                 "un nombre": [3], "un dictionnaire": {"video": True},
                 "un type du catalogue au lieu d'une famille": ["video_image"]}
    passees = [quoi for quoi, v in mauvaises.items()
               if leve(op.creer, "jordan", "x", 0, operations=v) is None]
    dit(not passees, "« operations » refuse ce qui n'est pas une liste de familles",
        ", ".join(passees) or f"{len(mauvaises)} formes refusees")
    try:
        op.creer("jordan", "x", 0, operations="video")
        cle_refus = None
    except acces.ErreurAcces as e:
        cle_refus = e.cle
    dit(cle_refus == "erreur.acces_operations",
        "le refus nomme sa phrase, pour la page et pour l'API", str(cle_refus))
    dit(len([f for f in op.fiches.values() if f["nom"] == "x"]) == 0,
        "une liste refusee n'ecrit aucune cle")

    permis = acces.operation_permise
    cas = [
        ([], "video", True, "une cle sans liste peut tout"),
        ([], "type_que_personne_ne_connait", True, "meme un type a venir"),
        (["detourer"], "detourer", True, "sa famille passe"),
        (["detourer"], "video", False, "une autre famille ne passe pas"),
        (["detourer"], "video_image", False, "animer une image est une video"),
        (["video"], "video_image", True, "et la cle video l'accepte"),
        (["video"], "fluidifier", True, "fluidifier est une video"),
        (["retouche"], "retoucher_zone", True, "les trois retouches sont une famille"),
        (["retouche"], "edition", True, "l'edition aussi"),
        (["image"], "planche", True, "une planche est une image"),
        (["image"], "edition", False, "une edition n'est pas une image neuve"),
        (["detourer"], "question", True, "une question n'est jamais refusee"),
        (["detourer"], "refus", True, "un refus non plus : il n'a rien rendu"),
        (["detourer"], "type_que_personne_ne_connait", False,
         "un type sans famille est FERME a une cle restreinte"),
        (["detourer"], None, False, "pas de type : ferme"),
    ]
    faux = [f"{quoi} ({ops}, {t!r})" for ops, t, attendu, quoi in cas
            if permis(ops, t) is not attendu]
    dit(not faux, "operation_permise : familles, questions, et types inconnus fermes",
        "; ".join(faux) or f"{len(cas)} cas")
    dit(set(acces.FAMILLES.values()) == set(acces.OPERATIONS),
        "chaque famille est atteinte par un type, et aucun type ne mene hors d'OPERATIONS",
        repr(sorted(set(acces.FAMILLES.values()) ^ set(acces.OPERATIONS))))

    # La fiche publique est une COPIE : la page ou le serveur qui la modifie
    # ne doit pas ouvrir la cle.
    pub = op.fiche(o_det["fiche"]["id"])
    pub["operations"].append("video")
    dit(op.fiches[o_det["fiche"]["id"]]["operations"] == ["agrandir", "detourer"],
        "modifier la fiche publique ne touche pas la cle")
    # Le renouvellement garde ce que la cle peut faire : seul le secret change.
    rn = op.renouveler(o_det["fiche"]["id"], compte="jordan", maintenant=T0 + 5)
    dit(rn["fiche"]["operations"] == ["agrandir", "detourer"],
        "renouvelee, la cle peut toujours la meme chose", repr(rn["fiche"]["operations"]))

    # Le disque : la liste survit ; une fiche d'avant (sans le champ) peut tout ;
    # une liste abimee rend le fichier ILLISIBLE, et non la cle ouverte.
    op2 = acces.Acces(po)
    op2.charger()
    dit(not op2.illisible
        and op2.fiche(o_det["fiche"]["id"])["operations"] == ["agrandir", "detourer"],
        "relue du disque, la liste tient")
    brut_o = json.loads(brut_du_disque(po))
    for x in brut_o:
        x.pop("operations", None)
    with open(po, "w", encoding="utf-8") as fh:
        json.dump(brut_o, fh)
    op3 = acces.Acces(po)
    op3.charger()
    dit(not op3.illisible and op3.fiche(o_det["fiche"]["id"])["operations"] == [],
        "une fiche ecrite avant ce champ se relit, et peut tout")
    for abimee in ("detourer", ["detourer", "peindre"], [None], {"a": 1}):
        for x in brut_o:
            x["operations"] = abimee
        with open(po, "w", encoding="utf-8") as fh:
            json.dump(brut_o, fh)
        op4 = acces.Acces(po)
        op4.charger()
        dit(op4.illisible and not op4.fiches,
            f"une liste abimee ({abimee!r}) rend le fichier illisible : une "
            f"restriction cassee ne se lit pas comme « tout »")
finally:
    shutil.rmtree(dossier, ignore_errors=True)

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
