"""
Experimentos do trabalho. Gera gráficos e tabelas em resultados/.

  1. Fraude: taxa com que um provador trapaceiro passa em k rodadas,
     comparada com o limite teórico 2^(-k).
  2. Vulnerabilidade: fração de pessoas com cor única a cada rodada do
     refinamento de cores na rede real.
  3. Privacidade x utilidade: perturbando uma fração das arestas antes
     de publicar, quanto cai a reidentificação (pelos dois ataques) e
     quanto mudam as métricas da rede.

Rodar:
  python src/experimentos.py                 # rede ego-Facebook (baixa na 1ª vez)
  python src/experimentos.py --rede sintetica # sem internet
  python src/experimentos.py --rede karate    # rápido, para testar
"""

import argparse
import csv
import os
import random
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from dados import carregar_rede
from grafos import anonimizar
from protocolo_zk import taxa_de_fraude
from refinamento_cores import fracao_unicos, refinar
from reidentificacao import ataque, ataque_propagacao, metricas_utilidade, publicar

PASTA_RESULTADOS = os.path.join(os.path.dirname(__file__), "..", "resultados")


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


def experimento_fraude(rodadas_max=10, tentativas=20000):
    """Grafos não isomorfos com mesmo número de vértices e arestas:
    o trapaceiro não tem como conhecer um isomorfismo."""
    print("\n[1] Taxa de fraude x número de rodadas")
    G0 = nx.cycle_graph(6)  # hexágono
    G1 = nx.disjoint_union(nx.cycle_graph(3), nx.cycle_graph(3))  # dois triângulos
    linhas = []
    for k in range(1, rodadas_max + 1):
        empirica = taxa_de_fraude(G0, G1, k, tentativas, semente=k)
        linhas.append({"rodadas": k, "taxa_empirica": empirica, "teorica": 2 ** -k})
        print(f"  k={k:2d}  empírica={empirica:.4f}  teórica={2 ** -k:.4f}")
    salvar_csv("fraude.csv", linhas)

    fig, ax = plt.subplots(figsize=(6, 4))
    ks = [l["rodadas"] for l in linhas]
    ax.plot(ks, [l["teorica"] for l in linhas], "k--", label="limite teórico $2^{-k}$")
    ax.plot(ks, [max(l["taxa_empirica"], 1e-4) for l in linhas], "o-", label="simulação")
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

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([l["rodada"] for l in linhas], [100 * l["fracao_unicos"] for l in linhas], "o-")
    ax.set_xlabel("rodada do refinamento de cores")
    ax.set_ylabel("% de pessoas com cor única")
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3)
    salvar_figura(fig, "vulnerabilidade.png")


def experimento_perturbacao(G, fracoes=(0, 0.001, 0.01, 0.05, 0.1, 0.2), repeticoes=3, semente=0):
    """Compara os dois ataques à medida que a base publicada recebe ruído."""
    print("\n[3] Privacidade x utilidade")
    rng = random.Random(semente)
    base = metricas_utilidade(G, rng=random.Random(semente))
    media = lambda xs: sum(xs) / len(xs)
    linhas = []
    for f in fracoes:
        cores, prop, prop_err, agrup, dist = [], [], [], [], []
        for _ in range(repeticoes):
            publicado, segredo = publicar(G, f, rng)
            cores.append(ataque(G, publicado, segredo)["fracao_acertos"])
            r = ataque_propagacao(G, publicado, segredo, rng=rng)
            prop.append(r["fracao_acertos"])
            prop_err.append(r["fracao_erros"])
            m = metricas_utilidade(publicado, rng=random.Random(semente))
            agrup.append(m["agrupamento_medio"])
            dist.append(m["distancia_media"])
        linha = {
            "perturbacao": f,
            "reidentificados_refinamento": media(cores),
            "reidentificados_propagacao": media(prop),
            "erros_propagacao": media(prop_err),
            "agrupamento_medio": media(agrup),
            "distancia_media": media(dist),
            "erro_agrupamento": abs(media(agrup) - base["agrupamento_medio"]) / base["agrupamento_medio"],
            "erro_distancia": abs(media(dist) - base["distancia_media"]) / base["distancia_media"],
        }
        linhas.append(linha)
        print(f"  {100 * f:5.1f}% das arestas alteradas: "
              f"refinamento {100 * linha['reidentificados_refinamento']:5.1f}% | "
              f"propagação {100 * linha['reidentificados_propagacao']:5.1f}% "
              f"(+{100 * linha['erros_propagacao']:.1f}% errados) | "
              f"agrupamento {linha['agrupamento_medio']:.3f} (orig. {base['agrupamento_medio']:.3f}) | "
              f"distância {linha['distancia_media']:.2f} (orig. {base['distancia_media']:.2f})")
    salvar_csv("perturbacao.csv", linhas)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    xs = [100 * l["perturbacao"] for l in linhas]
    ax1.plot(xs, [100 * l["reidentificados_refinamento"] for l in linhas], "o-", label="refinamento de cores")
    ax1.plot(xs, [100 * l["reidentificados_propagacao"] for l in linhas], "s-", label="propagação (Narayanan e Shmatikov)")
    ax1.set_xscale("symlog", linthresh=0.1)
    ax1.set_xlabel("% das arestas alteradas antes de publicar")
    ax1.set_ylabel("% de pessoas reidentificadas")
    ax1.set_ylim(0, 105)
    ax1.set_title("Privacidade")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)
    ax2.plot(xs, [100 * l["erro_agrupamento"] for l in linhas], "o-", label="coeficiente de agrupamento")
    ax2.plot(xs, [100 * l["erro_distancia"] for l in linhas], "s-", label="distância média")
    ax2.set_xscale("symlog", linthresh=0.1)
    ax2.set_xlabel("% das arestas alteradas antes de publicar")
    ax2.set_ylabel("% de distorção em relação à rede original")
    ax2.set_title("Utilidade perdida")
    for ax in (ax1, ax2):
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{x:g}" for x in xs])
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)
    salvar_figura(fig, "privacidade_utilidade.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rede", default="facebook", choices=["facebook", "sintetica", "karate"])
    parser.add_argument("--repeticoes", type=int, default=3)
    args = parser.parse_args()

    os.makedirs(PASTA_RESULTADOS, exist_ok=True)
    G = carregar_rede(args.rede)
    print(f"Rede '{args.rede}': {G.number_of_nodes()} vértices, {G.number_of_edges()} arestas")

    experimento_fraude()
    experimento_vulnerabilidade(G)
    experimento_perturbacao(G, repeticoes=args.repeticoes)


if __name__ == "__main__":
    main()
