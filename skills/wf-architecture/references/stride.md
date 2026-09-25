# Threat model STRIDE com ASVS 5.0

Arquivo: `docs/security/threat-model.md`. Uma tabela por fronteira de confiança.

## Categorias e onde procurar o controle no ASVS 5.0

| STRIDE | Ameaça típica | Capítulos ASVS 5.0 para o controle |
|---|---|---|
| Spoofing (identidade falsa) | login forjado, token roubado, serviço se passando por outro | Autenticação, Gerenciamento de sessão, Tokens autocontidos |
| Tampering (adulteração) | parâmetro alterado, mensagem na fila modificada, upload malicioso | Validação e lógica de negócio, Manipulação de arquivos, Comunicação segura |
| Repudiation (negação) | ação sensível sem rastro | Log e tratamento de erro |
| Information disclosure (vazamento) | IDOR, stack trace na resposta, segredo em log | Autorização, Proteção de dados, Log e tratamento de erro |
| Denial of service | endpoint sem limite, query sem paginação, arquivo gigante | Validação e lógica de negócio (limites), Manipulação de arquivos |
| Elevation of privilege | usuário comum chega em rota de admin, injeção de comando | Autorização, Codificação e sanitização |

Os nomes dos capítulos seguem o ASVS 5.0 (maio de 2025). Cite o requisito exato (`V<cap>.<seção>.<item>`)
consultando https://github.com/OWASP/ASVS, não pela memória.

## Modelo por fronteira

```markdown
## Fronteira: Internet -> API

| # | STRIDE | Ameaça concreta | Controle | ASVS | Status |
|---|---|---|---|---|---|
| T1 | S | Token JWT aceito com alg none | Validar alg fixo e assinatura | Tokens autocontidos | ok |
| T2 | I | GET /orders/{id} devolve pedido de outro cliente | Query escopada ao usuário autenticado | Autorização | pendente |
| T3 | D | POST /orders sem limite de taxa | Rate limit por usuário e IP | Validação e lógica de negócio | pendente |
```

Fronteiras que costumam faltar: serviço interno sem autenticação ("está na rede privada"),
worker que confia em qualquer mensagem da fila, integração com LLM (prompt injection, ferramenta
com permissão demais: OWASP LLM01 e LLM06).

Status `pendente` em ameaça alta bloqueia a aprovação da Fase 5.
