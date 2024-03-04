## Start example in Docker

```shell
docker compose -f examples/real_world/docker-compose.yaml --profile api --profile grafana up --build -d
```

## Stop example in Docker

```shell
docker compose -f examples/real_world/docker-compose.yaml --profile api --profile grafana down
```

## Interfaces

1. Grafana - http://127.0.0.1:3000/
2. Swagger - http://127.0.0.1:8080/docs/
