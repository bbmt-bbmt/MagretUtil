# MagretUtil
psexec like utilisant wmi pour réseaux Magret.

Le logiciel est multithreadé par salle.

Toutes les versions : [release](https://github.com/bbmt-bbmt/MagretUtil/releases)

lien pour télécharger la dernière version:
[zip-file](https://github.com/bbmt-bbmt/MagretUtil/releases/download/latest/MagretUtil-v0.3-32.zip)


# liste des commandes disponible
pour afficher l'aide d'une commande
```
commande help
```
Les options entre <> sont obligatoires.
Les options entre [] sont facultatives.


## selected
Affiche les salles sélectionnées.


vert  -> la machine est allumée et taggée

mauve -> la machine est allumée et non taggée

jaune -> la machine est allumée et taggée mais le tag est plus ancien que le dernier tag utilisé

gris  -> la machine est éteinte

rouge -> la machine est en erreur

## select
Selectionne les salles, machines où les prochaines commandes agiront.

On peut passer une expression régulière

select notag permet de choisir toutes les machines non taggées
```
select salle1 salle2 machine1 machine2
select *
select reg .*(1|2)
select notag
```

## users
Modifie les utilisateurs sur les stations sélectionnées.

Le mot clé admin à la fin de la commande permet de mettre l'utilisateur dans le groupe Administrateur

Ajouter un utilisateur:
```
users add <name> <password> [<admin>]  
```
Effacer un utilisateur:
```
users del <name> 
```
Afficher tous les utilisateurs:
```
users show
``` 
gris -> utilisateur désactivé | vert -> utilisateur actif | asterix rouge -> l'utilisateur est administrateur

Changer le password de l'utilisateur:
```
users chpass <name> <password>
```
Afficher tous les groupes d'un utilisateur
```
users groupes <name>
```
Afficher les utilisateurs connectés sur les machines selectionnées
```
users logged
```

## update
Met à jours les salles sélectionnées.

## run
Lance une commande dos ou un executable à distance.

Lancer une commande dos:
```
run cmd <commande> [<parametre>...] [--param=<param>] [--timeout=t] [--no-wait]
```
Lancer un executable:
```
run file <nom_fichier> [<option>...] [--param=<param>] [--timeout=t] [--no-wait]
```
Nettoyer le dossier resté sur la machine lors d'erreurs ou de l'utilisation de --no-wait
```
run clean
```

Explications des options:
```
--timeout=<t>    temps pour attendre la fin de l'execution en seconde
--no-wait        si l'option est spécifiée, on n'attend pas la réponse de la commande
--param=<param>  permet de passer des parametres avec un tiret.
                 On peut utiliser les "" pour passer plusieurs parametres
```

## result
Afficher le résultat de la dernière commande d'une machine
result mix affiche le resultat de toutes les machines mélangés sans doublon
```
result <machine>
result mix
```

## cmp
Compare le resultat de la commande run par rapport au resultat d'une machine donnée
```
cmp <nom_machine> [--seuil=s]
```
Explications  des options:
```
--seuil=s  le seuil en pourcentage d'acceptation
           ou de rejet pour la comparaison [default: 100]
```

## put
Envoie un fichier dans un répertoire donné sur la machine distante:
```
put <path_file> <path_dir>
```

## flush
Ecrit tous les résultats (après une commande run) des machines selectionnées dans un fichier csv
```
flush
```

## errors
Affiche ou efface les erreurs des machines affichées en rouge
```
errors <machine>
errors
errors clear
```

## tag
tag les machines sélectionnées en mettant un fichier texte sur c:
```
tag [help]
```

## wol
Allume les machines selectionnées. Un dossier mac doit être crée pour stocker les adresses mac lorsque la machine est vue pour la première fois.
```
wol
```

## shutdown
Eteint les machines sélectionnées.
```
shutdown
```

## vnc
Lance/ferme une session vnc (ultravnc) sur la machine sélectionnée
```
vnc <machine>
vnc close <machine>
```

## password
Lance la procédure d'élévation de privilège si on n'est pas connecté en administrateur du domaine.
Avec l'option uac, l'élévation de privilège tente de bypasser le contrôle utilisateur (uac).
```
password
password uac
```

## prog
Liste ou désinstalle un programme donné
Les programmes affichés en vert peuvent être désinstallé directement avec prog uninstall
Les programmes affichés en rouge nécessitent une commande spécifique. 
Il faut alors lancer prog uninstall logiciel_rouge puis result nom_machine pour avoir cette commande
```
prog list 
prog list java -> liste les programmes contenant java dans leur nom
pro uninstall scratch -> desinstalle le programme contenant scratch dans son nom
```

## quit
quitte

## Exemples
On selectionne toutes les salles mises dans le fichier conf.ini:
```
select *
```
On affiche les comptes utilisateurs des machines sélectionnées:
```
users show
```
On créé un compte administrateur sur les machines sélectionnées:
```
users add testadmin passtestadmin admin
```
On execute une commande dos:
```
run cmd ipconfig|findstr /R "Passerelle"
```
On affiche le résultat de la commande du poste SDE-P01:
```
result SDE-P01
```
On compare le resultat avec les machines selectionnées:
```
cmp SDE-P01
```
On execute flash.exe avec l'option -install sans attendre le résultat de la commande:
```
run file flash.exe --param=-install --no-wait
```
On nettoie les dossiers restés sur les machines:
```
run clean
```
On affiche les erreurs éventuelles:
```
errors
```
On recherche les programmes installés puis on les affichent:
```
prog list
result SDE-P01
```



