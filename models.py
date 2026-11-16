"""Entidades do EvoFit acadêmico: regras do domínio, sem SQL ou dependência do Flask.

POO: Usuario é abstrata; Personal e Aluno usam herança e respondem ao mesmo
método pode_prescrever(). Treino possui ItemTreino: uma relação de composição.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re


class ErroDominio(ValueError):
    """Uma regra violada pode ser apresentada ao usuário com status HTTP seguro."""

    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.status = status


def texto(valor, campo, limite, obrigatorio=True):
    """Validação no servidor complementa o required/maxlength do HTML."""
    if not isinstance(valor, str):
        raise ErroDominio(f'{campo}: informe um texto.')
    valor = valor.strip()
    if (obrigatorio and not valor) or len(valor) > limite:
        raise ErroDominio(f'{campo}: use de {1 if obrigatorio else 0} a {limite} caracteres.')
    return valor


def inteiro(valor, campo, minimo=1, maximo=1_000_000_000):
    # bool é subclasse de int em Python, mas não representa um identificador.
    if isinstance(valor, bool) or not isinstance(valor, int) or not minimo <= valor <= maximo:
        raise ErroDominio(f'{campo}: informe um inteiro entre {minimo} e {maximo}.')
    return valor


def numero(valor, campo, minimo=0, maximo=9999):
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str, Decimal)):
        raise ErroDominio(f'{campo}: informe um número válido.')
    try:
        resultado = Decimal(str(valor))
    except InvalidOperation:
        raise ErroDominio(f'{campo}: informe um número válido.') from None
    if not resultado.is_finite() or not Decimal(str(minimo)) <= resultado <= Decimal(str(maximo)):
        raise ErroDominio(f'{campo}: use um valor entre {minimo} e {maximo}.')
    if resultado.as_tuple().exponent < -2:
        raise ErroDominio(f'{campo}: use no máximo duas casas decimais.')
    return resultado


class Usuario(ABC):
    """A entidade não conhece banco, senha nem detalhes de uma requisição HTTP."""

    def __init__(self, nome, email, objetivo='', id=None, personal_id=None):
        self.id = id
        self.personal_id = personal_id
        self.nome = nome
        self.email = email
        self.objetivo = objetivo

    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, valor):
        self._nome = texto(valor, 'Nome', 150)

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, valor):
        valor = texto(valor, 'E-mail', 200).lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', valor):
            raise ErroDominio('Informe um e-mail válido.')
        self._email = valor

    @property
    def objetivo(self):
        return self._objetivo

    @objetivo.setter
    def objetivo(self, valor):
        self._objetivo = texto(valor, 'Objetivo', 500, False)

    @property
    @abstractmethod
    def papel(self):
        """Cada subclasse informa o papel que pode ser salvo no banco."""

    @abstractmethod
    def pode_prescrever(self):
        """Mesmo método, comportamentos diferentes: polimorfismo."""

    def publico(self):
        return dict(id=self.id, nome=self.nome, email=self.email, papel=self.papel,
                    objetivo=self.objetivo, personal_id=self.personal_id)


class Personal(Usuario):
    @property
    def papel(self):
        return 'personal'

    def pode_prescrever(self):
        return True


class Aluno(Usuario):
    @property
    def papel(self):
        return 'aluno'

    def pode_prescrever(self):
        return False


def usuario_do_banco(linha):
    classe = Personal if linha['papel'] == 'personal' else Aluno
    return classe(linha['nome'], linha['email'], linha['objetivo'], linha['id'], linha['personal_id'])


@dataclass
class Exercicio:
    nome: str
    grupo_muscular: str
    instrucoes: str = ''
    id: int | None = None

    def __post_init__(self):
        self.nome = texto(self.nome, 'Exercício', 150)
        self.grupo_muscular = texto(self.grupo_muscular, 'Grupo muscular', 80)
        self.instrucoes = texto(self.instrucoes, 'Instruções', 1000, False)


@dataclass
class ItemTreino:
    exercicio_id: int
    series: int
    repeticoes: str
    carga: Decimal
    descanso: int

    def __post_init__(self):
        self.exercicio_id = inteiro(self.exercicio_id, 'Exercício')
        self.series = inteiro(self.series, 'Séries', 1, 20)
        self.repeticoes = texto(self.repeticoes, 'Repetições', 30)
        self.carga = numero(self.carga, 'Carga', 0, 1999)
        self.descanso = inteiro(self.descanso, 'Descanso', 0, 1800)


@dataclass
class Treino:
    aluno_id: int
    titulo: str
    exercicios: list[ItemTreino]
    id: int | None = None

    def __post_init__(self):
        self.aluno_id = inteiro(self.aluno_id, 'Aluno')
        self.titulo = texto(self.titulo, 'Título', 150)
        if not isinstance(self.exercicios, list) or not 1 <= len(self.exercicios) <= 30:
            raise ErroDominio('Um treino precisa ter entre 1 e 30 exercícios.')
        if not all(isinstance(item, ItemTreino) for item in self.exercicios):
            raise ErroDominio('A lista de exercícios é inválida.')
        if len({item.exercicio_id for item in self.exercicios}) != len(self.exercicios):
            raise ErroDominio('Inclua cada exercício apenas uma vez no treino.')
