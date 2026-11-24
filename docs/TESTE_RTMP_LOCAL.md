# Teste de ponta a ponta: RTMP local → Ingest Control → MP4

Objetivo: validar a recepção e a gravação de um sinal sintético, sem equipamentos da emissora e sem publicar na internet.

A branch **feat/ingest-api-gravacao-agendada** contém um piloto local com SQLite, FFmpeg, agendamento e esta infraestrutura de teste. Não está mesclada na main enquanto a validação não for concluída.

## 1. Pré-requisitos no Windows

- Python 3.10 ou mais recente.
- FFmpeg para Windows com codec \`libx264\`, instalado no PATH (ou variável \`INGEST_FFMPEG\` com o caminho completo para \`ffmpeg.exe\`).
- MediaMTX Windows AMD64: https://github.com/bluenviron/mediamtx/releases
- GitHub: branch \`feat/ingest-api-gravacao-agendada\`. Baixe o ZIP desta branch ou faça checkout com Git.
- Não use fontes, chaves ou credenciais reais da emissora.

Para verificar: abra um terminal no Windows, execute \`python --version\` e \`ffmpeg -version\`.

Baixe o MediaMTX, crie a pasta \`tools\mediamtx\` na raiz do projeto e extraia nela **mediamtx.exe** e **mediamtx.yml**. Não adicione esses binários ao Git.

## 2. Inicie 3 janelas (nesta ordem)

**Janela 1 — servidor RTMP**

Execute \`teste-rtmp\INICIAR_SERVIDOR_RTMP.bat\`.

- Deve exibir RTMP listener em \`127.0.0.1:1935\`.
- O script desativa RTSP, HLS, WebRTC, SRT, API e outros listeners para reduzir a superfície de teste.
- Deixe a janela aberta.

**Janela 2 — transmissão do sinal sintético**

Execute \`teste-rtmp\GERAR_SINAL_RTMP.bat\`.

- Gera um padrão animado de teste em **640×360, 25 fps** e um tom **440 Hz**, em H.264/AAC.
- Publica em \`rtmp://127.0.0.1:1935/live/test\`.
- Deixe a janela aberta.
- Se ocorrer \`Connection refused\`, volte à Janela 1.
- Se ocorrer \`Unknown encoder 'libx264'\`, instale uma build de FFmpeg com esse encoder.

**Janela 3 — Ingest Control**

Execute \`INICIAR_INGEST.bat\` na raiz do repositório.

Abra no mesmo PC:

<http://127.0.0.1:8765/operacao-real.html>

Confirme "Serviço online" e "FFmpeg disponível".

## 3. Cadastre o sinal no painel

No formulário **Fontes de sinal**:

| Campo | Valor |
|---|---|
| Nome | Teste RTMP Local |
| Protocolo | RTMP |
| Endereço | \`rtmp://127.0.0.1:1935/live/test\` |

Clique em **Adicionar sinal**. Aparecerá na lista de fontes cadastradas.

## 4. Grave 20–30 segundos

Em **Gravação imediata**, selecione **Teste RTMP Local**, informe "Teste de captura" e clique em **Iniciar gravação real**. Acompanhe a sessão ativa, aguarde 20–30 segundos e clique em **Parar**.

Verifique o status **completed** no histórico e procure o MP4 em:

\`%USERPROFILE%\IngestControl\gravacoes\`

Abra o arquivo e confira imagem animada e áudio contínuo. Opcionalmente, no terminal:

\`ffprobe -hide_banner "CAMINHO_DO_ARQUIVO.mp4"\`

O arquivo deve conter vídeo H.264 e áudio AAC. Se falhar, verifique o log em \`%USERPROFILE%\IngestControl\logs\`.

## 5. Teste o agendamento automático

Com as três janelas abertas, agende a mesma fonte para começar cerca de 3 minutos no futuro, durar 1 minuto e usar **0 minuto** nas margens de pré/pós-gravação (para simplificar o primeiro teste).

Sem apertar REC, observe a sessão começar na hora marcada, terminar após a duração e gerar um segundo MP4.

Não altere o relógio do Windows. Se o computador estiver desligado ou o agente indisponível, a gravação não será executada.

## Quando considerar o teste aprovado

1. Servidor MediaMTX aceitou publicação do FFmpeg.
2. Cadastro RTMP está no SQLite após reiniciar o painel.
3. O botão REC iniciou uma sessão real e STOP encerrou o FFmpeg.
4. O arquivo MP4 reproduz vídeo e áudio corretamente.
5. Agendamento automático criou outro arquivo no horário.

## Limites

- É um **piloto**, não um sistema de gravação confiável para produção.
- O protocolo RTMP do servidor de teste funciona **apenas em 127.0.0.1**, no próprio computador.
- O painel do GitHub Pages permanece demonstrativo. A interface real opera em \`127.0.0.1:8765\`.
- O preview de imagem ao vivo ainda não está implementado no painel real.
- O agente ainda não tem autenticação para acesso de outras máquinas, retomada após falhas, alertas ou redundância.

Documentação oficial: https://mediamtx.org/docs/kickoff/install e https://mediamtx.org/docs/publish/ffmpeg
