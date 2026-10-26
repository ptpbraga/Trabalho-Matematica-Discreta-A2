# Provas de conhecimento zero e a anonimização de redes sociais

Código do trabalho de Matemática Discreta (A2), FGV EMAp, Ciência de Dados e IA.

Davi da Cunha Ribeiro, João Pedro Menezes Barros Dantas de Souza e Pedro Tolentino Pires Braga.

## A ideia em uma frase

Quando uma plataforma troca os nomes de uma rede social por números, a base publicada é um grafo isomorfo ao original e o segredo é o isomorfismo. Uma prova de conhecimento zero deixa a plataforma provar que a base é legítima sem revelar quem é quem. Mas a estrutura do grafo, sozinha, já permite reidentificar as pessoas.

## O que tem aqui

| Arquivo | O que faz |
|---|---|
| `src/grafos.py` | Permutações de vértices, isomorfismo e anonimização (trocar nomes por números). |
| `src/protocolo_zk.py` | Protocolo de conhecimento zero para isomorfismo de grafos (Goldreich, Micali e Wigderson): provador honesto, provador trapaceiro, verificador e simulador. |
| `src/refinamento_cores.py` | Refinamento de cores (Weisfeiler-Leman de dimensão 1), implementado do zero. |
| `src/reidentificacao.py` | Os dois ataques de reidentificação, a perturbação de arestas e as métricas de utilidade. |
| `src/dados.py` | Carrega a rede ego-Facebook do SNAP (baixa na primeira vez). |
| `src/exemplo_pequeno.py` | Exemplo de 6 vértices, com o refinamento rodada a rodada e o protocolo, para resolver à mão no relatório. |
| `src/experimentos.py` | Os três experimentos do trabalho, que salvam gráficos e tabelas em `resultados/`. |
| `testes/test_tudo.py` | Testes automáticos. |

## Como rodar

Precisa de Python 3.10 ou mais novo.

```bash
pip install -r requirements.txt

# exemplo pequeno (instantâneo)
python src/exemplo_pequeno.py

# experimentos na rede ego-Facebook (baixa ~1 MB na primeira vez; leva alguns minutos)
python src/experimentos.py

# sem internet: rede sintética parecida com uma rede social
python src/experimentos.py --rede sintetica

# testes
python -m pytest testes/
```

Se o download automático falhar, baixe `facebook_combined.txt.gz` em <https://snap.stanford.edu/data/ego-Facebook.html> e coloque o arquivo na pasta `dados/`.

## Os experimentos

**1. Fraude.** Um provador que não conhece o isomorfismo só passa numa rodada se adivinhar o desafio, com chance 1/2. O experimento simula 20.000 tentativas para cada número de rodadas k e compara a taxa observada com o limite teórico 2^(-k). Gera `fraude.png` e `fraude.csv`.

**2. Vulnerabilidade.** Roda o refinamento de cores na rede e mede, a cada rodada, quantas pessoas ficam com uma cor só delas. Quem tem cor única pode ser reconhecido apenas pelo formato das suas conexões. Gera `vulnerabilidade.png` e `vulnerabilidade.csv`.

**3. Privacidade x utilidade.** Antes de publicar, uma fração das arestas é trocada por arestas aleatórias. Medimos quantas pessoas cada ataque ainda reidentifica e quanto as métricas da rede (agrupamento e distância média) se distorcem. Gera `privacidade_utilidade.png` e `perturbacao.csv`.

Os dois ataques comparados no experimento 3:

- **Refinamento de cores:** casa cada pessoa com o único vértice publicado que tem a mesma cor. É exato quando a base não tem ruído, mas basta alterar 0,1% das arestas para ele parar de funcionar.
- **Propagação** (versão simplificada do ataque de Narayanan e Shmatikov, 2009): o atacante conhece umas 20 pessoas (as "sementes") e vai identificando as demais pelos vizinhos em comum, aceitando só os pares que se destacam. Tolera bem o ruído.

Num teste com uma rede sintética de 4.000 vértices, a propagação ainda reidentificou cerca de 95% das pessoas com 20% das arestas alteradas, enquanto o coeficiente de agrupamento já tinha se distorcido em mais de 40%. Os números da rede ego-Facebook saem quando vocês rodarem `python src/experimentos.py`.

## Referências do código

- Jeremy Kun, *Zero Knowledge Proofs: A Primer* (2016): https://jeremykun.com/2016/07/05/zero-knowledge-proofs-a-primer/
- A. Narayanan e V. Shmatikov, *De-anonymizing Social Networks* (2009): https://arxiv.org/abs/0903.3276
- J. McAuley e J. Leskovec, rede ego-Facebook, SNAP: https://snap.stanford.edu/data/ego-Facebook.html
