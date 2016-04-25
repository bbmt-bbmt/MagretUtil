#! python3
# coding: utf-8

import re
import docopt2
import Privilege
import gc
from var_global import *
import os
import subprocess
import getpass
from Groupe import Groupe
from colorama import Fore


def select(param):
    """Sélectionne les groupes, utiliser * pour tout selectionner
En utilisant select reg il est possible d'utiliser une expression régulière
pour sélectionner les salles

Usage:
  select help
  select reg <expression_reg>
  select <nom>...
"""
    global groupes, selected_groupes, machines_dict

    doc = select.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    if arg['reg']:
        try:
            pattern = re.compile(arg['<expression_reg>'])
            selected_groupes = [g for g in groupes if pattern.fullmatch(g.name)]
            selected_machines_groupes = [m.name for g in selected_groupes
                                         for m in g]
            selected_machines = [name for name in machines_dict
                                 if pattern.fullmatch(name) and
                                 name not in selected_machines_groupes]
            if selected_machines:
                selected_groupes.append(Groupe('AUTRES', selected_machines))
        except re.error:
            print("L'expression régulière n'est pas valide")
    if arg['<nom>']:
        if '*' in arg['<nom>']:
            selected_groupes = groupes
        else:
            # on sélectionne les groupes de la commande select
            selected_groupes = [g for g in groupes if g.name in arg['<nom>']]
            # on récupère les noms des machines déja mis dans les groupes selectionnés
            selected_machines_groupes = [m.name for g in selected_groupes for m in g]
            # on sélectionne les machines de la commande select sauf si elles
            # existent déja dans un groupe
            selected_machines = [name for name in machines_dict
                                 if name in arg['<nom>'] and
                                 name not in selected_machines_groupes]
            # si la liste des machines à sélectionner n'est pas vide
            # on crée le groupe AUTRES
            if selected_machines:
                selected_groupes.append(Groupe('AUTRES', selected_machines))
    selected([])
    return


def selected(param):
    """Affiche les groupes sélectionnées
en vert la machine est allumée
en gris la machine est éteinte
en rouge la machine a un message d'erreur (utiliser errors pour l'afficher)

Usage:
  selected [help]
"""
    global groupes, selected_groupes, machines_dict
    doc = selected.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        return print(doc)
    if selected_groupes == []:
        print('Auncun groupe sélectionné')
    else:
        print('-' * (os.get_terminal_size().columns - 1))
        print("\n".join([m.str_groupe() for m in selected_groupes]).strip())
    return


def update(param):
    """Met à jour les stations allumées ou éteintes des groupes selectionnées

Usage:
  update [help]
"""
    global groupes, selected_groupes, machines_dict

    doc = update.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    for groupe in selected_groupes:
        machines_dict.clear()
        groupe.update()
        machines_dict.update({machine.name: machine for s in groupes
                              for machine in s})
        gc.collect()
    selected([])
    return


def users(param):
    """Modification d'utilisateur sur les stations sélectionnées
en vert: les utilisateurs activés
en gris: les utilisateurs désactivés
avec un asterix rouge devant: l'utilisateur appartient au groupe Administrateur

Usage:
  users add <name> <password> [<admin>]
  users del <name>
  users show
  users chpass <name> <password>
  users groupes <name>
  users help
"""
    global groupes, selected_groupes

    doc = users.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    str_resultat = ""
    if arg['help']:
        print(doc)
        return

    for groupe in selected_groupes:
        if arg['add']:
            groupes = ['Administrateurs'] if arg['<admin>'] == 'admin'\
                else ['Utilisateurs']
            groupe.add_user(arg['<name>'], arg['<password>'], groupes)
        if arg['del']:
            groupe.del_user(arg['<name>'])
        if arg['show']:
            str_resultat += groupe.str_users()
        if arg['chpass']:
            groupe.chpwd_user(arg['<name>'], arg['<password>'])
        if arg['groupes']:
            str_resultat += groupe.str_user_groups(arg['<name>'])

    if str_resultat != '':
        print('-' * (os.get_terminal_size().columns - 1))
        print(str_resultat.strip())
    else:
        selected([])
    return


def run(param):
    """Execute une commande ou un fichier à distance
run result permet d'afficher le résultat de la derniere commande exécutée
run file permet de lancer un executable à distance
run clear nettoie les repertoires laissés sur la machine
(arrive si le programme plante ou lors de l'utilisation
de l'option --no-wait)

Usage:
  run cmd <commande> [<parametre>...] [--param=<param>] [--timeout=t] [--no-wait]
  run file <nom_fichier> [<option>...] [--param=<param>] [--timeout=t] [--no-wait]
  run result <machine>
  run clean
  run help

Options:
    --timeout=<t>    temps pour attendre la fin de l'execution en seconde
    --no-wait        si l'option est spécifié, on n'attend pas la réponse de la commande
    --param=<param>  permet de passer des parametres avec un tirer.
                     On peut utiliser les "" pour passer plusieurs parametres
"""
    global groupes, selected_groupes, machines_dict

    doc = run.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['--param'] is None:
        arg['--param'] = ''
    if arg['help']:
        print(doc)
        return
    try:
        timeout = int(arg['--timeout'])
    except:
        timeout = None
    if arg['cmd']:
        list_join = [arg['<commande>']]\
            + arg['<parametre>'] + [arg['--param'].strip('"')]
        cmd = ' '.join(list_join)
        for groupe in selected_groupes:
            groupe.run_remote_cmd(cmd, timeout, arg["--no-wait"])
        selected([])
    if arg['file']:
        for groupe in selected_groupes:
            groupe.run_remote_file(arg['<nom_fichier>'],
                                   " ".join(arg['<option>'] + [arg['--param'].strip('"')]),
                                   timeout,
                                   arg["--no-wait"])
        selected([])
    if arg['result']:
        if arg['<machine>'] in machines_dict.keys():
            str_resultat = machines_dict[arg['<machine>']].last_output_cmd \
                if machines_dict[arg['<machine>']].last_output_cmd != "" \
                else "Aucun resultat à afficher"
            print(str_resultat.strip())
        else:
            print("%s n'existe pas" % arg['<machine>'])
    if arg['clean']:
        for groupe in selected_groupes:
            groupe.clean()
        selected([])
    return


def cmp(param):
    """Compare le resultat de la commande run par rapport au resultat
d'une machine donnée

Usage:
  cmp [help] <nom_machine> [--seuil=s]
  cmp help

Options:
  --seuil=s  le seuil en pourcentage d'acceptation
             ou de rejet pour la comparaison [default: 100]
"""
    global groupes, selected_groupes, machines_dict

    doc = cmp.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    str_resultat = 'Comparaison des résultats de la dernière commande exécutée:\n\n'
    if arg['help']:
        print(doc)
        return
    try:
        str_ref = machines_dict[arg['<nom_machine>']].last_output_cmd
    except KeyError:
        print("la machine n'existe pas")
        return
    str_resultat += "\n".join([groupe.str_cmp(str_ref, int(arg['--seuil']))
                               for groupe in selected_groupes])
    print(str_resultat)
    return


def flush(param):
    """Ecris tous les résultats des machines sélectionnées dans un fichier csv

Usage:
  flush [help]
"""
    global groupes, selected_groupes, machines_dict

    doc = flush.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)

    if arg['help']:
        print(doc)
        return

    str_file = ''
    with open("flush.csv", 'w') as flush_file:
        for groupe in selected_groupes:
            list_output = ['"%s"::"%s"' % (machine.name, machine.last_output_cmd)
                           for machine in groupe if machine.etat == 1]
            str_file += "\n".join(list_output)
        flush_file.write(str_file)

    print('flush effectué')
    return


def put(param):
    """envoie un fichier dans un repertoire de destination sur les machines

Usage:
  put [help] <path_file> <path_dir>
  put help
"""
    global groupes, selected_groupes, machines_dict

    doc = put.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)

    if arg['help']:
        print(doc)
        return

    for groupe in selected_groupes:
        groupe.put(arg['<path_file>'], arg['<path_dir>'])

    selected([])
    return


def wol(param):
    """Réveil une machine ou les groupes selectionnées

Usage:
  wol [help] [<machine>]
  wol help
"""
    global groupes, selected_groupes, machines_dict
    doc = wol.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    if arg['<machine>'] is None:
        for groupe in selected_groupes:
            salle.wol()
    else:
        try:
            machines_dict[arg['<machine>']].wol()
        except KeyError:
            print("Le poste n'existe pas")
            return
    print("wol effectué")
    print("lancé la commande update pour mettre à jours l'affichage")
    return


def shutdown(param):
    """Eteint une machine ou les groupes selectionnées

Usage:
  shutdown [help] [<machine>]
  shutdown help
"""
    global groupes, selected_groupes, machines_dict
    doc = shutdown.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    if arg['<machine>'] is None:
        for groupe in selected_groupes:
            salle.shutdown()
    else:
        try:
            machines_dict[arg['<machine>']].shutdown()
        except KeyError:
            print("Le poste n'existe pas")
            return
    print("shutdown effectué")
    print("lancé la commande update pour mettre à jours l'affichage")
    return


class VncViewer:
    _vnc = {}

    def __init__(self):
        raise Exception("Cette classe ne doit pas être instancié")
        return

    @staticmethod
    def open():
        VncViewer.close()
        try:
            VncViewer._vnc['viewer_process'] = subprocess.Popen(
                ['vnc\\vncviewer.exe', '/listen'], stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print("vncviewer n'existe pas")
        return

    @staticmethod
    def close():
        try:
            VncViewer._vnc['viewer_process'].kill()
            VncViewer._vnc['viewer_process'] = None
            VncViewer._vnc = {}
        except (KeyError, AttributeError):
            pass
        finally:
            subprocess.call(["taskkill", "/F", "/IM", "vncviewer.exe"],
                            stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        return


def vnc(param):
    """Lance/ferme une session vnc sur la machine donnée

Usage:
  vnc help
  vnc close <machine>
  vnc <machine>

"""
    global groupes, selected_groupes, machines_dict
    doc = vnc.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    if arg['close']:
        try:
            VncViewer.close()
            machines_dict[arg['<machine>']].vnc_close()
        except KeyError:
            print("La machine n'existe pas")
            return
    else:
        if arg['<machine>']:
            try:
                VncViewer.open()
                machines_dict[arg['<machine>']].vnc_open()
            except KeyError:
                print("La machine n'existe pas")
                VncViewer.close()
                return
    selected([])
    return


def help(param):
    """Pour avoir de l'aide sur une commande : commande help

Commandes :
  selected: affiche les groupes sélectionnées
  select: selectionne les groupes à utliser (voir le fichier conf.ini)
  users: commande pour manipuler les usilisateurs locaux
  update: met à jours les groupes sélectionnées
  run: execute une commande à distance
  cmp: compare les résultats d'une commande run
  errors: affiche les erreurs des machines en rouge
  put: envoie un fichier dans un repertoire de destination sur les machines
  password: demande le mot de passe pour élever ses privilèges
  flush: écrit un fichier csv contenant les résultats de la dernière commande
  wol: allume les machines selectionnées
        (un dossier mac doit être crée pour stocker les adresses mac)
  shutdown: éteint les machines selectionnées
  quit : quitte
"""
    print(help.__doc__)
    return


def errors(param):
    """Affiche les erreurs des machines selectionnées qui sont affichées en rouge.
errors clear efface toutes les erreurs

Usage:
  errors clear
  errors help
  errors [<machine>]

"""
    global groupes, selected_groupes, machines_dict
    str_resultat = ""
    doc = errors.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    if arg['clear']:
        for groupe in selected_groupes:
            for machine in groupe:
                machine.message_erreur = ''
        selected([])
        return
    if arg['<machine>'] is None:
        for groupe in selected_groupes:
            str_resultat += groupe.str_erreurs()
    else:
        try:
            str_resultat = Fore.LIGHTRED_EX + arg['<machine>'] + ': ' +\
                Fore.RESET + '\n' +\
                machines_dict[arg['<machine>']].message_erreur
        except KeyError:
            str_resultat = "Le poste n'existe pas"
    print(str_resultat.strip())
    return


def password(param):
    """Demande le mot de passe du compte mis dans le fichier conf.ini
et élève les privilèges de l'application avec ce compte
L'option uac sert à passer le contrôle uac

Usage:
  password help
  password [uac]

"""
    global domaine
    doc = password.__doc__
    if not domaine or domaine['login'] is None:
        print("Aucun domaine et login dans le fichier conf.ini")
        return

    arg = docopt2.docopt(doc, argv=param, help=False)
    user_pass = getpass.getpass('mot de passe pour le compte %s: ' % domaine['login'])
    uac = arg['uac']
    try:
        Privilege.get_privilege(domaine['login'], user_pass, domaine['name'], uac)
        raise SystemExit()
    except OSError as o:
        str_resultat = Fore.LIGHTRED_EX\
            + "Erreur lors de l'élevation de privilège: "\
            + fix_str(o.strerror) + Fore.RESET
        print(str_resultat)
    return


def quit(param):
    global groupes, selected_groupes, machines_dict

    # pour être sur que le garbage collector nettoie bien tout ceux
    # qui a été laissé par les thread
    groupes.clear()
    selected_groupes.clear()
    machines_dict.clear()
    gc.collect()
    raise SystemExit


def main():
    pass


if __name__ == '__main__':
    main()
