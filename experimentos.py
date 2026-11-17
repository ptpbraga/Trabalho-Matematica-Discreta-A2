"""
Experimentos do trabalho. Gera gráficos e tabelas em resultados/.

  1. Fraude: taxa com que um provador trapaceiro passa em k rodadas,
     comparada com o limite teórico 2^(-k), com intervalo de confiança.
  2. Vulnerabilidade: fração de pessoas com cor única a cada rodada do
     refinamento de cores na rede real.
  3. Privacidade x utilidade: perturbando uma fração das arestas antes
     de publicar, quanto cai a reidentificação (pelos dois ataques) e
     quanto mudam as métricas da rede. Cada nível de ruído é repetido
     várias vezes; a tabela traz média e desvio-padrão, e todas as
     repetições ficam salvas em perturbacao_repeticoes.csv.

Rodar:
  python src/experimentos.py                  # rede ego-Facebook (baixa na 1ª vez)
  python src/experimentos.py --rede sintetica # sem internet
  python src/experimentos.py --rede karate    # rápido, para testar
  python src/experimentos.py --so-graficos    # refaz resumo e figuras a partir dos CSVs

Tudo é reprodutível: as sementes estão fixas (opção --semente) e o
ambiente usado fica registrado em resultados/ambiente.txt.
"""

import argparse
import csv
import math
import os
import platform
import random
import statistics
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import scipy

from dados import carregar_rede
from protocolo_zk import taxa_de_fraude
from refinamento_cores import fracao_unicos, refinar
from reidentificacao import ataque, ataque_propagacao, metricas_utilidade, publicar

PASTA_RESULTADOS = os.path.join(os.path.dirname(__file__), "..", "resultados")
FRACOES = (0, 0.001, 0.01, 0.05, 0.1, 0.2)


def salvar_csv(nome, linhas):
    caminho = os.path.join(PASTA_RESULTADOS, nome)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    print(f"  tabela salva em {caminho}")


def salvar_figura(fig, nome):
    caminho = os.path.join(PASTA_RESULTADOS, nome)
    fig.savefig(caminho, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  figura salva em {caminho}")


def intervalo_wilson(sucessos, n, z=1.96):
    """Intervalo de confiança de 95% (Wilson) para uma proporção."""
    p = sucessos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centro - meia, centro + meia


def experimento_fraude(rodadas_max=10, tentativas=20000):
    """Grafos não isomorfos com mesmo número de vértices e arestas:
    o trapaceiro não tem como conhecer um isomorfismo.
    A semente da rodada k é k."""
    print("\n[1] Taxa de fraude x número de rodadas")
    G0 = nx.cycle_graph(6)  # hexágono
    G1 = nx.disjoint_union(nx.cycle_graph(3), nx.cycle_graph(3))  # dois triângulos
    linhas = []
    for k in range(1, rodadas_max + 1):
        empirica = taxa_de_fraude(G0, G1, k, tentativas, semente=k)
        baixo, alto = intervalo_wilson(round(empirica * tentativas), tentativas)
        linhas.append({"rodadas": k, "tentativas": tentativas, "taxa_empirica": empirica,
                       "ic95_baixo": baixo, "ic95_alto": alto, "teorica": 2 ** -k})
        print(f"  k={k:2d}  empírica={empirica:.4f}  IC95=[{baixo:.4f}, {alto:.4f}]  teórica={2 ** -k:.4f}")
    salvar_csv("fraude.csv", linhas)
    grafico_fraude(linhas)


def grafico_fraude(linhas):
    fig, ax = plt.subplots(figsize=(6, 4))
    ks = [l["rodadas"] for l in linhas]
    emp = [max(l["taxa_empirica"], 1e-4) for l in linhas]
    baixo = [max(l["ic95_baixo"], 1e-5) for l in linhas]
    alto = [l["ic95_alto"] for l in linhas]
    ax.plot(ks, [l["teorica"] for l in linhas], "k--", label="limite teórico $2^{-k}$")
    ax.errorbar(ks, emp, yerr=[np.subtract(emp, baixo), np.subtract(alto, emp)],
                fmt="o-", capsize=3, label="simulação (IC de 95%)")
    ax.set_yscale("log")
    ax.set_xlabel("número de rodadas $k$")
    ax.set_ylabel("chance de o trapaceiro passar")
    ax.legend()
    ax.grid(alpha=0.3)
    salvar_figura(fig, "fraude.png")


def experimento_vulnerabilidade(G):
    print("\n[2] Pessoas com cor única a cada rodada do refinamento")
    inicio = time.time()
    historico = refinar(G)
    print(f"  refinamento estabilizou em {len(historico) - 1} rodadas ({time.time() - inicio:.1f}s)")
    linhas = []
    for r, coloracao in enumerate(historico):
        n_cores = len(set(coloracao.values()))
        f = fracao_unicos(coloracao)
        linhas.append({"rodada": r, "cores": n_cores, "fracao_unicos": f})
        print(f"  rodada {r}: {n_cores} cores, {100 * f:.1f}% com cor única")
    salvar_csv("vulnerabilidade.csv", linhas)
    grafico_vulnerabilidade(linhas)


def grafico_vulnerabilidade(linhas):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([l["rodada"] for l in linhas], [100 * l["fracao_unicos"] for l in linhas], "o-")
    ax.set_xlabel("rodada do refinamento de cores")
    ax.set_ylabel("% de pessoas com cor única")
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3)
    salvar_figura(fig, "vulnerabilidade.png")


def experimento_perturbacao(G, fracoes=FRACOES, repeticoes=20, semente=0):
    """Compara os dois ataques à medida que a base publicada recebe ruído.

    Cada repetição sorteia de novo o ruído, a troca de nomes e as 20
    sementes do ataque por propagação. O gerador de números aleatórios
    começa em `semente`, então rodar de novo dá exatamente os mesmos números.
    """
    print(f"\n[3] Privacidade x utilidade ({repeticoes} repetições por nível)")
    rng = random.Random(semente)
    base = metricas_utilidade(G, rng=random.Random(semente))
    print(f"  rede original: agrupamento {base['agrupamento_medio']:.3f}, "
          f"distância média {base['distancia_media']:.2f}")
    brutas = []
    for f in fracoes:
        inicio = time.time()
        for rep in range(repeticoes):
            publicado, segredo = publicar(G, f, rng)
            rc = ataque(G, publicado, segredo)
            rp = ataque_propagacao(G, publicado, segredo, rng=rng)
            m = metricas_utilidade(publicado, rng=random.Random(semente))
            brutas.append({
                "perturbacao": f, "repeticao": rep,
                "refinamento_aceitos": rc["aceitos"], "refinamento_acertos": rc["acertos"],
                "refinamento_erros": rc["erros"], "refinamento_avaliados": rc["avaliados"],
                "propagacao_aceitos": rp["aceitos"], "propagacao_acertos": rp["acertos"],
                "propagacao_erros": rp["erros"], "propagacao_avaliados": rp["avaliados"],
                "agrupamento_medio": m["agrupamento_medio"], "distancia_media": m["distancia_media"],
            })
        print(f"  {100 * f:5.1f}% das arestas alteradas: {repeticoes} repetições em {time.time() - inicio:.0f}s")
    salvar_csv("perturbacao_repeticoes.csv", brutas)
    linhas = resumir(brutas, base)
    salvar_csv("perturbacao.csv", linhas)
    for l in linhas:
        print(f"  {100 * l['perturbacao']:5.1f}%: refinamento {100 * l['refinamento_reid_media']:5.1f}% "
              f"| propagação {100 * l['propagacao_reid_media']:5.1f}% ± {100 * l['propagacao_reid_dp']:.1f} "
              f"(mediana {100 * l['propagacao_reid_mediana']:.1f}%, precisão {100 * l['propagacao_precisao_agregada']:.1f}%) "
              f"| agrupamento {l['agrupamento_media']:.3f} | distância {l['distancia_media']:.2f}")
    grafico_perturbacao(linhas, brutas)


def resumir(brutas, base):
    """Resumo de cada métrica, por nível de ruído.

    Para a reidentificação: média, desvio-padrão (amostral), mediana,
    mínimo e máximo entre as repetições. A precisão é agregada: soma dos
    acertos dividida pela soma dos pares aceitos em todas as repetições
    (a média das precisões de cada repetição daria peso demais a
    repetições em que quase nada foi aceito).
    """
    def md(xs):
        return statistics.mean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0)

    linhas = []
    for f in sorted({b["perturbacao"] for b in brutas}):
        grupo = [b for b in brutas if b["perturbacao"] == f]
        linha = {"perturbacao": f, "repeticoes": len(grupo)}
        for nome in ("refinamento", "propagacao"):
            reid = [b[f"{nome}_acertos"] / b[f"{nome}_avaliados"] for b in grupo]
            erro = [b[f"{nome}_erros"] / b[f"{nome}_avaliados"] for b in grupo]
            aceitos = sum(b[f"{nome}_aceitos"] for b in grupo)
            acertos = sum(b[f"{nome}_acertos"] for b in grupo)
            linha[f"{nome}_reid_media"], linha[f"{nome}_reid_dp"] = md(reid)
            linha[f"{nome}_reid_mediana"] = statistics.median(reid)
            linha[f"{nome}_reid_min"], linha[f"{nome}_reid_max"] = min(reid), max(reid)
            linha[f"{nome}_erro_media"], linha[f"{nome}_erro_dp"] = md(erro)
            linha[f"{nome}_aceitos_media"] = aceitos / len(grupo)
            linha[f"{nome}_precisao_agregada"] = acertos / aceitos if aceitos else float("nan")
        agr = [b["agrupamento_medio"] for b in grupo]
        dis = [b["distancia_media"] for b in grupo]
        linha["agrupamento_media"], linha["agrupamento_dp"] = md(agr)
        linha["distancia_media"], linha["distancia_dp"] = md(dis)
        linha["distorcao_agrupamento"] = abs(linha["agrupamento_media"] - base["agrupamento_medio"]) / base["agrupamento_medio"]
        linha["distorcao_distancia"] = abs(linha["distancia_media"] - base["distancia_media"]) / base["distancia_media"]
        linhas.append(linha)
    return linhas


def grafico_perturbacao(linhas, brutas=None):
    """À esquerda, cada repetição como um ponto e a mediana como linha;
    à direita, a distorção média das métricas da rede."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    xs = [100 * l["perturbacao"] for l in linhas]
    if brutas:
        for nome, cor, desloc in (("refinamento", "tab:orange", -0.04), ("propagacao", "tab:blue", 0.04)):
            px = [100 * b["perturbacao"] * (1 + desloc) for b in brutas]
            py = [100 * b[f"{nome}_acertos"] / b[f"{nome}_avaliados"] for b in brutas]
            ax1.scatter(px, py, s=10, alpha=0.35, color=cor, linewidths=0)
    ax1.plot(xs, [100 * l["refinamento_reid_mediana"] for l in linhas], "o-", color="tab:orange",
             label="refinamento de cores")
    ax1.plot(xs, [100 * l["propagacao_reid_mediana"] for l in linhas], "s-", color="tab:blue",
             label="propagação (Narayanan e Shmatikov)")
    ax1.set_ylabel("% de pessoas reidentificadas")
    ax1.set_ylim(-3, 105)
    ax1.set_title("Privacidade (pontos: repetições; linha: mediana)")
    ax1.legend(fontsize=8, loc="upper right")
    ax2.plot(xs, [100 * l["distorcao_agrupamento"] for l in linhas], "o-", label="coeficiente de agrupamento")
    ax2.plot(xs, [100 * l["distorcao_distancia"] for l in linhas], "s-", label="distância média")
    ax2.set_ylabel("% de distorção em relação à rede original")
    ax2.set_title("Utilidade perdida")
    ax2.legend(fontsize=8)
    for ax in (ax1, ax2):
        ax.set_xscale("symlog", linthresh=0.1)
        ax.set_xlabel("% das arestas alteradas antes de publicar")
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{x:g}".replace(".", ",") for x in xs])
        ax.set_xlim(-0.03, 1.25 * max(xs))
        ax.grid(alpha=0.3)
    salvar_figura(fig, "privacidade_utilidade.png")


def registrar_ambiente(args, G, segundos):
    caminho = os.path.join(PASTA_RESULTADOS, "ambiente.txt")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(f"rede: {args.rede} ({G.number_of_nodes()} vértices, {G.number_of_edges()} arestas)\n")
        f.write(f"semente do experimento 3: {args.semente}; sementes do experimento 1: k = 1..10\n")
        f.write(f"repetições por nível de ruído: {args.repeticoes}\n")
        f.write(f"python {platform.python_version()} | networkx {nx.__version__} | numpy {np.__version__} "
                f"| scipy {scipy.__version__} | {platform.platform()}\n")
        f.write(f"tempo total: {segundos / 60:.1f} min\n")
    print(f"  ambiente registrado em {caminho}")


def ler_csv(nome):
    with open(os.path.join(PASTA_RESULTADOS, nome), encoding="utf-8") as f:
        return [{k: float(v) for k, v in linha.items()} for linha in csv.DictReader(f)]


def refazer_graficos(rede="facebook", semente=0):
    """Refaz o resumo do experimento 3 e as figuras a partir das tabelas
    já salvas, sem rodar os ataques de novo."""
    grafico_fraude(ler_csv("fraude.csv"))
    grafico_vulnerabilidade(ler_csv("vulnerabilidade.csv"))
    brutas = ler_csv("perturbacao_repeticoes.csv")
    base = metricas_utilidade(carregar_rede(rede), rng=random.Random(semente))
    linhas = resumir(brutas, base)
    salvar_csv("perturbacao.csv", linhas)
    grafico_perturbacao(linhas, brutas)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rede", default="facebook", choices=["facebook", "sintetica", "karate"])
    parser.add_argument("--repeticoes", type=int, default=20)
    parser.add_argument("--semente", type=int, default=0)
    parser.add_argument("--so-graficos", action="store_true",
                        help="só refaz as figuras a partir dos CSVs em resultados/")
    args = parser.parse_args()

    os.makedirs(PASTA_RESULTADOS, exist_ok=True)
    if args.so_graficos:
        refazer_graficos(args.rede, args.semente)
        return
    inicio = time.time()
    G = carregar_rede(args.rede)
    print(f"Rede '{args.rede}': {G.number_of_nodes()} vértices, {G.number_of_edges()} arestas")

    experimento_fraude()
    experimento_vulnerabilidade(G)
    experimento_perturbacao(G, repeticoes=args.repeticoes, semente=args.semente)
    registrar_ambiente(args, G, time.time() - inicio)


if __name__ == "__main__":
    main()
