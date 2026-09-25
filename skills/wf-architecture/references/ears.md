# EARS: requisitos com ID

EARS (Easy Approach to Requirements Syntax) força cada requisito a ter gatilho e resposta
verificáveis. Um requisito por linha, ID estável `REQ-NNN`, nunca reaproveitado.

| Padrão | Forma | Exemplo |
|---|---|---|
| Ubíquo | THE SYSTEM SHALL <resposta> | `REQ-001: THE SYSTEM SHALL registrar toda alteração de preço com autor e data.` |
| Evento | WHEN <evento> THE SYSTEM SHALL <resposta> | `REQ-002: WHEN o usuário envia o formulário de cadastro THE SYSTEM SHALL responder 201 com o ID criado.` |
| Indesejado | IF <condição> THEN THE SYSTEM SHALL <resposta> | `REQ-003: IF o token expirou THEN THE SYSTEM SHALL responder 401 sem revelar se a conta existe.` |
| Estado | WHILE <estado> THE SYSTEM SHALL <resposta> | `REQ-004: WHILE a fila tiver mais de 1000 itens THE SYSTEM SHALL recusar novos jobs com 429.` |
| Opcional | WHERE <recurso> THE SYSTEM SHALL <resposta> | `REQ-005: WHERE o SSO estiver habilitado THE SYSTEM SHALL ocultar o login por senha.` |

## Não funcionais

Mesmo formato de ID, sempre com número e forma de medir:

```
REQ-010: THE SYSTEM SHALL responder GET /orders em p95 < 250 ms com 200 req/s (medido com k6).
REQ-011: THE SYSTEM SHALL manter 99,9% de disponibilidade mensal (SLO no monitoramento).
REQ-012: THE SYSTEM SHALL atender ASVS 5.0 nível L2 nos capítulos de autenticação e sessão.
REQ-013: THE SYSTEM SHALL carregar a página inicial com LCP <= 2,5 s e INP <= 200 ms (Lighthouse CI).
```

## Rastreabilidade

Cada teste cita o ID que prova, no nome ou num comentário:

```python
def test_req_003_token_expirado_retorna_401():
    ...
```

Com `[spec]` no `.dev-workflows.toml`, o gate nível 3 falha se algum `REQ-` da spec não aparecer
em nenhum arquivo de teste.
