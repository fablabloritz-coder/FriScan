# Déploiement FrigoScan avec Docker

## Prérequis
- Serveur Ubuntu avec Docker et Docker Compose installés
- Accès SSH au serveur

## Étapes de déploiement

1. **Copier le dossier FrigoScan sur le serveur**
   
   Exemple :
   ```bash
   scp -r FrigoScan/ user@IP_SERVEUR:/home/user/
   ```

2. **Se connecter au serveur**
   ```bash
   ssh user@IP_SERVEUR
   cd /home/user/FrigoScan
   ```

3. **Construire et lancer le conteneur**
   ```bash
   docker compose up -d --build
   ```

4. **Accéder à l'application**
   - Ouvre un navigateur sur : `http://IP_SERVEUR:8000`

5. **Données persistantes**
   - Les données (BDD, fichiers) sont stockées dans `server/data` sur l'hôte.

6. **Arrêter/redémarrer**
   ```bash
   docker compose stop
   docker compose start
   # ou pour tout relancer :
   docker compose restart
   ```

7. **Mettre à jour l'application**
   - Copier les nouveaux fichiers, puis :
   ```bash
   docker compose up -d --build
   ```

---

**Remarque** :
- Pour changer le port, modifie la section `ports` dans `docker-compose.yml`.
- Pour activer le mode debug, passe `DEBUG=true` dans les variables d'environnement.
