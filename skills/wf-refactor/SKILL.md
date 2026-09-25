---
name: wf-refactor
description: Use para refatorar, reorganizar, renomear, extrair, simplificar ou limpar código sem mudar o comportamento. Congela o comportamento com testes antes de mexer e mexe em passos pequenos.
license: MIT
metadata:
  dev-workflows:
    uses: []
    external: []
---

# Workflow Refactor

## 1. Rede de segurança

Os testes atuais cobrem o comportamento que você vai tocar? Se não, escreva **testes de
caracterização** antes de mudar qualquer coisa: eles registram o que o código faz hoje, mesmo que
pareça estranho. Rode e confirme que estão verdes.

## 2. Passos pequenos

Cada passo deixa o código compilando e os testes verdes. Rode os testes a cada passo, não só no fim.
Renomeação: procure também em strings, configs, rotas e docs (`grep -rn`), não só nos imports.

## 3. Comportamento não muda

Os testes de caracterização não são editados. Se você precisa editar um deles, a mudança não é
refactor: pare e pergunte ao usuário.

## 4. Gate e relatório

`"${CLAUDE_PLUGIN_ROOT}/scripts/quality-gate" --tier 1` (nível 2 se o refactor atravessa módulos).
No relatório, as linhas líquidas: um bom refactor costuma reduzir. Se aumentou, explique.

## Não faça

- Misturar refactor com feature ou correção de bug no mesmo diff.
- Mudar API pública sem o usuário pedir.
- Criar camada ou abstração nova "para ficar mais limpo" sem um uso concreto hoje.
