"""
Funções básicas sobre grafos e permutações de vértices.

Um grafo é sempre um nx.Graph simples (sem laços nem arestas múltiplas).
Uma permutação é um dicionário {vértice_antigo: vértice_novo}, bijetor.
"""

import random

import networkx as nx


def permutacao_aleatoria(vertices, rng=random):
    """Sorteia uma bijeção aleatória dos vértices neles mesmos."""
    vertices = list(vertices)
    imagens = vertices[:]
    rng.shuffle(imagens)
    return dict(zip(vertices, imagens))


def aplicar_permutacao(G, pi):
    """Devolve a cópia de G com cada vértice v renomeado para pi[v].

    Em termos de matriz de adjacência, isso é calcular P A P^T.
    """
    H = nx.Graph()
    H.add_nodes_from(pi[v] for v in G.nodes)
    H.add_edges_from((pi[u], pi[v]) for u, v in G.edges)
    return H


def compor(sigma, pi):
    """Composição sigma ∘ pi: primeiro aplica pi, depois sigma."""
    return {v: sigma[pi[v]] for v in pi}


def inversa(pi):
    """Permutação inversa."""
    return {imagem: v for v, imagem in pi.items()}


def eh_isomorfismo(G, H, pi):
    """Confere se pi é um isomorfismo de G em H.

    Precisa ser uma bijeção entre os vértices e levar arestas em arestas
    e não-arestas em não-arestas. Como pi é bijeção e os grafos têm o mesmo
    número de arestas, basta checar que toda aresta de G vira aresta de H.
    """
    if set(pi.keys()) != set(G.nodes) or set(pi.values()) != set(H.nodes):
        return False
    if len(set(pi.values())) != len(pi):
        return False
    if G.number_of_edges() != H.number_of_edges():
        return False
    return all(H.has_edge(pi[u], pi[v]) for u, v in G.edges)


def anonimizar(G, rng=random):
    """Troca os rótulos de G por inteiros aleatórios 0..n-1.

    Devolve (grafo_publicado, segredo), em que segredo[v] é o número
    que a pessoa v recebeu. O grafo publicado é isomorfo a G e o
    segredo é exatamente esse isomorfismo.
    """
    vertices = list(G.nodes)
    numeros = list(range(len(vertices)))
    rng.shuffle(numeros)
    segredo = dict(zip(vertices, numeros))
    return aplicar_permutacao(G, segredo), segredo
