#! python3
# coding: utf-8

# todo
# multithreader par machine
# nettoyer le code

import os
import sys
import configparser
import logging
import re
import gc
import traceback
import getpass


from logging import FileHandler
from colorama import Fore
import colorama
colorama.init()


#logger = logging.getLogger('MagretUtil')
##logger_info = logging.getLogger('Info')
#logger.setLevel(logging.WARNING)
##logger_info.setLevel(logging.INFO)
#formatter = logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s\n' + '=' * 100 + '\n%(message)s' + '=' * 100)
## file_handler = RotatingFileHandler('error.log', mode='w', 1000000, 1)
#file_handler = FileHandler('error.log', 'w')
#file_handler.setLevel(logging.WARNING)
#file_handler.setFormatter(formatter)
#logger.addHandler(file_handler)
#stream_handler = logging.StreamHandler()
#stream_handler.setLevel(logging.INFO)
#logger_info.addHandler(stream_handler)

from Groupe import Groupe
from Salle import Salle
import commandes
import var_global
import Privilege
import AutoComplete


def _protect_quotes(text):
    lst = text.split('"')
    for i, item in enumerate(lst):
        if i % 2:
            lst[i] = re.sub(r'\s', "::", item)
    return '"'.join(lst)


def _remove_protect_char(lst_str):
    return [re.sub(r'::', ' ', s) for s in lst_str]


def lire_fichier_ini(fichier):
    """ Retourne les variables necessaire pour le fonctionnement retourne un
    dictionnaire {nom_groupe:nbre_poste}"""
    try:
        config = configparser.ConfigParser()
        config.read(fichier, encoding="utf-8-sig")
    except configparser.Error:
        print(Fore.LIGHTRED_EX + "[!] Erreur lors de l'initialisation du fichier ini : " + Fore.RESET)
        raise SystemExit(0)

    groupes_dict = {}
    groupes_dict['GroupesMagret'] = {}
    groupes_dict['Groupes'] = {}
    groupes_dict['GroupesFile'] = {}    
    domaine = {}
    try:
        try:
            for groupe in config['GroupesMagret']:
                num_poste = config['GroupesMagret'][groupe].split('-')[1]
                try:
                    nbre_poste = int(num_poste[1:])
                except ValueError:
                    nbre_poste = 0
                if nbre_poste != 0:
                    groupes_dict['GroupesMagret'][groupe.upper()] = nbre_poste
        except KeyError:
            print(Fore.LIGHTMAGENTA_EX + "[!] Aucun groupe Magret" + Fore.RESET)

        try:
            for groupe in config['Groupes']:
                groupes_dict['Groupes'][groupe.upper()] = config['Groupes'][groupe]
        except KeyError:
            print(Fore.LIGHTMAGENTA_EX + "[!] Aucun groupe non Magret" + Fore.RESET)

        try:
            groupes_dict['GroupesFile']['file'] = config['GroupesFile']['file'] 
        except KeyError:
            print(Fore.LIGHTMAGENTA_EX + "[!] Aucun fichier pour définir des groupes" + Fore.RESET)

    except Exception as e:
        print(Fore.LIGHTRED_EX + '[!] Erreur de lecture du fichier config' + Fore.RESET)
        #logger.critical(e)
        raise e
    domaine['name'] = config.get('Domaine', 'domaine', fallback=None)
    domaine['login'] = config.get('Domaine', 'login', fallback=None)
    return groupes_dict, domaine


def erreur_final(e_type, e_value, e_tb):
    if e_type == KeyboardInterrupt:
        raise SystemExit(0)
    print(Fore.LIGHTRED_EX + '[!] Erreur critique, voir le fichier de log' + Fore.RESET)
    os.system("pause")
    with open("error.log", "w") as f:
        f.write(''.join(traceback.format_exception(e_type, e_value, e_tb)))
    #logger.critical(''.join(traceback.format_exception(e_type, e_value, e_tb)))
    # pdb.post_mortem(e_tb)
    return


# def init_groupes_old(ini_groupes):
#     global groupes, selected_groupes, machines_dict
# 
#     for ini_salle, nbre in ini_groupes['GroupesMagret'].items():
#         groupes.append(Salle(ini_salle, nbre))
#     for ini_groupe, list_machine in ini_groupes['Groupes'].items():
#         list_machine = list_machine.split(',')
#         groupes.append(Groupe(ini_groupe, list_machine))
#     groupes.sort(key=lambda x: x.name)
# 
#     machines_dict.update({machine.name: machine for g in groupes for machine in g})
#     return


def init_groupes(ini_groupes):
    groupes_machines_names = {}
    all_names_machines = []

    # [GroupesMagret]
    for ini_salle, nbre in ini_groupes['GroupesMagret'].items():
        # on reécrit le nom des machines
        num = len(str(nbre)) if nbre >= 10 else 2
        str_template = '%s-P%0--i'.replace('--', str(num))
        names_machines = [str_template % (ini_salle, i) for i in range(1, nbre + 1)]
        # dict qui fait le lien nom groupe-noms de machines
        groupes_machines_names[ini_salle] = names_machines
        # on crée une salle vide qu'on remplire plus tard
        # on l'ajoute aux groupes globaux
        var_global.groupes.append(Salle(ini_salle, 0))
        all_names_machines.extend(names_machines)

    # [Groupes]
    for ini_groupe, list_machines in ini_groupes['Groupes'].items():
        list_machines = list_machines.split(',')
        groupes_machines_names[ini_groupe] = list_machines
        all_names_machines.extend(list_machines)
        var_global.groupes.append(Groupe(ini_groupe, []))

    # [GroupesFile]
    try:
        file = open(ini_groupes['GroupesFile']['file'], encoding="utf-8-sig", errors='replace')
        for line in file:
            list_name = line.strip(" \n,").split(',')
            if list_name[1:]:
                all_names_machines.extend(list_name[1:])
                groupes_machines_names[list_name[0]] = list_name[1:]
                var_global.groupes.append(Groupe(list_name[0], []))

    except FileNotFoundError:
        print(Fore.LIGHTRED_EX + "[!] Fichier csv introuvable" + Fore.RESET)
    except KeyError:
        pass

    # code ansi pour remonter le curseur : c'est plus jolie
    up = len(var_global.groupes) + 1
    print('\x1b[%sA' % up)

    # on crée un groupe avec toute les machines, ça permet de lancer
    # une action en multithreadant sur toutes les machines
    # on met à jour le dictionnaire des machines existantes
    var_global.groupe_selected_machines = Groupe('en cours', all_names_machines)
    var_global.machines_dict.update(var_global.groupe_selected_machines.dict_machines)

    # on remplie les groupes avec les machines créés au dessus
    for g in var_global.groupes:
        machines = [i for k, i in var_global.machines_dict.items()
                    if k in groupes_machines_names[g.name]]
        g.machines = machines
        g.dict_machines = {m.name: m for m in machines}
        g.machines.sort(key=lambda x: x.name)
    var_global.groupes.sort(key=lambda x: x.name)
    return


def main():
    sys.excepthook = erreur_final
    try:
        if not os.path.isdir('mac'):
            os.mkdir('mac')
    except:
        print(Fore.LIGHTRED_EX + "[!] Erreur lors de la création du répertoire mac" + Fore.RESET)
        os.system("pause")

    ini_groupes, dom = lire_fichier_ini('conf.ini')
    # on initialise la variable domaine qui contient le login administrateur
    # du domaine
    var_global.domaine.update(dom)

    # Si le login du fichier config est différent que celui avec lequel
    # on est connecté, on lance la procédure délévation de privilège
    if var_global.domaine['login'] is not None and getpass.getuser() != var_global.domaine['login']:
        commandes.password([])

    # Si une demande de bypasser l'uac est demandé, on lance la procédure
    if sys.argv[1:] and sys.argv[1] == "pass_uac":
        Privilege.pass_uac()
        raise SystemExit(0)

    #logger_info.info('Création des alias')
    print(Fore.LIGHTGREEN_EX + '[+] Création des alias' + Fore.RESET)
    alias_cmd = var_global.lire_alias_ini()

    print(Fore.LIGHTGREEN_EX + '[+] Initialisation des salles :' + Fore.RESET)
    init_groupes(ini_groupes)

    AutoComplete.init_auto_complete()

    # efface l'écran
    print('\x1b[2J', end='')

    commandes.select(['*'])
    print('-' * (os.get_terminal_size().columns - 1))
    print(Fore.LIGHTGREEN_EX + "Taper help ou la touche 'enter' pour obtenir de l'aide" + Fore.RESET)
    print('-' * (os.get_terminal_size().columns - 1))

    while True:
        param = input('>>>')
        param = _protect_quotes(param)
        param = param.strip()
        param = param.split(' ')
        param = _remove_protect_char(param)
        cmd = param[0]
        if cmd in alias_cmd:
            # permet de créer des alias avec un parametre
            str_replace =""
            if param[1:]:
                str_replace = " ".join(param[1:])
            param = _protect_quotes(alias_cmd[cmd].replace("$$",str_replace))
            param = param.strip()
            param = param.split(' ')
            param = _remove_protect_char(param)
            cmd = param[0]
        param.remove(cmd)
        cmd = cmd.lower()
        cmd_funct = getattr(commandes, cmd, commandes.help)
        try:
            # on efface la dernière erreur avant de lancer
            # la prochaine commande
            if cmd != 'errors':
                for m in var_global.groupe_selected_machines:
                    m.message_erreur = ''

            cmd_funct(param)

            # nettoie une partie de ceux qui a été laissé par les threads
            # de la dernière commande
            # contrôle l'augmentation de la mémoire pour le multithread
            gc.collect()
            # print('com-ref: ', pythoncom._GetInterfaceCount())
            print('-' * (os.get_terminal_size().columns - 1))
        except Warning:
            cmd_funct(['help'])
            gc.collect()
            # print(pythoncom._GetInterfaceCount())
            print('-' * (os.get_terminal_size().columns - 1))

if __name__ == '__main__':
    main()
