"""
Refinamento de cores (teste de Weisfeiler-Leman de dimensão 1).

Começa com todos os vértices da mesma cor. A cada rodada, a nova cor de
um vértice é dada pelo par (cor atual, multiconjunto das cores dos
vizinhos). Na primeira rodada isso equivale a separar os vértices pelo
grau. O processo para quando o número de cores deixa de aumentar.

Um vértice que termina com uma cor só dele pode ser reconhecido apenas
pela estrutura da rede: é um vértice reidentificável.

Observação: isso NÃO é uma coloração própria no sentido da Lista 9.
Vizinhos podem terminar com a mesma cor.
"""

from collections import Counter


def refinar(G, max_rodadas=None):
    """Roda o refinamento de cores em G.

    Devolve a lista de colorações, uma por rodada (a posição 0 é a
    coloração inicial, toda igual). Cada coloração é um dicionário
    {vértice: inteiro}. As cores são canônicas: grafos isomorfos
    recebem as mesmas cores nos vértices correspondentes.
    """
    return refinar_juntos([G], max_rodadas)[0]


def refinar_juntos(grafos, max_rodadas=None):
    """Refina vários grafos com uma paleta de cores compartilhada.

    Isso permite comparar cores entre grafos diferentes: se o vértice v
    de G e o vértice w de H terminam com a mesma cor, eles são
    indistinguíveis pelo refinamento.

    Devolve, para cada grafo, a lista de colorações rodada a rodada.
    """
    cores = [{v: 0 for v in G.nodes} for G in grafos]
    historico = [[dict(c)] for c in cores]
    n_cores = 1
    rodada = 0
    while max_rodadas is None or rodada < max_rodadas:
        # Assinatura de cada vértice: sua cor e as cores dos vizinhos.
        assinaturas = []
        for G, c in zip(grafos, cores):
            assinaturas.append({
                v: (c[v], tuple(sorted(c[u] for u in G.neighbors(v))))
                for v in G.nodes
            })
        # Paleta canônica: ordena as assinaturas distintas de todos os grafos.
        paleta = {a: i for i, a in enumerate(sorted(
            {a for ass in assinaturas for a in ass.values()}))}
        novas = [{v: paleta[a] for v, a in ass.items()} for ass in assinaturas]
        rodada += 1
        if len(paleta) == n_cores:
            break  # estabilizou: as classes de cor não mudam mais
        n_cores = len(paleta)
        cores = novas
        for h, c in zip(historico, cores):
            h.append(dict(c))
    return historico


def classes(coloracao):
    """Agrupa os vértices por cor: {cor: [vértices]}."""
    grupos = {}
    for v, cor in coloracao.items():
        grupos.setdefault(cor, []).append(v)
    return grupos


def vertices_unicos(coloracao):
    """Vértices que são os únicos com a sua cor."""
    contagem = Counter(coloracao.values())
    return [v for v, cor in coloracao.items() if contagem[cor] == 1]


def fracao_unicos(coloracao):
    """Fração dos vértices que ficaram com cor única."""
    if not coloracao:
        return 0.0
    return len(vertices_unicos(coloracao)) / len(coloracao)
