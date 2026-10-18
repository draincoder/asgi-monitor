FROM python:3.14-slim-bookworm AS python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv

RUN uv venv $VENV_PATH
ENV PATH="$VENV_PATH/bin:$PATH"

FROM python-base AS builder-base
RUN apt-get update && apt-get install -y gcc git

WORKDIR $PYSETUP_PATH
COPY requirements.txt .

RUN uv pip install --no-cache --python $VENV_PATH/bin/python -r requirements.txt

FROM python-base AS production
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH
RUN apt-get update && apt-get install -y curl

WORKDIR /app
COPY ./app /app/app

ENTRYPOINT ["python", "-Om", "app.main"]
