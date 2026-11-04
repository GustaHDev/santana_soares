# Sistema de Gestão de Viagens: Documentação do Projeto

Versão do documento: 2026-11-03
Projeto: sistema web para uma empresa de logística de caminhões (transporte de carga por tonelada).

## 0. Como usar este documento (instruções para a IA que for gerar o código)

- Este documento é a fonte de verdade das decisões de negócio e de modelagem. Siga-o à risca.
- Tudo o que não está marcado como **(SUGESTÃO)** foi decidido com o responsável pelo projeto.
- Itens marcados como **(SUGESTÃO)** são recomendações técnicas ainda não confirmadas: podem ser usados, mas devem ser sinalizados como tal no código ou nos comentários.
- A seção 13 lista pontos em aberto. **Não invente regras de negócio.** Se algo necessário não estiver aqui, pergunte antes de implementar.
- Nomes de modelos, campos, rotas, mensagens e interface ficam **em português** (a empresa não tem planos de atuar fora do Brasil).
- O código a ser gerado agora é o **MVP** (seção 2). As fases seguintes estão documentadas para que o modelo de dados e a arquitetura já as comportem, mas **não devem ser implementadas agora**, salvo pedido explícito.

## 1. Contexto e objetivo

- A empresa não possui nenhum sistema. Hoje registra apenas o que **ganha** (faturamento) em planilhas de Excel, organizando as viagens e o valor que cada cliente paga por viagem. Os gastos não são medidos.
- Plano atual: **migrar essa organização de planilhas para um sistema centralizado e organizado.**
- Objetivo de longo prazo: com os dados centralizados, a empresa poder planejar crescimento ou fazer cortes quando necessário.
- Quem preenche os dados: os **motoristas** (pelo celular, na estrada) e os **administradores** (que completam e fecham as viagens e cuidam dos cadastros e do financeiro).
- O sistema não define processos operacionais da empresa (como os motoristas são orientados a preencher). Cabe ao sistema apenas dar suporte ao fluxo descrito aqui.
- O volume de motoristas e viagens por mês é desconhecido. Use paginação e filtros nas listagens desde o início. O volume esperado é pequeno e não exige arquitetura especial.

## 2. Escopo e fases

### MVP (implementar agora)
Cadastro e uso de:
- usuários (admin e motorista, login por celular);
- motoristas;
- cidades;
- clientes e a relação cliente-cidade com o preço da tonelada;
- viagens, incluindo o fluxo motorista cria, admin completa e fecha.

### Fase 2 (documentada, não implementar agora)
- Abastecimento (registrado pelo motorista)
- Desconto/adiantamento (lançado pelo admin)
- Fechamento mensal de salário

### Fases futuras (a detalhar quando chegar a hora)
- Relatórios: faturamento por mês, cliente e cidade; margem por viagem; consumo médio.
- Importação do histórico das planilhas (não definida; não faz parte do escopo atual).
- Controle de custos (manutenção, pneus, pedágio, seguro etc.) e financeiro (recebimento por viagem).
- Migração da interface para o modelo híbrido (seção 3).

## 3. Stack e arquitetura

### Stack
- **Linguagem/framework:** Python + Django.
- **Banco:** PostgreSQL.
- **Aplicação web.** Não é desktop e não é app nativo. Os motoristas acessam pelo celular, pelo navegador. Todos têm sinal de internet durante as viagens, então **não há modo offline** nem necessidade de PWA no MVP.
- **Interface do MVP:** somente Django, usando o **Django Admin** personalizado.
- **Objetivo final de interface: modelo híbrido.** Django Admin para os cadastros que mudam pouco (cidades, clientes, preços, motoristas) e telas próprias (templates Django) para o que se faz todo dia (completar e fechar viagens, descontos, fechamento mensal, tudo do motorista). A migração é gradual, depois do MVP.
- **(SUGESTÃO)** Telas próprias futuras com templates Django + HTMX + Tailwind, responsivas, pensadas para celular.
- **(SUGESTÃO)** Deploy com Docker em uma VPS, HTTPS, backup diário do banco guardado fora do servidor.
- Configuração regional: `LANGUAGE_CODE = "pt-br"`, `TIME_ZONE = "America/Sao_Paulo"`, `USE_TZ = True`. Moeda em R$.

### Arquitetura
Monólito modular com o padrão MVT do Django, mais camada de serviços:

| Camada | Responsabilidade |
|---|---|
| **Views / Admin** | HTTP e permissões. Chamam services (escrita) ou selectors (leitura). Não contêm regra de negócio. |
| **Services** (`services.py`) | Escritas e regras de negócio (criar viagem copiando o preço, fechar viagem, fechar mês). Cada service tem um objetivo só e usa `transaction.atomic` quando altera mais de uma tabela. |
| **Selectors** (`selectors.py`) | Leituras para telas e relatórios. |
| **Models / QuerySets customizados** | Estrutura, constraints e filtros reutilizáveis (ex.: `do_mes`, `abertas`). |

Regras de arquitetura:
- **Sem Repository Pattern.** O ORM do Django já faz essa função. Os services e selectors usam `Model.objects` diretamente.
- **Sem lógica de negócio em signals.** Chame o service explicitamente.
- **Contas importantes em funções puras** (sem acesso ao banco), fáceis de testar. Exemplo: `calcular_salario`.
- Sem DDD completo, arquitetura hexagonal, CQRS ou microsserviços.
- Dinheiro em `DecimalField`/`NUMERIC` (nunca float). Peso em `NUMERIC(10,3)`.
- Todas as tabelas com `criado_em` e `atualizado_em`.
- Auditoria com `django-simple-history` nas entidades que afetam dinheiro (Viagem, ClienteCidade e, na fase 2, Desconto e Fechamento).
- Senhas sempre com hash (padrão do Django). Nunca guardar senha em texto.

### Estrutura de apps
```
projeto/
├── config/        # settings, urls
├── core/          # constantes, utilitários, mixins
├── usuarios/      # Usuario, Motorista, autenticação
├── cadastros/     # Cidade, Cliente, ClienteCidade
├── viagens/       # Viagem (MVP); Abastecimento (fase 2)
│   ├── models.py
│   ├── services.py
│   └── selectors.py
├── financeiro/    # Desconto, Fechamento (fase 2)
│   └── services/  # fechamento.py, descontos.py, salario.py (função pura)
└── relatorios/    # fase futura: selectors e views de leitura
```
Dependências em uma direção só: `financeiro` usa `viagens`; `viagens` usa `cadastros` e `usuarios`; nunca o contrário.

Constantes em `core`:
```python
COMISSAO_MOTORISTA = Decimal("0.12")   # 12%, fixa para todos
```

## 4. Papéis e permissões

Existem exatamente dois papéis, definidos pelo campo `role` da tabela `Usuario`: **admin** e **motorista**. Podem existir vários admins.

### Autenticação
- Login por **celular** para todos (admin e motorista). O campo `celular` é o `USERNAME_FIELD` de um modelo de usuário customizado.
- O **admin cria o usuário do motorista com uma senha inicial**, e o motorista **troca a senha no primeiro acesso** (campo `precisa_trocar_senha`).

### Matriz de permissões (MVP)

| Recurso | Admin | Motorista |
|---|---|---|
| Usuários e motoristas | criar, editar, inativar | ver o próprio perfil; trocar a própria senha |
| Cidades, clientes, ClienteCidade (preços) | criar, editar, inativar | **sem acesso**. Só seleciona cliente/cidade ao criar uma viagem, **sem ver preços** |
| Viagens | ver todas, editar, completar e fechar; editar viagem fechada até o fechamento mensal | criar viagem; ver **somente as próprias**; editar e excluir a própria viagem **só enquanto `aberta`**; campos do admin nunca aparecem |

### Regra de visibilidade financeira
O motorista **não vê nenhum valor financeiro**, exceto o que lhe compete: salário, descontos e adiantamentos (a partir da fase 2). Em especial, **nunca** vê `tonelada_cliente`, `tonelada_motorista`, `valor_total`, `valor_motorista` nem o lucro da empresa. Cuidado: o `__str__` de `ClienteCidade` não deve conter o preço.

## 5. Regras de negócio

1. **Cada motorista usa um único caminhão fixo.** Caminhão não é entidade: a `placa_caminhao` fica no cadastro do Motorista.
2. **Uma viagem tem um cliente, um destino e uma nota fiscal.** O destino é a cidade do `ClienteCidade` escolhido.
3. **Preço do cliente por cliente + cidade.** Dois clientes na mesma cidade podem pagar valores diferentes, e o mesmo cliente pode pagar valores diferentes em cidades diferentes. O preço fica em `ClienteCidade.preco_tonelada` e muda, no máximo, cerca de uma vez por ano.
4. **O cliente é cadastrado uma única vez.** Para atender várias cidades, cria-se uma linha em `ClienteCidade` para cada cidade. Não se duplica o cliente.
5. **Valor da tonelada para o motorista (`tonelada_motorista`)** fica em `Viagem`, preenchido pelo **admin**. É o mesmo valor para todos os motoristas num dado cliente + cidade e é menor que o preço do cliente (a diferença é o lucro da empresa).
6. **Snapshot do preço do cliente.** Quando a viagem é criada, o sistema copia `ClienteCidade.preco_tonelada` para `Viagem.tonelada_cliente`. Reajustes futuros no cadastro não alteram viagens antigas. O admin pode editar `tonelada_cliente` na viagem antes do fechamento.
7. **Sugestão de `tonelada_motorista` (aprovada):** ao completar uma viagem, o sistema sugere o `tonelada_motorista` da última viagem do mesmo `ClienteCidade`, para o admin não digitar toda vez. O admin pode alterar.
8. **Comissão do motorista: 12% fixa**, sobre o `valor_motorista`. Os 88% restantes do `valor_motorista` cobrem os custos da empresa (diesel e demais). O diesel é **pago pela empresa**, em **posto externo** (não há tanque próprio).
9. **Viagem conta para o mês da `data_chegada`.** Uma viagem que sai dia 30 e chega dia 2 entra no mês seguinte.
10. **CTE:** só existe para clientes com `faz_cte = true`. Para os demais, o campo **não é exibido** na interface (para evitar erros do admin) e fica nulo.
11. **Nada é apagado**, com uma exceção: viagem ainda **não fechada** (`aberta`) pode ser excluída. Cadastros são inativados (campo `ativo`), nunca removidos.
12. **CNPJ não é usado.** Não crie esse campo.

## 6. Modelo de dados

Convenções: `PROTECT` em todas as chaves estrangeiras (nada em cascata). `criado_em` e `atualizado_em` em todas as tabelas. Abaixo, "Quem" indica quem preenche o campo.

### 6.1 `Usuario` (app `usuarios`), MVP
Modelo de usuário customizado (`AbstractBaseUser` + `PermissionsMixin`).

| Campo | Tipo | Obrigatório | Quem | Observação |
|---|---|---|---|---|
| id | auto | sim | sistema | |
| celular | CharField, único | sim | admin | Login (`USERNAME_FIELD`). (SUGESTÃO) guardar só dígitos, com DDD |
| nome | CharField | sim | admin | |
| password | hash do Django | sim | admin (inicial) | |
| role | choices: `admin`, `motorista` | sim | admin | |
| ativo | bool (padrão True) | sim | admin | Usar como `is_active` |
| precisa_trocar_senha | bool (padrão True) | sim | sistema | Vira False após a troca no primeiro acesso |

### 6.2 `Motorista` (app `usuarios`), MVP
Perfil ligado ao usuário com `role = motorista`.

| Campo | Tipo | Obrigatório | Quem | Observação |
|---|---|---|---|---|
| id | auto | sim | sistema | |
| usuario | OneToOne → Usuario | sim | admin | |
| placa_caminhao | CharField, **único** | sim | admin | Um motorista, um caminhão fixo |

Nome, celular e situação (ativo) ficam em `Usuario`.

### 6.3 `Cidade` (app `cadastros`), MVP

| Campo | Tipo | Obrigatório | Quem |
|---|---|---|---|
| id | auto | sim | sistema |
| nome | CharField | sim | admin |
| uf | CharField(2) | sim | admin |
| ativo | bool (padrão True) | sim | admin |

Único: `(nome, uf)`.

### 6.4 `Cliente` (app `cadastros`), MVP

| Campo | Tipo | Obrigatório | Quem | Observação |
|---|---|---|---|---|
| id | auto | sim | sistema | |
| nome | CharField | sim | admin | |
| faz_cte | bool | sim | admin | Varia **por cliente**, não por cidade |
| ativo | bool (padrão True) | sim | admin | |

### 6.5 `ClienteCidade` (app `cadastros`), MVP
Liga um cliente a uma cidade que ele atende e guarda o preço da tonelada **nessa combinação**.

| Campo | Tipo | Obrigatório | Quem | Observação |
|---|---|---|---|---|
| id | auto | sim | sistema | |
| cliente | FK → Cliente | sim | admin | |
| cidade | FK → Cidade | sim | admin | |
| preco_tonelada | Decimal(12,2), > 0 | sim | admin | Valor que o **cliente** paga por tonelada nessa cidade |
| ativo | bool (padrão True) | sim | admin | |

Único: `(cliente, cidade)`. Com histórico (`simple_history`). O `__str__` deve ser `"Cliente — Cidade"`, **sem preço**.

### 6.6 `Viagem` (app `viagens`), MVP

**Campos preenchidos pelo motorista** (na criação ou depois, enquanto a viagem está `aberta`):

| Campo | Tipo | Obrigatório | Observação |
|---|---|---|---|
| id | auto | sim | |
| motorista | FK → Motorista | sim | Definido automaticamente pelo usuário logado |
| cliente_cidade | FK → ClienteCidade | sim | Define cliente **e destino** |
| origem | FK → Cidade | sim | Cidade da tabela `Cidade` (não é texto livre) |
| data_saida | date | sim | Data de carregamento |
| nota_fiscal | CharField | sim | Uma por viagem |
| peso_ton | Decimal(10,3), > 0 | sim | Peso em toneladas |
| km_inicial | inteiro ≥ 0 | sim | Quilometragem no início |
| data_chegada | date, nulo até preencher | para fechar | Data em que chegou no cliente |
| km_final | inteiro, nulo até preencher | para fechar | Quilometragem no final |

**Campos preenchidos pelo admin ou pelo sistema** (nunca visíveis ao motorista):

| Campo | Tipo | Obrigatório | Quem | Observação |
|---|---|---|---|---|
| tonelada_cliente | Decimal(12,2) | sim | sistema, admin edita | Snapshot copiado de `ClienteCidade.preco_tonelada` na criação. Preenchido pelo sistema; o admin pode editar antes do fechamento |
| tonelada_motorista | Decimal(12,2), nulo até preencher | para fechar | admin | Sugerido pela última viagem do mesmo `ClienteCidade` |
| cte | CharField, nulo | só se `cliente.faz_cte` | admin | Campo oculto na interface quando o cliente não faz CTE |
| status | choices: `aberta`, `fechada` | sim | sistema | Padrão `aberta` |
| fechada_em | datetime, nulo | não | sistema | Preenchido ao fechar |
| fechada_por | FK → Usuario, nulo | não | sistema | Admin que fechou |
| fechamento | FK → Fechamento, nulo | não | sistema | **Fase 2.** Preenchido no fechamento mensal |

**Valores calculados (não são gravados):**
```
km_rodado       = km_final − km_inicial
valor_total     = peso_ton × tonelada_cliente      # faturamento da viagem
valor_motorista = peso_ton × tonelada_motorista    # base da comissão
margem_bruta    = valor_total − valor_motorista    # lucro da empresa por viagem
diesel_litros   = soma dos litros dos abastecimentos da viagem   # fase 2
media_km_por_l  = km_rodado / diesel_litros                      # fase 2
```
Implementar como propriedades do model e/ou `annotate` nos selectors. Os preços por tonelada são o único snapshot gravado. Com histórico (`simple_history`).

### 6.7 `Abastecimento` (app `viagens`), **Fase 2**

| Campo | Tipo | Obrigatório | Quem | Observação |
|---|---|---|---|---|
| id | auto | sim | sistema | |
| motorista | FK → Motorista | sim | sistema | Usuário logado |
| viagem | FK → Viagem, nulo | não | sistema | Vínculo **automático pela data** (entre `data_saida` e `data_chegada`) |
| data | date | sim | motorista | |
| litros | Decimal | sim | motorista | |
| valor_litro | Decimal | sim | motorista | |
| posto | CharField | sim | motorista | Posto externo |
| km_no_abastecimento | inteiro | sim | motorista | |

`total = litros × valor_litro` (calculado). O abastecimento é registrado pelo **motorista**.

### 6.8 `Desconto` (app `financeiro`), **Fase 2**
Descontos e adiantamentos usam a mesma tabela.

| Campo | Tipo | Obrigatório | Observação |
|---|---|---|---|
| id | auto | sim | |
| motorista | FK → Motorista | sim | |
| valor | Decimal(12,2), > 0 | sim | |
| motivo | CharField | sim | |
| data | date | sim | Define o mês do lançamento |
| tipo | choices: `desconto`, `adiantamento`, `ajuste`, `saldo_anterior` | sim | `ajuste` é crédito (soma ao salário). Os demais abatem |
| fechamento | FK → Fechamento, nulo | não | Nulo enquanto o mês está aberto |

**Só o admin lança.** O motorista **pode ver** os seus.

### 6.9 `Fechamento` (app `financeiro`), **Fase 2**

| Campo | Tipo | Observação |
|---|---|---|
| id | auto | |
| motorista | FK → Motorista | |
| mes_referencia | date (dia 1 do mês) | |
| valor_viagens | Decimal(12,2) | Soma dos `valor_motorista` das viagens do mês |
| comissao_percentual | Decimal | Snapshot do percentual usado (0,12) |
| valor_comissao | Decimal(12,2) | `valor_viagens × comissao_percentual` |
| total_descontos | Decimal(12,2) | Descontos + adiantamentos + saldos anteriores − ajustes |
| salario_liquido | Decimal(12,2), ≥ 0 | Nunca negativo |
| fechado_em, fechado_por | datetime, FK → Usuario | |
| pago_em | datetime, nulo | Nulo até o pagamento |

Único: `(motorista, mes_referencia)`.

## 7. Fórmulas

```
valor_total      = peso_ton × tonelada_cliente
valor_motorista  = peso_ton × tonelada_motorista
margem_bruta     = valor_total − valor_motorista

# Fase 2, no fechamento mensal de um motorista:
valor_viagens    = soma(valor_motorista) das viagens fechadas com data_chegada no mês
valor_comissao   = valor_viagens × 0,12
liquido_bruto    = valor_comissao − total_descontos
salario_liquido  = max(liquido_bruto, 0)
```
Se `liquido_bruto < 0` (por exemplo, adiantamento maior que o salário), o `salario_liquido` é gravado como **0** e o sistema cria **automaticamente** um lançamento `Desconto` do tipo `saldo_anterior` no mês seguinte com o valor devido (`|liquido_bruto|`).

Os 88% restantes do `valor_motorista` cobrem os custos operacionais da empresa (diesel etc.). O controle desses custos está fora do escopo atual.

## 8. Fluxos

### 8.1 Viagem (MVP)
1. **Motorista cria a viagem** informando `cliente_cidade` (cliente e destino), `origem`, `data_saida`, `nota_fiscal`, `peso_ton` e `km_inicial`. O sistema define `motorista`, `status = aberta` e copia o preço para `tonelada_cliente`.
2. Durante a viagem, o motorista preenche `data_chegada` e `km_final` quando disponíveis (a viagem pode estar sem eles enquanto está em andamento).
3. Enquanto `aberta`, o motorista pode **editar** os seus campos e **excluir** a viagem.
4. **Admin completa a viagem:** preenche `tonelada_motorista` (com sugestão da última viagem do mesmo `ClienteCidade`), `cte` (se o cliente faz CTE) e pode ajustar `tonelada_cliente`.
5. **Admin fecha a viagem** (service `fechar_viagem`). Para fechar, **todos os campos são obrigatórios**: os campos do motorista, `data_chegada`, `km_final`, `tonelada_cliente`, `tonelada_motorista` e, quando `cliente.faz_cte = true`, o `cte`. Se faltar algo, o fechamento é **bloqueado** com mensagem clara. Ao fechar: `status = fechada`, `fechada_em` e `fechada_por`.
6. Depois de `fechada`, **só o admin edita** (o motorista não edita nem exclui). O admin pode editar até o fechamento mensal (fase 2). Depois do fechamento mensal, a viagem fica **travada para todos**.

### 8.2 Fechamento mensal (Fase 2)
1. O admin executa "fechar mês" para um motorista e um mês de referência.
2. O sistema calcula (seção 7), grava o `Fechamento` e preenche `fechamento` nas viagens e descontos do mês, **numa única transação**.
3. Registros com `fechamento` preenchido ficam **bloqueados** para edição e exclusão (validar no service e, de preferência, também no banco).
4. O pagamento é um passo separado: o admin marca `pago_em`.
5. Se o admin precisar **reabrir** um mês: só admin, só se `pago_em` for nulo, registrando quem reabriu e quando. Erros descobertos depois do pagamento entram como lançamento `ajuste` no mês seguinte.

Regras de verificação no fechamento mensal:
- O sistema **avisa** (sem bloquear) se o motorista tem viagem em andamento.
- Viagem que exige CTE e ainda não o tem **bloqueia** o fechamento (na prática, essa viagem não consegue ser fechada pelo admin).

## 9. Restrições e validações

No banco (`CheckConstraint`/`UniqueConstraint`):
- `Viagem`: `km_final >= km_inicial` (quando `km_final` não é nulo); `data_chegada >= data_saida` (quando não é nula); `peso_ton > 0`; preços > 0.
- `Viagem` fechada: `data_chegada`, `km_final`, `tonelada_cliente` e `tonelada_motorista` não nulos quando `status = 'fechada'`.
- `ClienteCidade`: único `(cliente, cidade)`. `Motorista.placa_caminhao`: único. `Cidade`: único `(nome, uf)`.
- `Fechamento` (fase 2): único `(motorista, mes_referencia)`.

Na aplicação (services):
- `cte` obrigatório para fechar **apenas** se `cliente.faz_cte`; oculto/nulo caso contrário.
- Motorista só vê e altera as **próprias** viagens, e só enquanto `aberta`.
- Campos do admin (`tonelada_*`, `cte`, `status`, `fechada_*`) não aparecem para o motorista.
- Só é possível criar viagem com `ClienteCidade` ativo.

## 10. Testes prioritários
Concentre testes onde um erro custa dinheiro:
- snapshot: alterar `ClienteCidade.preco_tonelada` não muda viagens existentes;
- fechar viagem: bloqueia se faltar campo obrigatório, inclusive o CTE quando o cliente faz CTE;
- permissões: o motorista nunca vê viagens de outro motorista nem valores financeiros;
- (fase 2) cálculo do salário, saldo devedor e bloqueio de edição após o fechamento mensal.

## 11. Decisões descartadas
- Caminhão como entidade separada (um motorista usa sempre o mesmo caminhão).
- CNPJ do cliente.
- Duplicar o cadastro do cliente por cidade (usa-se `ClienteCidade`).
- Comissão ou `tonelada_motorista` como constante (a comissão é constante; a tonelada do motorista **não** é: varia por cliente e cidade e fica em `Viagem`).
- Várias notas fiscais, clientes ou destinos por viagem.
- Tanque próprio de diesel.
- Modo offline, PWA e app nativo no MVP.
- Repository Pattern, DDD completo, microsserviços.

## 12. Segurança e operação
- Senhas com hash do Django; troca obrigatória no primeiro acesso.
- Motoristas nunca recebem `is_superuser`.
- (SUGESTÃO) HTTPS, backup diário do banco fora do servidor, e teste periódico de restauração.
- Auditoria de alterações em dinheiro com `django-simple-history`.

## 13. Pontos em aberto e sugestões a confirmar
Nenhum deles muda o modelo de dados. Confirme ou corrija antes de implementar:

1. **Interface do motorista no MVP (SUGESTÃO).** "Somente Django" foi interpretado como Django Admin para admin **e** motorista, com dois `AdminSite` separados (`is_staff = True` para ambos) e permissões que limitam o motorista às próprias viagens. Se o motorista preferir telas próprias simples desde o MVP, isso muda só a camada de interface.
2. **Escolha de cliente e cidade (SUGESTÃO).** No MVP, um único campo de seleção (com busca) lista as combinações ativas como "Cliente — Cidade". O fluxo "escolhe a cidade e depois o cliente" fica para as telas próprias.
3. **Valores calculados não são gravados (SUGESTÃO).** Só os preços por tonelada são snapshot. `valor_total`, `valor_motorista` e `km_rodado` são calculados.
4. **Tipo de `nota_fiscal` e `cte` (SUGESTÃO).** Texto (`CharField`), para preservar zeros à esquerda.
5. **Troca de `cliente_cidade` em viagem `aberta` (SUGESTÃO).** O sistema recopia `tonelada_cliente`, a menos que o admin já tenha editado esse valor.
6. **Aviso de preço (SUGESTÃO).** Avisar (sem bloquear) o admin quando `tonelada_motorista >= tonelada_cliente`, pois a viagem teria lucro zero ou negativo.
7. **Exclusão de viagem `aberta` pelo admin.** Está definido que o motorista dono pode excluir. Falta definir se o admin também pode.
8. **Fase 2, vínculo automático do abastecimento.** Falta definir o que fazer quando a viagem ainda não tem `data_chegada` (em andamento), quando o abastecimento ocorre fora de qualquer viagem e quando as datas da viagem são alteradas depois.
9. **Fase 2, edição de abastecimento e descontos.** Falta definir se o admin pode editar ou excluir abastecimentos feitos pelo motorista, e se o motorista pode corrigir os próprios.
10. **Fase 2, bloqueio do fechamento mensal.** Falta definir o tratamento exato de viagens `abertas` com `data_chegada` dentro do mês (bloquear ou só avisar).

## 14. Sugestão de prompt para iniciar o código
> Leia integralmente o documento anexo, que contém as decisões do projeto. Implemente **somente o MVP** (seção 2): apps `usuarios`, `cadastros` e `viagens` com os models, constraints, services e a configuração do Django Admin conforme as seções 3, 4, 6 e 9. Siga as regras de arquitetura da seção 3 (services, selectors, sem Repository, sem lógica em signals). Não implemente a fase 2. Não invente regras: para qualquer ponto não coberto ou listado na seção 13, pergunte antes. Comece pela estrutura do projeto, os models e as migrations, e me mostre antes de seguir para os services e o admin.
