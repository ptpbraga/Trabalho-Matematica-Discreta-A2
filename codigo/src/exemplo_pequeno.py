"""
Exemplo pequeno para resolver à mão no trabalho.

Grafo com 6 vértices: um triângulo 1-2-3 e um caminho 1-4-5-6.
Mostra o refinamento de cores rodada por rodada e uma execução curta
do protocolo de conhecimento zero.

Rodar:  python src/exemplo_pequeno.py
"""

import random

import networkx as nx

from grafos import anonimizar
from protocolo_zk import Provador, Verificador, executar_protocolo
from refinamento_cores import classes, refinar, vertices_unicos


def grafo_exemplo():
    G = nx.Graph()
    G.add_edges_from([(1, 2), (1, 3), (2, 3), (1, 4), (4, 5), (5, 6)])
    return G


def mostrar_refinamento(G):
    print("=== Refinamento de cores ===")
    for rodada, coloracao in enumerate(refinar(G)):
        grupos = sorted(sorted(vs) for vs in classes(coloracao).values())
        print(f"Rodada {rodada}: {len(grupos)} cor(es) -> {grupos}")
    final = refinar(G)[-1]
    print(f"Vértices com cor única (reidentificáveis): {sorted(vertices_unicos(final))}")
    print()


def mostrar_protocolo(G, rodadas=4, semente=1):
    print("=== Protocolo de conhecimento zero (isomorfismo) ===")
    rng = random.Random(semente)
    G1, phi = anonimizar(G, rng)  # G0 = G original, G1 = versão publicada
    print(f"Base publicada G1 (arestas): {sorted(tuple(sorted(e)) for e in G1.edges)}")
    print(f"Segredo phi (pessoa -> número), só o provador conhece: {phi}")
    p = Provador(G, G1, phi, random.Random(semente + 1))
    v = Verificador(G, G1, random.Random(semente + 2))
    t = executar_protocolo(p, v, rodadas)
    for i, r in enumerate(t.rodadas, 1):
        print(f"Rodada {i}: H = {sorted(tuple(sorted(e)) for e in r.H.edges)}")
        print(f"          desafio = G{r.desafio}, resposta = {r.resposta}, aceita = {r.aceita}")
    print(f"Resultado: {'ACEITO' if t.aceito else 'REJEITADO'}")


if __name__ == "__main__":
    G = grafo_exemplo()
    mostrar_refinamento(G)
    mostrar_protocolo(G)
