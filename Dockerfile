FROM python:3.11-slim

WORKDIR /tutorcrm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock* ./

RUN uv pip install --system -r pyproject.toml

COPY . .

CMD ["python", "main.py"]