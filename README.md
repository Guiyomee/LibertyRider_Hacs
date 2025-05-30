# Liberty Rider

![Version](https://img.shields.io/badge/version-0.0.1-blue)
![Home Assistant](https://img.shields.io/badge/home_assistant-2025.5.3+-blue)

Liberty Rider est une intégration personnalisée pour Home Assistant qui permet de récupérer et afficher des données du service Liberty Rider via une intégration native.

---

## Fonctionnalités

- Récupération des données utilisateur Liberty Rider
- Support de la configuration via le flux de configuration (`config_flow`)
- Mise à jour automatique avec `aiohttp` et `beautifulsoup4`
- Support multilingue (fr/en)

---

## Installation

### Via HACS (recommandé)

1. Assurez-vous d’avoir installé HACS dans Home Assistant.
2. Ajoutez le dépôt suivant comme dépôt personnalisé dans HACS :  
   `https://github.com/Guiyomee/LibertyRider_Hacs`
3. Installez l’intégration depuis HACS.
4. Redémarrez Home Assistant.
5. Configurez l’intégration via l’interface utilisateur dans Configuration → Intégrations.

### Manuellement

1. Téléchargez ce dépôt.
2. Copiez le dossier `custom_components/liberty_rider` dans le répertoire `config/custom_components/` de Home Assistant.
3. Redémarrez Home Assistant.
4. Configurez l’intégration via l’interface utilisateur.

---

## Configuration

- La configuration se fait via l’interface graphique, pas besoin d’éditer `configuration.yaml`.
- Suivez les instructions à l’écran pour connecter votre compte Liberty Rider.

---

## Dépendances

- `aiohttp`
- `beautifulsoup4`

---

## Contribution

Les contributions sont les bienvenues !  
Merci de respecter la structure du projet et les bonnes pratiques Home Assistant.

---

## Contact

Créé par [Guiyomee](https://github.com/Guiyomee)