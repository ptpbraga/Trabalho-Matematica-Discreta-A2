# Provas de conhecimento zero e a anonimização de redes sociais

Código do trabalho de Matemática Discreta (A2), FGV EMAp, Ciência de Dados e IA.

Davi da Cunha Ribeiro, João Pedro Menezes Barros Dantas de Souza, Mateus de Campos Cavalcanti e Pedro Tolentino Pires Braga.

## A ideia em uma frase

Quando uma plataforma troca os nomes de uma rede social por números, a base publicada é um grafo isomorfo ao original e o segredo é o isomorfismo. Uma prova de conhecimento zero deixa a plataforma provar que a base é legítima sem revelar quem é quem. Mas a estrutura do grafo, sozinha, já permite reidentificar as pessoas.

## O que tem aqui

| Arquivo | O que faz |
|---|---|
| `codigo/src/grafos.py` | Permutações de vértices, isomorfismo e anonimização (trocar nomes por números). |
| `codigo/src/protocolo_zk.py` | Protocolo de conhecimento zero para isomorfismo de grafos (Goldreich, Micali e Wigderson): provador honesto, provador trapaceiro, verificador e simulador. |
| `codigo/src/refinamento_cores.py` | Refinamento de cores (Weisfeiler-Leman de dimensão 1), implementado do zero. |
| `codigo/src/reidentificacao.py` | Os dois ataques de reidentificação, a perturbação de arestas e as métricas de utilidade. |
| `codigo/src/dados.py` | Carrega a rede ego-Facebook do SNAP (baixa na primeira vez). |
| `codigo/src/exemplo_pequeno.py` | Exemplo de 6 vértices, com o refinamento rodada a rodada e o protocolo, para resolver à mão no relatório. |
| `codigo/src/experimentos.py` | Os três experimentos do trabalho, que salvam gráficos e tabelas em `resultados/`. |
| `codigo/testes/test_tudo.py` | Dez testes automáticos. |

## Como rodar

Precisa de Python 3.10 ou mais novo. Os comandos abaixo são rodados de dentro da pasta `codigo`.

```bash
cd codigo
pip install -r requirements.txt

# exemplo pequeno (instantâneo)
python src/exemplo_pequeno.py

# experimentos na rede ego-Facebook (baixa ~1 MB na primeira vez; leva cerca de 30 minutos)
python src/experimentos.py

# mesma coisa com outra semente ou outro número de repetições
python src/experimentos.py --semente 1 --repeticoes 10

# sem internet: rede sintética parecida com uma rede social
python src/experimentos.py --rede sintetica

# refaz o resumo e as figuras a partir das tabelas em resultados/, sem rodar os ataques
python src/experimentos.py --so-graficos

# testes
python -m pytest testes/
```

O script tenta baixar a rede do site do SNAP e, se não conseguir, de uma cópia do mesmo arquivo no GitHub. Se os dois falharem, baixe `facebook_combined.txt.gz` em <https://snap.stanford.edu/data/ego-Facebook.html> e coloque o arquivo em `codigo/dados/`.

## Os experimentos

**1. Fraude.** Um provador que não conhece o isomorfismo só passa numa rodada se adivinhar o desafio, com chance 1/2. O experimento simula 20.000 tentativas para cada número de rodadas k e compara a taxa observada, com intervalo de confiança de 95% (Wilson), com o limite teórico 2^(-k). A semente de cada k é o próprio k. Gera `fraude.png` e `fraude.csv`.

**2. Vulnerabilidade.** Roda o refinamento de cores na rede e mede, a cada rodada, quantas pessoas ficam com uma cor só delas. Quem tem cor única pode ser reconhecido apenas pelo formato das suas conexões. Gera `vulnerabilidade.png` e `vulnerabilidade.csv`.

**3. Privacidade x utilidade.** Antes de publicar, uma fração das arestas é trocada por arestas aleatórias. Medimos quantas pessoas cada ataque ainda reidentifica e quanto as métricas da rede (agrupamento e distância média) se distorcem. Cada nível de ruído é repetido 20 vezes (semente inicial 0). Gera `privacidade_utilidade.png`, `perturbacao.csv` (resumo por nível) e `perturbacao_repeticoes.csv` (todas as 120 repetições).

Métricas de cada ataque, por repetição: **pares aceitos** (pessoas a quem o ataque atribuiu um número), **acertos** (pares aceitos com o número certo), **erros** (os demais) e **pessoas avaliadas** (4.039 no refinamento; 4.019 na propagação, que não ganha crédito pelas 20 sementes). Taxa de reidentificação = acertos / pessoas avaliadas. Precisão = soma dos acertos / soma dos pares aceitos nas 20 repetições. O resumo traz média, desvio-padrão amostral, mediana, mínimo e máximo.

O ambiente usado (versões e sementes) fica registrado em `resultados/ambiente.txt`.

Os dois ataques comparados no experimento 3:

- **Refinamento de cores:** casa cada pessoa com o único vértice publicado que tem a mesma cor. É exato quando a base não tem ruído, mas basta alterar 0,1% das arestas para ele parar de funcionar.
- **Propagação** (versão simplificada do ataque de Narayanan e Shmatikov, 2009): o atacante conhece umas 20 pessoas (as "sementes") e vai identificando as demais pelos vizinhos em comum, aceitando só os pares que se destacam. Tolera bem o ruído.

## Resultados na rede ego-Facebook

A rede tem 4.039 pessoas e 88.234 amizades. As tabelas completas estão em `codigo/resultados/`.

- **Fraude:** a taxa simulada acompanha 2^(-k), e o intervalo de 95% contém o valor teórico nos dez casos: 50,4% com uma rodada, 3,1% com cinco e 0,13% com dez.
- **Vulnerabilidade:** o grau sozinho identifica 0,7% das pessoas; grau mais graus dos amigos identifica 93,2%; o refinamento estabiliza em 93,7%.
- **Ruído** (20 repetições por nível):

| Arestas alteradas | Refinamento | Propagação (média ± d.p.) | Propagação (mediana) | Precisão da propagação | Agrupamento médio |
|---|---|---|---|---|---|
| 0% | 93,7% | 73,4 ± 6,8% | 71,6% | 100% | 0,606 |
| 0,1% | 0% | 72,7 ± 4,6% | 72,1% | 99,9% | 0,601 |
| 1% | 0% | 70,2 ± 8,0% | 72,4% | 98,5% | 0,565 |
| 5% | 0% | 55,1 ± 10,9% | 57,4% | 92,9% | 0,445 |
| 10% | 0% | 32,5 ± 21,2% | 40,5% | 89,4% | 0,349 |
| 20% | 0% | 8,9 ± 15,4% | 0,1% | 77,4% | 0,229 |

Com ruído, o refinamento não aceita nenhum par: o zero é falha da correspondência exata, não anonimato. A partir de 10% de ruído, a propagação vira "tudo ou nada": algumas repetições passam de 40%, outras quase não saem das sementes.

## Referências do código

- Jeremy Kun, *Zero Knowledge Proofs: A Primer* (2016): https://jeremykun.com/2016/07/05/zero-knowledge-proofs-a-primer/
- A. Narayanan e V. Shmatikov, *De-anonymizing Social Networks* (2009): https://arxiv.org/abs/0903.3276
- J. McAuley e J. Leskovec, rede ego-Facebook, SNAP: https://snap.stanford.edu/data/ego-Facebook.html
