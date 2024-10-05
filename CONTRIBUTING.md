**Development**
After cloning the project, you'll need to set up the development environment. Here are the guidelines on how to do this.

## Virtual Environment with [pdm](https://pdm-project.org/en/latest/)

Create a virtual environment in a directory using Python's `.venv` module:

```bash
pdm use
```
That will create a `./.venv/` directory with Python binaries, allowing you to install packages in an isolated environment.

# Activate the Environment

```bash
source ./.venv/bin/activate
```
## Installing Dependencies

After activating the virtual environment as described above, run:

```bash
just install
```
The link to install [just](https://github.com/casey/just).

If you do not want to install just, then follow these steps:
```bash
    pdm install -G:all
    pip install -r docs/requirements.txt
    pre-commit install
```
## Running Tests
To run tests with your current **ASGI Monitor** application and Python environment, use:

```bash
just test
```
or:

```bash
pytest tests --cov=asgi_monitor --cov-append --cov-report term-missing -v
```

## Running lint
To run lints with your current **ASGI Monitor** application and Python environment, use:
```bash
just lint
```
or:

```bash
pre-commit run --all-files
```
