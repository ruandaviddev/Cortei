#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cortei - corta vídeos por cena, automaticamente.

Sem argumentos abre a janela. Também funciona pela linha de comando:
    python cortei.py video.mp4 --so-analisar
    python cortei.py video.mp4 --modo secos --sens 6
"""
import os
import sys
import queue
import argparse
import threading
import subprocess

import motor

NOME = "Cortei"


def _recurso(nome):
    """Caminho de um arquivo que acompanha o programa (funciona no .exe também)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nome)

# Paleta (tema escuro)
BG = "#0E1014"
CARD = "#171A21"
BORDA = "#262B35"
TEXTO = "#E9ECF2"
SUAVE = "#8E96A6"
DESTAQUE = "#7C5CFF"
DESTAQUE_HOVER = "#6B49F2"
CAMPO = "#0E1014"
OK = "#3DD68C"
ERRO = "#FF6B6B"

MODOS = {"Só cortes secos": "secos", "Secos + transições": "transicoes"}


def abrir_janela():
    from tkinter import filedialog, messagebox
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")

    root = ctk.CTk(fg_color=BG)
    root.title(NOME)
    root.geometry("720x680")
    root.minsize(660, 620)

    def _icone():
        try:
            caminho = _recurso("cortei.ico")
            if sys.platform.startswith("win") and os.path.exists(caminho):
                root.iconbitmap(caminho)
        except Exception:                                        # noqa
            pass
    # o CustomTkinter coloca o ícone padrão dele por volta de 200 ms; o nosso vem depois
    root.after(300, _icone)

    arquivos = []
    fila = queue.Queue()
    cancelar = threading.Event()
    estado = {"rodando": False, "pasta": None, "ok": False, "passo": 0}

    # ---------- helpers de visual ----------
    def fonte(tam, negrito=False):
        return ctk.CTkFont(size=tam, weight="bold" if negrito else "normal")

    def botao_principal(pai, texto, comando, **kw):
        return ctk.CTkButton(pai, text=texto, command=comando, height=40,
                             corner_radius=10, fg_color=DESTAQUE,
                             hover_color=DESTAQUE_HOVER, text_color="white",
                             text_color_disabled="#6F6A8F",
                             font=fonte(13, True), **kw)

    def botao_suave(pai, texto, comando, **kw):
        return ctk.CTkButton(pai, text=texto, command=comando, height=40,
                             corner_radius=10, fg_color="transparent",
                             hover_color=BORDA, border_width=1, border_color=BORDA,
                             text_color=TEXTO, text_color_disabled="#5A606C",
                             font=fonte(13), **kw)

    def nova_pagina(titulo, subtitulo):
        """Página com título, corpo e rodapé (rodapé ancorado embaixo)."""
        pag = ctk.CTkFrame(root, fg_color="transparent")
        rodape = ctk.CTkFrame(pag, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=28, pady=(8, 22))
        ctk.CTkLabel(pag, text=titulo, text_color=TEXTO, font=fonte(22, True),
                     anchor="w").pack(fill="x", padx=28, pady=(8, 0))
        ctk.CTkLabel(pag, text=subtitulo, text_color=SUAVE, font=fonte(13),
                     anchor="w", justify="left", wraplength=620
                     ).pack(fill="x", padx=28, pady=(2, 12))
        corpo = ctk.CTkFrame(pag, fg_color=CARD, corner_radius=14,
                             border_width=1, border_color=BORDA)
        corpo.pack(fill="both", expand=True, padx=28)
        return pag, corpo, rodape

    # ---------- cabeçalho + indicador de etapas ----------
    cab = ctk.CTkFrame(root, fg_color="transparent")
    cab.pack(fill="x", padx=28, pady=(20, 6))
    ctk.CTkLabel(cab, text="✂  " + NOME, text_color=TEXTO,
                 font=fonte(26, True)).pack(side="left")

    etapas = ctk.CTkFrame(root, fg_color="transparent")
    etapas.pack(fill="x", padx=28, pady=(10, 8))
    nomes_etapas = ["Vídeos", "Ajustes", "Resultado"]
    circulos, rotulos, linhas = [], [], []
    etapas.grid_columnconfigure((1, 3), weight=1)
    for i, nome in enumerate(nomes_etapas):
        col = i * 2
        item = ctk.CTkFrame(etapas, fg_color="transparent")
        item.grid(row=0, column=col)
        c = ctk.CTkLabel(item, text=str(i + 1), width=28, height=28, corner_radius=14,
                         fg_color=BORDA, text_color=SUAVE, font=fonte(12, True))
        c.pack(side="left")
        r = ctk.CTkLabel(item, text=nome, text_color=SUAVE, font=fonte(13))
        r.pack(side="left", padx=(8, 0))
        circulos.append(c)
        rotulos.append(r)
        if i < len(nomes_etapas) - 1:
            ln = ctk.CTkFrame(etapas, height=2, fg_color=BORDA, corner_radius=1)
            ln.grid(row=0, column=col + 1, sticky="ew", padx=12)
            linhas.append(ln)

    def atualizar_etapas(passo, tudo_ok=False):
        for i in range(3):
            feito = i < passo or (tudo_ok and i == passo)
            if feito:
                circulos[i].configure(text="✓", fg_color=OK, text_color=BG)
                rotulos[i].configure(text_color=TEXTO, font=fonte(13))
            elif i == passo:
                circulos[i].configure(text=str(i + 1), fg_color=DESTAQUE, text_color="white")
                rotulos[i].configure(text_color=TEXTO, font=fonte(13, True))
            else:
                circulos[i].configure(text=str(i + 1), fg_color=BORDA, text_color=SUAVE)
                rotulos[i].configure(text_color=SUAVE, font=fonte(13))
        for i, ln in enumerate(linhas):
            ln.configure(fg_color=OK if i < passo else BORDA)

    # ======================================================================
    # Página 1: vídeos
    # ======================================================================
    pag1, corpo1, rod1 = nova_pagina(
        "Escolha os vídeos",
        "Pode escolher vários de uma vez. Cada um vira uma pasta de clipes, um por cena.")
    topo1 = ctk.CTkFrame(corpo1, fg_color="transparent")
    topo1.pack(fill="x", padx=18, pady=(18, 10))
    botao_principal(topo1, "Escolher vídeos…", lambda: escolher(), width=170).pack(side="left")
    botao_suave(topo1, "Limpar tudo", lambda: limpar(), width=100).pack(side="left", padx=8)
    lbl_qtd = ctk.CTkLabel(topo1, text="nenhum vídeo escolhido", text_color=SUAVE)
    lbl_qtd.pack(side="right")
    lista = ctk.CTkScrollableFrame(corpo1, fg_color=CAMPO, corner_radius=10,
                                   border_width=1, border_color=BORDA)
    lista.pack(fill="both", expand=True, padx=18, pady=(0, 18))
    btn_prox1 = botao_principal(rod1, "Próximo  →", lambda: mostrar(1), width=140,
                                state="disabled")
    btn_prox1.pack(side="right")

    # ======================================================================
    # Página 2: ajustes
    # ======================================================================
    pag2, corpo2, rod2 = nova_pagina(
        "Ajustes",
        "Os valores padrão costumam funcionar. Se cortar a mais ou a menos, volte e mude a sensibilidade.")
    int2 = ctk.CTkFrame(corpo2, fg_color="transparent")
    int2.pack(fill="both", expand=True, padx=22, pady=18)

    ctk.CTkLabel(int2, text="O que procurar", text_color=SUAVE, font=fonte(12)
                 ).pack(anchor="w")
    modo_var = ctk.StringVar(value="Secos + transições")
    ctk.CTkSegmentedButton(
        int2, values=list(MODOS), variable=modo_var, height=38, corner_radius=10,
        fg_color=CAMPO, unselected_color=CAMPO, unselected_hover_color=BORDA,
        selected_color=DESTAQUE, selected_hover_color=DESTAQUE_HOVER,
        text_color=TEXTO, font=fonte(13)).pack(fill="x", pady=(6, 4))
    ctk.CTkLabel(int2, text="“Secos + transições” também pega zoom in/out, tremble zoom e slides.",
                 text_color=SUAVE, font=fonte(11)).pack(anchor="w", pady=(0, 20))

    topo_s = ctk.CTkFrame(int2, fg_color="transparent")
    topo_s.pack(fill="x")
    ctk.CTkLabel(topo_s, text="Sensibilidade", text_color=SUAVE, font=fonte(12)
                 ).pack(side="left")
    lbl_sens = ctk.CTkLabel(topo_s, text="5", text_color=TEXTO, font=fonte(15, True))
    lbl_sens.pack(side="right")
    sens_var = ctk.IntVar(value=5)
    ctk.CTkSlider(
        int2, from_=1, to=10, number_of_steps=9, variable=sens_var,
        progress_color=DESTAQUE, button_color=DESTAQUE,
        button_hover_color=DESTAQUE_HOVER, fg_color=BORDA,
        command=lambda v: lbl_sens.configure(text=str(int(round(v))))
    ).pack(fill="x", pady=(8, 4))
    ext = ctk.CTkFrame(int2, fg_color="transparent")
    ext.pack(fill="x", pady=(0, 20))
    ctk.CTkLabel(ext, text="menos cortes", text_color=SUAVE, font=fonte(11)).pack(side="left")
    ctk.CTkLabel(ext, text="mais cortes", text_color=SUAVE, font=fonte(11)).pack(side="right")

    linha_d = ctk.CTkFrame(int2, fg_color="transparent")
    linha_d.pack(fill="x", pady=(0, 16))
    ctk.CTkLabel(linha_d, text="Duração mínima de uma cena", text_color=TEXTO,
                 font=fonte(13)).pack(side="left")
    dur_var = ctk.StringVar(value="0.5")
    ctk.CTkEntry(linha_d, textvariable=dur_var, width=64, height=32, justify="center",
                 fg_color=CAMPO, border_color=BORDA, text_color=TEXTO).pack(side="right")
    ctk.CTkLabel(linha_d, text="segundos", text_color=SUAVE).pack(side="right", padx=(0, 8))

    rapido_var = ctk.BooleanVar(value=False)
    ctk.CTkSwitch(
        int2, text="Modo rápido  (não recodifica; o corte pode errar alguns quadros)",
        variable=rapido_var, progress_color=DESTAQUE, button_color="white",
        fg_color=BORDA, text_color=TEXTO, font=fonte(12)).pack(anchor="w")

    botao_suave(rod2, "←  Voltar", lambda: mostrar(0), width=110).pack(side="left")
    botao_principal(rod2, "Cortar e exportar", lambda: iniciar(True), width=170
                    ).pack(side="right")
    botao_suave(rod2, "Só analisar", lambda: iniciar(False), width=120
                ).pack(side="right", padx=8)

    # ======================================================================
    # Página 3: resultado
    # ======================================================================
    pag3, corpo3, rod3 = nova_pagina(
        "Resultado", "Os clipes ficam numa pasta “<nome do vídeo>_cenas”, ao lado de cada vídeo.")
    int3 = ctk.CTkFrame(corpo3, fg_color="transparent")
    int3.pack(fill="both", expand=True, padx=18, pady=16)
    lbl_status = ctk.CTkLabel(int3, text="", text_color=TEXTO, font=fonte(16, True),
                              anchor="w")
    lbl_status.pack(fill="x")
    barra = ctk.CTkProgressBar(int3, height=8, corner_radius=4, fg_color=BORDA,
                               progress_color=DESTAQUE)
    barra.set(0)
    barra.pack(fill="x", pady=(10, 12))
    texto = ctk.CTkTextbox(int3, fg_color=CAMPO, corner_radius=10, border_width=1,
                           border_color=BORDA, text_color=TEXTO,
                           font=ctk.CTkFont(family="Consolas", size=12), wrap="word")
    texto.pack(fill="both", expand=True)
    texto.configure(state="disabled")

    btn_refazer = botao_suave(rod3, "←  Ajustar e refazer", lambda: mostrar(1), width=170)
    btn_refazer.pack(side="left")
    btn_cancelar = botao_suave(rod3, "Cancelar", lambda: cancelar.set(), width=100)
    btn_cancelar.pack(side="left", padx=8)
    btn_novo = botao_principal(rod3, "Novo corte", lambda: novo_corte(), width=130)
    btn_novo.pack(side="right")
    btn_pasta = botao_suave(rod3, "Abrir pasta", lambda: abrir_pasta(), width=120)
    btn_pasta.pack(side="right", padx=8)

    paginas = [pag1, pag2, pag3]

    def mostrar(passo, tudo_ok=False):
        if estado["rodando"]:
            return
        for p in paginas:
            p.pack_forget()
        paginas[passo].pack(fill="both", expand=True)
        estado["passo"] = passo
        atualizar_etapas(passo, tudo_ok)

    def escrever(msg):
        texto.configure(state="normal")
        texto.insert("end", msg + "\n")
        texto.see("end")
        texto.configure(state="disabled")

    def limpar_log():
        texto.configure(state="normal")
        texto.delete("1.0", "end")
        texto.configure(state="disabled")

    def botoes_resultado(rodando):
        btn_cancelar.configure(state="normal" if rodando else "disabled")
        btn_refazer.configure(state="disabled" if rodando else "normal")
        btn_novo.configure(state="disabled" if rodando else "normal")
        btn_pasta.configure(state="normal" if (not rodando and estado["pasta"]) else "disabled")

    # ---------- lista de vídeos ----------
    def atualizar_lista():
        for w in lista.winfo_children():
            w.destroy()
        if not arquivos:
            ctk.CTkLabel(lista, text="Nenhum vídeo ainda.\nClique em “Escolher vídeos…”.",
                         text_color=SUAVE, justify="center").pack(pady=40)
        for a in arquivos:
            linha_a = ctk.CTkFrame(lista, fg_color="transparent")
            linha_a.pack(fill="x", pady=1)
            ctk.CTkLabel(linha_a, text=os.path.basename(a), text_color=TEXTO,
                         anchor="w").pack(side="left", fill="x", expand=True, padx=(6, 0))
            ctk.CTkButton(linha_a, text="✕", width=28, height=24, fg_color="transparent",
                          hover_color=BORDA, text_color=SUAVE,
                          command=lambda x=a: remover(x)).pack(side="right")
        lbl_qtd.configure(text=("%d vídeo(s)" % len(arquivos)) if arquivos
                          else "nenhum vídeo escolhido")
        btn_prox1.configure(state="normal" if arquivos else "disabled")

    def remover(a):
        if a in arquivos:
            arquivos.remove(a)
        atualizar_lista()

    def escolher():
        novos = filedialog.askopenfilenames(
            title="Escolha os vídeos",
            filetypes=[("Vídeos", " ".join(motor.EXTENSOES)), ("Todos os arquivos", "*.*")])
        for a in novos:
            if a not in arquivos:
                arquivos.append(a)
        atualizar_lista()

    def limpar():
        arquivos.clear()
        atualizar_lista()

    def novo_corte():
        arquivos.clear()
        estado["pasta"] = None
        atualizar_lista()
        mostrar(0)

    def abrir_pasta():
        pasta = estado["pasta"]
        if pasta and os.path.isdir(pasta):
            if sys.platform.startswith("win"):
                os.startfile(pasta)                              # noqa
            elif sys.platform == "darwin":
                subprocess.Popen(["open", pasta])
            else:
                subprocess.Popen(["xdg-open", pasta])

    # ---------- trabalho em segundo plano ----------
    def trabalho(exportar_clipes, params, videos):
        modo, sens, dur_min, rapido = params
        total_cenas = 0
        try:
            total = len(videos)
            for n, video in enumerate(videos, 1):
                nome = os.path.basename(video)
                fila.put(("log", "\n[%d/%d]  %s" % (n, total, nome)))
                fila.put(("status", "Analisando…  (%d de %d)" % (n, total)))
                base = (n - 1) / total
                fatia = 1.0 / total
                cortes, nq, fps = motor.analisar(
                    video, modo, sens, dur_min,
                    progresso=lambda p: fila.put(
                        ("prog", base + fatia * p * (0.6 if exportar_clipes else 1.0))),
                    cancelar=cancelar)
                cenas = motor.cenas_a_partir_dos_cortes(cortes, nq)
                total_cenas += len(cenas)
                fila.put(("log", "  %d cena(s) encontrada(s)" % len(cenas)))
                if not exportar_clipes:
                    for c in cortes:
                        fila.put(("log", "    corte em %s" % motor.formatar_tempo(c / fps)))
                    continue
                fila.put(("status", "Cortando…  (%d de %d)" % (n, total)))
                pasta = motor.pasta_padrao(video)
                motor.exportar(
                    video, cortes, nq, fps, pasta, rapido,
                    progresso=lambda p: fila.put(("prog", base + fatia * (0.6 + 0.4 * p))),
                    log=lambda m: fila.put(("log", m)), cancelar=cancelar)
                fila.put(("pasta", pasta))
                fila.put(("log", "  ✔ clipes em: " + pasta))
            fila.put(("prog", 1.0))
            if exportar_clipes:
                msg = "Pronto!  %d clipe(s) de %d vídeo(s)" % (total_cenas, total)
            else:
                msg = "Análise concluída:  %d cena(s) em %d vídeo(s)" % (total_cenas, total)
            fila.put(("fim", (msg, OK, True)))
        except motor.Cancelado:
            fila.put(("log", "\nCancelado."))
            fila.put(("fim", ("Cancelado", SUAVE, False)))
        except Exception as e:                                   # noqa
            fila.put(("log", "\n✖ ERRO: %s" % e))
            fila.put(("fim", ("Algo deu errado. Veja os detalhes abaixo.", ERRO, False)))

    def iniciar(exportar_clipes):
        if estado["rodando"]:
            return
        if not arquivos:
            messagebox.showinfo(NOME, "Escolha pelo menos um vídeo primeiro.")
            mostrar(0)
            return
        try:
            dur_min = float(dur_var.get().replace(",", "."))
            if dur_min <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(NOME, "Duração mínima inválida. Use um número, ex.: 0.5")
            return
        mostrar(2)
        estado["rodando"] = True
        estado["pasta"] = None
        cancelar.clear()
        limpar_log()
        barra.set(0)
        lbl_status.configure(text="Começando…", text_color=TEXTO)
        botoes_resultado(True)
        params = (MODOS[modo_var.get()], int(round(sens_var.get())), dur_min,
                  rapido_var.get())
        threading.Thread(target=trabalho,
                         args=(exportar_clipes, params, list(arquivos)),
                         daemon=True).start()

    def sondar():
        try:
            while True:
                tipo, dado = fila.get_nowait()
                if tipo == "log":
                    escrever(dado)
                elif tipo == "prog":
                    barra.set(min(1.0, max(0.0, dado)))
                elif tipo == "status":
                    lbl_status.configure(text=dado, text_color=TEXTO)
                elif tipo == "pasta":
                    estado["pasta"] = dado
                elif tipo == "fim":
                    msg, cor, ok = dado
                    estado["rodando"] = False
                    lbl_status.configure(text=msg, text_color=cor)
                    botoes_resultado(False)
                    atualizar_etapas(2, tudo_ok=ok)
        except queue.Empty:
            pass
        root.after(100, sondar)

    atualizar_lista()
    mostrar(0)
    sondar()
    root.mainloop()


# --------------------------------------------------------------------------
# Linha de comando
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Cortei: detecta cenas e exporta clipes.")
    ap.add_argument("video", nargs="?", help="arquivo de vídeo (sem isso abre a janela)")
    ap.add_argument("--modo", choices=["secos", "transicoes"], default="transicoes")
    ap.add_argument("--sens", type=int, default=5, help="1 (menos cortes) a 10 (mais cortes)")
    ap.add_argument("--min", type=float, default=0.5, dest="dur_min",
                    help="duração mínima de cada cena em segundos")
    ap.add_argument("--so-analisar", action="store_true", help="só mostra os tempos")
    ap.add_argument("--rapido", action="store_true", help="não recodifica")
    ap.add_argument("--saida", help="pasta de saída")
    a = ap.parse_args()

    if not a.video:
        abrir_janela()
        return

    cortes, nq, fps = motor.analisar(a.video, a.modo, a.sens, a.dur_min)
    print("%d cena(s); cortes em:" % (len(cortes) + 1))
    for c in cortes:
        print("  %s  (quadro %d)" % (motor.formatar_tempo(c / fps), c))
    if not a.so_analisar:
        pasta = a.saida or motor.pasta_padrao(a.video)
        motor.exportar(a.video, cortes, nq, fps, pasta, a.rapido, log=print)
        print("Clipes em:", pasta)


if __name__ == "__main__":
    main()
