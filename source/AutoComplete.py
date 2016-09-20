#! python3
# coding: utf-8

import readline
import glob
import var_global


class Completer:
    """Classe qui fournit la fonction complete à readline
    la fonction walk est récursive et cyclique pour parcourir
    l'arbre des options de commandes """

    def __init__(self, option_tree):
        self.option_tree = option_tree
        return

    def walk(self, words, tree):
        if len(words) == 0:
            results = [x for x in tree]
            results.sort()
            return results
        if len(words) == 1 and readline.get_line_buffer()[-1] != ' ':
            # le glob permet l'autocomplétion des path
            return [x for x in tree if x.startswith(words[0])] + glob.glob(words[0] + "*")
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
            # le glob permet de modifier dynamiquement la liste des fichiers qui peuvent
            # être autocompléter dans les commandes qui manipulent un path
            # if words[-1:]:
            #     self.option_tree["put"] = glob.glob(words[-1] + "*")
            #     self.option_tree["run"]["file"] = [f for f in glob.glob(words[-1] + "*") 
            #                                 if re.fullmatch(".*(\.exe|\.msi)", f) or os.path.isdir(f)] + ["--param", "--timeout", "--no-wait"]
            self.results = self.walk(words, self.option_tree) + [None]
        return self.results[state]


def init_auto_complete():
    groupe_name = [g.name for g in var_global.groupes]
    machines_name = [name for name in var_global.machines_dict]
    cmd_select = groupe_name + ['help', 'reg', 'notag', 'oldtag'] + machines_name

    option_tree = {
        "select": cmd_select,
        "selected": ["help", "tagview"],
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
            "file": ["--param", "--timeout", "--no-wait"],
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

    alias_cmd = var_global.lire_alias_ini()
    for key in alias_cmd:
        option_tree[key] = []

    readline.set_completer_delims(' ')
    readline.parse_and_bind('tab: complete')
    completer = Completer(option_tree)
    readline.set_completer(completer.complete)
    return
