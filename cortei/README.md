# ✂ Cortei

Corta vídeos por cena, automaticamente. Você escolhe o vídeo, o Cortei acha
onde cada cena troca (corte seco, zoom in/out, tremble zoom, slides) e salva
cada cena como um clipe separado, pronto para importar no CapCut ou em
qualquer editor.

Funciona 100% no seu computador. Sem API, sem conta, sem custo.

## Como usar (Windows)

1. Instale o [Python](https://www.python.org/downloads/) (marque **Add python.exe to PATH**).
2. Baixe este projeto (**Code → Download ZIP**) e extraia numa pasta.
3. Dê dois cliques em **`COMECAR.bat`**. Na primeira vez ele instala o que falta.
4. Siga os 3 passos da janela: **Vídeos** (escolha um ou vários) → **Ajustes** (opcional) → **Resultado**.
   No passo 2, **Cortar e exportar** gera os clipes e **Só analisar** só mostra os tempos dos cortes.
   Se o resultado não ficou bom, use **Ajustar e refazer** no passo 3.

Os clipes saem numa pasta `<nome do vídeo>_cenas`, ao lado do vídeo
(`video_cena_001.mp4`, `video_cena_002.mp4`...), junto com um `.txt` com os tempos.

### Pela linha de comando

```bash
pip install -r requirements.txt
python cortei.py                                  # abre a janela
python cortei.py video.mp4 --so-analisar          # só mostra os tempos
python cortei.py video.mp4 --modo secos --sens 6  # exporta os clipes
```

## Ajustes

| Opção | O que faz |
|---|---|
| **Só cortes secos** | Procura apenas troca instantânea de imagem. |
| **Secos + transições** | Também pega zoom in/out, tremble zoom e slides. |
| **Sensibilidade (1–10)** | Cortou a mais? Diminua. Deixou passar? Aumente. |
| **Duração mínima** | Cenas mais curtas que isso são unidas à vizinha (padrão 0,5 s). |
| **Modo rápido** | Não recodifica: mais veloz, mas o corte pode errar alguns quadros. |

Dica: **Só analisar** mostra os tempos sem gerar arquivos, bom para testar a sensibilidade.

## Como funciona

Os quadros são lidos em baixa resolução e comparados entre si. Um salto brusco
entre dois quadros seguidos indica corte seco; uma diferença grande entre quadros
um pouco distantes indica transição. O limite se adapta ao nível de movimento de
cada trecho. Sem rede neural: é só cálculo de imagem, rápido e local.

## Limites

- Cenas com movimento muito forte (câmera balançando, luzes piscando) podem gerar
  corte a mais; cenas muito parecidas podem passar sem corte. Ajuste a
  sensibilidade por vídeo.
- Numa transição, o corte cai aproximadamente no meio dela.

## Estrutura

- `cortei.py`: janela (CustomTkinter) e linha de comando
- `motor.py`: detecção de cenas e exportação (sem interface, reutilizável)

## Ideias para o futuro

- Escolher onde cortar nas transições (começo, meio ou fim)
- Arrastar e soltar vídeos na janela
- Gerar projeto do CapCut direto com a timeline cortada
- Detecção por modelo de IA local (ex.: TransNetV2)

## Licença

MIT. Veja [LICENSE](LICENSE).
