---
name: wf-bugfix
description: Use para corrigir bug, erro, exceção, falha, regressão, comportamento errado ("não funciona", "quebrou", "fix"). Reproduz, acha a causa raiz e prova a correção com um teste de regressão que falha antes e passa depois.
---

# Workflow Bugfix

## 1. Reproduzir

Encontre o comando, teste ou requisição que mostra o erro, e rode. Sem reprodução, colete mais dado
(stack trace, log, entrada exata) em vez de chutar uma correção.

## 2. Achar a causa raiz

- Siga o fluxo real do ponto de entrada até o erro.
- Ache todos os chamadores da função que você pretende mudar (`grep -rn "nomeDaFuncao(" .`).
- Escreva a causa em uma ou duas frases antes de editar. Se não consegue, ainda não achou.
- Corrija no ponto por onde todos os chamadores passam, não só no caminho que o relato citou.

## 3. Provar com teste de regressão

1. Escreva o teste que reproduz o bug.
2. Prove que ele falha sem a correção: `git stash push <arquivos da correção>`, rode o teste, veja vermelho, `git stash pop`.
3. Rode de novo com a correção: verde.

Um teste que passa com e sem a correção não prova nada; reescreva.

## 4. Gate

`"${CLAUDE_PLUGIN_ROOT}/scripts/quality-gate" --tier 1` (ou o nível que o `dev-router` definiu).

## 5. Relatório

Causa em uma frase, o que mudou, o teste que prova (nome e saída vermelho/verde) e o veredito do gate.

## Não faça

- Silenciar o erro com `try/except` ou `catch` vazio.
- Mudar o teste até ele passar em vez de corrigir o código.
- Corrigir o sintoma num chamador e deixar a causa na função compartilhada.
