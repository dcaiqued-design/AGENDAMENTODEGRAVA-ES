# Ingest Control — Canal Rural

Sistema demonstrativo para monitoramento visual de sinais, programação de gravações e gerenciamento de ingest.

## Versão v0.6

Migração do protótipo HTML do Ingest Control para uma base de código versionada. Interface azul-marinho e branca com menu lateral, quatro canais simulados, indicadores operacionais, agenda avançada, filtros, histórico demonstrativo e seleção de temas.

**Atenção:** não é uma solução de gravação em produção. Os previews, status e comandos REC/STOP são demonstrativos. Não há recepção ou gravação real de RTMP, SRT e SDI. Os agendamentos demonstrativos são armazenados localmente no navegador (localStorage), não em servidor.

## Estrutura

- `index.html`: interface e estrutura de navegação
- `assets/styles.css`: estilos e temas
- `assets/app.js`: interações e formulário demonstrativo
- `AGENTS.md`: diretrizes para o Codex

## Executar

Não são necessárias dependências Node. Na pasta do repositório:

```bash
python -m http.server 8000
```

Abra `http://localhost:8000`.

## Próximas etapas

1. Modelagem de dados e API persistente para fontes, programas, canais e agendamentos.
2. Autenticação, permissões e logs auditáveis antes de uso por operadores.
3. Agente Windows para captação real com FFmpeg/MediaMTX, seguido de SRT e SDI/DeckLink.
4. Monitoramento real de sinal, gravações, falhas e arquivos.
5. Integração de agenda com programação automática de REC/STOP.
6. Testes de carga, reconexão, alertas e segurança.

O Codex Cloud é um ambiente de desenvolvimento, não substitui um servidor de gravação contínua. Não cadastre chaves RTMP, credenciais ou dados confidenciais no código.
