"""
shell.py
--------
Interface de linha de comando (REPL) do simulador (objetivo 5.2 do
enunciado: "interface via linha de comando, oferecendo um menu
interativo"). Os comandos imitam de propósito os comandos reais do
Linux (mkdir, cd, ls, touch, cat, cp, mv, rm, chmod, stat...) para que
a comparação pedida no README (5.5) seja direta.

O parsing usa `shlex.split` para respeitar aspas (`echo "duas palavras"`),
e um tratamento especial de regex para o operador de redirecionamento
(`>` e `>>`) do comando `echo`, já que esses operadores não existem como
tokens normais de shlex.
"""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
from typing import Callable

from .errors import FSError
from .filesystem import FileSystem
from .models import FileType, perm_to_string

_ECHO_REGEX = re.compile(r"^\s*(.*?)\s*(>>|>)\s*(\S+)\s*$")

_TYPE_ALIASES = {
    "numerico": FileType.NUMERIC, "numérico": FileType.NUMERIC, "num": FileType.NUMERIC,
    "char": FileType.CHAR, "caractere": FileType.CHAR, "texto": FileType.CHAR,
    "bin": FileType.BINARY, "binario": FileType.BINARY, "binário": FileType.BINARY,
    "prog": FileType.PROGRAM, "programa": FileType.PROGRAM,
}

HELP_TEXT = """\
Comandos disponíveis:

  Diretórios:
    pwd                      mostra o diretório atual
    ls [-l] [caminho]        lista o conteúdo de um diretório
    cd <caminho>             muda o diretório atual ('..' sobe um nível)
    mkdir <nome>             cria um diretório
    rmdir <nome>             remove um diretório vazio
    tree [caminho]           desenha a árvore de diretórios

  Arquivos:
    touch <nome> [tipo]      cria arquivo vazio (tipo: char|num|bin|prog)
    echo "texto" > arquivo   sobrescreve o conteúdo do arquivo
    echo "texto" >> arquivo  acrescenta texto ao final do arquivo
    cat <arquivo>            mostra o conteúdo do arquivo
    cp <origem> <destino>    copia um arquivo (cria um inode novo)
    mv <origem> <destino>    move/renomeia (mesmo inode, só muda a entrada)
    rm <arquivo>             remove um arquivo
    ln <origem> <link>       cria um hard link (mesmo inode, novo nome)
    find <trecho>            busca arquivos/dirs cujo nome contenha <trecho>

  Permissões e usuários:
    chmod <NNN> <arquivo>    muda permissões (ex: chmod 640 segredo.txt)
    stat <arquivo>           mostra o FCB/inode completo do arquivo
    whoami                   mostra o usuário atual
    su <usuario>             troca o usuário atual (kauan | visitante)

  Disco / sistema:
    df                       uso do disco simulado (blocos livres/ocupados)
    diskmap                  mapa visual de blocos ocupados ('X') e livres ('.')
    clear                    limpa a tela
    help                     mostra esta lista de comandos
    exit / quit              sai do simulador
"""


class Shell:
    def __init__(self, fs: FileSystem | None = None, echo_prompt: bool = True):
        self.fs = fs or FileSystem()
        self.echo_prompt = echo_prompt
        self.running = True
        self.commands: dict[str, Callable[[list[str]], None]] = {
            "help": self.cmd_help, "pwd": self.cmd_pwd, "ls": self.cmd_ls,
            "cd": self.cmd_cd, "mkdir": self.cmd_mkdir, "rmdir": self.cmd_rmdir,
            "tree": self.cmd_tree, "touch": self.cmd_touch, "cat": self.cmd_cat,
            "cp": self.cmd_cp, "mv": self.cmd_mv, "rm": self.cmd_rm, "ln": self.cmd_ln,
            "find": self.cmd_find, "chmod": self.cmd_chmod, "stat": self.cmd_stat,
            "whoami": self.cmd_whoami, "su": self.cmd_su, "df": self.cmd_df,
            "diskmap": self.cmd_diskmap, "clear": self.cmd_clear,
            "exit": self.cmd_exit, "quit": self.cmd_exit,
        }

    # -- loop principal --------------------------------------------------
    def prompt(self) -> str:
        return f"{self.fs.current_user}@minifs:{self.fs.pwd()}$ "

    def run(self) -> None:
        print("=== Mini-Sistema de Arquivos em Memória (minifs) ===")
        print("Digite 'help' para ver os comandos disponíveis.\n")
        while self.running:
            try:
                line = input(self.prompt())
            except EOFError:
                print()
                break
            self.execute_line(line)

    def execute_line(self, line: str) -> None:
        line = line.strip()
        if not line or line.startswith("#"):
            return
        if self.echo_prompt:
            pass  # o próprio input() já ecoa em modo interativo
        if line.split()[0] == "echo":
            self._handle_echo(line)
            return
        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            print(f"erro de sintaxe: {exc}")
            return
        cmd, *args = tokens
        handler = self.commands.get(cmd)
        if handler is None:
            if cmd in {"py", "python", "python3"}:
                try:
                    subprocess.run([cmd, *args], check=False)
                except FileNotFoundError:
                    print(f"comando não encontrado: {cmd!r} (digite 'help')")
                return
            print(f"comando não encontrado: {cmd!r} (digite 'help')")
            return
        try:
            handler(args)
        except FSError as exc:
            print(f"erro: {exc}")
        except (ValueError, IndexError) as exc:
            print(f"erro de uso do comando '{cmd}': {exc}")

    # -- echo (caso especial por causa do '>' / '>>') --------------------
    def _handle_echo(self, line: str) -> None:
        rest = line[len("echo"):]
        match = _ECHO_REGEX.match(rest)
        if not match:
            print('uso: echo "texto" > arquivo   ou   echo "texto" >> arquivo')
            return
        raw_content, operator, target = match.groups()
        try:
            content = shlex.split(raw_content)
            content_str = " ".join(content) if content else ""
        except ValueError:
            content_str = raw_content.strip().strip('"').strip("'")
        try:
            self.fs.write(target, content_str, append=(operator == ">>"))
            verbo = "adicionado a" if operator == ">>" else "escrito em"
            print(f"({len(content_str)} bytes {verbo} {target})")
        except FSError as exc:
            print(f"erro: {exc}")

    # -- comandos: diretórios --------------------------------------------
    def cmd_help(self, args: list[str]) -> None:
        print(HELP_TEXT)

    def cmd_pwd(self, args: list[str]) -> None:
        print(self.fs.pwd())

    def cmd_ls(self, args: list[str]) -> None:
        long = "-l" in args
        paths = [a for a in args if a != "-l"]
        path = paths[0] if paths else ""
        entries = self.fs.ls(path)
        if not long:
            print("  ".join(e.entry_name for e, _ in entries) or "(vazio)")
            return
        if not entries:
            print("(vazio)")
            return
        for node, fcb in entries:
            mtime = fcb.fmt_time(fcb.modified_at)
            print(f"{fcb.permission_string()}  {fcb.link_count:>2}  "
                  f"{fcb.owner:<10}{fcb.group:<10}{fcb.size:>6}  {mtime}  {node.entry_name}")

    def cmd_cd(self, args: list[str]) -> None:
        target = args[0] if args else "~"
        self.fs.cd(target)

    def cmd_mkdir(self, args: list[str]) -> None:
        if not args:
            raise ValueError("uso: mkdir <nome>")
        self.fs.mkdir(args[0])
        print(f"diretório criado: {args[0]}")

    def cmd_rmdir(self, args: list[str]) -> None:
        if not args:
            raise ValueError("uso: rmdir <nome>")
        self.fs.rmdir(args[0])
        print(f"diretório removido: {args[0]}")

    def cmd_tree(self, args: list[str]) -> None:
        start = self.fs.resolve(args[0]) if args else None
        for line in self.fs.tree_lines(start):
            print(line)

    # -- comandos: arquivos -----------------------------------------------
    def cmd_touch(self, args: list[str]) -> None:
        if not args:
            raise ValueError("uso: touch <nome> [tipo]")
        ftype = _TYPE_ALIASES.get(args[1].lower(), FileType.CHAR) if len(args) > 1 else FileType.CHAR
        self.fs.touch(args[0], file_type=ftype)
        print(f"arquivo criado/atualizado: {args[0]} (tipo: {ftype.value})")

    def cmd_cat(self, args: list[str]) -> None:
        if not args:
            raise ValueError("uso: cat <arquivo>")
        print(self.fs.read(args[0]))

    def cmd_cp(self, args: list[str]) -> None:
        if len(args) != 2:
            raise ValueError("uso: cp <origem> <destino>")
        self.fs.cp(args[0], args[1])
        print(f"copiado: {args[0]} -> {args[1]}")

    def cmd_mv(self, args: list[str]) -> None:
        if len(args) != 2:
            raise ValueError("uso: mv <origem> <destino>")
        self.fs.mv(args[0], args[1])
        print(f"movido: {args[0]} -> {args[1]}")

    def cmd_rm(self, args: list[str]) -> None:
        if not args:
            raise ValueError("uso: rm <arquivo>")
        self.fs.rm(args[0])
        print(f"removido: {args[0]}")

    def cmd_ln(self, args: list[str]) -> None:
        if len(args) != 2:
            raise ValueError("uso: ln <origem> <link>")
        self.fs.ln(args[0], args[1])
        print(f"hard link criado: {args[1]} -> mesmo inode de {args[0]}")

    def cmd_find(self, args: list[str]) -> None:
        if not args:
            raise ValueError("uso: find <trecho-do-nome>")
        results = self.fs.find(args[0])
        print("\n".join(results) if results else "nenhum resultado encontrado")

    # -- comandos: permissões / usuários -----------------------------------
    def cmd_chmod(self, args: list[str]) -> None:
        if len(args) != 2:
            raise ValueError("uso: chmod <NNN> <arquivo>")
        fcb = self.fs.chmod(args[0], args[1])
        print(f"permissões de {args[1]} alteradas para {args[0]} ({perm_to_string(fcb.permissions)})")

    def cmd_stat(self, args: list[str]) -> None:
        if not args:
            raise ValueError("uso: stat <arquivo>")
        fcb = self.fs.stat(args[0])
        print(f"  Arquivo: {args[0]}")
        print(f"  Inode:   {fcb.inode_id}")
        print(f"  Tipo:    {fcb.file_type.value}")
        print(f"  Tamanho: {fcb.size} bytes  ({len(fcb.block_list)} blocos)")
        print(f"  Blocos:  {fcb.block_list}")
        print(f"  Links:   {fcb.link_count}")
        print(f"  Permissões: {fcb.permission_string()}  (dono: {fcb.owner}, grupo: {fcb.group})")
        print(f"  Criado em:    {fcb.fmt_time(fcb.created_at)}")
        print(f"  Modificado em:{fcb.fmt_time(fcb.modified_at)}")
        print(f"  Acessado em:  {fcb.fmt_time(fcb.accessed_at)}")

    def cmd_whoami(self, args: list[str]) -> None:
        print(self.fs.whoami())

    def cmd_su(self, args: list[str]) -> None:
        if not args:
            raise ValueError("uso: su <usuario>")
        self.fs.su(args[0])
        print(f"usuário atual: {args[0]}")

    # -- comandos: disco / sistema -----------------------------------------
    def cmd_df(self, args: list[str]) -> None:
        print(self.fs.disk.summary())

    def cmd_diskmap(self, args: list[str]) -> None:
        print(self.fs.disk.usage_map())
        print("('X' = bloco ocupado, '.' = bloco livre)")

    def cmd_clear(self, args: list[str]) -> None:
        print("\033c", end="")

    def cmd_exit(self, args: list[str]) -> None:
        print("Encerrando o simulador. Até mais!")
        self.running = False


def run_script(fs: FileSystem, lines: list[str], verbose: bool = True) -> None:
    """Executa uma lista de comandos não-interativamente (usado pelo modo
    --demo e pelos testes), imprimindo o prompt e o comando antes da saída
    para simular uma sessão real de terminal."""
    shell = Shell(fs)
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            if verbose and line.startswith("#"):
                print(f"\n{line}")
            continue
        if verbose:
            print(f"{shell.prompt()}{line}")
        shell.execute_line(line)
        if not shell.running:
            break
