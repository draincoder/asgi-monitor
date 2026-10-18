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

## Set up [uv](https://docs.astral.sh/uv/getting-started/installation/)

Install uv 0.13.1 or newer. Python 3.11–3.14 are supported.
The following command creates `.venv` and installs the locked development dependencies:

```bash
uv sync --all-groups --python 3.14
```

Use `--python 3.11`, `3.12`, or `3.13` to test another supported version.
Commands run through `uv run` do not require activating the environment.

## Install dependencies with [just](https://github.com/casey/just)

```bash
just install
```
or
```bash
uv sync --all-groups
uv run pre-commit install
```

## Running tests

Run tests with the current project Python and dependencies:

```bash
just test
```
or
```bash
uv run pytest tests -q
```

Run the full tox compatibility matrix:

```bash
just full-test
```
or
```bash
uv run tox
```

## Dependency compatibility

Keep runtime lower bounds at tested compatible versions. The development lock file
uses the newest versions within the supported ranges; development tools do not
become dependencies of the published library.

The tox matrix is defined in `pyproject.toml` and uses tox-uv to build and test the
installed wheel in isolated environments:

- `3.11-minimum`: lowest compatible direct dependencies (`lowest-direct`), with
  current compatible transitive dependencies.
- `3.11-latest` through `3.14-latest`: newest compatible dependencies (`highest`).

Requirements are read from `project.dependencies` and the `test`, `asgi`, and
`wsgi` dependency groups. There is no separate list of pinned minimum versions.
Run a single environment or inspect the available ones:

```bash
uv run tox list
uv run tox -e 3.11-minimum
uv run tox -e 3.14-latest
```

Use `uv run tox run --recreate` to resolve fresh dependencies for every environment.
CI runs one test job per tox environment daily at 00:00 UTC and on pushes and pull
requests. Each job recreates its environment and collects coverage and JUnit XML
in the same test run. Test dependencies are resolved independently of `uv.lock`;
the lock file supplies the tox runner. Reproduce the test runs with coverage:

```bash
uv run tox run --recreate -- --cov=asgi_monitor --junitxml=junitxml.xml \
  --cov-report term --cov-report xml:coverage.xml
```

## Running lint

```bash
just lint
```
or
```bash
uv run pre-commit run --all-files
```

## Build documentation

```bash
just doc
```
or
```bash
uv run sphinx-build -M html docs docs-build
echo "Open file://`pwd`/docs-build/html/index.html"
```

## We look forward to your contribution!
