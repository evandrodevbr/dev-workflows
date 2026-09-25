---
name: wf-readme
description: Use para criar, auditar, melhorar, reescrever ou padronizar o README (e docs vizinhos como CONTRIBUTING e CHANGELOG) de um repositório. Tudo que o README afirma vem de um fato real do repo e os comandos mostrados são executados antes da entrega. Não use para docstrings, comentários de código, documentação de API gerada ou textos de UI (esses ficam com wf-frontend).
license: MIT
metadata:
  dev-workflows:
    uses: []
    external: [readme-crafter, good-readme, curating-readme, avoid-ai-writing]
---

# Workflow README

O README é construído a partir do repositório (manifest, código, scripts, config, git), nunca de
memória. Fato sem fonte vira pergunta ao usuário.

## Escala pelo tamanho do pedido

| Pedido | Fluxo |
|---|---|
| Ajuste pontual (corrigir um comando, um link, uma seção) | editar e rodar a Fase 5 só no trecho tocado |
| README novo, reescrita ou padronização | Fases 1 a 5 |

## Skills (se instaladas)

- `readme-crafter`: classifica o projeto e sugere estrutura sob medida.
- `good-readme`: cria com exemplos reais ou audita contra uma rubrica de 22 critérios.
- `curating-readme`: padroniza README e docs vizinhos; traz o script `audit-repo.sh`.
- `avoid-ai-writing`: remove AI-isms do texto final.

Sem elas, o fluxo abaixo funciona sozinho.

## Fase 1: SCAN (fatos reais)

1. Leia o manifest (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`...): nome, descrição,
   versão, scripts, `bin`, dependências.
2. Ache os entrypoints e o que o projeto de fato faz (CLI, rotas, exports públicos).
3. Leia o README atual, `LICENSE`, `CONTRIBUTING.md`, a CI (`.github/workflows/`) e `.env.example`.
4. Capture o contexto: `git remote -v` e `git log --oneline -5`.
5. Monte a lista de fatos, cada um com a fonte (`arquivo:linha` ou comando). O que não tem fonte vira pergunta.

## Fase 2: CLASSIFY (tipo e público)

- Tipo: biblioteca, CLI, web app, API, framework, monorepo, agente.
- Distribuição: público ou interno. Público primário: novo usuário, contribuidor, operador ou avaliador.
- Cada decisão com a fonte ("CLI porque `package.json` tem `bin`").
- Para CLI, rode o `--help` real e use essa saída como base da seção de uso.
- Se o código não revela a intenção, até 3 perguntas ao usuário.

## Fase 3: AUDIT (se já existe README)

- Compare cada afirmação com o repo: comandos, caminhos, variáveis de ambiente, versões, badges.
- Registre o que está certo, desatualizado, errado e faltando. Divergência com o código é achado, mesmo em README bonito.
- Dependência opcional apresentada como obrigatória e passo que bloqueia o primeiro uso são achados.
- Com `good-readme`, registre a nota de partida.

Sem README, siga direto para a Fase 4.

## Fase 4: GENERATE

1. Estrutura por tipo: título, badges do que existe, uma linha de descrição, o que faz, pré-requisitos,
   quick start copiável, uso, configuração (tabela de env vars do `.env.example`), estrutura,
   contribuição, licença. Detalhe em [references/estrutura.md](references/estrutura.md).
2. Badge só do que existe: licença com `LICENSE`, build com CI configurada, versão com pacote publicado.
3. Todo comando e exemplo mostrado precisa rodar neste repo.
4. Uma língua por arquivo; tradução vai em arquivo separado (`README.pt-BR.md`).
5. Passe `avoid-ai-writing` no texto, se instalada.

## Fase 5: VERIFY (antes de entregar)

1. **Rode os comandos** de instalação e quick start num ambiente limpo (clone novo ou diretório
   temporário). O que não der para rodar (precisa de credencial, serviço externo, hardware),
   liste no relatório com o motivo. Nunca escreva "testado" sobre o que não rodou.
2. **Links locais resolvem**: cada `](caminho)` aponta para arquivo que existe.
3. **Links externos respondem**: `curl -sI -o /dev/null -w '%{http_code}' <url>` em cada um.
4. **Referências existem**: arquivos, scripts, env vars e flags citados estão no repo.
5. **Índice bate** com os headings, se houver índice.
6. Nenhum `TODO:` sobrou no texto final.

Comandos prontos: [references/verificacao.md](references/verificacao.md).

## Relatório

O que mudou, os achados da auditoria (antes e depois), os comandos executados com o resultado e o
que não pôde ser verificado.

## Não faça

- Inventar instalação, comando, exemplo, screenshot ou feature.
- Copiar a estrutura de outro projeto sem adaptar ao tipo e ao público.
- Duplicar a mesma informação em duas seções.
- Encher de emojis ou badges decorativos.

## Critério de aceite

- [ ] Toda afirmação tem fonte no repo ou virou pergunta respondida.
- [ ] Comandos de instalação e quick start executados, ou listados como não verificáveis com motivo.
- [ ] Links locais e externos resolvem; arquivos citados existem.
- [ ] Badges só do que existe; nenhum `TODO:` no texto final.
