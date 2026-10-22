# Roteiro do vídeo técnico — Sprint 4 (até 5 min)

O enunciado pede a solução **funcionando**, os **diferenciais** e a **justificativa de cada
tecnologia GoodWe e conceito sustentável**. O roteiro abaixo cabe em 4min45 e deixa 15 s
de folga. Grave a tela do app no formato de celular (Chrome DevTools, 430 × 900) e a mesa
com o ESP32 com o celular.

| Tempo | Cena | O que mostrar | Fala (resumo) |
|---|---|---|---|
| 0:00–0:20 | Abertura | Diagrama `docs/arquitetura-da-solucao.png` | "ChargeGrid transforma o carregador residencial HCA G2 em eletroposto compartilhado para galerias, com a IA como motor lógico." |
| 0:20–0:50 | Arquitetura | Diagrama, destacando Medição → Supabase → Motor → App | Supabase como fonte única de verdade; o que é real e o que é simulado (seção 3.3 do README). |
| 0:50–1:20 | Hardware | ESP32: botão = plugue, LED azul → verde → vermelho | RNF001: a cor do LED é a cor do app. Smart meter e SEMS no contexto real. |
| 1:20–2:20 | Jornada do motorista | QR Code → modo kWh → estimativa → Pix → sessão ao vivo → encerrar → recibo | Tarifa travada no plug-in (ANEEL); DLM repartindo 12,1 kW; pré-autorização de R$ 43,80 e captura de R$ 8,76; split 90/10; CO₂ no recibo. |
| 2:20–3:20 | IA para o gestor | Previsão (galeria × eletroposto), consumo × geração, load shifting, Tarifa e fator α | Random Forest e K-Means; previsão Open-Meteo para planejar, SEMS para faturar; desconto solar −12% e ponta +18%. Citar R² 0,961 e erro diário de 6,1% na galeria. |
| 3:20–3:55 | Síndico Virtual | Perguntar "Por que a vaga 02 está limitada?" e uma pergunta de previsão | LangGraph + RAG no pgvector + ferramentas que leem o modelo de ML; guardrails e LGPD; o LLM não inventa número. |
| 3:55–4:25 | Simulador e sustentabilidade | Simulador de vagas, tela Impacto | Fórmula RN009 com fator 0,72; ≈ 90 MWh/ano de sol, 95% consumido no local, ≈ 18 tCO₂/ano evitadas (seção 8.1). |
| 4:25–4:45 | Fechamento | README no GitHub | Limitações honestas e próximos passos: motor em Edge Functions, ESP32 via Supabase, dados reais do SEMS. |

## Checklist antes de gravar

- [ ] Confirmar que as Edge Functions `assistente` e `pagamentos` estão publicadas e respondendo (o app em `api` cai para regras locais se a IA não responder).
- [ ] Usar `app/dist/ChargeGrid-app-local.html` (gerado pelo `build.py` com a chave anon do `.env`) para que IA e pagamento chamem o Supabase de verdade.
- [ ] ESP32 gravado, rede `GoodWe-Demo` no ar, LED respondendo ao botão.
- [ ] Subir no YouTube como **não listado** e colar o link no `README.md` e no `.txt` de entrega.
