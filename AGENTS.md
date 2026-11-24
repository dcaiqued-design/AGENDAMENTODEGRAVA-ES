# Ingest Control — orientações ao Codex

- Use português brasileiro para interface, mensagens e documentação.
- Preserve o design v0.6: menu lateral azul-marinho, fundo claro e acentos azuis, sem verde como cor predominante.
- Mantenha quatro canais, indicadores, comandos rápidos, agenda de gravações e histórico na página inicial.
- Mantenha as opções avançadas de programação: programas, sinal/protocolo, PGM/Clean Feed/ISO, formato, qualidade, áudio, armazenamento, recorrência, margens, alertas e comportamento em falhas.
- **Nunca** apresente estados demonstrativos como reais. Ações REC/STOP continuam simuladas até a integração confirmada com o agente de gravação.
- Não armazene chaves RTMP, segredos, credenciais ou dados sensíveis no JavaScript público ou em localStorage.
- Separe frontend, backend e agente de captura Windows. SDI/DeckLink exige integração nativa; o navegador não capta SDI diretamente.
- Preserve acessibilidade, responsividade e temas. Valide qualquer alteração em navegadores desktop e mobile.
