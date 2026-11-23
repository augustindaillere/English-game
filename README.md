# GreenFlag, site compagnon (V1)

Site statique en anglais, aligné sur le plateau de 30 cases : une page d'accueil avec le bouton "Start a game", un sommaire (contents.html), une page par case colorée (13), 5 pages "Go further", une page "How to play" et une page "About".
Pas de base de données, pas de JavaScript, pas de dépendance externe (environ 400 Ko au total).

## Structure

```
content/tiles.json   <- tout le texte des cases (à modifier ici)
assets/style.css     <- le style (variables de couleurs en haut du fichier, pour la future maquette)
assets/flag.svg      <- logo / favicon
build.py             <- génère le site dans dist/
dist/                <- le site prêt à mettre en ligne (généré, ne pas modifier à la main)
```

## Générer le site

Python 3 suffit (aucune bibliothèque nécessaire, sauf pour les QR codes).

```bash
python3 build.py                                   # génère dist/
pip install qrcode                                  # une seule fois, pour les QR codes
python3 build.py --base-url https://VOTRE-URL/greenflag   # + QR codes dans dist/qr/ et dist/print.html
python3 build.py --base-url https://VOTRE-URL/greenflag --hide-checks   # version finale sans les étiquettes "to verify"
```

`dist/print.html` est une page imprimable avec, pour chaque case du plateau, le texte court du plateau et son QR code.
Les QR codes pointent vers `<base-url>/tiles/<id>.html` : l'id ne doit donc plus changer une fois les QR imprimés.

Tester en local : `cd dist && python3 -m http.server 8000` puis ouvrir http://localhost:8000

## Modifier le contenu

Dans `content/tiles.json`, chaque case a :
- `id` : nom dans l'URL (ne pas changer après impression des QR codes)
- `tile` : numéro de la case sur le plateau (`null` = page "Go further", hors plateau)
- `type` : `good`, `bad` ou `finish` ; `effect` : l'effet écrit sur la case ("Double your move", "Back to tile 14"...)
- `board` : la phrase courte imprimée sur le plateau
- `intro`, `sections` (avec `text`, `facts` ou `list`), `related`, `sources`
- `"check": true` sur un chiffre = à vérifier (affiche une étiquette jaune "to verify")

Puis relancer `python3 build.py`.

## Mise en ligne (comme crazydev)

Même méthode que crazydev : à chaque push sur `main`, GitHub Actions construit et vérifie le site, puis se connecte au VPS en SSH et lance `scripts/deploy.sh`.
Ce script met à jour le dépôt dans `/opt/english-game` et relance le conteneur Docker (Nginx avec le site), publié sur `127.0.0.1:8080`.
Le Nginx du VPS (`/etc/nginx/sites-available/crazydev`) redirige déjà ce port vers `augustin-daillere.angers.mds-project.fr`, donc rien à changer côté Nginx.

### Mise en place (une seule fois)

1. Dans GitHub, dépôt English-game > Settings > Secrets and variables > Actions, recréer les mêmes secrets que crazydev :
   `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_KNOWN_HOSTS`.
2. Sur le VPS :
   ```bash
   cd /opt/crazydev && docker compose down          # arrête crazydev (libère le port 8080, rien n'est supprimé)
   sudo git clone https://github.com/augustindaillere/English-game.git /opt/english-game
   sudo chown -R $USER /opt/english-game
   cd /opt/english-game && docker compose up -d --build
   ```
3. Ensuite, chaque push sur `main` met le site à jour automatiquement.

Revenir à crazydev : `cd /opt/english-game && docker compose down && cd /opt/crazydev && docker compose up -d`.

## À faire avant la version finale

- Vérifier les chiffres marqués "to verify" et tous les liens des sources (ils n'ont pas pu être testés pendant la rédaction).
- Ajouter les sources de votre recherche "green IT et eco design".
- Appliquer la maquette : commencer par les variables en haut de `assets/style.css`.

