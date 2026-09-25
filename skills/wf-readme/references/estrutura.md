# Estrutura do README por tipo

Ordem base. Corte a seção que não se aplica em vez de preencher com texto genérico.

| Seção | Fonte no repo | Obrigatória para |
|---|---|---|
| Título e uma linha de descrição | `name`/`description` do manifest | todos |
| Badges | `LICENSE`, `.github/workflows/`, registro do pacote | só o que existe |
| O que faz | entrypoints, exports, rotas | todos |
| Pré-requisitos | `engines`, `requires-python`, `go` no `go.mod`, Dockerfile | todos |
| Quick start | scripts do manifest, `Makefile` | todos |
| Uso | saída real do `--help`, exemplos que rodam | CLI, biblioteca |
| API | exports públicos, OpenAPI | biblioteca, API |
| Configuração | `.env.example`, arquivo de config | quem tem env vars |
| Estrutura do projeto | árvore real (`git ls-files`) | monorepo, app |
| Contribuição | `CONTRIBUTING.md`, comandos de teste e lint | open source |
| Licença | `LICENSE` | todos |

## Por tipo

- **Biblioteca**: instalação pelo gerenciador, um exemplo mínimo que roda, link para a API.
- **CLI**: instalação, `--help` real, dois ou três comandos comuns com a saída.
- **Web app**: pré-requisitos, `.env`, como subir em dev, como rodar os testes.
- **API**: como subir, onde está o OpenAPI, autenticação, um `curl` que funciona.
- **Monorepo**: tabela de pacotes com uma linha cada e o comando para rodar todos.

## Quick start

Copiável de ponta a ponta: clonar, instalar, configurar, rodar, ver o primeiro resultado.
Dependência opcional fica fora do caminho principal, numa seção à parte.
