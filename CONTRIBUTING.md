# Development

After cloning the project, you'll need to set up the development environment. Here are the guidelines on how to do this.

The development workflow should look like this:
- Add feature/fix bug
- Run tests
- Add tests
- Run tests
- Lint
- Add docs
- Open PR

## Create venv with [PDM](https://pdm-project.org/en/latest/)

```bash
pdm venv create 3.10
```

## Activate venv

```bash
source .venv/bin/activate
```

## Install dependencies with [just](https://github.com/casey/just)

```bash
just install
```
or
```bash
pdm install -G:all
pip install -r docs/requirements.txt
pre-commit install
```

## Running tests

```bash
just test
```
or
```bash
pytest tests --cov=asgi_monitor --cov-append --cov-report term-missing -v
```

## Running lint

```bash
just lint
```
or
```bash
pre-commit run --all-files
```

## Build documentation

```bash
just doc
```
or
```bash
sphinx-build -M html docs docs-build
echo "Open file://`pwd`/docs-build/html/index.html"
```

## We look forward to your contribution!
