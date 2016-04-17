#! python3
# coding: utf-8


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
