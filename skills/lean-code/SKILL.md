---
name: lean-code
description: Use sempre que for escrever ou mudar código. Escolhe a menor solução que resolve de verdade - reaproveitar antes de escrever, apagar antes de somar, sem abstração especulativa e sem dependência desnecessária.
---

# Lean Code

Primeiro entenda o problema e o código que ele toca. Depois suba a escada e pare no primeiro degrau
que resolve.

## Escada

1. **Precisa existir?** Pedido especulativo ("para depois", "vai que") não entra. Diga isso em uma linha.
2. **Já existe no projeto?** Procure helper, componente, tipo ou padrão parecido antes de escrever (`grep` por nomes e por comportamento; o agente `explorer` faz isso).
3. **A biblioteca padrão resolve?**
4. **A plataforma resolve?** HTML/CSS nativo antes de JS, constraint do banco antes de código, recurso do framework antes de utilitário próprio.
5. **Uma dependência já instalada resolve?**
6. **Cabe em poucas linhas?**
7. Só então: o mínimo de código novo.

## Regras

- **Bug se corrige na causa.** Antes de editar uma função, ache todos os chamadores. Uma correção no ponto por onde todos passam é menor que uma por chamador, e não deixa os outros quebrados.
- **Sem abstração sem uso:** interface com uma implementação, factory de um produto, configuração para valor que nunca muda.
- **Dependência nova exige justificativa** em uma linha (o que ela faz que os degraus 3 a 6 não fazem) e consulta ao `safedeps` antes de instalar. O gate lista as novas.
- **Apague o que ficou morto** por causa da mudança.
- **Entre duas soluções do mesmo tamanho**, fique com a que está certa nos casos de borda.

## Nunca simplifique

Validação na fronteira do sistema, tratamento de erro que evita perda de dado, controles de segurança,
acessibilidade básica e qualquer coisa que o usuário pediu explicitamente.

## Orçamento de diff (linhas líquidas, referência)

| Nível | Orçamento |
|---|---|
| 0 | 20 |
| 1 | 100 |
| 2 | 400 |
| 3 | 400 por fatia entregue |

Estourou: justifique no relatório ou quebre em partes menores.

## Atalho consciente

Quando cortar caminho de propósito (lock global, busca O(n²), heurística simples), deixe um comentário
`lean:` dizendo o limite e quando evoluir: `# lean: lock global; trocar por lock por conta se a vazão importar`.
