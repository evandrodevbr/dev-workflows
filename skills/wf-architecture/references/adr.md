# Modelo de ADR

Arquivo: `docs/architecture/adr/NNNN-titulo-curto.md` (S-ADR de segurança em `docs/security/adr/`).
Numeração sequencial. ADR aceito não é reescrito: uma decisão nova cria outro ADR com `Substitui:`.

```markdown
# ADR-0003: PostgreSQL como banco de pedidos

- Status: proposto | aceito | substituído por ADR-NNNN
- Data: 2026-09-24
- Requisitos: REQ-002, REQ-010
- Substitui: (se houver)

## Contexto
O que força a decisão agora. Restrições reais (volume, equipe, custo, prazo), com números.

## Opções
1. PostgreSQL gerenciado: prós, contras.
2. MongoDB: prós, contras.
3. Manter o SQLite atual: prós, contras.

## Decisão
A opção escolhida e o motivo principal, em duas ou três frases.

## Consequências
- Boas: o que fica mais fácil.
- Ruins: o que fica mais difícil ou caro, e o que foi aceito conscientemente.
- Como desfazer, se precisar, e quanto custa.
```

Um ADR por decisão. Se duas decisões dependem uma da outra, dois ADRs que se referenciam.
