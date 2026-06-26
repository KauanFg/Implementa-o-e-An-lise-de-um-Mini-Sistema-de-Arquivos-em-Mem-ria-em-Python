"""
models.py
---------
Estruturas de dados fundamentais do simulador: o tipo de arquivo e o
File Control Block (FCB), que aqui também desempenha o papel do "inode"
do sistema de arquivos simulado.

Mapeamento conceitual C -> Python (discutido em detalhe no README):
    struct FCB { ... }   em C    ->   @dataclass class FCB   em Python
    ponteiros (FCB*)             ->   referências de objeto (o Python já
                                       trabalha por referência; não existe
                                       aritmética de ponteiros, mas o
                                       comportamento de "apontar para a
                                       mesma estrutura" é idêntico)
    malloc / free                ->   Disk.allocate_blocks / Disk.free_blocks
                                       (alocação e liberação são feitas
                                       explicitamente sobre o vetor que
                                       simula o disco, não sobre a memória
                                       do processo Python)
    enum tipado (typedef enum)   ->   enum.Enum (FileType)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time


class FileType(Enum):
    """Tipo do arquivo armazenado no FCB (campo 'tipo' pedido no enunciado)."""

    DIRECTORY = "diretório"
    NUMERIC = "numérico"
    CHAR = "caractere"
    BINARY = "binário"
    PROGRAM = "programa"

    @property
    def short(self) -> str:
        """Letra usada na primeira coluna de `ls -l`, como no Linux real."""
        return "d" if self is FileType.DIRECTORY else "-"


# Permissões padrão (estilo umask do Linux): rw-r--r-- para arquivos comuns
# e rwxr-xr-x para diretórios (precisam de 'x' para permitir navegação/cd).
PERM_DEFAULT_FILE = 0o644
PERM_DEFAULT_DIR = 0o755

_RWX_CHARS = "rwxrwxrwx"


def perm_to_string(mode: int) -> str:
    """Converte uma permissão numérica (0..0o777) para a string 'rwxr-xr-x'
    exibida pelo `ls -l` real."""
    bits = format(mode & 0o777, "09b")
    return "".join(ch if bit == "1" else "-" for bit, ch in zip(bits, _RWX_CHARS))


def parse_numeric_mode(mode_str: str) -> int:
    """Converte uma string como '754' (chmod numérico) para inteiro 0o754.

    Levanta ValueError se a string não tiver exatamente 3 dígitos octais
    (0-7), replicando a validação que o `chmod` real faz.
    """
    if len(mode_str) != 3 or not all(c in "01234567" for c in mode_str):
        raise ValueError(
            "modo inválido: use 3 dígitos octais, ex: 754 (rwxr-xr--)"
        )
    return int(mode_str, 8)


@dataclass
class FCB:
    """File Control Block — os 'metadados' do arquivo/diretório.

    Em um sistema de arquivos real este bloco fica no disco e é localizado
    via inode_id (número do inode). Aqui ele fica em uma tabela em memória
    (ver InodeTable em filesystem.py), mas seu papel é exatamente o mesmo:
    guardar TUDO sobre o arquivo, exceto o(s) nome(s) pelos quais ele é
    referenciado nos diretórios — por isso múltiplas entradas de diretório
    (hard links) podem compartilhar o mesmo FCB.
    """

    inode_id: int
    name: str                      # nome "de nascimento", usado em stat/debug
    file_type: FileType
    owner: str
    group: str
    permissions: int = PERM_DEFAULT_FILE
    size: int = 0                  # em bytes (== caracteres, neste simulador)
    block_list: list[int] = field(default_factory=list)  # alocação indexada
    link_count: int = 1             # nº de entradas de diretório apontando p/ ele
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)

    # -- helpers -----------------------------------------------------
    def touch_access(self) -> None:
        self.accessed_at = time.time()

    def touch_modify(self) -> None:
        now = time.time()
        self.modified_at = now
        self.accessed_at = now

    def permission_string(self) -> str:
        return self.file_type.short + perm_to_string(self.permissions)

    def is_directory(self) -> bool:
        return self.file_type is FileType.DIRECTORY

    @staticmethod
    def fmt_time(ts: float) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
