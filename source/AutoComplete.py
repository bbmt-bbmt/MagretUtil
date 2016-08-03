#! python3
# coding: utf-8

import readline
import re
import os
from var_global import *


class Completer:
    """Classe qui fournit la fonction complete à readline
    la fonction walk est récursive et cyclique pour parcourir
    l'arbre des options de commandes """

    def __init__(self, option_tree):
        self.option_tree = option_tree
        return

    def walk(self, words, tree):
        if len(words) == 0:
            results = [x + ' ' for x in tree]
            results.sort()
            return results
        if len(words) == 1 and readline.get_line_buffer()[-1] != ' ':
            return [x + ' ' for x in tree if x.startswith(words[0])]
        else:
            if type(tree) == list:
                return self.walk(words[1:], tree)
            if words[0] in tree.keys():
                return self.walk(words[1:], tree[words[0]])
            else:
                return []

    def complete(self, text, state):
        words = readline.get_line_buffer().split()
        # on premier appel au calcul la liste des options
        # pluto que de caluler la liste de manière récursive, on pourrait faire un itérateur avec yield
        # (pour s'entrainer)
        if state == 0:
            self.results = self.walk(words, self.option_tree) + [None]
        return self.results[state]


def init_auto_complete():
    global machines_dict, groupes
    groupe_name = [g.name for g in groupes]
    machines_name = [name for name in machines_dict]
    cmd_select = groupe_name + ['help', 'reg', 'notag'] + machines_name

    option_tree = {
        "select": cmd_select,
        "selected": {
            "help": []
        },
        "update": {
            "help": []
        },
        "tag": {
            "help": []
        },
        "users": {
            "add": ["admin"],
            "del": [],
            "show": [],
            "logged": [],
            "chpass": [],
            "groupes": [],
            "help": []
        },
        "run": {
            "cmd": ["--param", "--timeout", "--no-wait"],
            "file": ["--param", "--timeout", "--no-wait"] +
                    [f for f in os.listdir() if re.fullmatch(".*(\.exe|\.msi)", f)],
            "result": machines_name,
            "clean": [],
            "help": []
        },
        "prog": {
            "list": [],
            "help": [],
            "uninstall": []
        },
        "result": ["help", "mix"] + machines_name,
        "cmp": ["help", "--seuil"] + machines_name,
        "errors": ["clear", "help"] + machines_name,
        "put": ["help"],
        "password": ["help", "uac"],
        "flush": ["help"],
        "wol": ["help"],
        "shutdown": ["help"],
        "quit": [],
        "help": [],
        "vnc": ['help', "close"] + machines_name
    }

    alias_cmd = lire_alias_ini()
    for key in alias_cmd:
        option_tree[key] = []

    readline.parse_and_bind('tab: complete')
    completer = Completer(option_tree)
    readline.set_completer(completer.complete)
    return
