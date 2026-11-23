# ✂ Cortei

Corta vídeos por cena, automaticamente. Você escolhe o vídeo, o Cortei acha
onde cada cena troca (corte seco, zoom in/out, tremble zoom, slides) e salva
cada cena como um clipe separado, pronto para importar no CapCut ou em
qualquer editor.

Funciona 100% no seu computador. Sem API, sem conta, sem custo.

## Baixar (Windows)

**[⬇ Baixar o Cortei.exe](../../releases/latest)**: abra o link, role até **Assets** e clique em
`Cortei.exe`. Não precisa instalar nada nem ter Python. É só dar dois cliques.

> Na primeira vez, o Windows pode mostrar "O Windows protegeu seu computador", porque o
> programa não é assinado. Clique em **Mais informações → Executar assim mesmo**.
> Alguns antivírus também reclamam de programas feitos com PyInstaller (falso positivo comum).

**Atalho:** coloque o `Cortei.exe` numa pasta fixa (ex.: `Documentos\Cortei`), clique com o
botão direito nele → **Mostrar mais opções → Enviar para → Área de trabalho (criar atalho)**.
Também dá para fixar na barra de tarefas ou no Menu Iniciar.

## Como usar

1. Abra o Cortei e siga os 3 passos: **Vídeos** (escolha um ou vários) → **Ajustes** (opcional) → **Resultado**.
2. No passo 2, **Cortar e exportar** gera os clipes e **Só analisar** só mostra os tempos dos cortes.
3. Se o resultado não ficou bom, use **Ajustar e refazer** no passo 3.

Os clipes saem numa pasta `<nome do vídeo>_cenas`, ao lado do vídeo
(`video_cena_001.mp4`, `video_cena_002.mp4`...), junto com um `.txt` com os tempos.
Depois é só importar os clipes no CapCut (ou em qualquer editor).

## Para desenvolvedores

### Rodar pelo código-fonte

1. Instale o [Python](https://www.python.org/downloads/) (marque **Add python.exe to PATH**).
2. Baixe o projeto (**Code → Download ZIP**) e extraia numa pasta.
3. Dê dois cliques em **`COMECAR.bat`**. Na primeira vez ele instala o que falta.

### Gerar o `.exe` você mesmo

Dê dois cliques em **`CONSTRUIR_EXE.bat`**. Ele instala o PyInstaller e cria
`dist\Cortei.exe`: um arquivo único que roda em qualquer Windows, sem Python.

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
- `cortei.ico`: ícone do programa
- `COMECAR.bat` / `CONSTRUIR_EXE.bat`: abrir o programa / gerar o `.exe`

## Ideias para o futuro

- Escolher onde cortar nas transições (começo, meio ou fim)
- Arrastar e soltar vídeos na janela
- Gerar projeto do CapCut direto com a timeline cortada
- Detecção por modelo de IA local (ex.: TransNetV2)

## Licença e créditos

MIT. Veja [LICENSE](LICENSE).

O corte dos vídeos usa o [FFmpeg](https://ffmpeg.org/), distribuído junto pelo pacote
[imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg). A interface usa o
[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).
