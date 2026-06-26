"""
directory.py
------------
Estrutura de diretórios em árvore (objetivo 3.1).

Escolha de design: em vez de cada diretório guardar uma LISTA de filhos
(ex: list[DirectoryNode]), cada nó guarda apenas dois ponteiros:

    first_child     -> primeiro filho
    next_sibling    -> próximo irmão (outro filho do mesmo pai)

Essa é a representação clássica "filho mais à esquerda / irmão à direita"
(left-child right-sibling), usada por sistemas de arquivos Unix reais
(e descrita em Silberschatz, "Sistemas Operacionais") para mapear uma
árvore N-ária genérica em uma estrutura binária: qualquer árvore com
qualquer número de filhos por nó pode ser representada com APENAS dois
ponteiros por nó, em vez de um vetor/lista de tamanho variável. Isso
corresponde exatamente à sugestão do enunciado de usar "árvore binária"
para representar um diretório que, conceitualmente, é N-ário.

Cada DirectoryNode é uma ENTRADA DE DIRETÓRIO: ele tem um nome
(entry_name) e aponta para um inode (inode_id) na tabela de inodes
(InodeTable, em filesystem.py). Várias entradas podem apontar para o
mesmo inode_id — isso é exatamente o que torna possível um hard link
(ver Filesystem.ln em filesystem.py).
"""

from __future__ import annotations

from typing import Iterator, Optional


class DirectoryNode:
    """Uma entrada de diretório na árvore (pode ser arquivo OU diretório;
    quem decide isso é o FCB associado ao inode_id)."""

    def __init__(self, entry_name: str, inode_id: int, parent: Optional["DirectoryNode"] = None):
        self.entry_name = entry_name
        self.inode_id = inode_id
        self.parent = parent
        self.first_child: Optional["DirectoryNode"] = None
        self.next_sibling: Optional["DirectoryNode"] = None

    # -- navegação entre filhos -----------------------------------------
    def children(self) -> Iterator["DirectoryNode"]:
        """Percorre a lista encadeada de irmãos a partir do primeiro filho."""
        node = self.first_child
        while node is not None:
            yield node
            node = node.next_sibling

    def child_count(self) -> int:
        return sum(1 for _ in self.children())

    def find_child(self, name: str) -> Optional["DirectoryNode"]:
        for child in self.children():
            if child.entry_name == name:
                return child
        return None

    def add_child(self, node: "DirectoryNode") -> None:
        """Insere `node` como filho deste diretório (no fim da lista de
        irmãos, para preservar a ordem de criação — como `ls` sem
        ordenação mostraria)."""
        node.parent = self
        if self.first_child is None:
            self.first_child = node
            return
        cursor = self.first_child
        while cursor.next_sibling is not None:
            cursor = cursor.next_sibling
        cursor.next_sibling = node

    def remove_child(self, name: str) -> Optional["DirectoryNode"]:
        """Remove e retorna o filho chamado `name`, religando a lista de
        irmãos (igual a remover um nó de uma lista encadeada)."""
        prev = None
        cursor = self.first_child
        while cursor is not None:
            if cursor.entry_name == name:
                if prev is None:
                    self.first_child = cursor.next_sibling
                else:
                    prev.next_sibling = cursor.next_sibling
                cursor.parent = None
                cursor.next_sibling = None
                return cursor
            prev, cursor = cursor, cursor.next_sibling
        return None

    # -- utilidades -----------------------------------------------------
    def path(self) -> str:
        """Reconstrói o caminho absoluto subindo pelos ponteiros `parent`."""
        if self.parent is None:
            return "/"
        parts = []
        node = self
        while node.parent is not None:
            parts.append(node.entry_name)
            node = node.parent
        return "/" + "/".join(reversed(parts))

    def is_root(self) -> bool:
        return self.parent is None

    def __repr__(self) -> str:  # útil para debug
        return f"DirectoryNode({self.path()!r}, inode={self.inode_id})"
