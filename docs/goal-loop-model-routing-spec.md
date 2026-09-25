# Spec: loop de melhoria por meta e roteamento de modelos por ferramenta

**Estado:** implementada como CLIs opt-in; ranking e despacho pagos dependem de evidência válida da conta, benchmark autorizado e autorização pontual. Nesta captura não há notas AA importadas nem elegibilidade de conta confirmada.
**Consulta de fontes:** 2026-09-25 (UTC). **Escopo:** `dev-workflows` como kit multi-ferramenta, não somente OMP.
**Decisões já recebidas:** faixas de qualidade por **notas fixas**, Claude Code usado por **assinatura**, OpenRouter como fonte dos preços unitários de **referência** para cruzar os modelos do OpenCode.

## 1. Problema e resultado esperado

Na base anterior, `skills/dev-router/SKILL.md` dimensionava tarefas em níveis 0–3; `agents/*.md` fixavam Haiku/Sonnet/Opus; `scripts/quality-gate` escrevia `.dev-workflows/gate.json`; o hook Claude bloqueava o encerramento sem gate atual, enquanto o adapter OpenCode apenas avisava. Agora catálogo, roteador e controlador externo acrescentam avaliação de meta sem substituir esses mecanismos; `scripts/install.py` inclui OMP nativo, mantendo Hermes apenas com skills.

Entregar duas capacidades independentes e combináveis:

1. **Roteador:** listar os modelos realmente utilizáveis por ferramenta/conta, cruzar preços OpenRouter e evidência de benchmark de programação, mostrar ranking e escolher um modelo por função dentro de uma faixa de nota e de um orçamento explícitos.
2. **Controlador externo de experimentos:** medir um objetivo do **aplicativo** com avaliador independente, executar mudanças limitadas em worktrees isolados, aplicar o quality gate, aceitar apenas melhorias válidas e repetir até atingir o alvo ou um limite. Instalar skills/agentes não liga esse controlador automaticamente.

**Duas escalas diferentes:** `coding_score` (Artificial Analysis, seleção do agente/modelo, 0–100) não é `app_score` (avaliador específico do projeto, com unidade/direção/alvo configuráveis). Não usar um como prova do outro.

### Fora de escopo

Assinar serviços, criar chaves, alterar a cobrança Zen/Go, prometer preços iguais entre gateways, extrair dados protegidos da Artificial Analysis, publicar resultados/código, remover worktrees com mudanças, alterar testes protegidos, reimplementar o quality gate, ou rodar o loop em projetos sem objetivo verificável. Não adotar um framework Ralph como dependência obrigatória: aproveitar o padrão de contexto fresco e verificação externa com o Python já usado pelo projeto.

## 2. Fontes e interpretação

| Informação | Autoridade / campo | Regra |
|---|---|---|
| Catálogo Zen | [Zen `/v1/models`](https://opencode.ai/zen/v1/models), [docs Zen](https://opencode.ai/docs/zen); ID de uso `opencode/<id>` | Lista pública não prova acesso da conta nem cobrança. Zen tem modelos Claude; não excluir a família por suposição. |
| Catálogo Go | [Go `/v1/models`](https://opencode.ai/zen/go/v1/models), [docs Go](https://opencode.ai/docs/go); ID `opencode-go/<id>` | Assinatura de US$10/mês; cotas **por modelo** em equivalentes USD: 20% do limite mensal a cada 5h, 50% semanal, 100% mensal. A lista atual inclui GPT Luna, mas não Claude; reconsultar. |
| Acesso OpenCode local | [Modelos e providers](https://opencode.ai/docs/models), CLI `opencode models <provider> --refresh`; autenticação local/conta | Interseção com IDs exatos do provider instalado e habilitado; lista pública e credencial, isoladamente, não bastam. Erro de autorização retira candidato. |
| Preço comparativo | [OpenRouter Models API](https://openrouter.ai/docs/api/api-reference/models/get-models), `GET /api/v1/models` | `prompt`, `completion`, `input_cache_read`, `input_cache_write` são USD **por token**: multiplicar por 1.000.000 para mostrar USD/1M. Campo ausente = `n/d`, nunca zero. IDs OpenRouter não são IDs OpenCode. |
| Preço real e limites | Docs/console [Zen](https://opencode.ai/docs/zen) e [Go](https://opencode.ai/docs/go), ou plano da ferramenta usada | **Não** cobrar, estimar saldo Zen nem debitar cota Go por preço OpenRouter. Considerar overrides de contexto, janelas de pico e cache; quando indisponível, bloquear despacho automático pago. |
| Benchmark principal | [Artificial Analysis Coding Agent Index](https://artificialanalysis.ai/agents/coding-agents), [metodologia v1.5](https://artificialanalysis.ai/methodology/coding-agents-benchmarking) | Média de DeepSWE v1.1, Terminal-Bench 4.0 e SWE-Atlas-QnA; guardar agente/harness, variante, esforço, fallback, versão, data, link e score. Score do harness **não** é propriedade intrínseca de toda rota do modelo. |
| API AA | [Data API](https://artificialanalysis.ai/data-api/docs) e [API legada](https://artificialanalysis.ai/api-reference) | Endpoints autenticados de modelos expõem índices de natureza/versão distintas; a documentação consultada não oferece export público documentado do **Coding Agent Index v1.5**. `artificial_analysis_coding_index` da API legada, quando disponível, não é automaticamente o índice de agentes v1.5. Nunca trocar pelo Intelligence Index. Respeitar termos e atribuição. |

**Ingestão do benchmark:** preferir export/API oficial **documentado e autorizado** para o índice de agentes; até existir, aceitar snapshot auditado/importado manualmente da página pública com a atribuição e evidência por linha, observando seus termos. Sem scraping automático de interface privada, sem inventar pontuações para preencher lacunas. Qualquer outro benchmark entra com `metric_id` diferente e ranking separado; não juntar scores entre índices, versões ou harnesses sem justificativa experimental.

### Amostra auditável de cruzamento (não é ranking completo nem tabela de cobranças)

Valores observados em 2026-09-25: preço **OpenRouter** em USD/1M tokens (entrada / saída / leitura de cache / escrita de cache); nota do **Coding Agent Index v1.5**, com harness e variante indicados. A presença nos catálogos públicos não afirma elegibilidade de nenhuma conta.

| Modelo e IDs de exemplo | Preço OpenRouter | Nota AA da variante avaliada | Observação |
|---|---|---|---|
| GLM 5.3: `z-ai/glm-5.3`; `opencode/glm-5.3`; `opencode-go/glm-5.3` | 1,40 / 4,40 / 0,26 / n/d | 54, OpenCode (max) | Go publica cota mensal de US$15 para este modelo; benchmark no OpenCode não prova equivalência do backend de todas as rotas. |
| GPT-6 Luna: `openai/gpt-6-luna`; `opencode/gpt-6-luna`; `opencode-go/gpt-6-luna` | 0,10 / 0,50 / 0,01 / 0,125 | 41, Codex (max) | Faixa **média pela nota**, apesar do preço baixo; Go publica cota mensal de US$15. OpenRouter aplica preços diferentes acima de 272k tokens. |
| GPT-6 Sol: `openai/gpt-6-sol`; `opencode/gpt-6-sol` | 2,00 / 10,00 / 0,20 / 2,50 | 57, Codex (max) | Pontuação em outro harness; preço muda acima de 272k tokens. |
| Claude Opus 5.5: `anthropic/claude-opus-5.5`; `opencode/claude-opus-5-5` | 4,00 / 20,00 / 0,20 / 5,00 | 66, Claude Code (max) | Zen oferece esse ID publicamente; não presumir acesso na conta nem equiparar preço OpenRouter à assinatura Claude. |
| Kimi K3: `moonshotai/kimi-k3`; `opencode-go/kimi-k3`; `opencode/kimi-k3` | 0,8845 / 10,5346 / 0,33 / n/d | 52, Kimi Code CLI | Variante avaliada em outro harness; Go publica cota mensal de US$15. |
| Claude Sonnet/Haiku, MiMo-V2.6-Pro | IDs conforme catálogo de cada ferramenta; pareamento exige revisão | **n/d** | Não foi localizada nota dessas variantes no recorte público consultado; não atribuir nota de outra família/harness. |

Os preços acima vêm do [JSON OpenRouter](https://openrouter.ai/api/v1/models); notas da [leaderboard](https://artificialanalysis.ai/agents/coding-agents); cotas e IDs das [docs Go](https://opencode.ai/docs/go) e [Zen](https://opencode.ai/docs/zen). Cache `n/d` significa *não informado*, não gratuito. Listar também condição de preço/contexto e origem por modelo na saída gerada; dados mudam.

## 3. Política de roteamento

### 3.1 Faixas e funções

Usar **nota fixa** de 0 a 100; cortes configuráveis, defaults abaixo. Faixa não é preço nem tamanho físico do modelo:

| Faixa de qualidade | Intervalo | Uso padrão | Restrições |
|---|---|---|---|
| `leve` | `[10, 20)` | exploração/leitura em volume, coleta de dados públicos, sumarização mecânica e relatório do `verifier` | Agentes só de leitura; se nenhum candidato medido, faixa fica vazia. Nota `<10` inelegível por padrão. |
| `media` | `[20, 50)` | `implementer`, `ui-critic` nível 2 | Exigir ferramentas e contexto suficientes; escalar tarefas de alto risco para `alta`. |
| `alta` | `[50, 100]` | `planner`, `reviewer`, `security-auditor`, implementação nível 3/risco | Planejamento/revisão independentes e limites de custo. Notas `>80` continuam nesta **terceira** faixa. |

Não assumir que haverá candidato em todas as faixas: os exemplos publicados de 2026-09-25 não preenchem a faixa `leve`. Se vazia, registrar `no_scored_candidate`; propor o menor custo de outra faixa que cumpra o piso **após** orçamento/autorizações, ou usar um modelo fixado pelo usuário e rotular `unranked`; não afirmar que esta opção venceu no benchmark. `dev-router` continua a escolher nível e gatilhos de segurança; a faixa nunca reduz nível/gate nem torna revisão opcional.

### 3.2 Elegibilidade, custo e seleção

Para cada função, aplicar nesta ordem:

1. Escolher ferramenta/harness **em uso**, provider e conta de cobrança permitidos pelo usuário. Elegível só se `(provider, id, variante)` constar do catálogo local revalidado, autenticação/entitlement não negado e houver contexto, modalidade, tool calling e permissões requeridos. IDs e versões vinculados por mapa curado com proveniência; sem `fuzzy match` de nomes. `opencode/*` e `opencode-go/*` são rotas distintas. OMP pode usar esses providers se realmente configurados; Claude Code não vira multi-provider por declarar um ID Zen.
2. Para seleção **pontuada**, exigir benchmark de métrica/versão única e mapeamento de variante. `exact`: harness, modelo, esforço e caminho avaliados equivalentes; `proxy`: modelo e esforço compatíveis, mas harness/provider diferem, com risco explícito. Proxy só se a política da função autorizar; para migração/auth/segurança de nível 3, exigir `exact` ou aprovação humana da incerteza. `unranked` não entra em fronteira de qualidade nem ganha score emprestado.
3. Filtrar pelo intervalo da função e pelo custo/limite de cobrança autorizado. `score_top = max(score)` dos elegíveis da faixa; formar platô `score >= score_top - delta_points` (**pontos de nota**, não porcentagem). Defaults: `delta_points = 2` para `alta`, `3` para `media` e `leve`. No platô, escolher **menor consumo relevante para a ferramenta** no perfil de tokens da função: tarifa Zen para Zen, débito de cota Go para Go, consumo observado da assinatura para Claude quando medível. Publicar também o ranking **comparativo OpenRouter**, mas não usá-lo como custo real de outro gateway. Se o consumo relevante for desconhecido, não alegar escolha ótima: manter rota estática ou pedir seleção explícita. Desempate: nota maior, maior folga de cota, ID lexicográfico. Reportar top absoluto, economia estimada e fronteira de Pareto (nota e custo na mesma base).
4. Custo **referencial** por tarefa: `C_OR = u*P_entrada + o*P_saida + r*P_cache_leitura + w*P_cache_escrita + taxas_extras`, com `u,o,r,w` em tokens e preços da API OpenRouter **em USD por token**. Equivalentemente, se usar valores exibidos **em USD/1M**, dividir a soma dos quatro produtos por `1_000_000`. Usar `Decimal`, sem ponto flutuante para moeda. Se o perfil usa cache e seu preço não é informado, `C_OR = n/d`, sem comparar artificialmente como zero; componente com zero tokens não requer tarifa. Respeitar overrides de contexto/TTL/endpoint. Perfil de tokens vem de medições do próprio harness ou configuração explícita; previsão é **estimativa**, não fatura.
5. Zen: orçamento real conservador calculado com tarifa **Zen**, independente de `C_OR`, e saldo/limite confirmados; Go: verificar cota restante **do modelo** nas três janelas e estimar débito pela **tarifa Go**, não por `C_OR`. Quando saldo/restante não puder ser confirmado, não iniciar despacho automático com risco de cobrança; permitir execução manual fora do loop. Claude por assinatura: mostrar `C_OR` só como comparação, contar tokens/limites observáveis e parar ao atingir aviso de plano; sem consumo comparável não afirmar economia entre Opus/Sonnet/Haiku nem converter USD OpenRouter em cobrança. Nenhum fallback Go→saldo Zen sem autorização explícita separada; a opção `Use balance` da console pode cobrar automaticamente quando a cota acabar.
6. Se seleção mudar, exibir motivo (novo score, preço, disponibilidade, quota, contexto) e não trocar a ferramenta/provider/assinatura silenciosamente. Falha de autenticação, preço obsoleto, métrica ausente, índice diferente, rate-limit ou limite esgotado = `unavailable`/pausa; fallback só para rota previamente permitida que ainda cumpre requisitos e orçamento.

Na implementação, o ID de modelo OMP é opaco (pode conter `/`); apenas seu `selector` é qualificado pelo provider, e variantes `#esforço` só são elegíveis quando o `thinking` da CLI local anuncia esse esforço. `exact` exige o harness da ferramenta em execução; outra origem exige `proxy` autorizado. Rotas Zen e OMP pay-as-you-go exigem `--budget-usd` explícito antes mesmo de serem selecionadas. Overrides publicados pela API OpenRouter acima de um limiar de tokens entram apenas no preço comparativo do perfil.

**Exemplo de custo comparativo, não fatura:** perfil hipotético de 50k tokens de entrada sem cache, 150k de leitura de cache, 10k de saída e 0 de escrita dá aproximadamente US$0,0115 no OpenRouter para GPT-6 Luna e US$0,153 para GLM-5.3 nas tarifas-base observadas. A primeira tem nota 41 (`media`), a segunda 54 (`alta`); não chamar Luna de faixa `leve` por ser barata. Não usar esse perfil fictício para cobrar ou fixar o ranking final.

**Atualização:** cada snapshot contém data UTC e hash. Revalidar catálogo local por sessão, preços antes de aprovar gasto (24h no máximo), quotas antes de cada execução e score ao mudar versão do índice (recaptura pelo menos a cada 30 dias). Dados obsoletos impedem **autoescolha paga**; `models list` ainda os mostra como `stale`. Nenhum refresh automático de AA sem fonte/permissão documentada.

## 4. Contratos de dados e interface proposta

Manter a config do projeto em `.dev-workflows.toml` (já lida pelo gate), adicionando seções **sem alterar** `[commands]`, `[thresholds]`, `[spec]` e `[[check]]` existentes. `~/.config` pode conter preferências de conta, nunca chaves em arquivos do projeto. Exemplo de contrato, não arquivo configurado:

```toml
[loop]
enabled = false                    # somente comando explícito inicia experimento
harness = "opencode"              # claude | opencode | omp; Hermes após adapter real
max_iterations = 8
max_minutes = 90
max_stagnant = 2
min_improvement = 0.5
max_paid_usd = 0                  # >0 só com autorização interativa para Zen/pay-as-you-go

[loop.goal]
name = "qualidade_do_app"
direction = "maximize"            # minimize também permitido
unit = "points"                   # unidade do produto, não do AA
baseline_required = true
target = 80.0

[loop.evaluator]
argv = ["python3", "/caminho/fora/do/worktree/evaluate.py", "--json"]
timeout_seconds = 600
trusted_sha256 = "<hash aprovado do avaliador e testes protegidos>"
required_checks = ["test", "lint"]
require_gate_verdict = "pass"      # incomplete não é sucesso do loop

[models]
benchmark_metric = "aa_coding_agent_index_v1.5"
allow_proxy_score = false
max_price_age_hours = 24
max_score_age_days = 30

[models.bands]
leve = [10, 20]
media = [20, 50]
alta = [50, 100]                  # último limite inclusivo

[models.roles.explorer]
band = "leve"
max_loss_points = 3

[models.roles.implementer]
band = "media"
max_loss_points = 3

[models.roles.planner]
band = "alta"
max_loss_points = 2
```

**Contrato de avaliação (stdout exclusivamente JSON, erro em stderr):**

```json
{"schema_version":1,"metric":"qualidade_do_app","value":81.2,"unit":"points","direction":"maximize","checks":{"regression":"pass","security":"pass"},"evidence":["/relatorios/avaliacao.json"]}
```

Apenas o processo controlador interpreta `value`; saída ausente, NaN, métrica/unidade/direção divergente, evidência não verificável, prazo excedido, exit não zero, ou check obrigatório diferente de `pass` é **falha**, nunca score zero. Nomes de caminhos são ilustrativos; o avaliador real e seu alvo são definidos pelo projeto. Repetir baseline e candidato sob o mesmo avaliador, versão, dados e sementes. Expor variabilidade: para avaliador estocástico, fixar sementes/repetições e comparar média/intervalo conforme config do projeto, sem inferir melhoria de ruído.

**Registro de modelo:** `model_key=(provider,model_id,variant)`, `tool`, `billing_mode`, `openrouter_id`, `openrouter_canonical_slug`, `or_price_per_token={input,output,cache_read?,cache_write?,cache_write_1h?}`, `price_conditions`, `zen_or_go_native_tariff?`, `quota_window_remaining?`, `score={metric_id,version,value?,agent,harness,variant,settings,match_grade,source_url,observed_at}`, `availability={listed,authenticated,entitled,verified_at}`, `source_hash`. Tipos monetários como string decimal, `null` para desconhecido. Não gravar API keys, prompts do app ou dados privados no ranking. Não confundir variantes `max/high` do benchmark com preço base sem estimar seus tokens.

**Comandos de produto implementados:**

```text
python3 scripts/model_catalog.py sync --tool opencode --providers opencode,opencode-go
python3 scripts/model_catalog.py list --tool opencode --show-missing --format csv
python3 scripts/model_catalog.py route --tool opencode --role planner --explain
python3 scripts/goal_loop.py plan --config .dev-workflows.toml
python3 scripts/goal_loop.py run --config .dev-workflows.toml
python3 scripts/goal_loop.py status --run <id>
python3 scripts/goal_loop.py resume --run <id>
python3 scripts/goal_loop.py stop --run <id>
```

**Tabela completa gerada, não preenchida manualmente nesta spec:** uma linha por `(ferramenta, provider, ID, variante)` de **todos** os modelos publicados para Zen e Go no snapshot, inclusive os indisponíveis na conta e os sem nota. Colunas CSV/JSON: `nome`, `tool`, `provider/model#variant`, `openrouter_id`, `preco_or_entrada_usd_1m`, `preco_or_saida_usd_1m`, `preco_or_cache_leitura_usd_1m`, `preco_or_cache_escrita_usd_1m`, `condicao_de_preco`, `coding_index_versao`, `coding_index_nota`, `benchmark_por_componente_se_publicado`, `harness_aa`, `reasoning_aa`, `grau_do_match`, `faixa`, `preco_native_ou_cota`, `disponivel_na_conta`, `motivo_da_exclusao`, `fonte` e `capturado_em`. Reportar cobertura `pontuados/total` por ferramenta/faixa; ordenar ranking só entre notas comparáveis. `n/d` permanece explícito para score ou preço ausente, não omitir linhas. Export não contém credenciais nem dados do usuário.

`sync` de AA só aceita snapshot manual licenciado/verificado ou API específica oficialmente documentada; não há comando para raspar leaderboard não documentado. `plan` é sem gastos/mutações: imprime fontes, notas e `n/d`, mapeamentos, cotas, perfil de tokens, rotas por papel, baseline/evaluator e riscos. `run` exige aprovação explícita para orçamento pago, comandos com efeitos externos e mudanças de provider; nunca ativar por instalar o plugin. `status` mostra score inicial/melhor/meta, iterações, custo real/estimado separados, snapshots, gate e motivos de pausa. `stop` cancela novas tentativas e não apaga worktrees.

**Captura reproduzível da tabela:** [`model-catalog-zen-go-2026-09-25.csv`](model-catalog-zen-go-2026-09-25.csv), gerada pelos comandos `sync --tool opencode --providers opencode,opencode-go` e `list --tool opencode --show-missing --format csv` em **2026-09-25T07:18:38Z**. Contém 80 modelos Zen e 42 Go, cobertura AA 0/122 (não foi fornecido snapshot autorizado), oito pareamentos curados de preços OpenRouter e acesso local não confirmado (`opencode models --refresh` falhou para ambos); nenhum deles é automaticamente elegível. Hash do snapshot `1930d91de7992963aec39d4188f36d97a849ead60f4dc91ae66dc4b38c708cd7`; hashes dos corpos das fontes: Zen `1b8d7a3dd18412473419eed98e32be003db5307754a1c5ab0f491ff33b4806a4`, Go `4f3c2a14e77fa546f5ba833d85cca088918ab2ade7e4a0eaf8c5d9a478b48ae4`, OpenRouter `0d552d4f08b7c600c0aa2d8f8b926e1356856fd81a6c9ad0c02c5a3f3a7eab3c`. SHA-256 do CSV `80e2930877b20e5c47d4fd18f394c17a4683b257ca715496e91c63520d528230`. Rodar `sync` novamente atualiza preços/listas e **não** reproduz necessariamente os mesmos bytes históricos; preserve o snapshot JSON local se precisar reprocessar a captura exata. Os dados públicos de [Zen](https://opencode.ai/zen/v1/models), [Go](https://opencode.ai/zen/go/v1/models) e [OpenRouter](https://openrouter.ai/api/v1/models) não são prova de acesso ou fatura.

O [snapshot normalizado arquivado](model-catalog-snapshot-2026-09-25/catalog-opencode.json) permite reproduzir a captura **offline**: `python3 scripts/model_catalog.py list --tool opencode --show-missing --format csv --cache-dir docs/model-catalog-snapshot-2026-09-25 --as-of-utc 2026-09-25T07:18:38Z` gera exatamente o CSV acima (SHA-256 comprovado na execução CLI). Sem `--as-of-utc`, a obsolescência é recalculada com o horário atual e os bytes históricos podem mudar. SHA-256 dos bytes do JSON `a5a1ec44587976a9fe96399bb275662ccdf90e1d8149ac7857f03ae05bb83dcc`; o arquivo contém os 122 registros Zen/Go normalizados e 460 entradas públicas OpenRouter, sem evidência privada de conta nem AA licenciada.

**Importação auditada pelo usuário:** `--aa-snapshot` exige `metric_id=aa_coding_agent_index`, `version=1.5`, `ingestion=manual_audited`, `terms_accepted=true` **somente após aceitar os termos**, atribuição, URL oficial HTTPS, data UTC e linhas com ID/variante, score, agente, harness, configurações, match e URL da evidência. `--availability-snapshot` exige `tool`, `ingestion=manual_audited`, `user_confirmed=true`, data UTC e linhas com ID exato, `local_listed`, `authenticated`, `entitled`, `verified_at` e origem; não inclua tokens/chaves. `--price-overrides` pode incluir `native_tariffs` indexado por `model_key`: Zen/OMP payg exige tarifa USD/token, `available_balance_usd` e confirmação de conta/saldo recente; Go exige `quota_window_remaining` e `quota_window_debit` por modelo em `5h`, `weekly`, `monthly` e `use_balance_fallback=false`. Sem evidência atual das permissões e do perfil de tokens da tarefa, o roteador permanece indisponível; o comando `route` nunca invoca modelos.

**Limite de isolamento:** o agente usa ferramentas por papel e worktree com escrita limitada; seu ponteiro `.git` é montado somente para leitura e revalidado antes de operações Git do controlador. A CLI compartilha a rede para alcançar providers e pode ler arquivos do host. O avaliador e o gate usam `bubblewrap --unshare-net`; não confundir com filtro de egress do agente nem isolamento contra código malicioso do próprio usuário. Sem cotas/saldo auditados recentes, uso real confiável e autorização interativa, qualquer caminho cobrado é bloqueado ou pausado; uma chamada paga sem consumo reportado não pode ser retomada automaticamente. Previsões não impõem teto rígido de faturamento. A prova de execução sem gasto usa uma CLI Claude fictícia e verificador fictício em repositório descartável: baseline 0 → score 2 em duas iterações com gate aprovado; não comprova cobrança/entitlement de uma conta real.

### Adaptadores e responsabilidades

- **Núcleo Python sem SDK proprietário:** descoberta, tabela/relatório, política, estado transacional do loop e leitura do `gate.json`. Processo do controlador fora da pasta editável pelo agente; metadados por execução fora do worktree e artefatos `.dev-workflows/` ignorados para Git quando gerados no projeto. Sem polling/serviço silencioso.
- **Claude Code:** usar `claude -p --model` e subagentes `agents/*.md` com aliases permitidos `haiku|sonnet|opus|inherit`; não escrever `provider/model` incompatível no frontmatter canônico. Instalação via plugin existente; preservar hooks e autorização da ferramenta. Resolver versão/modelo da conta antes de anunciar score; `model` alias não prova variante exata. Assinatura não é precificação por token.
- **OpenCode:** usar `opencode run --model provider/id#variant --agent ...` conforme versão local. `scripts/install.py` gera agentes em `~/.config/opencode/agents` e plugin de hooks; estender conversão para `model` por papel/conta com **deny-by-default** de ferramentas nos subagentes de leitura, sem herdar permissão `* allow`. Não sobrepor arquivo existente não pertencente ao pacote. O plugin OpenCode apenas avisa no fim: controlador deve bloquear por conta própria em `gate.json`.
- **OMP:** adicionar alvo `omp` ao instalador com package/adapter OMP próprio, skills/agentes nativos e papéis `modelRoles` resolvidos no runtime, sem reusar diretamente `hooks/hooks.json` do Claude. OMP descobre agentes de extensões e aceita aliases de papel `@nome` ([docs](https://github.com/can1357/oh-my-pi/blob/main/docs/task-agent-discovery.md)); se papel não estiver configurado, herdar do pai ou bloquear com diagnóstico — nunca criar ID fictício. Hooks só com port nativo e testes; sem eles, controlador externo impõe gate. Não depender do worktree local de um usuário para distribuição.
- **Hermes:** instalação atual é só de skills; não alegar suporte a subagentes ou loop até existir executor/adapter testado. Scripts de ranking/report ainda podem operar fora do Hermes.

## 5. Algoritmo do loop

```text
INICIALIZAR: validar config, meta, avaliador protegido, orçamento, permissões,
             working tree do usuário e catálogo; obter baseline em sandbox isolado.
SE baseline já atinge target E checks/gate exigidos passaram: finalizar sem editar.
PARA i em 1..max_iterations, respeitando relógio/orçamento:
  criar worktree descartável A PARTIR do melhor estado aceito (nunca reset no tree do usuário)
  planejar UMA hipótese de melhoria com contexto fresco + feedback anterior e papel roteado
  implementar mudança pequena dentro de escopo e permissões do dev-router
  verificar arquivos protegidos, ponteiro Git detached e isolamento; criar commit candidato
  rodar quality-gate --tier N em worktree limpo do commit; validar base, diff, tempo e checks
  SE fail/incomplete obrigatório: rejeitar e registrar motivo, sem declarar sucesso
  SENÃO executar avaliador independente em OUTRO worktree limpo do mesmo commit
  SE score válido, não regrediu e melhorou >= min_improvement: guardar commit como melhor
  SENÃO: marcar tentativa rejeitada e incrementar estagnação
  persistir decisão, custo/uso, evidências e hashes atomicamente
  SE melhor.score atinge target E todos os checks obrigatórios passam: parar com success
  SE estagnação/limite/cancelamento: parar com estado explícito, não success
FIM: produzir patch/worktree do melhor estado; usuário decide se incorpora.
```

Estados da execução: `planned → baselined → running → success|exhausted|paused|cancelled|error`; resultados por tentativa: `accepted|rejected|paused|interrupted`. `success` só vem do avaliador **externo** atual + gate `pass` + invariantes; texto do agente, `<promise>COMPLETE</promise>`, exit zero isolado e `incomplete` nunca são conclusão. Rejeição não apaga evidência nem altera branch do usuário. `resume` confere hash do avaliador, config, snapshot de modelos, branch/base e último estado aceito; se houve edição concorrente do usuário ou atualização de dependência crítica, pausa até decisão. Uma única execução ativa por projeto, escrita atômica com lock; interrupção é retomável sem contabilizar a mesma tentativa duas vezes, salvo chamada paga de consumo indeterminado.

**Controle de riscos:** agente não pode escrever avaliador/testes ocultos, metas, snapshots de catálogo, relatório de execução ou hashes de aceitação; executar verificação em contexto separado do workspace editável, com checkout limpo dos checks/dados aprovados. Config/linhas de comando, páginas externas e saída do agente são dados não confiáveis, não autorização para instalar dependências, enviar dados, gastar saldo, publicar, executar migrations, modificar serviços de produção ou desativar gate. Para ações com efeito externo, legal, financeiro ou dados sensíveis, interromper para aprovação explícita do usuário no momento da ação. Nenhum `--dangerously-skip-permissions`, `--auto` indiscriminado ou force-push. Guardar diffs sem segredos e limitar retenção de logs.

## 6. Requisitos verificáveis (EARS)

- **REQ-001** WHEN `models sync` for chamado, THE SYSTEM SHALL identificar IDs exatos e variantes dos catálogos Zen/Go e da ferramenta local sem presumir acesso pela lista pública.
- **REQ-002** WHEN preços forem importados, THE SYSTEM SHALL preservar cada preço OpenRouter por token, cache read/write separados, condições, ID, URL, data e unidade USD/1M apresentada.
- **REQ-003** IF um preço/campo de cache estiver ausente, THEN THE SYSTEM SHALL mostrá-lo como `n/d` e impedir custo comparativo inválido para o perfil afetado.
- **REQ-004** WHEN uma nota AA for importada, THE SYSTEM SHALL preservar índice, versão, harness, agente, variante, configurações, pontuação, proveniência e data.
- **REQ-005** IF índice, variante, versão, origem ou correspondência não forem compatíveis, THEN THE SYSTEM SHALL rejeitar a comparação/roteamento pontuado, sem substituir por Intelligence Index.
- **REQ-006** WHEN `models list` for chamado, THE SYSTEM SHALL listar modelos disponíveis e indisponíveis, ID por ferramenta, faixas fixas, preço entrada/saída/cache, nota ou `n/d`, licença de cobrança e justificativa da elegibilidade.
- **REQ-007** WHEN escolher modelo por papel, THE SYSTEM SHALL filtrar requisitos, nota/intervalo e orçamento, selecionar menor custo dentro do platô de pontos do melhor da faixa e explicar escolhas/empates.
- **REQ-008** IF uma faixa estiver vazia, THEN THE SYSTEM SHALL reportar ausência, oferecer opção explícita rotulada (ou rota fixa `unranked`) e nunca fabricar uma nota para preencher a faixa.
- **REQ-009** IF provider, ID ou conta não estiverem efetivamente disponíveis, THEN THE SYSTEM SHALL não despachar o modelo, ainda que conste das docs públicas.
- **REQ-010** IF uma rota Go exceder uma janela de cota ou cair em `Use balance` sem autorização de pagamento, THEN THE SYSTEM SHALL pausar antes da chamada cobrada.
- **REQ-011** WHEN mostrar custo, THE SYSTEM SHALL distinguir `C_OR` de referência, cobrança Zen, débito de cota Go e assinatura Claude; tokens estimados não são fatura.
- **REQ-012** IF metadados pagos estiverem expirados ou indisponíveis, THEN THE SYSTEM SHALL bloquear seleção automática cobrada, mantendo relatório legível.
- **REQ-013** WHEN `plan` for chamado, THE SYSTEM SHALL validar objetivo, avaliador, isolamento, modelos, gate, riscos e orçamento **sem** executar agentes, criar branches nem gastar tokens.
- **REQ-014** IF a base do projeto tiver mudanças do usuário, THEN THE SYSTEM SHALL evitar apagá-las ou absorvê-las sem consentimento e exigir snapshot/base deliberados.
- **REQ-015** WHEN `run` for autorizado, THE SYSTEM SHALL medir baseline pelo mesmo avaliador protegido e contexto usado nas tentativas.
- **REQ-016** WHILE o loop estiver ativo, THE SYSTEM SHALL limitar tentativas por iteração, tempo, custo, estagnação e permissões; manter hipótese/contexto novo por iteração.
- **REQ-017** WHEN um agente modificar código, THE SYSTEM SHALL rodar o tier do `dev-router` e validar `gate.json` atual e checks obrigatórios antes de medir sucesso.
- **REQ-018** IF gate `fail` ou `incomplete` obrigatório, regressão, score inválido ou tampering ocorrer, THEN THE SYSTEM SHALL rejeitar a tentativa com evidência, sem alterar o melhor estado.
- **REQ-019** WHEN houver melhoria válida, THE SYSTEM SHALL promover somente o estado isolado vencedor e registrar score, dados, gate, custo e hashes que sustentam a decisão.
- **REQ-020** IF o score atingir a meta com checks válidos, THEN THE SYSTEM SHALL parar como `success` e oferecer patch/worktree, **sem** aplicar/publicar na branch do usuário.
- **REQ-021** IF limite, cancelamento ou erro ocorrer primeiro, THEN THE SYSTEM SHALL parar como `exhausted|cancelled|error` com melhor evidência e sem afirmar que atingiu a meta.
- **REQ-022** WHEN `resume` for chamado, THE SYSTEM SHALL verificar invariantes/hashes e retomar sem duplicar gastos/tentativas; mudança concorrente exige pausa.
- **REQ-023** WHILE qualquer adapter estiver ativo, THE SYSTEM SHALL preservar restrições de ferramentas/hook/gate aplicáveis e nunca promover permissões de agentes de leitura por herança.
- **REQ-024** WHEN gerar documentação ou ranking com dados AA, THE SYSTEM SHALL atribuir fonte e respeitar seus termos, mantendo métricas de índices diferentes em tabelas separadas.

## 7. Plano de implementação e prova de aceitação

| Ordem | Entrega e locais previstos | Requisitos | Prova comportamental |
|---|---|---|---|
| 1 | `scripts/model_catalog.py` + módulo pequeno de parsing em `scripts/` e fixtures em `qa/` | 001–006, 011, 012, 024 | Importar JSON oficial OpenRouter e snapshot AA consentido; testar preço com/sem cache, 1M, override 272k, desambiguação de alias e índices não misturados; `models list` real sem chave AA quando snapshot local existe. |
| 2 | `scripts/model_router.py`, contrato TOML e `qa/test_model_router.py` | 007–012 | Matriz Zen vs Go vs Claude/OMP; falta de score/faixa vazia, custo no platô, proxy, quota Go 5h/semana/mês, queda para saldo Zen negada, empate determinístico. Teste de integração com catálogo CLI local, sem despachar modelo pago. |
| 3 | `scripts/goal_loop.py`, estado isolado e `qa/test_goal_loop.py` | 013–022 | Projeto temporário com avaliador que mede qualidade real: baseline abaixo, primeira tentativa melhora, segunda atinge meta; gate atual obrigatório; regressão/`incomplete`/tampering rejeitados; retomada, limite e árvore de trabalho suja preservada. Teste executa CLI e inspeciona worktrees e relatórios, não somente mocks. |
| 4 | Converter por ferramenta em `scripts/install.py`, `adapters/opencode/`, novo `adapters/omp/`, `agents/`, `skills/dev-router/` | 001, 007, 009, 023 | Smoke de instalação e descoberta dos 7 agentes por runtime, modelos resolvidos e ferramenta de leitura sem permissão de escrita; OpenCode warning não substitui veredito do controlador; Hermes segue explicitamente skills-only. |
| 5 | README em inglês/português, `docs/SKILLS.md`, `CHANGELOG.md`, testes CI | Todos | Quickstart com `plan`/`run`/`resume`, fontes/atribuição, preços dinâmicos, caso `n/d` e gates; `qa/lint_skills.py`, `qa/test_gate.py` e novos testes verdes. |

**Critérios de pronto do produto:** um projeto descartável atinge meta numérica apenas após duas iterações comprovadas; falha de gate nunca encerra como sucesso; Zen e Go escolhem listas distintas sem cobrança cruzada; preço OpenRouter e tarifa real aparecem separados; modelos sem benchmark não entram no ranking por nota; Claude por assinatura não recebe custo fictício; estado retoma após interrupção; nenhuma branch/arquivo do usuário é destruído. Testar também um caso em que meta não é atingida antes de `max_iterations`. Roteamento sozinho não conta como entrega do loop, nem o inverso.

**Migração e reversão:** manter o comportamento atual por padrão (`[loop].enabled=false`, agentes existentes preservados); ativar explicitamente por projeto e ferramenta após diagnóstico; distribuir adapter OMP nativo sem presumir o worktree local; remover/corrigir caminhos antigos de modelo ao ativar roteamento em cada runtime. Desativar execução retornando `enabled=false` e usar papéis estáticos atuais. Não excluir relatórios/worktrees automaticamente; fornecer passos de recuperação e escolha de aplicação do patch. Spec nível 3: revisar com o usuário antes da implementação, conforme `agents/planner.md`.

## 8. Prompt original de implementação (registro histórico)

> Implemente no `dev-workflows` a spec `docs/goal-loop-model-routing-spec.md`, sem reduzir nenhum REQ-001…024. Preserve `dev-router`, quality gate e hooks atuais. Comece pelo importador de catálogo com proveniência e pelo roteador, depois integre Claude Code, OpenCode e OMP, e por fim o controlador de loop com worktrees/avaliador independente; Hermes permanece skills-only até existir adapter real. Use faixas **fixas de nota de código** `[10,20)`, `[20,50)`, `[50,100]`, não quantis relativos. Descubra apenas modelos acessíveis à conta/ferramenta. Cruze IDs curados Zen/Go/Claude/OMP com tarifas **OpenRouter** de entrada, saída, leitura e escrita de cache; marque campos faltantes `n/d` e informe os preços OpenRouter como **referência**, distintos da cobrança Zen, cota Go e assinatura Claude. Use exclusivamente um índice/versionamento de programação da Artificial Analysis por ranking; atribua fonte, guarde variante/harness e jamais converta nota do Intelligence Index em nota de código. Mostre ranking auditável por papel, escolha o modelo de menor custo dentro do platô dos melhores da faixa, bloqueie seleção cobrada sem autorização e nunca faça fallback Go→Zen cobrado sem aceite. No loop, estabeleça baseline, aceite apenas melhoria numérica com gate/checks obrigatórios aprovados e avaliador protegido, pare ao atingir alvo ou orçamento e preserve o trabalho do usuário. Entregue testes comportamentais, smoke CLI real, docs, tabela reproduzível com IDs/notas/preços `n/d` e limites honestamente reportados. Não apresente instalação de skills como se fosse o loop em funcionamento.
