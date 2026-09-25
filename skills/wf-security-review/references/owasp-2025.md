# Referências OWASP atuais

Confira a lista oficial em https://owasp.org/Top10/ se houver dúvida de nome ou ordem.

## Top 10:2021 (usado pelas skills vendorizadas) para Top 10:2025

| 2021 | 2025 | Observação |
|---|---|---|
| A01 Broken Access Control | A01 Broken Access Control | agora inclui SSRF |
| A02 Cryptographic Failures | A04 Cryptographic Failures | |
| A03 Injection | A05 Injection | XSS continua aqui |
| A04 Insecure Design | A06 Insecure Design | |
| A05 Security Misconfiguration | A02 Security Misconfiguration | subiu |
| A06 Vulnerable and Outdated Components | A03 Software Supply Chain Failures | **ampliada**: build, CI, registro de pacotes, dependências |
| A07 Identification and Authentication Failures | A07 Authentication Failures | |
| A08 Software and Data Integrity Failures | A08 Software or Data Integrity Failures | |
| A09 Security Logging and Monitoring Failures | A09 Security Logging and Alerting Failures | |
| A10 Server-Side Request Forgery | (dentro de A01) | |
| n/a | A10 Mishandling of Exceptional Conditions | **nova**: erro que falha aberto, exceção engolida, estado inconsistente após falha |

## API Security Top 10 (2023)

API1 Broken Object Level Authorization · API2 Broken Authentication · API3 Broken Object Property
Level Authorization · API4 Unrestricted Resource Consumption · API5 Broken Function Level
Authorization · API6 Unrestricted Access to Sensitive Business Flows · API7 Server Side Request
Forgery · API8 Security Misconfiguration · API9 Improper Inventory Management · API10 Unsafe
Consumption of APIs.

## ASVS 5.0 (maio de 2025)

Checklist por nível, mais de 300 requisitos em 17 capítulos (inclui segurança de frontend web e tokens
autocontidos). Use o nível que o `dev-router` definiu:

- **L1** (nível 2): o mínimo para qualquer aplicação exposta.
- **L2** (nível 3): aplicação com dados sensíveis ou transações; o padrão recomendado para a maioria.
- **L3**: só com pedido explícito (dado crítico, alto valor).

Fonte: https://github.com/OWASP/ASVS

## LLM Top 10 (2025), para features que chamam um LLM

LLM01 Prompt Injection · LLM02 Sensitive Information Disclosure · LLM03 Supply Chain · LLM04 Data and
Model Poisoning · LLM05 Improper Output Handling · LLM06 Excessive Agency · LLM07 System Prompt
Leakage · LLM08 Vector and Embedding Weaknesses · LLM09 Misinformation · LLM10 Unbounded Consumption.

O mais comum em código de aplicação: saída do modelo usada sem validação (LLM05), ferramentas ou
permissões demais para o agente (LLM06), segredo ou dado de outro usuário no prompt (LLM02) e custo
sem limite (LLM10).
