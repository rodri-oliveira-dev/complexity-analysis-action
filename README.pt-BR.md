# Complexity Analysis Action

[English](README.md) | Português (Brasil)

GitHub Action reutilizável para analisar a complexidade de projetos e soluções C# no CI. A Action instala e executa a CLI publicada [`ComplexityAnalysis.Tool`](https://www.nuget.org/packages/ComplexityAnalysis.Tool), sem replicar o motor de análise. O código da CLI, dos analyzers e do MCP está no [projeto principal](https://github.com/rodri-oliveira-dev/complexity-analyzers).

As versões da Action são independentes das versões da CLI. A primeira release estável planejada é `v1.0.0`, e a versão exata da CLI configurada atualmente é `1.0.1`.

> [!IMPORTANT]
> Esta é uma candidata a release. No momento desta atualização, a Action ainda não possui release publicada nem listagem no GitHub Marketplace. A plataforma suportada é Ubuntu. Para avaliar a Action antes da primeira release, utilize o **SHA completo de 40 caracteres de um commit revisado**. Não considere `@v1` ou `@v1.0.0` como disponíveis até a publicação.

## O que ela faz

A Complexity Analysis Action ajuda equipes .NET a avaliar a complexidade de código C# em pipelines, configurar quality gates, comparar alterações entre branches e apresentar regressões comprovadas nos pull requests.

Ela oferece:

- Análise de `.csproj`, `.sln` e `.slnx`.
- Relatórios JSON, SARIF 2.1.0 e resumo no GitHub Actions.
- Limites opcionais para complexidade Big-O, ciclomática, cognitiva, aninhamento, NLOC e duplicação.
- Comparação de snapshots para identificar alterações de complexidade entre base e PR.
- Upload opcional de SARIF ao GitHub Code Scanning.
- Comentário de PR opcional, limitado e atualizado sem duplicações.

Os resultados são métricas estruturais e estimativas de complexidade algorítmica, **não** benchmarks de runtime, otimização automática ou previsões precisas de tempo de execução. Evidências `Unknown` ou incomparáveis não equivalem a regressões.

## Requisitos

- Runner GitHub-hosted ou self-hosted **Ubuntu** com Bash, Python 3 e acesso ao NuGet.org. A Action instala o SDK .NET 10.
- Checkout do repositório contendo o arquivo de projeto ou solução. Para comparação com a base, o histórico Git correspondente precisa estar acessível.
- Permissão `contents: read` para análise e comparação sem publicação.
- Permissões adicionais somente quando SARIF ou comentários forem explicitamente habilitados.

Não há suporte anunciado para Windows ou macOS nesta primeira versão, pois os cenários end-to-end correspondentes ainda não foram validados.

## Como utilizar

Crie `.github/workflows/complexity-analysis.yml` no repositório consumidor. Antes da release, substitua o marcador `REVIEWED_FULL_40_CHARACTER_SHA` pelo SHA completo de um commit revisado da Action, e `MySolution.slnx` pelo caminho real do projeto ou solução.

```yaml
name: Complexity Analysis

on:
  pull_request:

permissions:
  contents: read

jobs:
  complexity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
        with:
          persist-credentials: false
      - id: complexity
        uses: rodri-oliveira-dev/complexity-analysis-action@REVIEWED_FULL_40_CHARACTER_SHA
        with:
          path: MySolution.slnx
          max-cyclomatic-complexity: "15"
          max-cognitive-complexity: "20"
          fail-on-quality-gate: "true"
          compare-with-base: "true"
          fail-on-regression: "true"
```

Esse exemplo usa apenas permissões de leitura. O marcador é proposital e **não é um ref executável** antes de ser substituído. Quando as tags existirem, também será possível usar `@v1.0.0` ou a referência compatível `@v1`; para maior reprodutibilidade, prefira um SHA completo.

Outros exemplos, para copiar e adaptar:

- [Análise básica](examples/basic-analysis.yml)
- [Quality gates](examples/quality-gates.yml)
- [Análise não bloqueante](examples/non-blocking-analysis.yml)
- [Upload SARIF](examples/sarif-upload.yml)
- [Análise de regressões em PRs](examples/secure-pr-analysis.yml)
- [Publicação isolada para PR de fork](examples/secure-pr-publish.yml)
- [Workflow completo](examples/consumer-workflow.yml)

Alguns arquivos de exemplo ainda contêm marcadores de SHA e caminhos de solução demonstrativos. Substitua-os antes de executar.

## Entradas (`with`)

| Entrada | Obrigatória | Padrão | Descrição |
| --- | --- | --- | --- |
| `path` | Sim | — | Caminho do `.csproj`, `.sln` ou `.slnx` dentro do workspace |
| `tool-version` | Não | `1.0.1` | Versão publicada e exata do pacote `ComplexityAnalysis.Tool` |
| `output-directory` | Não | `complexity-analysis-reports` | Pasta dos relatórios |
| `include-generated` | Não | `false` | Inclui código C# gerado |
| `detect-duplicates` | Não | `false` | Habilita a detecção normalizada de duplicação |
| `max-complexity` | Não | não definido | Limite de classe Big-O |
| `max-cyclomatic-complexity` | Não | não definido | Limite de complexidade ciclomática |
| `max-cognitive-complexity` | Não | não definido | Limite de complexidade cognitiva |
| `max-nesting-depth` | Não | não definido | Limite de aninhamento |
| `max-method-nloc` | Não | não definido | Limite de NLOC por método |
| `max-duplicate-rate` | Não | não definido | Limite da taxa de duplicação |
| `fail-on-quality-gate` | Não | `true` | Falha o job se um limite configurado for violado |
| `upload-sarif` | Não | `false` | Valida e envia SARIF ao Code Scanning |
| `compare-with-base` | Não | `false` | Habilita comparação automática com a revisão-base |
| `base-ref` | Não | não definido | Ref ou commit Git explícito como base |
| `fail-on-regression` | Não | `false` | Falha quando há regressões comprovadas |
| `baseline-path` | Não | não definido | Snapshot JSON existente no workspace |
| `comparison-output` | Não | `<output-directory>/comparison.json` | Caminho do relatório comparativo |
| `comment-on-pr` | Não | `false` | Publica/atualiza resumo de PR com permissão adicional |

Entradas booleanas aceitam somente as strings minúsculas `true` e `false`. Sem limites configurados, nenhum quality gate falha automaticamente. Para Big-O, são aceitas classificações como `constant`, `log_n`, `linear`, `n_log_n`, `quadratic`, `cubic`, `exponential` e `factorial` (consulte [a referência em inglês](README.md#inputs) para aliases e validações).

## Saídas

| Saída | Descrição |
| --- | --- |
| `report-path` | Caminho absoluto do relatório JSON |
| `sarif-path` | Caminho absoluto do SARIF 2.1.0 |
| `analysis-status` | `success`, `failed` ou `canceled` |
| `quality-gate-status` | `not-configured`, `passed`, `failed` ou `unknown` |
| `tool-version` | Versão exata da CLI executada |
| `baseline-report-path` | Caminho reservado para o snapshot base |
| `current-report-path` | Caminho reservado para o snapshot atual |
| `comparison-report-path` | Caminho do relatório de comparação JSON |
| `regression-count` | Quantidade de regressões comprovadas (0 se a comparação não concluiu) |
| `comparison-status` | `not-requested`, `no-regressions`, `regressions-detected`, `unavailable` ou `failed` |
| `pr-report-path` | Caminho do relatório estruturado de PR, quando gerado |

Esses caminhos representam arquivos do job, **não** links permanentes. Se precisar preservá-los, use `actions/upload-artifact`. Uma violação de quality gate pode deixar `analysis-status` como `success` porque a CLI executou corretamente; avalie também `quality-gate-status`.

## Comparação de regressões

`compare-with-base: "true"` gera snapshots da revisão-base e da revisão do PR e os compara usando a CLI, sem duplicar sua lógica. O resultado distingue regressões comprovadas, melhorias e evidências desconhecidas/incompatíveis.

Para usar um snapshot existente, configure `baseline-path`. Para indicar uma revisão-base explícita, utilize `base-ref`, respeitando as restrições da Action. Uma falha ao obter a revisão-base é um estado indisponível ou erro, **não** um resultado sem regressões.

Há duas políticas independentes: quality gates avaliam limites absolutos; `fail-on-regression` avalia regressões entre as revisões. Um método pode exceder um limite preexistente sem apresentar piora neste PR.

## Permissões e segurança

| Uso | Permissões mínimas relevantes |
| --- | --- |
| Análise, quality gates e comparação | `contents: read` |
| Upload SARIF | `contents: read`, `security-events: write` |
| Comentário direto em PR confiável do mesmo repositório | `contents: read`, `pull-requests: write` |
| Comentário em PR originado de fork | Análise somente leitura e publisher isolado com `actions: read`, `pull-requests: write` |

- **Nunca** execute a análise de código não confiável no contexto `pull_request_target`.
- A avaliação de arquivos MSBuild pode executar lógica do próprio projeto. A Action **não** isola processos ou a rede por sandbox.
- Não forneça segredos ou tokens de escrita ao job que analisa um PR não confiável.
- Para PRs de forks, use um workflow de análise somente leitura que gere um artefato validado e um workflow `workflow_run` separado que apenas publique o relatório, conforme os [exemplos seguros](examples/secure-pr-analysis.yml) e [de publicação](examples/secure-pr-publish.yml).
- A publicação de comentários diretos é opcional e deve ser reservada a workflows confiáveis, respeitando as políticas de segurança e permissões do repositório.

A publicação automática de resultados não é requisito para usar os relatórios JSON e o GitHub Job Summary.

## Solução de problemas

**Action não encontrada ao usar `@v1`:** ainda não há garantia de que as tags foram publicadas. Consulte [Releases](https://github.com/rodri-oliveira-dev/complexity-analysis-action/releases) e use um SHA completo revisado para avaliações.

**Falha na instalação:** confira a conexão com NuGet.org, o SDK/runtime .NET 10 e se `tool-version` especifica uma versão publicada exata.

**Caminho inexistente:** `path` precisa apontar para um projeto ou solução dentro do workspace. Verifique nomes de arquivos, maiúsculas/minúsculas e etapas de checkout.

**Comparação não disponível:** confira o histórico Git, a disponibilidade da revisão-base e se o caminho do projeto existe nas duas revisões. Não interprete um resultado `unavailable` como aprovação.

**SARIF rejeitado:** verifique a disponibilidade do Code Scanning, `security-events: write` e os erros do passo de upload.

**Comentário não publicado:** confirme o evento do PR e as permissões do token. PRs originados de forks geralmente não permitem escrita direta e devem utilizar o publicador isolado.

**Falha no quality gate:** revise os limites configurados, o relatório JSON e `quality-gate-status`. Regressões são uma verificação independente.

## Desenvolvimento e releases

A Action tem versionamento SemVer independente do `ComplexityAnalysis.Tool`, do Roslyn Analyzer e do MCP. As tags `vX.Y.Z` identificam releases específicas; a referência `vX`, quando criada, acompanha versões compatíveis da mesma major.

A publicação é controlada pelo mantenedor, conforme o [checklist de release](RELEASE_CHECKLIST.md) e a [orientação para o Marketplace](docs/marketplace.md). Até a aprovação e publicação, as referências à `v1.0.0` são um planejamento, não uma release existente.

Para validar alterações na Action, consulte [Contribuindo](CONTRIBUTING.md), o [guia de mantenedores](docs/maintainers.md) e as verificações de CI. Para conceitos e detalhes das métricas, consulte a documentação [Complexity Analyzers](https://github.com/rodri-oliveira-dev/complexity-analyzers).
