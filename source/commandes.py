#! python3
# coding: utf-8

import re
import docopt2
import Privilege
import gc
import var_global
import os
import subprocess
import getpass
from Groupe import Groupe
from Salle import Salle
from colorama import Fore
import time
import pathlib

ALLUME = 1


def select(param):
    """Sélectionne les groupes, utiliser * pour tout selectionner
En utilisant select reg il est possible d'utiliser une expression régulière
pour sélectionner les salles
select notag permet de selectionner toutes les machines non tagger
(pour finir une installation avec les logiciels installés depuis le dernier master)

Usage:
  select help
  select notag
  select reg <expression_reg>
  select <nom>...
"""
    doc = select.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    if arg['notag']:
        var_global.selected_machines = [m for name, m
                                        in var_global.machines_dict.items()
                                        if m.etat == ALLUME and m.tag is False]
        groupe_autre = Groupe('AUTRES', [])
        groupe_autre.machines.extend(var_global.selected_machines)
        groupe_autre.machines.sort(key=lambda x: x.name)
        groupe_autre.dict_machines = {m.name: m for m in var_global.selected_machines}
        var_global.selected_groupes = [groupe_autre, ]
    if arg['reg']:
        try:
            pattern = re.compile(arg['<expression_reg>'])
            var_global.selected_groupes = [g for g in var_global.groupes
                                           if pattern.fullmatch(g.name)]
            selected_machines_groupes = [m for g in var_global.selected_groupes
                                         for m in g]
            selected_machines = [m for name, m in var_global.machines_dict.items()
                                 if pattern.fullmatch(name) and
                                 m not in selected_machines_groupes]
            if selected_machines:
                groupe_autre = Groupe('AUTRES', [])
                groupe_autre.machines.extend(selected_machines)
                groupe_autre.machines.sort(key=lambda x: x.name)
                groupe_autre.dict_machines = {m.name: m for m in selected_machines}
                var_global.selected_groupes.append(groupe_autre)
        except re.error:
            print("L'expression régulière n'est pas valide")
    if arg['<nom>']:
        if '*' in arg['<nom>']:
            var_global.selected_groupes = var_global.groupes
        else:
            # on sélectionne les groupes de la commande select
            var_global.selected_groupes = [g for g in var_global.groupes
                                           if g.name in arg['<nom>']]
            # on récupère les noms des machines déja mis dans les groupes selectionnés
            selected_machines_groupes = [m.name
                                         for g in var_global.selected_groupes
                                         for m in g]
            # on sélectionne les machines de la commande select sauf si elles
            # existent déja dans un groupe
            selected_machines = [m for name, m in var_global.machines_dict.items()
                                 if name in arg['<nom>'] and
                                 m not in selected_machines_groupes]
            # si la liste des machines à sélectionner n'est pas vide
            # on crée le groupe AUTRES
            if selected_machines:
                groupe_autre = Groupe('AUTRES', [])
                groupe_autre.machines.extend(selected_machines)
                groupe_autre.machines.sort(key=lambda x: x.name)
                groupe_autre.dict_machines = {m.name: m for m in selected_machines}
                var_global.selected_groupes.append(groupe_autre)
    machines = [m for g in var_global.selected_groupes for m in g]
    var_global.groupe_selected_machines.machines = machines
    var_global.groupe_selected_machines.dict_machines = {m.name: m for m in machines}
    var_global.groupe_selected_machines.machines.sort(key=lambda x: x.name)
    var_global.selected_groupes.sort(key=lambda x: x.name)
    selected([])
    return


def selected(param):
    """Affiche les groupes sélectionnées
en vert la machine est allumée
en mauve la machine est allumée mais  n'a pas de tag_file (elle a du être re-installée)
en gris la machine est éteinte
en rouge la machine a un message d'erreur (utiliser errors pour l'afficher)

Usage:
  selected [help]
"""
    doc = selected.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        return print(doc)
    if var_global.selected_groupes == []:
        print('Auncun groupe sélectionné')
    else:
        print('-' * (os.get_terminal_size().columns - 1))
        print("\n".join([g.str_groupe() for g in var_global.selected_groupes]).strip())
    return


def update(param):
    """Met à jour les stations allumées ou éteintes des groupes selectionnées

Usage:
  update [help]
"""
    doc = update.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return

    groupes_machines_names = {}
    # on recupere le lien nom de groupe nom de machine
    # dans les groupes selectionnés
    for g in var_global.selected_groupes:
        groupes_machines_names[g.name] = list(g.dict_machines)

    # on met à jour les machines selectionnées
    var_global.groupe_selected_machines.update()
    var_global.machines_dict.update(var_global.groupe_selected_machines.dict_machines)

    # on enleve les groupes qui vont être mis à jour de la liste des groupes
    var_global.groupes = [g for g in var_global.groupes
                          if g not in var_global.selected_groupes]

    # on efface selected_groupe qui sera mis à jour après
    copy_selected_groupes = var_global.selected_groupes.copy()
    var_global.selected_groupes.clear()

    # on crée et initialise les groupes à jours
    for groupe in copy_selected_groupes:
        if type(groupe) == Salle:
            g = Salle(groupe.name, 0)
        else:
            g = Groupe(groupe.name, [])
        machines = [i for k, i in var_global.machines_dict.items()
                    if k in groupes_machines_names[g.name]]
        g.machines = machines
        g.dict_machines = {m.name: m for m in machines}
        g.machines.sort(key=lambda x: x.name)
    # on ajoute les nouveaux groupes dans la liste des groupes sauf
    # si c'est le groupe AUTRES et dans selected_groupes
        var_global.selected_groupes.append(g)
        if groupe.name == "AUTRES":
            continue
        var_global.groupes.append(g)

    # code ansi pour remonter le curseur : c'est plus jolie
    up = len(var_global.selected_groupes)
    print('\x1b[%sA' % up)

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
  users logged
  users chpass <name> <password>
  users groupes <name>
  users help
"""
    doc = users.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    str_resultat = ""
    if arg['help']:
        print(doc)
        return

    if arg['add']:
        grpes = ['Administrateurs'] if arg['<admin>'] == 'admin'\
            else ['Utilisateurs']
        var_global.groupe_selected_machines.add_user(arg['<name>'],
                                                     arg['<password>'], grpes)
    if arg['del']:
        var_global.groupe_selected_machines.del_user(arg['<name>'])
    if arg['chpass']:
        var_global.groupe_selected_machines.chpwd_user(arg['<name>'],
                                                       arg['<password>'])

    for groupe in var_global.selected_groupes:
        if arg['show']:
            str_resultat += groupe.str_users()
        if arg['logged']:
            str_resultat += groupe.str_logged()
        if arg['groupes']:
            str_resultat += groupe.str_user_groups(arg['<name>'])

    if str_resultat != '':
        print('-' * (os.get_terminal_size().columns - 1))
        print(str_resultat.strip().encode("cp850", "replace").decode("cp850", "replace"))
    else:
        selected([])
    return


def run(param):
    """Execute une commande ou un fichier à distance
run file permet de lancer un executable à distance
run clear nettoie les repertoires laissés sur la machine
(arrive si le programme plante ou lors de l'utilisation
de l'option --no-wait)

Usage:
  run cmd <commande> [<parametre>...] [--param=<param>] [--timeout=t] [--no-wait]
  run file <nom_fichier> [<option>...] [--param=<param>] [--timeout=t] [--no-wait]
  run clean
  run help

Options:
    --timeout=<t>    temps pour attendre la fin de l'execution en seconde
    --no-wait        si l'option est spécifié, on n'attend pas la réponse de la commande
    --param=<param>  permet de passer des parametres avec un tirer.
                     On peut utiliser les "" pour passer plusieurs parametres
"""
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
        var_global.groupe_selected_machines.run_remote_cmd(cmd, timeout, arg["--no-wait"])
        selected([])
    if arg['file']:
        var_global.groupe_selected_machines.run_remote_file(arg['<nom_fichier>'],
                               " ".join(arg['<option>'] + [arg['--param'].strip('"')]),
                               timeout,
                               arg["--no-wait"])
        selected([])
    if arg['clean']:
        var_global.groupe_selected_machines.clean()
        for f in os.listdir():
            if re.fullmatch(r'^todel[0-9]{1,4}[0-9|a-f]{32}$', f):
                subprocess.call(['rd', '/s', '/q', f], shell=True)
        selected([])
    return


def result(param):
    """afficher le résultat de la derniere commande exécutée

Usage:
  result help
  result mix
  result <machine>
  """
    doc = result.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    if arg['mix']:
        list_result = []
        selected_machines = [m for g in var_global.selected_groupes for m in g]
        for m in selected_machines:
            list_result.extend(m.last_output_cmd.split("\n"))
        set_result = set(list_result)
        list_result = list(set_result)
        list_result.sort(key=lambda s: s.lower())
        str_result = "\n".join(list_result)
        print(str_result.encode("cp850", "replace").decode("cp850", "replace"))
        return

    if arg['<machine>'] in var_global.machines_dict.keys():
        str_resultat = var_global.machines_dict[arg['<machine>']].last_output_cmd \
            if var_global.machines_dict[arg['<machine>']].last_output_cmd != "" \
            else "Aucun resultat à afficher"
        print(str_resultat.strip().encode("cp850", "replace").decode("cp850", "replace"))
    else:
        print("%s n'existe pas" % arg['<machine>'])
    return


def prog(param):
    """permet d'agir sur les programmes installés des machines
il faut utiliser la commande result pour voir le résultat
de la commande
prog uninstall: désinstalle un programme (nom entre "" si il y a des espaces)
prog list: liste les programmes. Si un filtre est donné, n'affiche que les
programmes qui contiennent le filtre
les logiciels affichés en vert peuvent être désinstallé avec prog uninstall
les logiciels affichés en rouge nécessite une commande particulière
après avoir lancé prog uninstall, utiliser la commande result pour
afficher la commande de desinstallation

Usage:
  prog help
  prog list [<filter>]
  prog uninstall <logiciel>

"""
    doc = prog.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    print("Cette commande peut prendre du temps pour se terminer")
    print()
    if arg['list']:
        try:
            arg['<filter>'] = arg['<filter>'].strip('"')
        except AttributeError:
            pass
        var_global.groupe_selected_machines.str_prog(arg['<filter>'])
    if arg['uninstall']:
        print("Si le programme a desinstaller était rouge dans prog list")
        print("Utiliser la commande result pour afficher la commande spécifique pour desinstaller")
        print("(Utiliser run cmd pour lancer cette commande)")
        print("(Pour une desinstallation silencieuse penser à /S ou /silent)")
        if arg['<logiciel>']:
            var_global.groupe_selected_machines.uninstall(arg['<logiciel>'].strip('"'))
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
    doc = cmp.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    str_resultat = 'Comparaison des résultats de la dernière commande exécutée:\n\n'
    if arg['help']:
        print(doc)
        return
    try:
        str_ref = var_global.machines_dict[arg['<nom_machine>']].last_output_cmd
    except KeyError:
        print("la machine n'existe pas")
        return
    str_resultat += "\n".join([groupe.str_cmp(str_ref, int(arg['--seuil']))
                               for groupe in var_global.selected_groupes])
    print(str_resultat)
    return


def flush(param):
    """Ecris tous les résultats des machines sélectionnées dans un fichier csv

Usage:
  flush [help]
"""
    doc = flush.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)

    if arg['help']:
        print(doc)
        return

    str_file = ''
    with open("flush.csv", 'w') as flush_file:
        for groupe in var_global.selected_groupes:
            list_output = ['"%s"::"%s"' % (machine.name, machine.last_output_cmd)
                           for machine in groupe if machine.etat == ALLUME]
            str_file += "\n".join(list_output) + "\n"
        flush_file.write(str_file)

    print('flush effectué')
    return


def put(param):
    """envoie un fichier dans un repertoire de destination sur les machines

Usage:
  put [help] <path_file> <path_dir>
  put help
"""
    doc = put.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)

    if arg['help']:
        print(doc)
        return
    var_global.groupe_selected_machines.put(arg['<path_file>'], arg['<path_dir>'])

    selected([])
    return


def wol(param):
    """Réveil les groupes selectionnées

Usage:
  wol [help]
"""
    doc = wol.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    var_global.groupe_selected_machines.wol()
    print("wol effectué")
    print("lancé la commande update pour mettre à jours l'affichage")
    return


def shutdown(param):
    """Eteint une machine ou les groupes selectionnées

Usage:
  shutdown [help]
"""
    doc = shutdown.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    var_global.groupe_selected_machines.shutdown()
    print("shutdown effectué")
    print("lancé la commande update pour mettre à jours l'affichage")
    return


class VncViewer:
    _vnc = {}
    # process du viewer
    _vnc['viewer_process'] = None
    # ref sur la derniere machine qui a eu une session vnc
    _vnc['old_machine_connection'] = None

    def __init__(self):
        raise Exception("Cette classe ne doit pas être instancié")
        return

    @staticmethod
    def open():
        VncViewer.close()
        try:
            VncViewer._vnc['viewer_process'] = subprocess.Popen(
                ['vnc\\vncviewer.exe', '/listen'], stderr=subprocess.DEVNULL)
            print('viewer lancé')
        except FileNotFoundError:
            print("vncviewer n'existe pas")
        return

    @staticmethod
    def close():
        # c'est un peu beaucoup pour fermer un process ...
        try:
            VncViewer._vnc['viewer_process'].kill()
            VncViewer._vnc['viewer_process'] = None
        except (KeyError, AttributeError):
            pass
        finally:
            subprocess.call(["taskkill", "/F", "/IM", "vncviewer.exe"],
                            stderr=subprocess.DEVNULL)
            try:
                VncViewer._vnc['old_machine_connection'].vnc_close()
            except:
                pass
        return


def vnc(param):
    """Lance/ferme une session vnc sur la machine donnée

Usage:
  vnc help
  vnc close <machine>
  vnc <machine>
"""
    doc = vnc.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    if arg['close']:
        try:
            VncViewer.close()
            var_global.machines_dict[arg['<machine>']].vnc_close()
        except KeyError:
            print("La machine n'existe pas")
            return
    else:
        if arg['<machine>']:
            try:
                VncViewer.open()
                VncViewer._vnc["old_machine_connection"] = var_global.machines_dict[arg['<machine>']]
                var_global.machines_dict[arg['<machine>']].vnc_open(os.getenv('COMPUTERNAME'))
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
  users: commande pour manipuler les utilisateurs locaux
  update: met à jours les groupes sélectionnées
  run: execute une commande à distance
  result: affiche le résultat de la dernière commande d'une machine donnée
  prog: liste les logiciels et peut désinstaller un programme donnée.
  cmp: compare les résultats d'une commande run
  errors: affiche les erreurs des machines en rouge
  put: envoie un fichier dans un repertoire de destination sur les machines
  password: demande le mot de passe pour élever ses privilèges
  flush: écrit un fichier csv contenant les résultats de la dernière commande
  tag: permet de tagger les machines avec un fichier texte
  vnc: lance une session vnc sur la machine sélectionnée
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
    str_resultat = ""
    doc = errors.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    if arg['clear']:
        for groupe in var_global.selected_groupes:
            for machine in groupe:
                machine.message_erreur = ''
        selected([])
        return
    if arg['<machine>'] is None:
        for groupe in var_global.selected_groupes:
            str_resultat += groupe.str_erreurs()
    else:
        try:
            str_resultat = Fore.LIGHTRED_EX + arg['<machine>'] + ': ' +\
                Fore.RESET + '\n' +\
                var_global.machines_dict[arg['<machine>']].message_erreur
        except KeyError:
            str_resultat = "Le poste n'existe pas"
    print(str_resultat.strip().encode("cp850", "replace").decode("cp850", "replace"))
    return


def password(param):
    """Demande le mot de passe du compte mis dans le fichier conf.ini
et élève les privilèges de l'application avec ce compte
L'option uac sert à passer le contrôle uac

Usage:
  password help
  password [uac]

"""
    doc = password.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return
    if not var_global.domaine or var_global.domaine['login'] is None:
        print("Aucun domaine et login dans le fichier conf.ini")
        var_global.domaine['name'] = input('domaine: ')
        var_global.domaine['name'] = var_global.domaine['name'] or None
        var_global.domaine['login'] = input('login: ')
        var_global.domaine['login'] = var_global.domaine['login'] or None
        if var_global.domaine['login'] is None:
            return
    user_pass = getpass.getpass('mot de passe pour le compte %s: ' % var_global.domaine['login'])
    uac = arg['uac']
    try:
        Privilege.get_privilege(var_global.domaine['login'],
                                user_pass, var_global.domaine['name'], uac)
        raise SystemExit(0)
    except OSError as o:
        str_resultat = Fore.LIGHTRED_EX\
            + "Erreur lors de l'élevation de privilège: "\
            + o.strerror + Fore.RESET
        print(str_resultat.encode("cp850", "replace").decode("cp850", "replace"))
    return


def tag(param):
    """tag les machines selectionnées en posant un fichier txt
dans c:
Cette commande permet d'identifier les machines qui viennent d'être
re-installées et qui n'ont pas le tag. Elles sont de couleur mauve.
Les tag sont datés, tag cmp permet de comparer les tag avec le dernier
fichier tag crée

Usage:
  tag [help]
  tag [cmp]
"""
    doc = tag.__doc__
    arg = docopt2.docopt(doc, argv=param, help=False)
    if arg['help']:
        print(doc)
        return

    if arg['cmp']:
        local_path = pathlib.Path('.')
        try:
            file_name = list(local_path.glob("tag_file_*"))[0].name
        except IndexError:
            file_name = ''
        var_global.groupe_selected_machines.run_remote_cmd("dir /B c:\\" + file_name)
        str_resultat = "\n".join([groupe.str_cmp(file_name, 100)
                                  for groupe in var_global.selected_groupes])
        print()
        print("les machines en rouge n'ont pas le même tag utilisé lors de la dernière commande tag")
        print(str_resultat)
        return

    var_global.groupe_selected_machines.run_remote_cmd("del c:\\tag_file_*")
    subprocess.call("del tag_file_*", shell=True, stderr=subprocess.DEVNULL)
    name_file = "tag_file_" + str(int(time.time()))
    tag_file = open(name_file, "w")
    tag_file.close()
    var_global.groupe_selected_machines.put(name_file, "c:\\")
    for m in var_global.groupe_selected_machines:
        m.tag = True

    selected([])
    return


def quit(param):
    # pour être sur que le garbage collector nettoie bien tout ceux
    # qui a été laissé par les thread
    var_global.groupes.clear()
    var_global.selected_groupes.clear()
    var_global.machines_dict.clear()
    var_global.groupe_selected_machines = None
    gc.collect()
    raise SystemExit(0)


def main():
    pass


if __name__ == '__main__':
    main()
