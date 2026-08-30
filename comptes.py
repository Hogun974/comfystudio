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
                 "cree": c.get("cree", ""), "vu": c.get("vu", "")}
                for c in sorted(self.gens.values(), key=lambda x: x["nom"].lower())]

    def creer(self, nom, mdp, admin=False):
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
        self.sauver()
        return self.gens[nom.lower()]

    def changer_mdp(self, nom, mdp):
        c = self.gens.get((nom or "").lower())
        if not c:
            raise ErreurCompte("compte inconnu")
        if len(mdp or "") < MDP_MINIMUM:
            raise ErreurCompte(f"mot de passe : {MDP_MINIMUM} caracteres au moins")
        c["sel"], c["empreinte"] = empreinte(mdp)
        self.sauver()

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

    def authentifier(self, nom, mdp):
        c = self.gens.get((nom or "").strip().lower())
        if not c or not verifier(mdp or "", c.get("sel"), c.get("empreinte")):
            # Un seul message pour les deux cas : dire « ce compte n'existe pas »
            # revient a publier la liste des comptes a qui veut la deviner.
            return None
        c["vu"] = time.strftime("%Y-%m-%d %H:%M")
        self.sauver()
        return c

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
