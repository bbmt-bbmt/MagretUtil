#! python3
# coding: utf-8

import configparser

def lire_alias_ini():
    """lit le fichier alias.ini et retourne
un dict{'alias':'commande'}
"""
    try:
        config = configparser.ConfigParser()
        config.read("alias.ini", encoding="utf-8-sig")
    except configparser.Error:
        print("erreur lors de l'initialisation du fichier alias.ini : ")
        raise SystemExit(0)

    alias_dict = {}
    commandes_name = {"select", "selected", "update", "users", "run", "result", "prog", "cmp", "flush", "put", "wol", "shutdown", "vnc", "help", "errors", "password", "tag", "quit"}

    try:
        for alias in config['Alias']:
            if alias not in commandes_name:
                alias_dict[alias] = config['Alias'][alias]
    except Exception:
        print("Erreur de lecture du fichier d'alias")
    return alias_dict

def fix_str2(string):
    return string.encode("cp850","replace").decode("utf-8", "replace")

def fix_str(string):
    """Retourne une chaine qui remplace les caractère unicode non reconnu par
    les bon caractère (utile pour les message d"erreur retourné par window
    cp1252 """
    char_w1252 = "\u2019\u201a\u2026ÿ\ufffd\u0160\u2014\u02c6\u201c"
    char_utf8 = "'éà Éèùêô"
    table_translate = str.maketrans(char_w1252, char_utf8)
    return string.translate(table_translate)

groupes = []
machines_dict = {}
selected_groupes = []
domaine = {}
