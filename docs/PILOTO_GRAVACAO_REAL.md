# Piloto de gravação real — Ingest Control

Esta branch adiciona um **agente de gravação local**, diferente do protótipo de interface v0.6. Na v0.7, os controles integrados estão na raiz do agente. A página /operacao-real.html continua disponível para diagnóstico.

## Requisitos

- Windows 10/11 (ou Linux para testes do servidor)
- Python 3.10+ instalado
- FFmpeg com suporte a RTMP/RTMPS/SRT (confirme com \`ffmpeg -protocols\`)
- Espaço livre em disco
- URL de origem de sinal **que você tem autorização para receber e gravar**
- Para automatizar gravações, computador e agente devem permanecer ligados

## Primeiro teste no Windows

1. Instale FFmpeg e coloque \`ffmpeg.exe\` no PATH ou configure a variável \`INGEST_FFMPEG\` para o executável.
2. Abra \`INICIAR_INGEST.bat\` na pasta do projeto.
3. Abra <http://127.0.0.1:8765/operacao-real.html> **no mesmo computador**.
4. Confira se os indicadores do serviço e do FFmpeg estão verdes.
5. Cadastre uma fonte RTMP/RTMPS ou SRT **de teste**.
6. Faça uma gravação manual de alguns segundos e pare pelo botão vermelho.
7. Localize o arquivo na pasta informada no rodapé do painel. Confira a reprodução e o áudio.
8. Programe outra gravação futura. Mantenha a janela do agente aberta até o fim e verifique o status.

O protótipo visual v0.6 continua disponível na raiz <http://127.0.0.1:8765/>. **Nenhum REC/STOP dessa tela demonstra captura real**.

### Armazenamento

Padrão: \`%USERPROFILE%\IngestControl\` no Windows, com:
- \`ingest.sqlite3\` — cadastro de fontes, agendamentos e histórico
- \`gravacoes/\` — MP4 gerados pelo FFmpeg
- \`logs/\` — logs individuais do processo FFmpeg

Para mudar o destino **antes de iniciar o agente**, configure \`INGEST_DATA_DIR\` no ambiente do Windows. Não mude enquanto grava. A URL da fonte pode conter credenciais e é salva no SQLite do computador; proteja acesso ao arquivo e faça backup criptografado conforme a política da empresa.

### Restrições e segurança

- O serviço escuta **somente 127.0.0.1**, sem login. **Não exponha a porta, não use túnel público nem reverse proxy para ela**. Mesmo em rede interna, a API precisa de autenticação/autorização e HTTPS antes de qualquer abertura de acesso.
- A página hospedada no GitHub Pages **não controla** esse agente: a interface operacional só é servida localmente, no endereço acima.
- Não cole chaves de produção no GitHub, no navegador público ou em chamados.
- O agendador grava apenas eventos pontuais: sem recorrência, resiliência a desligamentos, armazenamento compartilhado, preview, transcodificação avançada, gerenciamento de múltiplos perfis nem failover.
- Pré e pós-gravação aceitam 0–30 minutos. Até 4 gravações simultâneas, no máximo uma sessão por fonte; o limite é lógico, não garante desempenho do hardware.
- O vídeo é copiado para MP4 quando compatível (ex.: H.264). O áudio é convertido para AAC; fontes com codecs incompatíveis podem falhar. Verifique o resultado antes de uso operacional.
- Se o computador estiver desligado durante o horário, o agendamento será marcado como perdido após a janela. Se o agente fechar durante a gravação, a sessão será marcada como interrompida na próxima inicialização. Arquivos MP4 fragmentados podem ter recuperação parcial.
- O sistema não faz backup automático, não impõe cota, nem garante entrega à ilha de edição.
- O FFmpeg recebe a URL sem passar por shell. Ainda assim, somente cadastre fontes confiáveis, pois ele fará conexões de saída para os endereços informados.

### Testes automáticos

\`\`\`bash
python -m unittest discover -s tests -v
\`\`\`

Os testes cobrem banco, validação, conflitos de horários e estados do scheduler sem necessidade de receber vídeo real. O **teste de captura de mídia e agendamento no Windows depende de FFmpeg, rede e sinal efetivo**.

## Evolução proposta

1. Consolidar API, agendador, testes e observabilidade no Windows.
2. Adicionar autenticação/HTTPS e arquitetura de acesso remoto segura.
3. Conectar agenda avançada do painel v0.6 ao backend (mapeamento de protocolos e perfis).
4. Implementar preview real, codec configurável, perfis PGM/Clean/ISO e gravação em arquivo seguro.
5. Implementar retenção, backups, alarmes, reintentos e supervisão do serviço 24/7.
