"""
errors.py
---------
Exceções customizadas do mini-sistema de arquivos.

Centralizar os erros em uma hierarquia própria (em vez de usar Exception
genérica) é equivalente, em espírito, ao que faríamos em C retornando
códigos de erro (errno) a partir das chamadas de sistema simuladas:
cada operação tem uma falha "esperada" e bem identificada, que o shell
(interface de linha de comando) sabe transformar em uma mensagem clara
para o usuário, sem derrubar o programa.
"""


class FSError(Exception):
    """Classe base para todos os erros do sistema de arquivos simulado."""


class NotFoundError(FSError):
    """Arquivo ou diretório não encontrado (equivalente a ENOENT)."""


class AlreadyExistsError(FSError):
    """Já existe uma entrada com esse nome no diretório (equivalente a EEXIST)."""


class PermissionDeniedError(FSError):
    """Usuário atual não tem permissão RWX necessária (equivalente a EACCES)."""


class NotADirectoryError_(FSError):
    """Operação que exige diretório foi aplicada a um arquivo (ENOTDIR)."""


class IsADirectoryError_(FSError):
    """Operação que exige arquivo foi aplicada a um diretório (EISDIR)."""


class DirectoryNotEmptyError(FSError):
    """Tentativa de remover diretório que ainda contém entradas (ENOTEMPTY)."""


class InvalidNameError(FSError):
    """Nome de arquivo/diretório inválido (ex: contém '/', vazio, '.', '..')."""


class InvalidModeError(FSError):
    """Modo de permissão inválido passado para chmod."""


class DiskFullError(FSError):
    """Não há blocos livres suficientes no disco simulado (ENOSPC)."""
