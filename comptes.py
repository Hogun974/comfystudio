# -*- coding: utf-8 -*-
"""Comptes utilisateurs : stockage, empreintes, jetons de session.

Le studio a longtemps fonctionne sans comptes : chaque navigateur recevait un
identifiant opaque, et cela suffisait tant qu'on restait sur le meme appareil.
Deux limites ont fini par mordre — un espace par ADRESSE (127.0.0.1 et
192.0.2.10 sont deux cookies distincts, donc deux historiques), et rien pour
retrouver ses conversations depuis un telephone.

Un compte resout les deux : l'identite ne depend plus du navigateur mais de qui
l'on est, et suit sur tous les appareils.

Trois choix a expliquer :

- **Le mot de passe n'est jamais conserve.** On garde une empreinte scrypt avec
  un sel tire au hasard par compte. scrypt et non un simple SHA : il est concu
  pour etre lent et gourmand en memoire, ce qui rend le parcours d'un
  dictionnaire couteux meme si le fichier fuit.

- **La session est un jeton signe, pas une entree en memoire.** Une table en
  memoire deconnecterait tout le monde a chaque redemarrage du studio — et il
  redemarre souvent. Le jeton porte le nom et sa date de peremption, scelles
  par un HMAC : le serveur n'a rien a retenir, et ne peut pas etre trompe.

- **Les comptes ne sont pas obligatoires.** Un visiteur sans compte garde
  exactement le studio d'avant. Fermer la porte serait un autre choix, qui
  appartient a celui qui heberge, pas a ce fichier.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time

# Le second facteur. mfa.py n'importe que la bibliotheque standard : ce module
# reste donc aussi leger qu'avant, et un studio qui n'arme le MFA sur aucun
# compte ne paie rien.
import mfa

NOM_VALIDE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{1,23}")
DUREE_SESSION = 30 * 24 * 3600      # un mois : on n'ouvre pas un studio familial
                                    # tous les matins
MDP_MINIMUM = 8

# Parametres scrypt. n=2**14 tient en ~16 Mo et coute quelques dizaines de
# millisecondes : assez pour genantiser une attaque, assez peu pour ne pas
# bloquer la boucle du serveur a chaque ouverture de session.
_N, _R, _P = 2 ** 14, 8, 1


class ErreurCompte(ValueError):
    """Refus explicable a l'utilisateur : nom pris, mot de passe trop court…"""


class _BesoinMFA:
    """« Le mot de passe est bon, il manque le second facteur » — ET C'EST FAUX.

    __bool__ rend False, et ce n'est pas une coquetterie : c'est ce qui fait
    qu'un appelant qui ne sait rien du second facteur ECHOUE FERME. Le code
    d'avant s'ecrit « if not c: refuser » ; avec un sentinelle vrai, chaque
    site d'appel oublie aurait ouvert une session sur le seul mot de passe. Et
    un site oublie ne se voit pas : tout continue de marcher pour les comptes
    qui n'ont pas arme le facteur, c'est-a-dire pour tout le monde le jour ou
    l'on branche la fonctionnalite.

    Un objet et non None : « c is BESOIN_MFA » distingue les deux cas pour qui
    veut afficher le champ du code, sans qu'aucun test de verite ne le confonde
    avec une reussite.
    """

    __slots__ = ()

    def __bool__(self):
        return False

    def __repr__(self):
        return "BESOIN_MFA"


BESOIN_MFA = _BesoinMFA()


def empreinte(mdp, sel=None):
    """Empreinte scrypt d'un mot de passe, avec son sel."""
    sel = sel or secrets.token_bytes(16)
    brut = hashlib.scrypt(mdp.encode("utf-8"), salt=sel, n=_N, r=_R, p=_P,
                          dklen=32, maxmem=64 * 1024 * 1024)
    return base64.b64encode(sel).decode(), base64.b64encode(brut).decode()


def verifier(mdp, sel_b64, empreinte_b64):
    """compare_digest : une comparaison qui s'arrete au premier octet different
    laisse mesurer combien de tete est juste."""
    try:
        sel = base64.b64decode(sel_b64)
    except Exception:
        return False
    _, calcule = empreinte(mdp, sel)
    return hmac.compare_digest(calcule, empreinte_b64 or "")


def _empreintes_secours(secours):
    """Ce qui est GARDE d'un jeu de codes de secours : leur empreinte, jamais eux.

    Une seule ecriture pour les deux sites qui en produisent — la confirmation
    de l'enrolement et la regeneration. Recopiee, elle aurait diverge : c'est la
    lecon que banc_mutations.py a payee trois fois (« tant qu'il y a deux
    ecritures du meme enchainement, elles divergent »), et ici la divergence
    serait un jeu de codes garde EN CLAIR sans que rien ne le dise.

    normalise_secours() des DEUX cotes — ici et a la verification — sinon
    l'empreinte tombe a cote des que quelqu'un recopie son code en majuscules.
    """
    return [dict(zip(("sel", "empreinte"),
                     empreinte(mfa.normalise_secours(s)))) for s in secours]


def identifiant(nom):
    """L'identite d'espace attachee a ce compte.

    Trente-deux caracteres hexadecimaux, comme un identifiant de navigateur :
    tout le code de propriete deja ecrit continue de fonctionner sans savoir
    qu'il a affaire a un compte plutot qu'a un cookie.
    """
    return hashlib.sha256(("compte:" + nom.lower()).encode()).hexdigest()[:32]


class Comptes:
    """Le registre des comptes, sur disque, et les jetons de session."""

    def __init__(self, chemin, secret):
        self.chemin = chemin
        self.secret = secret.encode() if isinstance(secret, str) else secret
        self.gens = {}
        self.charger()

    # ── disque ───────────────────────────────────────────────────────────
    def charger(self):
        try:
            with open(self.chemin, encoding="utf-8") as f:
                for c in json.load(f):
                    self.gens[c["nom"].lower()] = c
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"comptes illisibles ({e}) — aucun compte charge", flush=True)

    def sauver(self):
        tmp = self.chemin + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(list(self.gens.values()), f, ensure_ascii=False, indent=1)
        try:
            os.chmod(tmp, 0o600)          # sans effet sur Windows, utile ailleurs
        except OSError:
            pass
        os.replace(tmp, self.chemin)

    # ── comptes ──────────────────────────────────────────────────────────
    def liste(self):
        """Sans sel ni empreinte : rien de secret ne sort d'ici."""
        return [{"nom": c["nom"], "admin": bool(c.get("admin")),
                 "cree": c.get("cree", ""), "vu": c.get("vu", ""),
                 "origine": bool(c.get("origine"))}
                for c in sorted(self.gens.values(), key=lambda x: x["nom"].lower())]

    def creer(self, nom, mdp, admin=False, origine=False):
        nom = (nom or "").strip()
        if not NOM_VALIDE.fullmatch(nom):
            raise ErreurCompte("nom invalide : 2 a 24 lettres, chiffres, . _ ou -")
        if nom.lower() in self.gens:
            raise ErreurCompte("ce nom est deja pris")
        if len(mdp or "") < MDP_MINIMUM:
            raise ErreurCompte(f"mot de passe : {MDP_MINIMUM} caracteres au moins")
        sel, emp = empreinte(mdp)
        self.gens[nom.lower()] = {
            "nom": nom, "sel": sel, "empreinte": emp, "admin": bool(admin),
            "cree": time.strftime("%Y-%m-%d %H:%M"), "vu": "",
        }
        # « origine » : CE MOT DE PASSE EST CELUI QUE LE STUDIO A TIRE LUI-MEME
        # au premier demarrage, et qu'il a imprime UNE fois dans la console. Le
        # drapeau n'est pose que dans ce cas-la, jamais pour un mot de passe
        # choisi par l'hebergeur (STUDIO_ADMIN_MDP) : celui-la est une decision,
        # et il n'y a rien a en mesurer. Celui-ci, non — il defile dans un
        # terminal, il se recolle dans un fil de discussion, et il est le seul
        # secret du studio tant que personne ne l'a change.
        #
        # Un drapeau plutot qu'une comparaison : garder le mot de passe pour
        # pouvoir dire « c'est encore lui » reviendrait a le conserver en clair,
        # ce que ce fichier refuse en tete. Le drapeau ne dit rien du secret, il
        # dit seulement que personne n'y a touche.
        if origine:
            self.gens[nom.lower()]["origine"] = True
        self.sauver()
        return self.gens[nom.lower()]

    def changer_mdp(self, nom, mdp):
        c = self.gens.get((nom or "").lower())
        if not c:
            raise ErreurCompte("compte inconnu")
        if len(mdp or "") < MDP_MINIMUM:
            raise ErreurCompte(f"mot de passe : {MDP_MINIMUM} caracteres au moins")
        c["sel"], c["empreinte"] = empreinte(mdp)
        # ICI ET NULLE PART AILLEURS. C'est le SEUL endroit du depot ou un mot
        # de passe est remplace — les deux portes qui en changent un, celle du
        # proprietaire (/api/compte/mdp) et celle de l'administration
        # (/api/admin/comptes), passent toutes les deux par cette methode. Poser
        # l'effacement dans les routes l'aurait recopie deux fois, et la seconde
        # aurait fini par diverger : l'ecran de premiere mise en route aurait
        # alors reclame indefiniment un changement deja fait, ce qui est la
        # facon la plus sure de le faire ignorer.
        c.pop("origine", None)
        self.sauver()

    def mdp_d_origine(self, nom):
        """Ce compte porte-t-il encore le mot de passe tire au demarrage ?"""
        return bool((self.gens.get((nom or "").lower()) or {}).get("origine"))

    def comptes_d_origine(self):
        """Les noms des comptes qui n'ont jamais change de mot de passe.

        Une LISTE et non un booleen : l'ecran qui la lit doit pouvoir nommer le
        compte a corriger. « il reste un mot de passe d'origine » envoie
        chercher lequel dans une page qui compte parfois vingt lignes.
        """
        return sorted(c["nom"] for c in self.gens.values() if c.get("origine"))

    def changer_role(self, nom, admin):
        c = self.gens.get((nom or "").lower())
        if not c:
            raise ErreurCompte("compte inconnu")
        if not admin and c.get("admin") and self.nombre_admins() <= 1:
            # Sans cette garde, on peut se retirer le dernier droit d'admin et
            # perdre l'acces a la page qui permettrait de le rendre.
            raise ErreurCompte("c'est le dernier administrateur")
        c["admin"] = bool(admin)
        self.sauver()

    def supprimer(self, nom):
        c = self.gens.get((nom or "").lower())
        if not c:
            raise ErreurCompte("compte inconnu")
        if c.get("admin") and self.nombre_admins() <= 1:
            raise ErreurCompte("c'est le dernier administrateur")
        self.gens.pop(nom.lower())
        self.sauver()

    def nombre_admins(self):
        return sum(1 for c in self.gens.values() if c.get("admin"))

    def est_espace_de_compte(self, pid):
        """Ce cookie designe-t-il l'espace d'un compte existant ?

        identifiant() n'est qu'un sha256 du nom, sans sel et sans secret :
        l'espace du compte « admin » se calcule de tete, hors ligne, sans rien
        savoir de l'installation visee. Un visiteur qui pose ce cookie sans
        jamais presenter de mot de passe reprenait ses conversations et sa
        mediatheque — en STUDIO_AUTH=libre, ou aucune session n'est exigee,
        cela suffisait.

        Saler l'empreinte serait plus propre, mais reattribuerait toutes les
        conversations deja rangees sous l'ancien identifiant. Refuser le cookie
        ferme la meme porte sans toucher aux donnees existantes.
        """
        return any(identifiant(c["nom"]) == pid for c in self.gens.values())

    def authentifier(self, nom, mdp, code=None):
        """Le compte, None, ou BESOIN_MFA — et ce troisieme cas est FAUX.

        LE SENTINELLE EST FALSY, ET C'EST TOUTE LA PROTECTION. Un appelant qui
        ne connait pas le second facteur ecrit « if not c: refuser », et il
        refuse : le code d'avant echoue FERME. S'il avait fallu comparer a une
        valeur particuliere, chaque site d'appel oublie aurait ouvert une
        session sur le seul mot de passe — et un site d'appel oublie ne se voit
        pas, puisque tout continue de marcher pour les comptes sans MFA.
        C'est la meme raison qui fait rendre a mfa.verifie() le PAS accepte
        plutot qu'un booleen : on ne demande pas a l'appelant de penser a
        quelque chose, on lui rend impossible de l'ignorer.
        """
        c = self.gens.get((nom or "").strip().lower())
        if not c or not verifier(mdp or "", c.get("sel"), c.get("empreinte")):
            # Un seul message pour les deux cas : dire « ce compte n'existe pas »
            # revient a publier la liste des comptes a qui veut la deviner.
            return None
        if (c.get("mfa") or {}).get("secret"):
            if not code:
                # LE MOT DE PASSE ETAIT BON, et on ne le dit pas autrement que
                # par cette demande de code. C'est inevitable — il faut bien
                # afficher le champ — mais rien d'autre ne fuit : le compte
                # n'est pas marque « vu », et l'echec du code rend le meme None
                # qu'un mot de passe faux.
                return BESOIN_MFA
            if not self.mfa_verifier(c["nom"], code):
                return None
        c["vu"] = time.strftime("%Y-%m-%d %H:%M")
        self.sauver()
        return c

    # ── le second facteur ────────────────────────────────────────────────
    # LE SECRET N'EST PAS UN MOT DE PASSE : il ne peut pas etre garde en
    # empreinte, puisqu'il faut le relire pour calculer le code attendu. Il est
    # donc en clair dans _comptes.json, comme il l'est dans toutes les
    # implementations de TOTP — et c'est pourquoi ce fichier est ecrit en 0600
    # et ne sort jamais par liste(). Les codes de SECOURS, eux, se comparent :
    # ils sont empreints comme des mots de passe.
    #
    # L'ENROLEMENT SE FAIT EN DEUX TEMPS, et le second n'est pas une politesse.
    # Armer le facteur au moment ou l'on tire le secret enferme dehors quiconque
    # a mal scanne le QR code, ferme l'onglet trop tot, ou dont l'horloge de
    # telephone est fausse : il ne pourra plus jamais entrer, et l'administrateur
    # non plus — c'est justement ce qu'on vient d'empecher. Le secret attend donc
    # dans « mfa_attente » tant qu'un code juste n'a pas ete presente.

    def mfa_arme(self, nom):
        """Ce compte exige-t-il un second facteur, ici et maintenant ?"""
        c = self.gens.get((nom or "").lower()) or {}
        return bool((c.get("mfa") or {}).get("secret"))

    def mfa_en_attente(self, nom):
        """Un enrolement est-il commence sans etre confirme ?

        LE SYMETRIQUE DE mfa_arme(), ET IL SE LIT AUTANT. Sans lui, un appelant
        qui veut distinguer « ce code ne correspond pas » d'« aucun enrolement
        en cours » n'a que l'exception de mfa_confirmer(), c'est-a-dire une
        PHRASE FRANCAISE a comparer — le contrat sur un texte que ce depot a
        deja defait deux fois. Les deux remedes different : l'un se retape,
        l'autre se recommence.
        """
        c = self.gens.get((nom or "").lower()) or {}
        return bool((c.get("mfa_attente") or {}).get("secret"))

    def mfa_preparer(self, nom):
        """Tire un secret et le met EN ATTENTE. Rend (secret, uri).

        Rappele deux fois, il tire un secret neuf : quelqu'un qui reprend un
        enrolement abandonne a scanne un QR code qu'il ne retrouve plus, et lui
        rendre l'ancien secret l'obligerait a chercher lequel de ses deux
        comptes d'application est le bon.
        """
        c = self.gens.get((nom or "").lower())
        if not c:
            raise ErreurCompte("compte inconnu")
        if self.mfa_arme(c["nom"]):
            raise ErreurCompte("le second facteur est deja arme sur ce compte")
        secret = mfa.secret_neuf()
        c["mfa_attente"] = {"secret": secret,
                            "depuis": time.strftime("%Y-%m-%d %H:%M")}
        self.sauver()
        return secret, mfa.uri(c["nom"], secret)

    def mfa_confirmer(self, nom, code):
        """Arme le facteur si le code tombe juste. Rend les codes de secours.

        EN CLAIR UNE SEULE FOIS, et jamais relisibles : ce qui est garde est
        leur empreinte scrypt. C'est le seul moment ou ils existent en clair,
        et l'interface doit le dire — un utilisateur qui ferme l'onglet en
        pensant les retrouver dans ses reglages ne les retrouvera pas.
        """
        c = self.gens.get((nom or "").lower())
        if not c:
            raise ErreurCompte("compte inconnu")
        attente = c.get("mfa_attente") or {}
        if not attente.get("secret"):
            raise ErreurCompte("aucun enrolement en cours")
        pas = mfa.verifie(attente["secret"], code)
        if pas is None:
            raise ErreurCompte("ce code ne correspond pas")
        secours = mfa.codes_de_secours()
        c["mfa"] = {"secret": attente["secret"],
                    "depuis": time.strftime("%Y-%m-%d %H:%M"),
                    # LE PAS QUI VIENT DE SERVIR EST DEJA CONSOMME. Sans cette
                    # ligne, le code tape pour CONFIRMER l'enrolement ouvrirait
                    # encore une session dans la minute — le rejeu, par la
                    # porte de l'enrolement.
                    "dernier_pas": pas,
                    "secours": _empreintes_secours(secours)}
        c.pop("mfa_attente", None)
        self.sauver()
        return secours

    def mfa_regenerer(self, nom):
        """Un jeu NEUF de codes de secours. L'ancien cesse de valoir.

        POURQUOI CETTE PORTE EXISTE. Les dix codes s'epuisent — c'est le but,
        ils sont a usage unique — et quelqu'un qui arrive au dernier n'a plus
        que deux issues : desarmer le facteur, ou perdre le compte. Sans elle,
        la seule facon d'en refaire etait de desarmer puis de reenroler, ce qui
        change le SECRET : il faut ressortir le telephone, effacer l'ancienne
        entree, en scanner une neuve. Une manoeuvre a trois etapes pour un
        besoin qui n'en demande aucune.

        LE SECRET NE BOUGE PAS, et c'est tout ce qui separe cette methode de
        « retirer puis preparer ». Le telephone deja enrole continue de servir ;
        seuls les codes de papier changent.

        L'ANCIEN JEU EST REMPLACE, jamais complete. Y ajouter dix codes en
        gardant les anciens laisserait valides ceux du papier qu'on regenere
        justement parce qu'on l'a perdu de vue — la seule raison d'appeler
        ceci.
        """
        c = self.gens.get((nom or "").lower())
        if not c:
            raise ErreurCompte("compte inconnu")
        m = c.get("mfa") or {}
        if not m.get("secret"):
            raise ErreurCompte("aucun second facteur sur ce compte")
        secours = mfa.codes_de_secours()
        m["secours"] = _empreintes_secours(secours)
        self.sauver()
        return secours

    def mfa_verifier(self, nom, code):
        """Un code TOTP, ou un code de secours. Vrai une seule fois chacun.

        L'ORDRE COMPTE PEU MAIS LE COUT, SI : on essaie TOTP d'abord parce
        qu'il est le cas courant et qu'il ne coute qu'un HMAC, la ou chaque
        code de secours coute un scrypt — dix scrypt a chaque saisie donneraient
        a qui essaie des codes au hasard un levier pour occuper le studio.
        """
        c = self.gens.get((nom or "").lower())
        m = (c or {}).get("mfa") or {}
        if not m.get("secret"):
            return False
        pas = mfa.verifie(m["secret"], code, dernier_pas=m.get("dernier_pas"))
        if pas is not None:
            # SUR LE DISQUE, ET TOUT DE SUITE. Garder le dernier pas en memoire
            # seulement rouvrirait le rejeu a chaque redemarrage du studio — et
            # il redemarre souvent, c'est ecrit en tete de ce fichier a propos
            # des sessions.
            m["dernier_pas"] = pas
            self.sauver()
            return True
        propre = mfa.normalise_secours(code)
        if not propre:
            return False
        for i, s in enumerate(m.get("secours") or []):
            if verifier(propre, s.get("sel"), s.get("empreinte")):
                # A USAGE UNIQUE : on le retire avant de rendre vrai. Un code de
                # secours rejouable est un second mot de passe permanent, note
                # sur un papier.
                m["secours"].pop(i)
                self.sauver()
                return True
        return False

    def mfa_secours_restants(self, nom):
        c = self.gens.get((nom or "").lower()) or {}
        return len((c.get("mfa") or {}).get("secours") or [])

    def mfa_retirer(self, nom):
        """Desarme le facteur, et efface le secret avec.

        Le garder « au cas ou » ferait qu'un compte desarme puis rearme
        reprendrait l'ancien secret : le telephone qu'on venait justement de
        perdre ouvrirait de nouveau le studio.
        """
        c = self.gens.get((nom or "").lower())
        if not c:
            raise ErreurCompte("compte inconnu")
        c.pop("mfa", None)
        c.pop("mfa_attente", None)
        self.sauver()

    # ── sessions ─────────────────────────────────────────────────────────
    def jeton(self, nom, duree=DUREE_SESSION):
        """« nom.peremption.signature », lisible mais infalsifiable."""
        fin = str(int(time.time() + duree))
        charge = f"{nom}.{fin}"
        signature = hmac.new(self.secret, charge.encode(), hashlib.sha256).hexdigest()[:32]
        return f"{charge}.{signature}"

    def nom_du_jeton(self, jeton):
        """Le compte designe par ce jeton, ou None. Ne leve jamais."""
        try:
            nom, fin, signature = (jeton or "").rsplit(".", 2)
        except ValueError:
            return None
        attendu = hmac.new(self.secret, f"{nom}.{fin}".encode(),
                           hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(signature, attendu):
            return None
        try:
            if time.time() > int(fin):
                return None
        except ValueError:
            return None
        # Le compte a pu etre supprime depuis que le jeton a ete remis.
        return self.gens.get(nom.lower(), {}).get("nom")

    def est_admin(self, nom):
        return bool(self.gens.get((nom or "").lower(), {}).get("admin"))
