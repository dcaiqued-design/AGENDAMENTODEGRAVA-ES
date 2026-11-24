# Ingest Control v0.7 — Canal Rural

Painel de ingest com agente FFmpeg e banco SQLite no computador de gravação. Esta é uma versão de revisão para o piloto.

## Operação local

1. Instale Python 3.10+ e FFmpeg com os protocolos RTMP/RTMPS e SRT no Windows.
2. Execute `INICIAR_INGEST.bat` e abra <http://127.0.0.1:8765/> no próprio computador.
3. Em **Sinais**, use a engrenagem dos canais 1 e 2 para vincular as fontes do piloto. Informe a URL somente no painel local.
4. Use **REC** e **STOP**. Confira o estado e o tempo decorrido em **Gravações**, e baixe os MP4 concluídos em **Arquivos**.

Os canais 3 e 4 estão fora do piloto. O indicador **Processo ativo** acompanha o FFmpeg. A verificação de imagem e áudio é feita no MP4. Os agendamentos pontuais executam REC e STOP pelo agente, com margens de pré e pós-gravação. O perfil usa MP4 com vídeo copiado e áudio AAC 128 kb/s. Opções avançadas pendentes aparecem desabilitadas no modo local.

O agente escuta em `127.0.0.1`. O banco e as mídias ficam em `%USERPROFILE%\IngestControl`. Mantenha a API local e guarde as URLs de sinal fora do repositório.

## Desenvolvimento e revisão

- `python scripts/setup_dev.py --require-capture` verifica os protocolos, a sintaxe JavaScript e os testes.
- `python scripts/start_dev.py` abre o painel em <http://127.0.0.1:8766/> com um banco separado.
- Abrir `index.html` diretamente no navegador mostra a prévia interativa com dados simulados.
- [Roteiro de validação no Windows](docs/VALIDACAO_V07_WINDOWS.md)

A v0.6 está na linha anterior do repositório. A integração v0.7 segue na branch `feat/v07-integracao-painel-azul`.
