# Ambiente de desenvolvimento — Ingest Control

Configuração reproduzível do projeto. Estes arquivos não comprovam que as configurações do ambiente hospedado foram salvas/publicadas no Codex.

## Base

- Repositório: `dcaiqued-design/AGENDAMENTODEGRAVA-ES`.
- Branch de integração: `feat/v07-integracao-painel-azul`.
- Python 3.10+; backend usa biblioteca padrão, sem pacotes pip.
- Node.js para checagem de sintaxe JavaScript; frontend estático, sem npm install ou build.
- FFmpeg com RTMP, RTMPS e SRT para testar captura. Ausência não impede testes unitários com processos simulados.
- Nenhum banco, vídeo, chave ou credencial deve ser incluído no repositório.

## Preparação / setup

Na raiz do checkout:

```sh
python scripts/setup_dev.py
```

Verifica arquivos, Python, JavaScript, disponibilidade do FFmpeg e executa os testes. Falhas de checagem/testes retornam código diferente de zero. Não instala ferramentas automaticamente nem altera o sistema operacional. Para exigir suporte à captura:

```sh
python scripts/setup_dev.py --require-capture
```

Se Python, Node ou FFmpeg estiverem ausentes, provisionar essas ferramentas na imagem do ambiente antes da verificação. No Windows com Python Launcher, pode-se usar `py -3` no lugar de `python`.

## Inicialização / start

```sh
python scripts/start_dev.py
```

O agente serve o painel azul e a API em `http://127.0.0.1:8766/`. Dados de desenvolvimento ficam em `~/IngestControl-dev`, separados dos dados de operação (`~/IngestControl`, porta 8765). Interromper com Ctrl+C. Não expor a porta por túnel ou proxy público.

Variáveis opcionais: `INGEST_DEV_PORT`, `INGEST_DEV_DATA_DIR`, `INGEST_FFMPEG`. Não colocar segredos nesses scripts. O serviço usa apenas loopback, sem autenticação remota.

## Conferência

- `GET /api/health`: JSON com serviço, FFmpeg e armazenamento.
- `GET /api/channels`: vínculos persistentes entre canais e fontes.
- `GET /api/jobs` e `/api/recordings`: dados do agente, sem exemplos visuais.
- Sem agente, o painel local bloqueia comandos e mostra estado desconhecido.
- A hospedagem estática continua demonstrativa e não controla o Windows remotamente.
- Captura no Windows, vídeo/áudio, comportamento de desktop/mobile e validação operacional precisam de testes específicos; testes unitários não os comprovam.

## Configuração hospedada no Codex

Os comandos acima são os valores preparados para setup e inicialização quando o ambiente oferecer esses campos. É necessário conferir o repositório/branch selecionados, executar o setup nesse ambiente e salvar suas configurações pelo fluxo disponível no Codex. A confirmação dessa etapa depende da resposta daquela interface; um commit ou deploy do site não a substitui.
