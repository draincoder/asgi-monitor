doc_source := "docs"
doc_target := "docs-build"

[private]
@default:
    just --list

# install all depends for developing
@install:
    uv sync --all-groups
    uv run pre-commit install

# run tests with the current project environment
@test:
    uv run pytest tests --cov=asgi_monitor --cov-append --cov-report term-missing -v

# run the full Python and dependency compatibility matrix
@full-test:
    uv run tox

# run pre-commit
@lint:
    uv run pre-commit run --all-files

# build documentation
@doc:
    uv run sphinx-build -M html {{ doc_source }} {{ doc_target }}
    echo "Open file://`pwd`/{{ doc_target }}/html/index.html"

# clean generated documentation and build cache
@doc-clean:
    uv run sphinx-build -M clean {{ doc_source }} {{ doc_target }}
