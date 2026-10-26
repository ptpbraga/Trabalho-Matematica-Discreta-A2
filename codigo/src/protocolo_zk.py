"""
Prova de conhecimento zero para isomorfismo de grafos
(Goldreich, Micali e Wigderson).

Cenário: G0 e G1 são públicos. O provador conhece phi, um isomorfismo
de G0 em G1 (ou seja, phi(G0) = G1), e quer convencer o verificador
disso sem revelar phi.

Uma rodada:
  1. O provador sorteia uma permutação sigma e envia H = sigma(G1).
  2. O verificador sorteia um desafio c em {0, 1}.
  3. O provador responde com um isomorfismo rho de G_c em H:
       c = 1  ->  rho = sigma
       c = 0  ->  rho = sigma ∘ phi
  4. O verificador aceita se rho de fato leva G_c em H.

Repetindo k rodadas, um provador que não conhece phi passa com
probabilidade no máximo 2^(-k).
"""

import random
from dataclasses import dataclass, field

from grafos import (
    aplicar_permutacao,
    compor,
    eh_isomorfismo,
    permutacao_aleatoria,
)


class Provador:
    """Provador honesto: conhece o isomorfismo phi de G0 em G1."""

    def __init__(self, G0, G1, phi, rng=None):
        self.G0, self.G1, self.phi = G0, G1, phi
        self.rng = rng or random.Random()
        self._sigma = None

    def compromisso(self):
        """Passo 1: envia uma cópia embaralhada de G1."""
        self._sigma = permutacao_aleatoria(self.G1.nodes, self.rng)
        return aplicar_permutacao(self.G1, self._sigma)

    def resposta(self, desafio):
        """Passo 3: entrega um isomorfismo de G_desafio na cópia H."""
        if desafio == 1:
            return self._sigma
        return compor(self._sigma, self.phi)


class ProvadorTrapaceiro:
    """Provador que NÃO conhece o isomorfismo.

    A melhor estratégia possível: chutar o desafio antes. Ele sorteia b,
    embaralha G_b e torce para o verificador pedir c = b. Se pedir o
    outro grafo, ele não tem como responder.
    """

    def __init__(self, G0, G1, rng=None):
        self.grafos = (G0, G1)
        self.rng = rng or random.Random()
        self._aposta = None
        self._sigma = None

    def compromisso(self):
        self._aposta = self.rng.randint(0, 1)
        G = self.grafos[self._aposta]
        self._sigma = permutacao_aleatoria(G.nodes, self.rng)
        return aplicar_permutacao(G, self._sigma)

    def resposta(self, desafio):
        if desafio == self._aposta:
            return self._sigma
        # Não sabe responder: devolve qualquer coisa (vai ser rejeitado).
        return self._sigma


class Verificador:
    def __init__(self, G0, G1, rng=None):
        self.grafos = (G0, G1)
        self.rng = rng or random.Random()
        self._H = None
        self._desafio = None

    def receber_compromisso(self, H):
        self._H = H

    def desafio(self):
        self._desafio = self.rng.randint(0, 1)
        return self._desafio

    def aceita(self, rho):
        G = self.grafos[self._desafio]
        return eh_isomorfismo(G, self._H, rho)


@dataclass
class Rodada:
    H: object
    desafio: int
    resposta: dict
    aceita: bool


@dataclass
class Transcricao:
    rodadas: list = field(default_factory=list)

    @property
    def aceito(self):
        return all(r.aceita for r in self.rodadas)


def executar_protocolo(provador, verificador, k):
    """Roda k rodadas e devolve a transcrição completa.

    O verificador rejeita na primeira rodada que falhar.
    """
    transcricao = Transcricao()
    for _ in range(k):
        H = provador.compromisso()
        verificador.receber_compromisso(H)
        c = verificador.desafio()
        rho = provador.resposta(c)
        ok = verificador.aceita(rho)
        transcricao.rodadas.append(Rodada(H, c, rho, ok))
        if not ok:
            break
    return transcricao


def simulador(G0, G1, k, rng=None):
    """Produz transcrições aceitas SEM conhecer o isomorfismo.

    Ideia da prova de conhecimento zero: o simulador sorteia o desafio c
    primeiro, embaralha G_c com uma permutação aleatória rho e escreve
    (H = rho(G_c), c, rho). Se G0 e G1 são isomorfos, essas transcrições
    têm exatamente a mesma distribuição das conversas reais. Logo, o
    verificador não aprende nada que ele mesmo não pudesse gerar sozinho.
    """
    rng = rng or random.Random()
    transcricao = Transcricao()
    for _ in range(k):
        c = rng.randint(0, 1)
        G = (G0, G1)[c]
        rho = permutacao_aleatoria(G.nodes, rng)
        H = aplicar_permutacao(G, rho)
        transcricao.rodadas.append(Rodada(H, c, rho, True))
    return transcricao


def taxa_de_fraude(G0, G1, k, tentativas=2000, semente=0):
    """Fração de vezes em que um trapaceiro passa por k rodadas."""
    rng = random.Random(semente)
    passou = 0
    for _ in range(tentativas):
        p = ProvadorTrapaceiro(G0, G1, random.Random(rng.random()))
        v = Verificador(G0, G1, random.Random(rng.random()))
        if executar_protocolo(p, v, k).aceito:
            passou += 1
    return passou / tentativas
