doc_source := "docs"
doc_target := "docs-build"

[private]
@default:
    just --list

# install all depends for developing
@install:
    pdm install -G:all
    pip install -r docs/requirements.txt
    pre-commit install

# run tests
@test:
    pytest tests --cov=asgi_monitor --cov-append --cov-report term-missing -v

# run pre-commit
@lint:
    pre-commit run --all-files

# build documentation
@doc:
    sphinx-build -M html {{ doc_source }} {{ doc_target }}
    echo "Open file://`pwd`/{{ doc_target }}/html/index.html"

# clean generated documentation and build cache
@doc-clean:
    sphinx-build -M clean {{ doc_source }} {{ doc_target }}
