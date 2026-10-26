"""
Ataque de reidentificação estrutural e perturbação de arestas.

Cenário do ataque: o atacante conhece a rede original G (por exemplo,
porque coletou as conexões públicas) e recebe a base publicada P, que é
G com os nomes trocados por números e, opcionalmente, algumas arestas
alteradas.

Dois ataques:
  ataque()            - refinamento de cores: casa cada vértice de G com o
                        único vértice de P que tem a mesma cor. Exato, mas
                        frágil a qualquer alteração nas arestas.
  ataque_propagacao() - parte de poucas pessoas conhecidas e vai
                        identificando as demais pelos vizinhos em comum.
                        Tolera ruído.
"""

import random

import networkx as nx
import numpy as np

from grafos import anonimizar
from refinamento_cores import classes, refinar_juntos


def perturbar(G, fracao, rng=random):
    """Remove fracao * m arestas e adiciona o mesmo número de arestas novas.

    O número de arestas fica igual, mas a estrutura muda. É uma defesa
    simples contra a reidentificação, que custa precisão nos dados.
    """
    H = G.copy()
    m = H.number_of_edges()
    k = int(round(fracao * m))
    if k == 0:
        return H
    removidas = rng.sample(list(H.edges), k)
    H.remove_edges_from(removidas)
    vertices = list(H.nodes)
    adicionadas = 0
    while adicionadas < k:
        u, v = rng.sample(vertices, 2)
        if not H.has_edge(u, v) and not G.has_edge(u, v):
            H.add_edge(u, v)
            adicionadas += 1
    return H


def ataque(G, publicado, segredo):
    """Tenta reidentificar os vértices de G na base publicada.

    Devolve um dicionário com:
      acertos     - vértices casados com o número correto
      erros       - vértices casados com o número errado
      fracao_acertos, fracao_erros
    """
    cores_G, cores_P = (h[-1] for h in refinar_juntos([G, publicado]))
    classes_G = classes(cores_G)
    classes_P = classes(cores_P)
    acertos = erros = 0
    for cor, vs in classes_G.items():
        ws = classes_P.get(cor, [])
        if len(vs) == 1 and len(ws) == 1:
            if segredo[vs[0]] == ws[0]:
                acertos += 1
            else:
                erros += 1
    n = G.number_of_nodes()
    return {
        "acertos": acertos,
        "erros": erros,
        "fracao_acertos": acertos / n,
        "fracao_erros": erros / n,
    }


def ataque_propagacao(G, publicado, segredo, n_sementes=20, limiar=0.5, rng=random):
    """Ataque por propagação, na linha de Narayanan e Shmatikov (2009).

    O refinamento de cores exige vizinhanças idênticas, então qualquer
    ruído o derruba. Este ataque tolera ruído:

      1. O atacante conhece a identidade de poucas pessoas (sementes),
         por exemplo contas famosas. Aqui sorteamos n_sementes.
      2. Cada par (v, w), com v na rede original e w na base publicada,
         recebe uma pontuação: quantos vizinhos de v já identificados
         estão ligados a w, dividido pela raiz do grau de w (para não
         favorecer quem tem muitos amigos).
      3. O par é aceito se w é o melhor candidato para v, v é o melhor
         candidato para w, e o melhor se destaca do segundo
         (excentricidade = (1º - 2º) / desvio padrão >= limiar).
      4. Repete até não aparecerem pares novos.

    As pontuações são calculadas todas de uma vez com matrizes:
    S = A_G[:, identificados] · A_P[imagens, :].

    Devolve as mesmas chaves de ataque(); sementes não contam como acerto.
    """
    nos_G = list(G.nodes)
    idx_G = {v: i for i, v in enumerate(nos_G)}
    nos_P = list(publicado.nodes)
    idx_P = {w: j for j, w in enumerate(nos_P)}
    A_G = nx.to_scipy_sparse_array(G, nodelist=nos_G, format="csr", dtype=np.float32)
    A_P = nx.to_scipy_sparse_array(publicado, nodelist=nos_P, format="csr", dtype=np.float32)
    grau_G = np.maximum(np.asarray(A_G.sum(axis=1)).ravel(), 1)
    grau_P = np.maximum(np.asarray(A_P.sum(axis=1)).ravel(), 1)

    sementes = rng.sample(nos_G, min(n_sementes, len(nos_G)))
    mapa = {idx_G[s]: idx_P[segredo[s]] for s in sementes}

    while True:
        linhas = np.fromiter(mapa.keys(), dtype=np.int64)
        colunas = np.fromiter(mapa.values(), dtype=np.int64)
        S = (A_G[:, linhas] @ A_P[colunas, :]).toarray()
        livres_G = np.ones(len(nos_G), bool)
        livres_G[linhas] = False
        livres_P = np.ones(len(nos_P), bool)
        livres_P[colunas] = False
        S[~livres_G, :] = 0
        S[:, ~livres_P] = 0

        frente = S / np.sqrt(grau_P)[None, :]     # pontuação de w para v
        tras = S / np.sqrt(grau_G)[:, None]       # pontuação de v para w
        melhor_w = frente.argmax(axis=1)
        melhor_v = tras.argmax(axis=0)

        # Excentricidade de cada linha, olhando só candidatos com pontuação > 0.
        positivos = frente > 0
        n_pos = positivos.sum(axis=1)
        top2 = -np.partition(-frente, 1, axis=1)[:, :2]
        soma = frente.sum(axis=1)
        soma2 = (frente ** 2).sum(axis=1)
        media = np.divide(soma, n_pos, out=np.zeros_like(soma), where=n_pos > 0)
        var = np.divide(soma2, n_pos, out=np.zeros_like(soma2), where=n_pos > 0) - media ** 2
        desvio = np.sqrt(np.maximum(var, 0))
        excentricidade = np.divide(top2[:, 0] - top2[:, 1], desvio,
                                   out=np.full_like(desvio, np.inf), where=desvio > 0)

        novos = 0
        for i in np.flatnonzero(livres_G & (top2[:, 0] > 0) & (excentricidade >= limiar)):
            j = melhor_w[i]
            if melhor_v[j] == i:
                mapa[i] = j
                novos += 1
        if novos == 0:
            break

    ids_sementes = {idx_G[s] for s in sementes}
    acertos = erros = 0
    for i, j in mapa.items():
        if i in ids_sementes:
            continue
        if segredo[nos_G[i]] == nos_P[j]:
            acertos += 1
        else:
            erros += 1
    n = G.number_of_nodes()
    return {
        "acertos": acertos,
        "erros": erros,
        "fracao_acertos": acertos / n,
        "fracao_erros": erros / n,
    }


def metricas_utilidade(G, amostra=200, rng=random):
    """Métricas que um pesquisador usaria na rede.

    A distância média é estimada por BFS a partir de uma amostra de
    vértices, para não ficar lento em redes grandes.
    """
    maior = G.subgraph(max(nx.connected_components(G), key=len))
    origens = rng.sample(list(maior.nodes), min(amostra, maior.number_of_nodes()))
    total = cont = 0
    for s in origens:
        for d in nx.single_source_shortest_path_length(maior, s).values():
            if d > 0:
                total += d
                cont += 1
    return {
        "grau_medio": 2 * G.number_of_edges() / G.number_of_nodes(),
        "agrupamento_medio": nx.average_clustering(G),
        "distancia_media": total / cont if cont else float("nan"),
        "componentes": nx.number_connected_components(G),
    }


def publicar(G, fracao_perturbacao=0.0, rng=random):
    """Simula a publicação: perturba as arestas e troca os nomes."""
    perturbado = perturbar(G, fracao_perturbacao, rng)
    publicado, segredo = anonimizar(perturbado, rng)
    return publicado, segredo
