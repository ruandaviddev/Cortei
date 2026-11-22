# -*- coding: utf-8 -*-
"""
Cortei - motor de detecção e corte (sem interface).

Detecta trocas de cena (cortes secos e transições como zoom in/out,
tremble zoom e slides) e exporta cada cena como um clipe separado.
Dependências: numpy e imageio-ffmpeg (traz o ffmpeg junto).
"""
import os
import re
import shutil
import subprocess

LARGURA, ALTURA = 160, 90          # tamanho reduzido usado só para analisar
EXTENSOES = ("*.mp4", "*.mov", "*.mkv", "*.avi", "*.webm", "*.m4v")

_SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class Cancelado(Exception):
    pass


# --------------------------------------------------------------------------
# ffmpeg
# --------------------------------------------------------------------------
def achar_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    caminho = shutil.which("ffmpeg")
    if caminho:
        return caminho
    raise RuntimeError(
        "ffmpeg não encontrado. Rode:  pip install imageio-ffmpeg"
    )


def info_video(ffmpeg, video):
    """Lê duração e fps do vídeo (via a saída de `ffmpeg -i`)."""
    p = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", video],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=_SEM_JANELA,
    )
    txt = p.stderr.decode("utf-8", "replace")
    if "Video:" not in txt:
        raise RuntimeError("Não consegui ler esse arquivo como vídeo.")
    duracao = None
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", txt)
    if m:
        duracao = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    fps = None
    linha_video = next((l for l in txt.splitlines() if "Video:" in l), "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*fps", linha_video)
    if m:
        fps = float(m.group(1))
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*tbr", linha_video)
        if m:
            fps = float(m.group(1))
    if not fps or fps < 1 or fps > 240:
        fps = 30.0
    return duracao, fps


# --------------------------------------------------------------------------
# Análise
# --------------------------------------------------------------------------
def _calcular_pontuacoes(video, ffmpeg, fps, duracao, progresso=None, cancelar=None):
    """
    Lê o vídeo reduzido (160x90) e calcula duas séries:
      d1[i] = diferença entre o quadro i-1 e o quadro i   (acha cortes secos)
      dk[i] = diferença entre os quadros i-k e i+k        (acha transições)
    """
    import numpy as np

    k = max(2, int(round(0.12 * fps)))
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-i", video,
        "-an", "-sn", "-vf", "scale=%d:%d" % (LARGURA, ALTURA),
        "-r", "%.5f" % fps, "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=_SEM_JANELA,
    )
    tamanho = LARGURA * ALTURA * 3
    janela = []          # últimos 2k+1 quadros
    d1, dk = [], []
    anterior = None
    total_estimado = int(duracao * fps) if duracao else 0
    i = 0
    try:
        while True:
            if cancelar is not None and cancelar.is_set():
                raise Cancelado()
            buf = proc.stdout.read(tamanho)
            if len(buf) < tamanho:
                break
            quadro = np.frombuffer(buf, dtype=np.uint8).astype(np.int16)
            d1.append(0.0 if anterior is None else float(np.abs(quadro - anterior).mean()))
            anterior = quadro
            janela.append(quadro)
            if len(janela) > 2 * k + 1:
                janela.pop(0)
            if len(janela) == 2 * k + 1:
                dk.append(float(np.abs(janela[-1] - janela[0]).mean()))
            i += 1
            if progresso and total_estimado and i % 30 == 0:
                progresso(min(0.99, i / total_estimado))
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        proc.kill()
        proc.wait()
    n = len(d1)
    if n < 2:
        raise RuntimeError("O vídeo parece vazio ou não pôde ser decodificado.")
    # alinha dk: dk[j] está centrado no quadro j (zeros nas pontas)
    dk_alinhado = [0.0] * k + dk + [0.0] * (n - k - len(dk))
    dk_alinhado = dk_alinhado[:n]
    return d1, dk_alinhado, k


def _limiares(sensibilidade):
    f = (10 - sensibilidade) / 9.0          # 0 (mais sensível) .. 1 (menos)
    f = min(1.0, max(0.0, f))
    return 10.0 + 30.0 * f, 8.0 + 22.0 * f   # (corte seco, transição)


def _linha_base(serie, raio):
    """Mediana móvel: o nível 'normal' de movimento de cada trecho."""
    import numpy as np
    a = np.asarray(serie, dtype=float)
    if len(a) <= 2 * raio + 1:
        return np.full(len(a), float(np.median(a)))
    pad = np.pad(a, raio, mode="edge")
    janelas = np.lib.stride_tricks.sliding_window_view(pad, 2 * raio + 1)
    return np.median(janelas, axis=1)


def _escolher_cortes(d1, dk, fps, modo, sensibilidade, dur_min):
    """Devolve lista de (indice_do_quadro, pontuacao)."""
    n = len(d1)
    thr_seco, thr_trans = _limiares(sensibilidade)
    raio = max(5, int(round(1.0 * fps)))
    base1 = _linha_base(d1, raio)
    basek = _linha_base(dk, raio)
    candidatos = []

    # --- cortes secos -------------------------------------------------
    secos = []
    for i in range(1, n):
        # precisa passar do limite E ficar bem acima do movimento normal
        # do trecho (evita falso corte em cenas com muito movimento)
        if d1[i] < thr_seco or d1[i] < 2.5 * base1[i]:
            continue
        lo, hi = max(1, i - 3), min(n, i + 4)
        vizinhos = [d1[j] for j in range(lo, hi) if j != i]
        maior_viz = max(vizinhos) if vizinhos else 0.0
        if modo == "secos":
            # basta ser o maior pico da vizinhança
            if d1[i] >= maior_viz:
                secos.append(i)
        else:
            # no modo com transições, o corte seco precisa ser um pico
            # isolado; o resto é tratado como transição abaixo
            if d1[i] >= 1.8 * maior_viz:
                secos.append(i)
    for i in secos:
        candidatos.append((i, d1[i]))

    # --- transições (zoom, tremble, slide...) -------------------------
    if modo != "secos":
        mascara = [dk[j] >= max(thr_trans, 1.5 * basek[j]) for j in range(n)]
        # fecha buracos pequenos (até 2 quadros)
        i = 0
        while i < n:
            if not mascara[i]:
                j = i
                while j < n and not mascara[j]:
                    j += 1
                if 0 < i and j < n and (j - i) <= 2:
                    for t in range(i, j):
                        mascara[t] = True
                i = j
            else:
                i += 1
        max_len = int(2.5 * fps)
        i = 0
        while i < n:
            if mascara[i]:
                s = i
                while i < n and mascara[i]:
                    i += 1
                e = i - 1
                if (e - s + 1) > max_len:
                    continue          # movimento contínuo, não é transição
                if any(s - 2 <= c <= e + 2 for c in secos):
                    continue          # já tem um corte seco exato aqui
                centro = (s + e) // 2
                candidatos.append((centro, max(dk[s:e + 1])))
            else:
                i += 1

    # --- tira cortes colados (mantém o mais forte) ---------------------
    min_quadros = max(1, int(round(dur_min * fps)))
    aceitos = []
    for idx, score in sorted(candidatos, key=lambda c: -c[1]):
        if idx < min_quadros or idx > n - min_quadros:
            continue
        if all(abs(idx - a) >= min_quadros for a, _ in aceitos):
            aceitos.append((idx, score))
    return sorted(aceitos)


def analisar(video, modo="transicoes", sensibilidade=5, dur_min=0.5,
             progresso=None, cancelar=None):
    """
    Devolve (cortes, total_quadros, fps), onde `cortes` é a lista de índices
    de quadro onde começa cada nova cena (a primeira cena começa no 0).
    """
    ffmpeg = achar_ffmpeg()
    duracao, fps = info_video(ffmpeg, video)
    d1, dk, _ = _calcular_pontuacoes(video, ffmpeg, fps, duracao, progresso, cancelar)
    cortes = _escolher_cortes(d1, dk, fps, modo, sensibilidade, dur_min)
    if progresso:
        progresso(1.0)
    return [c for c, _ in cortes], len(d1), fps


# --------------------------------------------------------------------------
# Exportação
# --------------------------------------------------------------------------
def formatar_tempo(segundos):
    m, s = divmod(segundos, 60)
    h, m = divmod(int(m), 60)
    return "%02d:%02d:%06.3f" % (h, m, s)


def cenas_a_partir_dos_cortes(cortes, total_quadros):
    limites = [0] + list(cortes) + [total_quadros]
    return [(limites[i], limites[i + 1]) for i in range(len(limites) - 1)]


def exportar(video, cortes, total_quadros, fps, pasta_saida, rapido=False,
             progresso=None, log=None, cancelar=None):
    """Corta o vídeo em clipes. Devolve a lista de arquivos criados."""
    ffmpeg = achar_ffmpeg()
    os.makedirs(pasta_saida, exist_ok=True)
    base = os.path.splitext(os.path.basename(video))[0]
    cenas = cenas_a_partir_dos_cortes(cortes, total_quadros)
    arquivos = []
    for n, (ini, fim) in enumerate(cenas, 1):
        if cancelar is not None and cancelar.is_set():
            raise Cancelado()
        saida = os.path.join(pasta_saida, "%s_cena_%03d.mp4" % (base, n))
        # pequena margem (poucos ms) para o corte nunca cair exatamente
        # sobre o tempo de um quadro: evita quadro a mais ou a menos
        margem = min(0.002, 0.25 / fps)
        inicio_s = max(0.0, ini / fps - margem)
        duracao_s = (fim - ini) / fps - margem
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
               "-ss", "%.4f" % inicio_s, "-i", video]
        if fim < total_quadros:
            cmd += ["-t", "%.4f" % duracao_s]
        if rapido:
            cmd += ["-c", "copy", "-avoid_negative_ts", "make_zero"]
        else:
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart"]
        cmd.append(saida)
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           creationflags=_SEM_JANELA)
        if r.returncode != 0:
            raise RuntimeError("Erro do ffmpeg na cena %d:\n%s"
                               % (n, r.stderr.decode("utf-8", "replace")[-600:]))
        arquivos.append(saida)
        if log:
            log("  cena %03d  %s → %s  (%.2fs)" % (
                n, formatar_tempo(ini / fps), formatar_tempo(fim / fps), duracao_s))
        if progresso:
            progresso(n / len(cenas))
    # lista de tempos (útil para conferir)
    lista = os.path.join(pasta_saida, "%s_cortes.txt" % base)
    with open(lista, "w", encoding="utf-8") as f:
        f.write("Cenas de %s (fps %.3f)\n" % (os.path.basename(video), fps))
        for n, (ini, fim) in enumerate(cenas, 1):
            f.write("cena %03d  %s  ->  %s\n" % (
                n, formatar_tempo(ini / fps), formatar_tempo(fim / fps)))
    return arquivos


def pasta_padrao(video):
    base = os.path.splitext(os.path.basename(video))[0]
    return os.path.join(os.path.dirname(os.path.abspath(video)), base + "_cenas")


