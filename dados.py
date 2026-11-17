"""
Carregamento da rede ego-Facebook (repositório SNAP, Stanford).

https://snap.stanford.edu/data/ego-Facebook.html

O arquivo facebook_combined.txt.gz tem uma aresta por linha
("u v"), 4.039 vértices e 88.234 arestas. Se ele não estiver em
dados/, o script tenta baixar do SNAP e, se falhar, de uma cópia no GitHub.
"""

import gzip
import os
import urllib.request

import networkx as nx

URLS = [
    "https://snap.stanford.edu/data/facebook_combined.txt.gz",
    # cópia do mesmo arquivo no repositório do livro Think Complexity
    "https://raw.githubusercontent.com/AllenDowney/ThinkComplexity2/master/data/facebook_combined.txt.gz",
]
PASTA = os.path.join(os.path.dirname(__file__), "..", "dados")
ARQUIVO = os.path.join(PASTA, "facebook_combined.txt.gz")


def baixar_facebook():
    os.makedirs(PASTA, exist_ok=True)
    if os.path.exists(ARQUIVO):
        return ARQUIVO
    for url in URLS:
        try:
            print(f"Baixando {url} ...")
            urllib.request.urlretrieve(url, ARQUIVO)
            return ARQUIVO
        except OSError as erro:
            if os.path.exists(ARQUIVO):
                os.remove(ARQUIVO)  # não deixa arquivo pela metade
            print(f"  falhou ({erro}), tentando o próximo endereço")
    raise RuntimeError("Não consegui baixar a rede. Coloque facebook_combined.txt.gz em dados/.")


def carregar_facebook():
    """Devolve a rede ego-Facebook como nx.Graph."""
    caminho = baixar_facebook()
    with gzip.open(caminho, "rt") as f:
        return nx.parse_edgelist(f, nodetype=int)


def carregar_rede(nome="facebook"):
    """Carrega uma rede pelo nome.

    'facebook' - ego-Facebook do SNAP (precisa de internet na 1ª vez)
    'karate'   - clube de karatê de Zachary (vem com o NetworkX)
    'sintetica'- rede aleatória com agrupamento parecido com rede social,
                 útil para testar sem baixar nada
    """
    if nome == "facebook":
        return carregar_facebook()
    if nome == "karate":
        return nx.karate_club_graph()
    if nome == "sintetica":
        return nx.powerlaw_cluster_graph(4000, 20, 0.6, seed=42)
    raise ValueError(f"rede desconhecida: {nome}")
