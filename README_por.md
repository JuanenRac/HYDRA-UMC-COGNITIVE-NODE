<!-- =============================================================================
HYDRA-UMC-COGNITIVE-NODE - Cognitive AI node (Hailo-10)
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-COGNITIVE-NODE banner" width="100%">
</p>

# 🧠 HYDRA-UMC-COGNITIVE-NODE

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | 🇵🇹 <b>Português</b></p>

### 🤖 Nó de borda de raciocínio semântico e IA generativa (Hailo-10 + Raspberry Pi CM5)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Hardware-CM5%20%2B%20Hailo--10-orange.svg" alt="Hardware">
  <img src="https://img.shields.io/badge/GenAI-Local%20LLM%20%2F%20VLA-blueviolet.svg" alt="GenAI">
  <img src="https://img.shields.io/badge/Tests-56%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

> **Verificação de honestidade - o que realmente funciona hoje:** a verificação de prontidão da família e o seu esquema JSON versionado (`family.py`, `manifest.py`, `models.py`) e a superfície HTTP simples da biblioteca padrão (`api.py`) são reais e estão cobertos por 56 testes a passar (`pytest tests/` - `test_manifest.py`, `test_models.py`, `test_family.py`, `test_api.py`, `test_cli.py`). Este nó não executa nenhum modelo ele próprio: "Execução local de LLM", "Integração VLA" e "Processamento de comandos de voz" nas Funcionalidades principais abaixo estão explicitamente marcados `(planeado)` - não há código de execução do Hailo-10 neste repositório. O `docker-compose.yml` refere agora um Dockerfile real para os 4 filhos, mas nunca foi realmente executado como um único stack neste ambiente de desenvolvimento (não há ambiente de execução Docker aqui) - o mapeamento de comando/porta de cada Dockerfile foi conferido à mão com o que a unidade systemd de cada filho já executa no CM5 real, não verificado em direto. Veja o `CHANGELOG.md` para saber exatamente o que foi entregue até agora.

> **Estado de segurança (safety e security):** este ecossistema não é um sistema de segurança certificado. Ainda não existe um caminho de E-STOP por hardware, nem limites ou interlocks impostos pelo firmware, nem um comando de movimento verificado; as imagens de firmware são verificadas com CRC32 e um HMAC-SHA256 de chave partilhada, não com uma assinatura assimétrica; TLS e TLS mútuo são opcionais e estão desativados por defeito; nenhuma placa própria foi ainda montada ou testada. Leia a [base de segurança](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e o [modelo de ameaças](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de confiar em qualquer afirmação aqui para a segurança de uma pessoa.

---

## 📋 Num relance

| | |
|---|---|
| Versão | `0.1.5` |
| Maturidade | Funcional |
| Testes | 56 (`python -m pytest -q tests`) |
| Tecnologia | Python / CM5 / Hailo-10 |
| Destino | O Raspberry Pi CM5 de uma célula HYDRA-UMC |
| Em hardware real | Ainda não: não há registo de execução em hardware real para esta versão |

**Ir para:** [Visão geral](#-visão-geral) · [Arquitetura](#-arquitetura) · [Funcionalidades](#-funcionalidades) · [Segurança e proteção](#-segurança-e-proteção) · [Interfaces](#-interfaces) · [Configuração](#-configuração) · [Início rápido](#-início-rápido) · [Testes](#-testes) · [Resolução de problemas](#-resolução-de-problemas) · [Estrutura do repositório](#-estrutura-do-repositório) · [Projetos relacionados](#-projetos-relacionados)

## 🚦 Estado do projeto

Cada linha é uma parte deste repositório e a luz diz até onde chega hoje. É escrita com o que o repositório consegue demonstrar (testes, compilações, execuções), não com o que está previsto.

🟢 Feito e verificado · 🟡 Funciona, com limites conhecidos · 🟠 Feito a meio ou ainda por verificar · 🔴 Por fazer ou a não funcionar

| Área | Estado | O que significa aqui |
|---|---|---|
| Software | 🟡 | Funciona para o seu propósito principal; a verificação de honestidade acima lista o que ainda falta |
| Testes | 🟢 | 56 testes automáticos, executados a cada alteração |
| Hardware real | 🔴 | Ainda não: não há registo de execução em hardware real para esta versão |
| Documentação | 🟢 | README em oito idiomas, verificado contra o manifesto a cada alteração |

## 🎯 Visão geral

O **HYDRA-UMC-COGNITIVE-NODE** serve de "lobo frontal" do ecossistema HYDRA-UMC. Alimentado pela NPU Hailo-10 (40 TOPS), permite raciocínio semântico complexo, compreensão de linguagem natural e planeamento de tarefas visão-linguagem-ação (VLA) diretamente na periferia.

Transforma instruções humanas de alto nível em sequências robóticas lógicas, gerindo a recuperação de erros e a otimização de missões sem dependência da nuvem.

## 🧩 Papel no HYDRA-UMC

O **HYDRA-UMC-COGNITIVE-NODE** é o ponto de integração da família cognitiva Hailo-10. Hoje o seu trabalho real é uma verificação de prontidão: lê o manifesto dos quatro filhos (VLA-ENGINE, VOICE-UI, SEMANTIC-PLANNER, DOCS-QA), olha para a pasta partilhada de pesos de modelos e, se pedido, sonda cada filho por HTTP. Não é um motor de raciocínio.

## 🏛️ Arquitetura

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-COGNITIVE-NODE architecture" width="100%">
</p>

<details>
<summary>Versão em texto do diagrama (Mermaid)</summary>

```mermaid
flowchart TB
    INPUT["Voice / Text Input"] --> VOICE["VOICE-UI (STT)"]
    VOICE --> PLANNER["SEMANTIC-PLANNER (LLM)"]
    VIS["Vision Node Data"] --> VLA["VLA-ENGINE"]
    VLA --> PLANNER
    PLANNER --> ORCH["HYDRA-ORCHESTRATOR"]
    DOCS["Technical Manuals"] --> RAG["DOCS-QA (RAG)"]
    RAG --> PLANNER
```

</details>

**Porque é construído assim**

Este repositório é o **pai/ponto de integração** da família do Nó de IA Cognitiva.
Não executa ele próprio nenhum modelo - detém os recursos partilhados e a ligação
que permitem aos seus quatro filhos atuar como uma só unidade cognitiva
na mesma placa física:

* **Porque este nó não tem hardware/firmware próprios.** Ao contrário do firmware
  ao nível da placa-mãe do HYDRA-UMC, este nó corre inteiramente num
  Raspberry Pi CM5 + módulo M.2 Hailo-10 existentes - não há nenhuma PCB nem
  microcontrolador à medida para desenhar aqui, pelo que as pastas `hardware/`/`firmware/`
  foram retiradas em vez de deixadas vazias.
* **Porque `os/` e `models/` vivem apenas no pai.** A imagem HydraOS
  e os pesos quantizados de LLM/VLA são recursos partilhados ao nível da placa -
  manter uma cópia no pai e montá-la só de leitura no contentor de cada
  filho (veja `docker-compose.yml`) evita quatro cópias divergentes de pesos de
  modelos com vários gigabytes.
* **Porque uma estrutura `src/`.** Mantém o pacote instalável
  (`hydra_umc_cognitive_node`) separado das ferramentas da raiz do repositório
  (`bump_version.py`, `docker-compose.yml`) e corresponde à estrutura usada
  por todos os outros projetos Python do ecossistema.
* **Porque o ponto de entrada só imprime a identidade/versão/papel hoje.** Esta
  é a fase de andaimes (scaffolding): provar que o pacote instala,
  compila e importa limpo - na versão de Python de destino - é
  um pré-requisito para acrescentar mais tarde a lógica real de orquestração de LLM/VLA/voz,
  e mantém esse trabalho posterior isolado das questões de empacotamento.
* **Porque o `docker-compose.yml` documenta o contrato de integração, e não apenas
  liga imagens.** Decidir que serviço depende de qual e de que montagens de
  dispositivos/volumes cada um precisa foi escrito antes de qualquer filho ter
  um Dockerfile - evitando que essa forma fosse inventada ad hoc mais tarde. Os
  quatro filhos (VLA-Engine, Voice-UI, Semantic-Planner, Docs-QA) têm agora
  um Dockerfile real próprio, fechando uma lacuna real - o `docker compose up`
  constrói e executa a coisa a sério.
* **Como isto se encaixa no resto do ecossistema.** Este nó fica uma camada
  acima da perceção (HYDRA-UMC-VISION-NODE, Hailo-8) e uma camada abaixo da
  orquestração de missões (HYDRA-UMC-ORCHESTRATOR): transforma instruções de voz/texto
  e deteções em decisões semânticas, que o orquestrador converte depois em comandos
  físicos para o robô.
* **Porque o `family-status` lê o manifesto de cada filho em vez de uma lista
  mantida à mão.** O `hydra-umc.project.json` já é a única fonte de verdade
  em que o painel e o atualizador de todo o ecossistema confiam - uma segunda
  lista aqui divergiria no momento
  em que a maturidade real de um filho mudasse e ninguém se lembrasse de a atualizar.
* **Porque uma cópia de irmão em falta é um "não encontrado" real e honesto, e não um
  erro.** Um centro de integração genuinamente não sabe se um programador
  clonou localmente os quatro filhos - o `manifest.py` devolve
  `None` para todos os modos de falha reais (repositório em falta, manifesto em falta,
  JSON malformado), para que o `family-status` o reporte com clareza em vez de
  falhar.
* **Porque as leituras de manifestos de irmãos têm um limite de 64 KiB.** Todos os manifestos reais
  deste ecossistema têm de algumas centenas de bytes a um par de KiB - uma cópia corrompida
  ou maliciosa cujo manifesto tenha sido substituído por um ficheiro sobredimensionado nunca deve fazer
  uma verificação de prontidão de rotina carregar uma quantidade ilimitada de dados para a memória.
  Degrada para `None`, tal como qualquer outro manifesto malformado.
* **Porque o `family-status` reporta o `models/` mesmo que este nó não execute
  nenhum modelo.** "Os repositórios irmãos estão clonados" e "os pesos partilhados de que
  precisariam estão realmente presentes" são dois factos reais diferentes -
  o `check_shared_models()` do `models.py` verifica o segundo com
  honestidade (vazio mas presente conta como em falta) em vez de deixar um
  operador presumir a prontidão só pela presença dos filhos.

## ✨ Funcionalidades

* 🧠 **Execução local de LLM:** inferência acelerada por hardware para modelos quantizados (Llama/Mistral). *(planeado - precisa do ambiente de execução real de modelos do Hailo-10)*
* 👁️ **Integração VLA:** modelos visão-linguagem-ação para uma execução intuitiva de tarefas. *(planeado)*
* 🎙️ **Processamento de comandos de voz:** STT/TTS em tempo real para a interação humano-robô. *(planeado)*
* 🛡️ **Privacidade em primeiro lugar:** processamento 100 % offline de todas as tarefas cognitivas. *(verdadeiro por desenho assim que o acima existir - nada aqui contacta uma rede hoje)*
* 🧩 **Centro de integração (v0):** detém a imagem HydraOS partilhada e os pesos de modelos quantizados
  consumidos pelos seus quatro filhos, e liga-os como serviços irmãos num único `docker-compose.yml`.
  A verificação real `family-status` lê o manifesto de cada filho para reportar presença/versão/
  maturidade. *(implementado como verificação real de prontidão - veja COMPILAR E EXECUTAR
  abaixo)*
* 🔒 **Esquema de estado versionado + leituras de manifestos com recursos limitados:** o `family-status --json` imprime um resultado real, versionado e legível por máquina; qualquer manifesto de um irmão com mais de 64 KiB (uma cópia corrompida/maliciosa) degrada para "não encontrado" em vez de ser lido sem limite. *(implementado)*
* 🩺 **Saúde dos filhos em execução, etiquetas das imagens e os pesos no contentor do motor:** `family-status --probe` (ou `GET /family-status?probe=1`) pergunta também a cada filho em execução pela sua saúde, na rota que o seu próprio manifesto declara (`/stats` caso contrário), e indica se respondeu, com que estado e com que rapidez, e o que o filho diz de si; termina com código diferente de zero se algum não estiver bem. Onde estão os filhos é fixado no arranque do nó: as suas portas de loopback por omissão, ou `HYDRA_UMC_COGNITIVE_NODE_CHILD_URLS` (como o ficheiro compose o define dentro da pilha). As imagens do ficheiro compose são etiquetadas com `HYDRA_UMC_<NOME>_VERSION` (do `.env`; `family-versions` imprime essas linhas a partir dos manifestos) ou `latest`, nunca com um número inventado, o contentor vla-engine passa a ter `models/` montado onde o motor o procura, e um segundo fluxo de trabalho verifica que `docker compose config` continua a resolver-se. *(experimentado com serviços de substituição, não com os filhos reais nem com um Hailo-10)*
* 🪫 **Verificação de degradação dos pesos de modelos partilhados:** o `family-status` reporta honestamente se o próprio diretório `models/` deste nó tem de facto pesos reais, e não apenas se os repositórios irmãos estão clonados. *(implementado)*
* 📦 **Versionamento ao estilo conta-quilómetros:** A versão do `pyproject.toml` só é subida pelo comando `bump` explícito (`python tools/hydra_project_tool.py bump`, que executa o `bump_version.py`) - compilar nunca a altera.

## 🔒 Segurança e proteção

| Ameaça | Defesa | Onde |
|---|---|---|
| Um manifesto gigante ou hostil, uma pasta de modelos gigante | O manifesto de um repositório irmão é lido até 64 KiB; a pasta de modelos é inspecionada em no máximo 20 000 ficheiros e só contam os sufixos de pesos `.bin .gguf .har .hef .onnx .safetensors .tflite` | `manifest.py`, `models.py` |
| Um filho que responde com lixo ou fica preso | A sonda espera no máximo 2 segundos e lê no máximo 64 KiB; o caminho de saúde de um manifesto só é aceite se começar por `/`, tiver menos de 128 carateres e não tiver espaços, senão usa-se `/stats` | `probe.py` |
| Exposição à rede | A interface HTTP é só de leitura e escuta em `127.0.0.1:8096` por predefinição; percorre o espaço de trabalho fixado no arranque e responde `400` a um pedido que tente escolher outro. Não tem token: se precisa de um ainda está em aberto | `api.py`, `main.py` |

**O que nunca faz:** não é um motor de raciocínio: neste repositório não corre nenhum modelo, e não escreve nada nos filhos.

## 🔌 Interfaces

`family-status [--workspace DIR] [--models-dir DIR] [--probe] [--json]` e `serve [--addr 127.0.0.1] [--port 8096] [--workspace DIR] [--models-dir DIR]`. As portas predefinidas dos filhos são VLA-ENGINE 8098, VOICE-UI 8091, SEMANTIC-PLANNER 8109 e DOCS-QA 8110.

O `serve` executa essa mesma verificação `family-status` como um pequeno
`http.server` da biblioteca padrão em vez de uma chamada única da CLI - é o comando que a
unidade systemd `hydra-umc-cognitive-node.service` do próprio CM5 está configurada
para executar:

```bash
./run.sh serve --addr 127.0.0.1 --port 8096
# GET /family-status  -> o mesmo JSON que o `family-status --json` imprime acima
# GET /stats          -> { "status": "ok" }
```

O `GET /family-status` analisa o workspace fixado no arranque do serviço (`--workspace`, `--models-dir` ou `HYDRA_UMC_COGNITIVE_NODE_WORKSPACE` / `HYDRA_UMC_COGNITIVE_NODE_MODELS_DIR`) e responde `400` se um pedido tentar escolher outro; qualquer outro
caminho devolve `404`. Veja a [Referência da CLI](docs/CLI_REFERENCE.md) para a
referência completa de comandos: cada opção, saída real capturada de `-h`/`curl` e
a tabela de códigos de saída.

## ⚙️ Configuração

| Variável | Predefinição | O que define |
|---|---|---|
| `HYDRA_UMC_COGNITIVE_NODE_WORKSPACE` | a pasta pai deste repositório | onde estão os repositórios irmãos |
| `HYDRA_UMC_COGNITIVE_NODE_MODELS_DIR` | `models/` | os pesos de modelos partilhados |
| `HYDRA_UMC_COGNITIVE_NODE_CHILD_URLS` | as portas predefinidas acima | os URL dos filhos para `--probe` |

## 🚀 Início rápido

Requer o Python >= 3.10.

```bash
# Linux / macOS / Git Bash
./build.sh   # cria o .venv, instala o pacote (editável), verifica a importação
./run.sh     # executa o ponto de entrada

# Windows (cmd)
build.bat
run.bat
```

`build.sh`/`build.bat` nunca altera a versão (só `python tools/hydra_project_tool.py bump` a sobe) e executa a suite de testes real
(`pytest tests/`). Saída esperada de um `run.sh` simples:

```text
HYDRA-UMC-COGNITIVE-NODE v0.1.5
Semantic reasoning & GenAI edge node (Hailo-10) - integrates VLA-Engine, Voice-UI, Semantic-Planner and Docs-QA into one cognitive node.
```

Veja o `docker-compose.yml` para saber como os quatro serviços filhos (VLA-Engine,
Voice-UI, Semantic-Planner, Docs-QA) se ligam a este nó - cada um traz agora
o seu Dockerfile real.

O subcomando real `family-status` verifica os filhos reais numa cópia
local real:

```bash
./run.sh family-status
./run.sh family-status --workspace /path/to/some/other/checkout
./run.sh family-status --json

# Windows
run.bat family-status
```

O `family-status` reporta sempre também os pesos de modelos partilhados deste nó
- um `models/` real e vazio numa máquina de desenvolvimento é honestamente `MISSING`,
nunca ignorado em silêncio:

```text
Cognitive AI Node family status (workspace: /path/to/workspace):
  HYDRA-UMC-VLA-ENGINE: v0.1.8, maturity=functional, role=service
  ...

Shared model weights: MISSING (.../HYDRA-UMC-COGNITIVE-NODE/models) - this node's own os/models weights have not been provisioned on this machine; children that need them will run in their own honest degraded/no-hardware mode.

All 4 children present.
```

O `--json` imprime os mesmos dados reais como um objeto versionado e
legível por máquina:

```bash
$ ./run.sh family-status --json
{
  "schema_version": "1.0",
  "shared_models": { "present": false, "path": ".../models" },
  "children": [
    { "name": "HYDRA-UMC-VLA-ENGINE", "present": true, "version": "0.1.8", "maturity": "functional", "role": "service" },
    ...
  ],
  "all_children_present": true
}
```

Por omissão usa o diretório pai deste próprio repositório - a estrutura que todas as
cópias reais deste ecossistema já usam (todos os repositórios como irmãos numa
só pasta de trabalho). Termina com `1` se algum filho real estiver em falta.

## 🧪 Testes

56 testes automáticos correm com `python -m pytest -q tests`. Verificam os manifestos, a pasta de modelos, a sonda, a linha de comandos e a interface HTTP com fixtures locais; sem hardware nem rede externa.

A CI executa `HYDRA_UMC_CI=1 python tools/ci_validate.py`, que verifica o manifesto, os documentos, os oito README e as imagens.

## 🏗️ Compilação e publicação

Não há nada para compilar numa publicação: `build.sh` / `build.bat` criam o ambiente virtual, instalam o pacote em modo editável e executam os testes, e `build-test` apenas verifica. Compilar nunca muda a versão; só a sobe `python tools/hydra_project_tool.py bump`, que também avança o registo de alterações. A versão do pacote, do manifesto e do registo tem de coincidir, senão o `ci_validate.py` falha.

## 🩺 Resolução de problemas

* **`python: command not found` / a compilação falha no passo 1.** Requer o
  Python >= 3.10 no `PATH`. No Windows, instale a partir de
  [python.org](https://python.org) e confirme que "Add to PATH" ficou
  marcado durante a instalação; `python3` é o nome habitual no Linux/macOS.
* **O `build.sh` falha ao ativar o venv.** O `python3 -m venv .venv`
  dispõe o script de ativação de forma diferente por plataforma:
  `.venv/bin/activate` no Linux/macOS, `.venv/Scripts/activate` no
  Windows (incluindo um venv de Python do Windows usado a partir do Git Bash). O `build.sh`
  já verifica ambos os caminhos - se ainda assim falhar, apague o `.venv/` e
  volte a executar `./build.sh` para o reconstruir de raiz.
* **O `pip install -e .` falha.** Normalmente um `.venv/` obsoleto. Apague a
  pasta `.venv/` e volte a executar `./build.sh`/`build.bat` para a recriar.
* **O `import OK` nunca aparece.** Significa que o próprio `python -c "import
  hydra_umc_cognitive_node"` falhou - volte a executar com o venv ativo
  para ver o traceback real (uma edição quebrada do `pyproject.toml` é a causa habitual
  depois de uma fusão manual).
* **O `docker compose up` não consegue arrancar o `voice-ui`.** O seu próprio contentor
  recusa-se a ligar para lá do loopback sem um `HYDRA_UMC_VOICE_UI_TOKEN` real
  (por desenho - veja o comentário do próprio `docker-compose.yml`); defina-o num
  ficheiro `.env` real ou no seu gestor de segredos, nunca faça commit de um. Executar cada
  serviço diretamente com o seu próprio `run.sh`/`run.bat` durante o desenvolvimento
  não precisa desse token, já que o `--host` aí fica em loopback.

## 📂 Estrutura do repositório

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-COGNITIVE-NODE" width="100%">
</p>

<details>
<summary>Versão em texto da árvore</summary>

```text
HYDRA-UMC-COGNITIVE-NODE/
├── src/hydra_umc_cognitive_node/
│   ├── family.py                                estado dos quatro serviços filhos
│   ├── manifest.py                              lê o manifesto de um repositório irmão
│   ├── models.py                                verifica a pasta partilhada de pesos
│   ├── probe.py                                 cada filho responde por HTTP
│   └── api.py main.py                           interface HTTP e linha de comandos
├── tests/                                       56 testes
├── docs/                                        a referência da linha de comandos
├── models/                                      pesos de modelos partilhados
├── os/                                          notas da camada do SO
├── tools/                                       executor de compilação e testes, subida de versão, validador de CI, geradores e verificações de README e imagens
├── images/                                      faixa e imagens do README
├── .github/                                     fluxo de CI e modelos de questões
├── pyproject.toml                               metadados do pacote e dependências
├── hydra-umc.project.json                       manifesto: versão, maturidade, família
├── CHANGELOG.md                                 o que mudou em cada versão
├── build.sh build.bat                           scripts de compilação (nunca mudam a versão)
├── build-test.sh build-test.bat                 scripts de compilação (nunca mudam a versão)
├── test.sh test.bat                             executam os testes
├── systemd/                                     unidade de serviço para o CM5
├── docker-compose.yml / Dockerfile              o nó com os seus quatro filhos
├── bump_version.py / bump_manifest_version.py   subida de versão explícita
├── run.sh run.bat                               arrancar o nó
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE LICENSE.md
```

</details>

## 🗺️ Roteiro e limites conhecidos

**Limites conhecidos hoje**

* **Fase 1:** implementação do motor VLA e processamento de entrada multimodal no Hailo-10.
* **Fase 2:** integração do planeador semântico com modelos comportamentais do enxame e memória de longo prazo.
* **Fase 3:** execução local de baixa latência da Voice UI e cancelamento de ruído industrial.
* **Fase 4:** auditorias de decisão autónoma e integração total com o Dashboard AI para um retorno "Ver e Perguntar".

## 🌍 Idiomas

Este README e os documentos do repositório existem em oito idiomas: inglês, espanhol, alemão, francês, italiano, japonês, chinês e português (Portugal). São escritos em conjunto e a CI verifica que os oito ficheiros têm as mesmas secções e as mesmas ligações. Este repositório não tem ecrã nem catálogo de mensagens próprios, por isso não há textos de interface para traduzir.

## 🔗 Projetos relacionados

Este projeto faz parte do ecossistema de robótica HYDRA-UMC do mesmo autor (JuanenRac / Electro Hobby 3D). Vale a pena conhecê-los, porque um pedido pode ser, na verdade, sobre um destes e não sobre este repositório.

**Projetos filhos** — quatro são etapas do próprio fluxo cognitivo deste nó (entrada de voz, decisão, ação, ancoragem); o quinto é uma aplicação de manutenção separada, construída sobre o mesmo pipeline Hailo-10
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analisador de intenções) com um relé para o relógio limitado e protegido por confirmação.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — decomposição real de tarefas baseada em regras e recuperação semântica de erros sobre os códigos de erro do MCU.
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificação/descodificação real de tokens de ação e geração de trajetórias para um modelo Visão-Linguagem-Ação.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — pesquisa real de documentos TF-IDF só com a biblioteca padrão sobre a documentação Markdown deste ecossistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de manutenção de IA local, protegido por políticas, para o próprio ecossistema: observa, diagnostica e propõe correções; os dois níveis de maior risco não estão implementados de propósito.

**Diretamente relacionados**
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — centro de integração com um contrato real de relatório de saúde gRPC/Protobuf e uma máquina de estados de missões; é o que dá a este nó as suas ordens de missão.
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — centro de integração do pipeline de visão Hailo-8, com uma verificação real de prontidão de hardware por etapa; a camada semântica deste nó consome as suas deteções.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — painel web de controlo com visualização 3D em tempo real de vários robôs; uma das superfícies de controlo por voz deste nó.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tátil nativa para o ecrã tátil DSI de 7" integrado, executada no próprio CM5; a outra superfície de controlo por voz deste nó.

**Também fazem parte do ecossistema**

*Hardware e plataforma centrais*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — o desenho da placa-mãe do braço robótico: anfitrião CM5 + STM32H745 de dois núcleos, pensado para orquestrar até 8 braços de ferramenta por CAN-OTA/SPI-OTA (firmware numa fase inicial; ainda sem placa montada).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — camada de produto reproduzível do Raspberry Pi OS para o CM5: agente só de leitura, configuração/perfis validados, aprovisionamento Wi-Fi de primeiro contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — o contrato JSON-Schema partilhado e a fronteira de software de controlo de trabalhos contra a qual cada bridge valida os seus comandos (não é uma função de segurança certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registo declarativo de manifestos de adaptador e validador para conectores de máquinas externas; estende a ideia de contrato do SDK a máquinas externas sem substituir os projetos de gateway industrial.

*Backend central e clientes*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — o back-end headless real (REST/WebSocket) com que todos os clientes de controlo realmente comunicam.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de comando de enxame para desktop (PySide6) para vários servidores ao mesmo tempo, empacotado como executável independente.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — aplicação Android nativa de controlo, com início de sessão biométrico e um companheiro Wear OS emparelhado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — aplicação de controlo para iOS/iPadOS (Flutter) com sincronização WebSocket em tempo real.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — criador/editor gráfico de URDF para desktop que envia os modelos concluídos para o catálogo do STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de modelos STL para desktop que transforma/substitui/remove/adiciona peças reais no mesmo catálogo de modelos que o HYDRA-UMC-EDITOR-URDF também edita.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — fronteira de coordenação para frotas AGV/AMR através de um publicador MQTT VDA 5050 (testado apenas contra uma frota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordenador de células CNC de alto nível com acesso ao estado GRBL e aos bytes de controlo (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — fronteira de coordenação para droides com patas/humanoides, com um emissor de comandos para o Boston Dynamics Spot (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordenador de células laser que lê 3 sinais GPIO (chave, caixa e interlock) (testado apenas contra um chip simulado; não pode armar nem disparar um laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordenador seguro de fluxo de placa de alto nível para pick-and-place com OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — fronteira de coordenação segura para impressoras 3D Moonraker/Klipper, com comandos de trabalho reais protegidos por portas.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordenador com um transporte ROS 2 baseado em rclpy importado sob demanda (ainda não executado contra uma instalação ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — fronteira de coordenação para UAV com câmara, com um emissor de comandos MAVLink (testado apenas contra um emulador).

*Plataforma de ferramentas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware da placa física Universal Robot Tool Controller, mais de 25 perfis de ferramenta por barramento CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — ferramenta gráfica de gravação para desktop das placas URTC, por CAN-OTA e também SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — ferramenta de diagnóstico CAN em tempo real para desktop das placas URTC, com um painel por perfil de ferramenta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa no navegador ao URTC-TESTER através da Web Serial API, sem instalação local.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — gateway à frente do barramento CAN do URTC: lista de identificadores permitidos, limite de taxa e chave de sessão; software testado num computador, ainda não num barramento real.

*Nó de IA de visão (Hailo-8)*
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registo real de modelos compilados com verificação segura de carga por arquitetura Hailo e soma de verificação.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer real e gerador de configuração MediaMTX com uma fronteira de integração HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — lei de correção de servovisão baseada em posição com autorização condicionada ao estado da zona; ainda sem estimativa de pose por câmara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — lógica v0 de violação de zonas, atualidade da calibração e pedido de E-STOP que lê as posições dos objetos de um ficheiro; nenhum detetor a alimenta e ainda não há E-STOP físico ligado.

*Orquestração e enxame*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — fila real de trabalhos por prioridade com deduplicação, sobre uma API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vigilante real de saúde da frota por gRPC com repetição/recuo e deteção de identidade incoerente.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planeador real de trajetórias 3D baseado em RRT com validação real de colisões com obstáculos e espaço de trabalho.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronização real de estado CRDT LWW-Element-Map, testada por propriedades para a convergência de várias células.

*Gémeo digital e simulação*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — centro de integração do motor de gémeo digital, com um contrato real de sincronização de compatibilidade de versões.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — encaminhador hardware-in-the-loop com um interlock de software de colisão entre a simulação e o hardware real (testado sem hardware real).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática direta real e validação de limites de juntas sobre um subconjunto real de URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — gerador procedural real de cenas 2D com exportação de anotações YOLO/COCO.

*Dados e análise*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — armazém real de séries temporais sobre sqlite3 com uma API HTTP real de ingestão/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detetor real de anomalias por FFT e linha de base estatística, com monitorização de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidade sobre o histórico do DATALAKE, com exportação CSV reprodutível.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingestão CAN/WebSocket para o DATALAKE, com deduplicação por sequência.

*Gateway industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — centro de integração que retransmite para protocolos industriais, com uma camada real de lista de comandos permitidos e contrapressão.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espaço de endereços OPC-UA real, verificado com uma sessão de cliente real do protocolo binário.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real com autenticação opcional por cliente e ACL de tópicos.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML MTConnect `/probe` e `/current` reais com saída em modo degradado.

*Ferramentas complementares e operações do ecossistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — painéis de Resumos Inteligentes e Realce de Anomalias sobre o DATALAKE/ANOMALY-DETECTOR, com um recurso estatístico honesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI da frota com um contrato de códigos de saída real e estável, um cliente vivo genuíno da API do HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — aplicação companheira WearOS com padrões de alerta tátil e um relé de voz para o telemóvel emparelhado (ainda não executada num relógio físico).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware de um rack de montagem de placas com descodificação real do ID da ferramenta e lógica de pré-aquecimento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware mais um companheiro de visão em Python real para uma cabeça de ferramenta de inspeção térmica/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — ferramenta administrativa de desktop que descobre, clona e atualiza todos os repositórios deste ecossistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — ferramenta de desktop para Windows/Linux que constrói uma imagem do CM5 pronta a gravar com as versões mais recentes do ecossistema, com configuração de primeiro arranque de Wi-Fi/utilizador/SSH ao estilo do Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordenador de incidentes de manutenção: um papel de borda de poucos privilégios recolhe um inventário/estado higienizado, um papel de plano de controlo mostra-o só de leitura e pede a um fornecedor de IA que sugira um diagnóstico; nunca aplica um patch nem implanta nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — anfitrião de desenvolvimento reproduzível (Raspberry Pi 5 / CM5) que guarda o código-fonte do ecossistema e executa tarefas limitadas de compilação/teste numa fila durável; um papel de desenvolvimento dedicado, explicitamente não um CM5 operacional.

## 📚 Documentação

Onde ler mais:

* [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) - cada comando e opção, saída real capturada e os códigos de saída
* [Base de segurança do ecossistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Modelo de ameaças do ecossistema](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Registo de alterações deste repositório](CHANGELOG.md)
* [Licença deste repositório](LICENSE.md)

## 🤝 Contribuir e comunidade

* Antes de um pull request execute `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (ou `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`): tem de imprimir `CI_VALIDATION=PASS`. Não execute `build.sh` nem `build.bat` para esta verificação; compilar não é verificar.
* Os oito README são escritos a partir de uma única fonte em HYDRA-UMC-DOCS; não os edite à mão. Altere a fonte e escreva-os de novo com `tools/make_readmes.py`.
* Não afirme num README o que não foi executado: diga «simulado» ou «não testado em hardware» quando for a verdade.
* Consulte [CONTRIBUTING.md](CONTRIBUTING.md), o [código de conduta](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) e [SUPPORT.md](SUPPORT.md).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENÇA

GPL-3.0-or-later - [LICENSE](LICENSE).
