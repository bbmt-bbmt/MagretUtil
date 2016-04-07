# MagretUtil
psexec like pour réseaux Magret

# liste des commandes disponible
pour afficher l'aide d'une commande
```
commande help
```
Les options entre <> sont obligatoires.
Les options entre [] sont facultatives.


## selected
affiche les salles sélectionné


vert  -> la machine est allumée

gris  -> la machine est éteinte

rouge -> la machine est en erreur

## select
selectionne les salles où les prochaines commandes agiront
```
select <salle>
select *
```

## users
Modifie les utilisateurs sur les stations sélectionnées

ajouter un utilisateur:
```
users add <name> <password> [<admin>]  
```
effacer un utilisateur:
```
users del <name> 
```
afficher tous les utilisateurs:
```
users show
``` 
gris -> utilisateur désactivé | vert -> utilisateur actif | asterix rouge -> l'utilisateur est administrateur
changer le password de l'utilisateur:
```
users chpass <name> <password>
```
afficher tous les groupes d'un utilisateur
```
users groupes <name>
```

## update
met à jours les salles sélectionnées

## run
lance une commande ou un executable à distance

lancer une commande dos:
```
run cmd <commande> [<parametre>...] [--param=<param>] [--timeout=t] [--no-wait]
```
lancer un executable:
```
run file <nom_fichier> [<option>...] [--param=<param>] [--timeout=t] [--no-wait]
```
afficher le résultat de la dernière commande d'une machine
```
run result <machine>
```
nettoyer le dossier resté sur la machine lors d'erreur ou de l'utilisation de --no-wait
```
run clean
```

Explication des options:
```
--timeout=<t>    temps pour attendre la fin de l'execution en seconde
--no-wait        si l'option est spécifié, on n'attend pas la réponse de la commande
--param=<param>  permet de passer des parametres avec un tirer.
                 On peut utiliser les "" pour passer plusieurs parametres
```

## cmp
Compare le resultat de la commande run par rapport au resultat d'une machine donnée
```
cmp <nom_machine> [--seuil=s]
```
Explicatio  des options:
```
--seuil=s  le seuil en pourcentage d'acceptation
           ou de rejet pour la comparaison [default: 100]
```

## put
envoie un fichier dans un répertoire donné sur la machine distante:
```
put <path_file> <path_dir>
```

## flush
écrit tous les résultats (après une commanderun) des machines selectionnées dans un fichier csv
```
flush
```

## errors
affiche ou efface les erreurs des machines en rouge
```
errors <machine>
errors *
errors clear
```

## wol
allume les machines selectionnées. Un dossier mac doit être crée pour stocker les adresses mac lorsque la machine est vue pour la première fois.
```
wol <machine>
wol *
```

## shutdown
éteint les machines sélectionnées
```
shutdown <machine>
shutdown *
```

## quit
quitte

# Exemple
On selectionne toutes les salles mis dans le fichier conf.ini
```
select *
```
on execute une commande dos:
```
run cmd ipconfig|findstr /R "Passerelle"
```
on affiche le résultat de la commande du poste SDE-P01
```
run result SDE-P01
```
on compare le resultat avec les machines selectionnées
```
cmp SDE-P01
```
on execute flash.exe avec l'option -install sans attendre le résultat de la commande
```
run file flash.exe --param=-install --no-wait
```
on nettoie les dossiers resté sur les machines
```
run clean
```
on affiche les erreurs éventuelles:
```
errors *
```

