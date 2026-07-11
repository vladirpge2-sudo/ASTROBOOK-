# AstroLivro Swiss API

API em FastAPI para cálculo de mapa natal com Swiss Ephemeris.

## Rotas

- `GET /health`
- `POST /natal-chart`
- `POST /natal-chart/coordinates`
- Documentação automática: `/docs`

## Exemplo

```json
{
  "name": "Vladir Fernandes",
  "date": "1990-10-06",
  "time": "11:25",
  "city": "Santos",
  "state": "SP",
  "country": "Brasil"
}
```

## Publicar no Render

1. Envie todos os arquivos deste projeto para um repositório do GitHub.
2. No Render, escolha **New > Blueprint**.
3. Conecte o repositório.
4. O Render detectará o arquivo `render.yaml`.
5. Confirme a criação do serviço.
6. Aguarde o status **Live**.
7. Teste `https://SEU-SERVICO.onrender.com/health`.

## Testes locais

```bash
pytest
```
