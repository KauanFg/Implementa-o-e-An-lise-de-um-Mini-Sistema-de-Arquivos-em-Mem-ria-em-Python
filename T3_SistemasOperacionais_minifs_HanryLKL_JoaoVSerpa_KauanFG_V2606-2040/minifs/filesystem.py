"""
filesystem.py
-------------
A classe FileSystem orquestra os três pilares do simulador:

    1. Uma tabela de inodes  (inode_id -> FCB)       — "quem é o arquivo"
    2. Um disco simulado      (Disk)                  — "onde estão os bytes"
    3. Uma árvore de diretórios (DirectoryNode)        — "como o usuário acha o arquivo"

Separar (1) de (3) é o que torna hard links possíveis: o NOME mora na
árvore (DirectoryNode.entry_name), os METADADOS e o CONTEÚDO moram no
inode (FCB) — exatamente como em um sistema de arquivos Unix real, onde
`ls -i` mostra que dois nomes diferentes podem ter o mesmo número de inode.

Cada método público (mkdir, touch, write, read, cp, mv, rm, chmod, ...)
funciona como uma "chamada de sistema" simulada: resolve o(s) caminho(s),
verifica permissões RWX para o usuário atual e só então modifica o
estado, levantando uma exceção de errors.py em caso de erro — nunca
deixando o programa quebrar com uma stack trace para o usuário final.
"""

from __future__ import annotations

from typing import Optional

from .directory import DirectoryNode
from .disk import Disk
from .models import FCB, FileType, PERM_DEFAULT_DIR, PERM_DEFAULT_FILE, parse_numeric_mode
from .errors import (
    AlreadyExistsError,
    DirectoryNotEmptyError,
    InvalidModeError,
    InvalidNameError,
    IsADirectoryError_,
    NotADirectoryError_,
    NotFoundError,
    PermissionDeniedError,
)

# Caracteres proibidos em nomes (simplificação realista: bastaria proibir
# '/', mas também bloqueamos espaço e alguns símbolos para evitar ambiguidade
# na hora de fazer o parse dos comandos do shell).
_INVALID_NAME_CHARS = set('/\\:*?"<>|')

# Usuários e grupos pré-cadastrados para os testes de permissão. Em um SO
# real isso viria de /etc/passwd e /etc/group; aqui, para manter o foco
# do trabalho no sistema de arquivos, usamos um dicionário fixo simples,
# como o enunciado sugere ("uma variável global simples").
DEFAULT_USERS = {
    "kauan": {"group": "alunos", "home": "/home/kauan"},
    "visitante": {"group": "externos", "home": "/home/visitante"},
}


def _validate_name(name: str) -> None:
    if not name or name in (".", "..") or any(c in _INVALID_NAME_CHARS for c in name):
        raise InvalidNameError(f"nome inválido: {name!r}")


class FileSystem:
    """Sistema de arquivos simulado em memória, com um único disco e uma
    única árvore de diretórios compartilhados por todos os usuários
    cadastrados (assim como um disco real compartilhado por todo o SO)."""

    def __init__(self, disk: Optional[Disk] = None):
        self.disk = disk or Disk()
        self.inodes: dict[int, FCB] = {}
        self._next_inode_id = 1
        self.users = dict(DEFAULT_USERS)
        self.current_user = "kauan"

        # cria o inode e o nó raiz "/"
        root_inode = self._new_inode("/", FileType.DIRECTORY, owner="root", group="root",
                                      permissions=PERM_DEFAULT_DIR)
        self.root = DirectoryNode("/", root_inode.inode_id)
        self.cwd = self.root

        # estrutura inicial mínima, só para o simulador não nascer vazio
        self.mkdir("home", at=self.root)
        home = self.root.find_child("home")
        for username, info in self.users.items():
            self.mkdir(username, at=home, owner_override=username)
        self.cwd = home.find_child("kauan")

    # ================================================================
    # Helpers internos
    # ================================================================
    def _new_inode(self, name: str, ftype: FileType, owner: str, group: str,
                   permissions: int) -> FCB:
        inode_id = self._next_inode_id
        self._next_inode_id += 1
        fcb = FCB(inode_id=inode_id, name=name, file_type=ftype, owner=owner,
                  group=group, permissions=permissions)
        self.inodes[inode_id] = fcb
        return fcb

    def _fcb(self, node: DirectoryNode) -> FCB:
        return self.inodes[node.inode_id]

    def _current_group(self) -> str:
        return self.users[self.current_user]["group"]

    def check_permission(self, fcb: FCB, action: str) -> bool:
        """Verifica permissão RWX do usuário atual sobre `fcb`, seguindo
        exatamente a regra de três classes do enunciado (3.3): primeiro
        tenta como 'owner', senão como 'group', senão cai em 'public'.
        `action` é um de 'r', 'w', 'x'."""
        if self.current_user == fcb.owner:
            shift = 6
        elif self._current_group() == fcb.group:
            shift = 3
        else:
            shift = 0
        bit = {"r": 4, "w": 2, "x": 1}[action]
        return bool((fcb.permissions >> shift) & bit)

    def _require(self, fcb: FCB, action: str, target_desc: str) -> None:
        if not self.check_permission(fcb, action):
            raise PermissionDeniedError(
                f"permissão negada: usuário '{self.current_user}' não tem "
                f"permissão de {action.upper()} sobre {target_desc!r} "
                f"(permissões atuais: {fcb.permission_string()}, "
                f"dono: {fcb.owner})."
            )

    def resolve(self, path: str, start: Optional[DirectoryNode] = None) -> DirectoryNode:
        """Resolve uma string de caminho (absoluto ou relativo) para o
        DirectoryNode correspondente, navegando pela árvore um componente
        por vez — análogo ao algoritmo real de lookup de caminho."""
        if path == "":
            return self.cwd
        if path == "~":
            return self.root.find_child("home").find_child(self.current_user)

        node = self.root if path.startswith("/") else (start or self.cwd)
        parts = [p for p in path.split("/") if p not in ("", ".")]
        for part in parts:
            if part == "..":
                node = node.parent or self.root
                continue
            fcb = self._fcb(node)
            if not fcb.is_directory():
                raise NotADirectoryError_(f"{node.path()!r} não é um diretório")
            self._require(fcb, "x", node.path())  # precisa de 'x' p/ atravessar o diretório
            child = node.find_child(part)
            if child is None:
                raise NotFoundError(f"não encontrado: {path!r} (em {node.path()})")
            node = child
        return node

    def resolve_parent_and_name(self, path: str) -> tuple[DirectoryNode, str]:
        """Separa um caminho em (diretório-pai, nome-final), útil para
        operações como mkdir/touch/rm que precisam do pai para checar
        permissão de escrita e inserir/remover a entrada."""
        path = path.rstrip("/")
        if "/" not in path:
            return self.cwd, path
        parent_path, name = path.rsplit("/", 1)
        parent = self.resolve(parent_path if parent_path else "/")
        return parent, name

    # ================================================================
    # 3.1 — Diretórios: mkdir / cd / pwd
    # ================================================================
    def mkdir(self, path: str, at: Optional[DirectoryNode] = None,
               owner_override: Optional[str] = None) -> DirectoryNode:
        parent, name = (at, path) if at is not None else self.resolve_parent_and_name(path)
        _validate_name(name)
        parent_fcb = self._fcb(parent)
        if at is None:  # pulamos a checagem na inicialização do FS (bootstrap)
            self._require(parent_fcb, "w", parent.path())
        if parent.find_child(name) is not None:
            raise AlreadyExistsError(f"já existe uma entrada chamada {name!r} em {parent.path()}")

        owner = owner_override or self.current_user
        group = self.users.get(owner, {"group": self._current_group()})["group"]
        fcb = self._new_inode(name, FileType.DIRECTORY, owner=owner, group=group,
                               permissions=PERM_DEFAULT_DIR)
        node = DirectoryNode(name, fcb.inode_id)
        parent.add_child(node)
        parent_fcb.touch_modify()
        return node

    def cd(self, path: str) -> None:
        node = self.resolve(path)
        fcb = self._fcb(node)
        if not fcb.is_directory():
            raise NotADirectoryError_(f"{path!r} não é um diretório")
        self.cwd = node

    def pwd(self) -> str:
        return self.cwd.path()

    # ================================================================
    # 3.2 — Arquivos: touch / write (echo) / read (cat) / cp / mv / rm
    # ================================================================
    def touch(self, path: str, file_type: FileType = FileType.CHAR) -> FCB:
        parent, name = self.resolve_parent_and_name(path)
        parent_fcb = self._fcb(parent)
        existing = parent.find_child(name)
        if existing is not None:
            fcb = self._fcb(existing)
            fcb.touch_access()  # `touch` em arquivo existente só atualiza data de acesso
            return fcb
        _validate_name(name)
        self._require(parent_fcb, "w", parent.path())
        fcb = self._new_inode(name, file_type, owner=self.current_user,
                               group=self._current_group(), permissions=PERM_DEFAULT_FILE)
        parent.add_child(DirectoryNode(name, fcb.inode_id))
        parent_fcb.touch_modify()
        return fcb

    def write(self, path: str, content: str, append: bool = False,
              file_type: FileType = FileType.CHAR) -> FCB:
        """Implementa `echo "texto" > arquivo` (append=False) e
        `echo "texto" >> arquivo` (append=True). Cria o arquivo se ele
        ainda não existir, exatamente como o bash real faz."""
        parent, name = self.resolve_parent_and_name(path)
        node = parent.find_child(name)
        if node is None:
            fcb = self.touch(path, file_type=file_type)
        else:
            fcb = self._fcb(node)
            if fcb.is_directory():
                raise IsADirectoryError_(f"{path!r} é um diretório")
            self._require(fcb, "w", path)

        old_content = self.disk.read_content(fcb.block_list) if append else ""
        new_content = old_content + content if append else content
        fcb.block_list = self.disk.write_content(fcb.block_list, new_content)
        fcb.size = len(new_content)
        fcb.touch_modify()
        return fcb

    def read(self, path: str) -> str:
        """Implementa `cat arquivo`."""
        node = self.resolve(path)
        fcb = self._fcb(node)
        if fcb.is_directory():
            raise IsADirectoryError_(f"{path!r} é um diretório, use 'ls'")
        self._require(fcb, "r", path)
        fcb.touch_access()
        return self.disk.read_content(fcb.block_list)

    def cp(self, src: str, dst: str) -> FCB:
        src_node = self.resolve(src)
        src_fcb = self._fcb(src_node)
        if src_fcb.is_directory():
            raise IsADirectoryError_(f"{src!r} é um diretório; cp de diretórios não é suportado")
        self._require(src_fcb, "r", src)

        dst_parent, dst_name = self.resolve_parent_and_name(dst)
        dst_parent_fcb = self._fcb(dst_parent)
        self._require(dst_parent_fcb, "w", dst_parent.path())
        if dst_parent.find_child(dst_name) is not None:
            raise AlreadyExistsError(f"já existe {dst_name!r} em {dst_parent.path()}")

        # cp cria um INODE NOVO (independente) com o mesmo conteúdo — por
        # isso, diferente de mv, alterar a cópia não afeta o original.
        content = self.disk.read_content(src_fcb.block_list)
        new_fcb = self._new_inode(dst_name, src_fcb.file_type, owner=self.current_user,
                                   group=self._current_group(), permissions=src_fcb.permissions)
        new_fcb.block_list = self.disk.write_content([], content)
        new_fcb.size = len(content)
        dst_parent.add_child(DirectoryNode(dst_name, new_fcb.inode_id))
        dst_parent_fcb.touch_modify()
        return new_fcb

    def mv(self, src: str, dst: str) -> None:
        src_parent, src_name = self.resolve_parent_and_name(src)
        src_parent_fcb = self._fcb(src_parent)
        moving_node = src_parent.find_child(src_name)
        if moving_node is None:
            raise NotFoundError(f"não encontrado: {src!r}")
        self._require(src_parent_fcb, "w", src_parent.path())

        dst_parent, dst_name = self.resolve_parent_and_name(dst)
        dst_parent_fcb = self._fcb(dst_parent)
        self._require(dst_parent_fcb, "w", dst_parent.path())
        if dst_parent.find_child(dst_name) is not None:
            raise AlreadyExistsError(f"já existe {dst_name!r} em {dst_parent.path()}")

        # mv NÃO toca no inode nem nos blocos de dados — só desliga o nó
        # de um pai e liga em outro (com o novo nome). Isso é O(1),
        # independente do tamanho do arquivo: prova de que mv é uma
        # operação puramente sobre a árvore de diretórios.
        src_parent.remove_child(src_name)
        moving_node.entry_name = dst_name
        dst_parent.add_child(moving_node)
        src_parent_fcb.touch_modify()
        dst_parent_fcb.touch_modify()

    def rm(self, path: str) -> None:
        """Remove um arquivo (não-diretório). Note que, seguindo o
        comportamento real do Unix, a checagem de permissão é sobre o
        diretório PAI (precisa poder escrever nele para remover uma
        entrada), não sobre o próprio arquivo."""
        parent, name = self.resolve_parent_and_name(path)
        parent_fcb = self._fcb(parent)
        node = parent.find_child(name)
        if node is None:
            raise NotFoundError(f"não encontrado: {path!r}")
        fcb = self._fcb(node)
        if fcb.is_directory():
            raise IsADirectoryError_(f"{path!r} é um diretório; use 'rmdir'")
        self._require(parent_fcb, "w", parent.path())

        parent.remove_child(name)
        parent_fcb.touch_modify()
        self._unlink_inode(fcb)

    def rmdir(self, path: str) -> None:
        parent, name = self.resolve_parent_and_name(path)
        parent_fcb = self._fcb(parent)
        node = parent.find_child(name)
        if node is None:
            raise NotFoundError(f"não encontrado: {path!r}")
        fcb = self._fcb(node)
        if not fcb.is_directory():
            raise NotADirectoryError_(f"{path!r} não é um diretório; use 'rm'")
        if node.first_child is not None:
            raise DirectoryNotEmptyError(f"diretório não vazio: {path!r}")
        self._require(parent_fcb, "w", parent.path())

        parent.remove_child(name)
        parent_fcb.touch_modify()
        del self.inodes[fcb.inode_id]

    def _unlink_inode(self, fcb: FCB) -> None:
        """Decrementa o contador de hard links; só libera de fato os
        blocos no disco e remove o inode quando o último nome que
        apontava para ele desaparece (link_count chega a 0) — é
        exatamente assim que o `rm` real funciona em arquivos com
        múltiplos hard links."""
        fcb.link_count -= 1
        if fcb.link_count <= 0:
            self.disk.free_blocks(fcb.block_list)
            del self.inodes[fcb.inode_id]

    # ================================================================
    # 3.3 — Permissões: chmod / whoami / su
    # ================================================================
    def chmod(self, mode_str: str, path: str) -> FCB:
        node = self.resolve(path)
        fcb = self._fcb(node)
        # Regra real do Unix: só o PROPRIETÁRIO (ou root) pode mudar as
        # permissões — não basta ter permissão de escrita no arquivo.
        if self.current_user != fcb.owner:
            raise PermissionDeniedError(
                f"permissão negada: apenas o proprietário ({fcb.owner}) pode "
                f"executar chmod em {path!r}; usuário atual: {self.current_user}."
            )
        try:
            fcb.permissions = parse_numeric_mode(mode_str)
        except ValueError as exc:
            raise InvalidModeError(str(exc)) from exc
        fcb.touch_modify()
        return fcb

    def whoami(self) -> str:
        return self.current_user

    def su(self, username: str) -> None:
        if username not in self.users:
            raise NotFoundError(f"usuário desconhecido: {username!r}")
        self.current_user = username

    # ================================================================
    # Bônus — hard links (ln)
    # ================================================================
    def ln(self, target: str, linkname: str) -> None:
        """Cria um hard link: uma NOVA entrada de diretório apontando
        para o MESMO inode do arquivo `target`. Não é permitido criar
        hard link de diretório — no Unix real essa restrição existe
        justamente para impedir ciclos na árvore de diretórios (um
        diretório se tornando ancestral de si mesmo), o que quebraria
        algoritmos como busca em profundidade e o próprio `rm -r`."""
        target_node = self.resolve(target)
        target_fcb = self._fcb(target_node)
        if target_fcb.is_directory():
            raise IsADirectoryError_(
                "não é possível criar hard link de diretório "
                "(evita ciclos na árvore de diretórios)"
            )
        dst_parent, dst_name = self.resolve_parent_and_name(linkname)
        dst_parent_fcb = self._fcb(dst_parent)
        self._require(dst_parent_fcb, "w", dst_parent.path())
        if dst_parent.find_child(dst_name) is not None:
            raise AlreadyExistsError(f"já existe {dst_name!r} em {dst_parent.path()}")

        dst_parent.add_child(DirectoryNode(dst_name, target_fcb.inode_id))
        target_fcb.link_count += 1
        dst_parent_fcb.touch_modify()

    # ================================================================
    # Consultas / listagem
    # ================================================================
    def ls(self, path: str = "") -> list[tuple[DirectoryNode, FCB]]:
        node = self.resolve(path) if path else self.cwd
        fcb = self._fcb(node)
        if not fcb.is_directory():
            return [(node, fcb)]
        self._require(fcb, "r", node.path())
        return [(child, self._fcb(child)) for child in node.children()]

    def stat(self, path: str) -> FCB:
        node = self.resolve(path)
        return self._fcb(node)

    def find(self, name_fragment: str, start: Optional[DirectoryNode] = None) -> list[str]:
        """Busca recursiva por substring no nome (bônus, equivalente a um
        `find . -name "*frag*"` simplificado)."""
        start = start or self.root
        matches: list[str] = []

        def _walk(node: DirectoryNode) -> None:
            if name_fragment.lower() in node.entry_name.lower() and not node.is_root():
                matches.append(node.path())
            for child in node.children():
                _walk(child)

        _walk(start)
        return matches

    def tree_lines(self, start: Optional[DirectoryNode] = None) -> list[str]:
        start = start or self.cwd
        lines = [f"{start.path()}"]

        def _walk(node: DirectoryNode, prefix: str) -> None:
            children = list(node.children())
            for i, child in enumerate(children):
                last = i == len(children) - 1
                connector = "└── " if last else "├── "
                fcb = self._fcb(child)
                suffix = "/" if fcb.is_directory() else ""
                lines.append(f"{prefix}{connector}{child.entry_name}{suffix}")
                extension = "    " if last else "│   "
                _walk(child, prefix + extension)

        _walk(start, "")
        return lines
