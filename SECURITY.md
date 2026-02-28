# 🔒 Politique de Sécurité — FriScan

## Versions supportées

| Version | Supportée |
|---------|-----------|
| 1.0.x   | ✅ Oui    |

## Signaler une vulnérabilité

Si vous découvrez une vulnérabilité de sécurité dans FriScan, merci de **ne pas** ouvrir une issue publique.

### Comment signaler

1. Ouvrez une **issue privée** sur GitHub (si les Security Advisories sont activés)
2. Ou contactez les mainteneurs directement

### Ce que nous attendons dans votre rapport

- Description de la vulnérabilité
- Étapes pour la reproduire
- Impact potentiel
- Suggestions de correction (si vous en avez)

### Notre engagement

- Nous accuserons réception de votre rapport sous **48 heures**
- Nous fournirons une estimation du délai de correction
- Nous vous tiendrons informé de l'avancement
- Nous vous créditerons dans le fix (sauf si vous préférez rester anonyme)

## Bonnes pratiques de sécurité

FriScan est conçu pour fonctionner **en réseau local**. Voici quelques recommandations :

- **Ne pas exposer** le serveur directement sur Internet sans protection
- **Mettre à jour** régulièrement les dépendances Python
- **Sauvegarder** votre base de données `friscan.db` régulièrement
- Le serveur ne gère pas d'authentification : il est prévu pour un usage **domestique local**

## Dépendances

Nous utilisons des dépendances open-source maintenues activement. Les mises à jour de sécurité sont suivies via `pip audit` et GitHub Dependabot.
