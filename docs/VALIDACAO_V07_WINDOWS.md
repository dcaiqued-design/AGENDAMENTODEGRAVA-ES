# Validação do Ingest Control v0.7 no Windows

Use a branch `feat/v07-integracao-painel-azul`. Execute `python scripts/setup_dev.py --require-capture` e rode `python scripts/start_dev.py` para validar com o banco de desenvolvimento. Abra <http://127.0.0.1:8766/> na máquina de captura.

## Roteiro de aceite

| Teste | Procedimento | Resultado esperado |
| --- | --- | --- |
| Fontes dos canais do piloto | Cadastre as duas fontes já testadas pelos botões de configuração. Para RTMP sintético, use o [roteiro MediaMTX](TESTE_RTMP_LOCAL.md). Para SRT, confira as pontas caller/listener, porta, stream ID e a configuração de latência da operação. | Os dois canais mostram nome e protocolo. As URLs não aparecem nas listas da API. Os canais 3 e 4 aparecem como não integrados. |
| REC e STOP individuais | Grave 20–30 s em cada canal a partir da página Sinais. Dê STOP pelo painel Início. | O processo inicia e o contador aparece nas duas telas. Após STOP, a sessão sai de ativo, entra em concluído e o MP4 fica disponível em Arquivos. |
| Gravação simultânea | Inicie os dois canais. Pare o primeiro enquanto o segundo continua. Repita com REC ALL e Parar todos. | Os processos, contadores e arquivos permanecem independentes e o último STOP finaliza cada arquivo. |
| Imagem e áudio | Baixe cada MP4, abra no VLC e use `ffprobe -hide_banner "arquivo.mp4"`. Confira início, meio e fim. | A imagem e o áudio correspondem ao sinal, sem cortes inesperados. Compare a duração da mídia com o intervalo de gravação. O painel mede tempo de sessão, que pode incluir a espera de conexão. |
| Agendamento | Marque um início futuro, use 0 de margem e aguarde. Repita com pré/pós e cancele outro agendamento antes de começar. | A gravação inicia e para sozinha. O estado final fica salvo. O agendamento cancelado não dispara. |
| Perda de sinal | Interrompa o codificador em uma gravação de teste e confira o histórico. Faça uma nova gravação depois de restabelecer o sinal. | A falha é registrada quando o FFmpeg sai. O painel libera novo REC. A integridade de arquivo parcial precisa de validação manual. |
| Persistência e arquivos | Após encerrar todas as gravações, reinicie o agente. Abra agendamentos, histórico e arquivos. Mova um MP4 de teste fora da pasta e atualize. | Fontes, agenda e sessões persistem. O arquivo removido deixa de aparecer em Arquivos e o download fica indisponível. |
| Uso prolongado | Repita com sinais reais, disco de destino e duração típicos do Canal Rural. | Sem perda perceptível de mídia, problemas de sincronismo, saturação de disco ou bloqueio de STOP. |

Registre por canal o protocolo, build do FFmpeg, modo do SRT, horário de início e fim, resultado do STOP, tamanho do MP4 e verificação de imagem e áudio. Use nomes genéricos no relato e omita URLs e chaves.

O piloto exige o agente e o Windows ligados durante os agendamentos. Preview ao vivo, reconexão automática, recorrência, SDI/DeckLink e acesso remoto continuam fora do escopo desta validação.
