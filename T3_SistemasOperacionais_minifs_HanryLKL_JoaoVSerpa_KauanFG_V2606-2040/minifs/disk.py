"""
disk.py
-------
Simulação física do "disco": um vetor de blocos de tamanho fixo, igual
ao `char disco[N_BLOCOS][TAMANHO_BLOCO]` sugerido no enunciado (objetivo
3.4). Cada posição do vetor é um bloco; um bitmap paralelo indica se o
bloco está livre ou ocupado — exatamente a estrutura que o Linux real
usa (block bitmap / free space management) para saber onde pode escrever.

Política de alocação escolhida: ALOCAÇÃO INDEXADA SIMPLIFICADA.
    - Cada arquivo guarda, no seu FCB, a LISTA dos índices de blocos que
      ele usa (FCB.block_list) — é o equivalente a um "bloco de índices"
      embutido diretamente no inode, em vez de em um bloco extra no disco.
    - Os blocos de um arquivo NÃO precisam ser contíguos no disco.
    - Vantagem sobre alocação contígua: não sofre fragmentação externa
      nem exige saber o tamanho final do arquivo de antemão; arquivos
      podem crescer/encolher sem precisar "mover" todo o conteúdo.
    - Vantagem sobre alocação encadeada (linked allocation): acesso
      whatever-aleatório a qualquer bloco é O(1) (basta indexar a lista),
      em vez de precisar seguir um ponteiro bloco-a-bloco.
   (Essa comparação entre os três métodos é retomada no README.)
"""

from __future__ import annotations

from .errors import DiskFullError

BLOCK_SIZE = 32     # bytes por bloco (pequeno de propósito, para que a
                     # fragmentação interna e a divisão em blocos fiquem
                     # visíveis mesmo com arquivos de texto curtos)
TOTAL_BLOCKS = 200   # disco simulado de 200 * 32 = 6400 bytes (~6.25 KB)


class Disk:
    """Disco simulado: vetor de blocos + bitmap de blocos livres/ocupados."""

    def __init__(self, total_blocks: int = TOTAL_BLOCKS, block_size: int = BLOCK_SIZE):
        self.total_blocks = total_blocks
        self.block_size = block_size
        # blocks[i] guarda o conteúdo (str) do bloco i, ou None se vazio.
        self.blocks: list[str | None] = [None] * total_blocks
        # free_bitmap[i] == True  <=>  bloco i está livre.
        self.free_bitmap: list[bool] = [True] * total_blocks

    # -- consultas -----------------------------------------------------
    def free_block_count(self) -> int:
        return sum(self.free_bitmap)

    def used_block_count(self) -> int:
        return self.total_blocks - self.free_block_count()

    def blocks_needed(self, content_length: int) -> int:
        """Quantos blocos são necessários para guardar `content_length`
        bytes (arredondando para cima — assim como o Linux real aloca
        em unidades de bloco, mesmo que o último bloco fique parcialmente
        ocupado; isso é a 'fragmentação interna' clássica)."""
        if content_length == 0:
            return 0
        return -(-content_length // self.block_size)  # ceil division

    # -- alocação / liberação ------------------------------------------
    def allocate_blocks(self, n: int) -> list[int]:
        """Aloca `n` blocos livres (não necessariamente contíguos) e
        retorna a lista de índices alocados. Levanta DiskFullError se
        não houver blocos livres suficientes — simula o ENOSPC real."""
        if n == 0:
            return []
        free_indices = [i for i, free in enumerate(self.free_bitmap) if free]
        if len(free_indices) < n:
            raise DiskFullError(
                f"sem espaço no disco simulado: necessários {n} blocos, "
                f"disponíveis {len(free_indices)} "
                f"(total {self.total_blocks}, em uso {self.used_block_count()})."
            )
        chosen = free_indices[:n]
        for i in chosen:
            self.free_bitmap[i] = False
        return chosen

    def free_blocks(self, indices: list[int]) -> None:
        for i in indices:
            self.free_bitmap[i] = True
            self.blocks[i] = None

    # -- leitura / escrita -----------------------------------------------
    def write_block(self, index: int, data: str) -> None:
        self.blocks[index] = data

    def read_block(self, index: int) -> str:
        return self.blocks[index] or ""

    def write_content(self, old_blocks: list[int], content: str) -> list[int]:
        """Substitui o conteúdo de um arquivo: libera os blocos antigos,
        aloca blocos novos para `content` e grava os pedaços (chunks).
        Retorna a nova lista de índices de blocos (a nova "tabela de
        índices" a ser guardada no FCB do arquivo)."""
        self.free_blocks(old_blocks)
        n_needed = self.blocks_needed(len(content))
        new_blocks = self.allocate_blocks(n_needed)
        for pos, block_idx in enumerate(new_blocks):
            start = pos * self.block_size
            chunk = content[start:start + self.block_size]
            self.write_block(block_idx, chunk)
        return new_blocks

    def read_content(self, block_list: list[int]) -> str:
        return "".join(self.read_block(i) for i in block_list)

    # -- visualização ------------------------------------------------
    def usage_map(self, width: int = 50) -> str:
        """Mapa visual de ocupação do disco, um caractere por bloco:
        'X' = ocupado, '.' = livre. Quebra em linhas de `width` blocos."""
        chars = ["." if free else "X" for free in self.free_bitmap]
        lines = ["".join(chars[i:i + width]) for i in range(0, len(chars), width)]
        return "\n".join(lines)

    def summary(self) -> str:
        used = self.used_block_count()
        free = self.free_block_count()
        pct = (used / self.total_blocks) * 100 if self.total_blocks else 0
        return (
            f"Disco simulado: {self.total_blocks} blocos x {self.block_size} bytes "
            f"= {self.total_blocks * self.block_size} bytes totais\n"
            f"Em uso: {used} blocos ({used * self.block_size} bytes, {pct:.1f}%)\n"
            f"Livres: {free} blocos ({free * self.block_size} bytes)"
        )
