"""Testes automáticos. Rodar com:  python -m pytest testes/"""

import os
import random
import sys

import networkx as nx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from grafos import anonimizar, aplicar_permutacao, eh_isomorfismo, inversa, permutacao_aleatoria
from protocolo_zk import (
    Provador,
    ProvadorTrapaceiro,
    Verificador,
    executar_protocolo,
    simulador,
    taxa_de_fraude,
)
from refinamento_cores import fracao_unicos, refinar, refinar_juntos, vertices_unicos
from reidentificacao import ataque, publicar


def test_permutacao_gera_grafo_isomorfo():
    G = nx.petersen_graph()
    pi = permutacao_aleatoria(G.nodes, random.Random(0))
    H = aplicar_permutacao(G, pi)
    assert eh_isomorfismo(G, H, pi)
    assert eh_isomorfismo(H, G, inversa(pi))


def test_completude_provador_honesto_sempre_passa():
    G0 = nx.karate_club_graph()
    for s in range(20):
        G1, phi = anonimizar(G0, random.Random(s))
        t = executar_protocolo(Provador(G0, G1, phi, random.Random(s)),
                               Verificador(G0, G1, random.Random(s + 100)), 30)
        assert t.aceito and len(t.rodadas) == 30


def test_correcao_trapaceiro_perto_de_meio_por_rodada():
    G0 = nx.cycle_graph(6)
    G1 = nx.disjoint_union(nx.cycle_graph(3), nx.cycle_graph(3))
    taxa = taxa_de_fraude(G0, G1, k=1, tentativas=4000)
    assert 0.45 < taxa < 0.55
    assert taxa_de_fraude(G0, G1, k=10, tentativas=4000) < 0.01


def test_simulador_gera_transcricoes_validas():
    G0 = nx.karate_club_graph()
    G1, _ = anonimizar(G0, random.Random(1))
    t = simulador(G0, G1, 20, random.Random(2))
    for r in t.rodadas:
        assert eh_isomorfismo((G0, G1)[r.desafio], r.H, r.resposta)


def test_exemplo_pequeno():
    G = nx.Graph([(1, 2), (1, 3), (2, 3), (1, 4), (4, 5), (5, 6)])
    final = refinar(G)[-1]
    assert sorted(vertices_unicos(final)) == [1, 4, 5, 6]
    assert final[2] == final[3]


def test_refinamento_concorda_com_networkx():
    """Grafos com o mesmo hash WL do NetworkX têm as mesmas classes de cor."""
    G = nx.karate_club_graph()
    H, _ = anonimizar(G, random.Random(3))
    cg, ch = (h[-1] for h in refinar_juntos([G, H]))
    assert sorted(cg.values()) == sorted(ch.values())
    assert nx.weisfeiler_lehman_graph_hash(G, iterations=5) == nx.weisfeiler_lehman_graph_hash(H, iterations=5)


def test_grafo_regular_nao_separa_nada():
    # Em grafos regulares o refinamento não distingue ninguém.
    assert fracao_unicos(refinar(nx.petersen_graph())[-1]) == 0


def test_ataque_sem_perturbacao_nao_erra():
    G = nx.karate_club_graph()
    publicado, segredo = publicar(G, 0.0, random.Random(4))
    r = ataque(G, publicado, segredo)
    assert r["erros"] == 0
    assert r["fracao_acertos"] == fracao_unicos(refinar(G)[-1])


def test_propagacao_tolera_ruido():
    G = nx.powerlaw_cluster_graph(600, 8, 0.5, seed=1)
    rng = random.Random(5)
    publicado, segredo = publicar(G, 0.05, rng)
    from reidentificacao import ataque_propagacao
    r = ataque_propagacao(G, publicado, segredo, n_sementes=10, rng=rng)
    assert r["fracao_acertos"] > 0.5
    assert r["fracao_erros"] < r["fracao_acertos"]
    # O refinamento exato não aguenta o mesmo ruído.
    assert ataque(G, publicado, segredo)["fracao_acertos"] < r["fracao_acertos"]
