# Chip Recharge Automation

Automação em Python que analisa a planilha de controle de chips do GrupoFly e identifica quais chips físicos precisam de recarga — substituindo uma checagem manual que era feita linha por linha na planilha.

## O problema

A empresa mantém uma planilha no Google Sheets ("Chip recarga") com todos os chips e números usados internamente (WhatsApp, alertas automatizados, SDRs, etc). Parte desses chips é **física** (SIM cards de verdade, que ficam sem sinal se não forem recarregados) e parte é **virtual/fixa** (números "Br DID", que têm recarga automática via outra ferramenta).

Até aqui, alguém precisava abrir a planilha, olhar chip por chip, checar a data da última recarga e decidir manualmente quais estavam vencidos — um processo repetitivo e sujeito a esquecimento (um chip físico sem crédito perde o número).

## O que a automação faz

```
Google Sheets → leitura (pandas) → validação → análise da regra de recarga → relatório
```

1. Conecta na planilha via API do Google Sheets (leitura apenas).
2. Valida a estrutura (a planilha tem as colunas esperadas?) e descarta linhas vazias/quebradas.
3. Filtra só os chips físicos com status ativo (só esses precisam de recarga manual).
4. Para cada um, calcula há quantos dias foi a última recarga e aplica a regra de negócio.
5. Gera um relatório de texto com o total de chips que precisam de recarga e o valor necessário.

## Regra de negócio

```
Para cada chip:
    se Tipo != "Físico": ignora (BR DID tem recarga automática, fora do escopo)
    se Status != "Ativo": ignora (Standby/Banido/cancelado não contam)

    valor = "Última recarga"

    se valor for "RECARREGAR" ou "RECARGA RECUSADA":
        -> precisa recarga (marcado como URGENTE)
    senão se valor estiver vazio, "-" ou não for uma data reconhecível:
        -> pendente de análise (não entra no valor total, mas aparece no relatório)
    senão:
        dias = hoje - data da última recarga
        se dias >= RECARGA_INTERVALO_DIAS:
            -> precisa recarga
```

Os dois parâmetros da regra (`RECARGA_INTERVALO_DIAS` e `VALOR_MINIMO_RECARGA`) **não ficam fixos no código** — vêm do `.env`, então dá pra ajustar o prazo ou o valor sem mexer em nada.

A coluna "Última recarga" da planilha mistura datas de verdade (em mais de um formato) com anotações manuais como "Assinatura", "RECARREGAR" e "RECARGA RECUSADA" — a automação trata cada caso, e nunca "chuta" um ano quando a data vem incompleta (isso viraria um alerta falso ou, pior, esconderia um chip que precisa de recarga).

## Arquitetura

```
chip-recharge-automation/
│
├── src/
│   ├── main.py                        # orquestra o fluxo inteiro
│   │
│   ├── config/
│   │   └── settings.py                # le o .env, centraliza credenciais e regra de negocio
│   │
│   ├── services/
│   │   ├── spreadsheet_service.py     # autentica e busca os dados no Google Sheets
│   │   ├── recharge_service.py        # aplica a regra de recarga (dias, urgencia, valor total)
│   │   └── discord_service.py         # notifica alguem no discord via PyAutoGUI (opcional)
│   │
│   ├── validators/
│   │   └── data_validator.py          # valida estrutura da planilha e descarta linhas vazias
│   │
│   ├── reports/
│   │   └── report_generator.py        # monta e salva o relatorio final (.txt)
│   │
│   └── utils/
│       ├── logger.py                  # log em arquivo + console
│       └── exceptions.py              # erros proprios do projeto
│
├── credentials/          # service_account.json (gitignored, nunca vai pro repo)
├── data/                 # dado de exemplo anonimizado
├── logs/                 # log de cada execucao (gitignored)
├── relatorios/           # relatorio de cada execucao (gitignored, tem dado real)
├── tests/
├── .env.example          # modelo sem informação real
└── requirements.txt
```

Cada camada tem uma responsabilidade só: `spreadsheet_service` não sabe nada sobre a regra de recarga, `recharge_service` não sabe nada sobre Google Sheets, `report_generator` só formata o que já foi calculado. Isso deixa fácil trocar qualquer peça (por exemplo, um dia ler de outra fonte além do Sheets) sem afetar o resto.

## Tecnologias

- **Python 3**
- **Pandas** — leitura e manipulação dos dados
- **gspread + google-auth** — integração com Google Sheets via Service Account (autenticação server-to-server, sem login interativo — ideal pra automação que roda sozinha)
- **python-dotenv** — configuração via variáveis de ambiente
- **`xdotool`/`wmctrl` (Linux) ou `pyautogui`/`pygetwindow` (Windows)** — só pra notificação opcional no Discord (ver seção própria abaixo); todo o resto do projeto usa API, não automação de interface
- **logging** (biblioteca padrão) — log estruturado em arquivo

## Segurança e privacidade

- A conta de serviço (Service Account) tem acesso de **somente leitura** e só à planilha específica — nada de acesso amplo ao Google Drive.
- A chave de acesso (`credentials/service_account.json`) nunca é commitada — está no `.gitignore` e tem permissão de arquivo restrita (só o dono do computador consegue ler).
- O `.env` (com o ID real da planilha) também é gitignorado; o `.env.example` no repositório só tem valores fictícios.
- Os relatórios e logs gerados (que contêm identificação real dos chips) ficam em pastas gitignoradas — nunca sobem pro GitHub.

## Como executar

### Testando rápido, sem precisar de Google Cloud

O projeto já vem pronto pra rodar com um dado de exemplo anonimizado (`data/example_data.xlsx`), sem precisar configurar nada no Google Cloud:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # já vem com FONTE_DADOS=local
python -m src.main
```

Isso já mostra o relatório completo funcionando (leitura, validação, regra de recarga) com dado fictício. Pra gerar um `example_data.xlsx` novo (ou editar os casos de teste), roda `python data/gerar_exemplo.py`.

### Usando com a planilha real (Google Sheets)

1. No `.env`, mude pra `FONTE_DADOS=sheets`
2. Crie uma Service Account no Google Cloud Console, ative a Google Sheets API, e gere uma chave (`IAM e admin > Contas de serviço > Chaves > Criar nova chave > JSON`)
3. Coloque o arquivo baixado em `credentials/service_account.json`
4. Compartilhe a planilha real com o e-mail da Service Account (papel: **Leitor**)
5. Preencha `SPREADSHEET_ID` e `SPREADSHEET_TAB_NAME` no `.env` com os dados da planilha real
6. `python -m src.main`

O relatório aparece no console e também é salvo em `relatorios/`. O log de cada execução fica em `logs/`.

## Notificação no Discord (opcional)

Depois de analisar a planilha inteira, a automação manda um resumo direto na DM de alguém no Discord — se não tiver nenhum chip pendente, manda "Não tem número pendente de recarga hoje."; se tiver, manda o número e a utilidade (`Uso`) de cada chip que precisa de recarga, com o valor total.

Diferente do resto do projeto (que usa API sempre que dá), essa parte usa **automação de interface** de propósito: a API de bot do Discord só consegue mandar DM pra quem estiver num servidor em comum com o bot, o que exigiria montar um servidor só pra isso. Como a ideia é só abrir o Discord (que a pessoa já usa) e mandar mensagem pro privado de alguém específico, a automação de interface resolve com bem menos setup.

### Decisões técnicas (e os problemas reais que elas resolvem)

Testando essa parte na prática apareceram alguns problemas que valem registrar, porque moldaram bastante a implementação final:

- **`xdotool` em vez de `pyautogui`** — o `pyautogui` (que por baixo usa `python-xlib`) não conseguia se autenticar no X11 no ambiente de teste, enquanto o `xdotool` (ferramenta nativa do sistema) funcionou sem problema. Como já precisávamos do `wmctrl` pra focar a janela, ficou mais simples ir de `xdotool` pra tudo e não adicionar mais uma dependência Python.
- **Discord precisa abrir com `--ozone-platform=x11`** — por padrão o Discord (Electron) roda com renderização nativa Wayland, e nesse modo a janela fica **invisível** pro `wmctrl`/`xdotool` (que só enxergam janelas X11/XWayland). A automação sempre abre o Discord com essa flag; se o Discord já estiver aberto sem ela (por exemplo, você abriu manualmente antes), é preciso fechar e deixar a automação abrir de novo.
- **Nunca digitar sem antes confirmar que abriu a conversa certa** — o Ctrl+K + Enter pareceu simples, mas digitando rápido demais a busca do Discord por vezes não filtrava a tempo e o Enter selecionava outro resultado. A automação agora **confere o título da janela** (ex: `@FrosT - Discord`) antes de digitar qualquer coisa; se não bater com o contato esperado, tenta de novo (até `DISCORD_MAX_TENTATIVAS_ABRIR_CONVERSA` vezes) e, se mesmo assim não conseguir confirmar, **desiste sem mandar nada** — mais vale falhar de forma visível do que mandar mensagem pro lugar errado.
- **Caractere acentuado às vezes sumia** (`"Físico"` virava `"Fsico"`, travessão `"—"` desaparecia) — digitar um caractere fora do teclado padrão faz o `xdotool` remapear uma tecla na hora, e isso ocasionalmente falhava. A automação agora tira acento e troca travessão por hífen antes de digitar qualquer coisa no Discord (o relatório `.txt` continua com acentuação normal).
- **Delay entre teclas configurável** (`DISCORD_DELAY_DIGITACAO_MS`, padrão 200ms) — digitar rápido demais também atrapalhava a busca do contato; um delay maior deixou bem mais estável.

Como funciona, resumindo: usa o atalho **Ctrl+K** do Discord ("Ir para...") pra buscar o nome do contato — evita depender de posição fixa na lista de contatos, que muda toda hora.

### Windows e Linux

A automação detecta o sistema operacional (`platform.system()`) e usa a ferramenta certa em cada um — a lógica de "abrir busca, digitar, conferir título, enviar" é a mesma, só a camada de baixo nível muda:

| | Linux | Windows |
|---|---|---|
| Apertar tecla / digitar | `xdotool` (binário de sistema) | `pyautogui` |
| Achar/focar janela | `wmctrl` (binário de sistema) | `pygetwindow` |
| Abrir o Discord | `flatpak run ... --ozone-platform=x11` (ou `discord` se instalado nativo) | `%LOCALAPPDATA%\Discord\Update.exe` |

No Linux precisei trocar o `pyautogui` (que uso no Windows) pelo `xdotool`: o `pyautogui` usa `python-xlib` por baixo, e ele não conseguia se autenticar no X11 no ambiente onde testei — o `xdotool` (ferramenta nativa do sistema) funcionou sem esse problema.

> ⚠️ Só tive Linux disponível pra testar de verdade (testei bastante, inclusive vários bugs reais que apareceram na prática — veja a lista abaixo). A parte Windows segue a documentação oficial do `pyautogui`/`pygetwindow`, mas não rodei num Windows de verdade ainda.

**Antes de tentar usar**, a automação confere se o Discord está instalado (`verificar_discord_instalado()` — olha o `%LOCALAPPDATA%\Discord` no Windows, ou `flatpak info` / `which discord` no Linux) e dá um erro claro, com link pra baixar, se não encontrar — em vez de deixar o resto do fluxo falhar tentando abrir um app que não existe.

**Setup:**
1. **Linux:** instalar `sudo apt install wmctrl xdotool`. **Windows:** as libs (`pyautogui`, `pygetwindow`) já entram no `pip install -r requirements.txt` (o `requirements.txt` só instala elas quando o sistema é Windows)
2. Ter o Discord desktop instalado (a automação abre/foca ele sozinha)
3. No `.env`: `DISCORD_ATIVADO=true` e `DISCORD_CONTATO_NOME=<nome de exibição exato da pessoa no Discord>`

Se `DISCORD_ATIVADO=false` (padrão), essa etapa é pulada e o resto da automação funciona normalmente — inclusive sem precisar de tela gráfica disponível (as libs/binários de automação só são usados quando a notificação de fato vai ser disparada).

### Problemas reais encontrados testando (e como foram resolvidos)

- **Discord precisa abrir com `--ozone-platform=x11`** (Linux) — por padrão o Discord (Electron) roda com renderização nativa Wayland, e nesse modo a janela fica **invisível** pro `wmctrl`/`xdotool`. A automação sempre abre o Discord com essa flag; se ele já estiver aberto sem ela, é preciso fechar e deixar a automação abrir de novo.
- **Nunca digitar sem antes confirmar que abriu a conversa certa** — o Ctrl+K + Enter pareceu simples, mas digitando rápido demais a busca do Discord por vezes não filtrava a tempo e o Enter selecionava outro resultado. A automação agora **confere o título da janela** (ex: `@FrosT - Discord`) antes de digitar qualquer coisa; se não bater com o contato esperado, tenta de novo (até `DISCORD_MAX_TENTATIVAS_ABRIR_CONVERSA` vezes) e, se mesmo assim não conseguir confirmar, **desiste sem mandar nada** — mais vale falhar de forma visível do que mandar mensagem pro lugar errado.
- **Caractere acentuado às vezes sumia** (`"Físico"` virava `"Fsico"`, travessão `"—"` desaparecia, no Linux) — digitar um caractere fora do teclado padrão faz a ferramenta de automação remapear uma tecla na hora, e isso ocasionalmente falhava. A automação agora tira acento e troca travessão por hífen antes de digitar qualquer coisa no Discord (o relatório `.txt` continua com acentuação normal).
- **Delay entre teclas configurável** (`DISCORD_DELAY_DIGITACAO_MS`, padrão 200ms) — digitar rápido demais também atrapalhava a busca do contato; um delay maior deixou bem mais estável.

> ⚠️ Hoje o `DISCORD_CONTATO_NOME` configurado é uma conta de teste pessoal, só pra validar o fluxo de envio. Antes de apontar pra pessoa responsável de verdade pelo PIX, vale rodar mais alguns testes.

## Melhorias futuras

- Trocar a notificação por API de bot do Discord (webhook num canal, por exemplo), caso a limitação da DM via bot deixe de ser um problema
- Agendar a execução (cron / scheduler) pra rodar sozinha todo dia
- Guardar um histórico das execuções (hoje cada relatório é um arquivo avulso)
- Interface visual simples pra ver o resultado sem abrir o `.txt`
- Notificar alguém quando a planilha estiver inacessível (hoje só fica registrado no log)
