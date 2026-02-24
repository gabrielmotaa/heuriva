<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="heuriva/static/assets/logo-light.svg">
    <source media="(prefers-color-scheme: light)" srcset="heuriva/static/assets/logo-dark.svg">
    <img alt="Heuriva Logo" src="heuriva/static/assets/logo-dark.svg" width="400">
  </picture>
</p>

# Heuriva

Automated Usability and UX Auditing.

## About

Heuriva is an open-source platform designed to automate and enhance web interface analysis. By leveraging Large Language Models (LLMs), Heuriva scrapes web pages and performs comprehensive heuristic evaluations on both code and visual screenshots. Our mission is to provide developers and designers with rapid, actionable insights to improve usability and UX without the manual overhead of traditional audits.

## Tech Stack

- **Python 3.13**
- **Django 5.2**
- **TailwindCSS**
- **LLM Integration** (currently only Google Gemini)

## Getting Started

### Prerequisites

- Docker and Docker Compose installed on your system
- Git
- UV

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/gabrielmotaa/heuriva.git
   cd heuriva
   ```

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

3. Install UV and create a virtual environment (for linking with vscode python interpreter)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv sync
   ```

4. Install prek and hook it into git
   ```bash
   uvx prek install
   ```

5. Start the development server with hot reload:
   ```bash
   docker compose watch
   ```

The application will be available at `http://localhost:8000`

### Docker Commands

- **Start the project with hot reload**: `docker compose watch`
- **Start the project normally**: `docker compose up`
- **Stop the project**: `docker compose down`
- **Stop and remove volumes**: `docker compose down -v`

## Development

The project uses Docker Compose watch mode for development, which automatically syncs your code changes to the container and rebuilds when dependencies change.

## Project Structure

This Django project follows a modular architecture with apps organized in a dedicated `apps` folder:

```
heuriva/
├── manage.py
├── heuriva/
│   ├── settings/
│   │   ├── base.py
│   │   └── local.py
│   ├── apps/
│   │   ├── accounts/
│   │   ├── pages/
│   │   └── ... (other apps)
│   ├── static/
│   ├── templates/
│   ├── urls.py
│   └── wsgi.py
└── ... (config files)
```

## Creating a New Django App

All Django apps must be created inside the `heuriva/apps/` directory. Follow these steps:

1. **Create the app folder**:
   ```bash
   mkdir heuriva/apps/myapp
   ```

2. **Generate the app structure**:
   ```bash
   uv run manage.py startapp myapp heuriva/apps/myapp
   ```

3. **Update the app `AppConfig`** in `heuriva/apps/myapp/apps.py`:
   ```python
   # Change the name attribute from:
   name = "myapp"
   # To:
   name = "heuriva.apps.myapp"
   ```

4. **Register the app** in the settings file (`heuriva/settings/base.py`):
   ```python
   INSTALLED_APPS = [
       # ...
       "heuriva.apps.myapp",
   ]
   ```

> **Important**: Always use the full dotted path `heuriva.apps.myapp` when referencing apps to maintain proper module resolution.

## Internationalization (i18n)

This project supports Portuguese Brazilian (pt-BR) translations. The translation files are located in `heuriva/locale/`.

### Updating Translations

When you add or modify translatable strings in your code, follow these steps:

1. **Extract translatable strings**:
   ```bash
   uv run manage.py makemessages -l pt_BR
   ```

2. **Edit the translation file** at `heuriva/locale/pt_BR/LC_MESSAGES/django.po` and add your translations.

3. **Compile the translations**:
   ```bash
   uv run manage.py compilemessages
   ```
