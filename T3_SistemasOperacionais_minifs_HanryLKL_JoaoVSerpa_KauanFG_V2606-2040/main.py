#!/usr/bin/env python3
"""
main.py
-------
Ponto de entrada do simulador.

Uso:
    python3 main.py            -> abre o shell interativo
    python3 main.py --demo     -> executa uma sessão de demonstração
                                   pré-roteirizada (não-interativa),
                                   exercitando todos os comandos e
                                   mostrando os erros tratados.
"""

from __future__ import annotations

import subprocess
import sys

from minifs.filesystem import FileSystem
from minifs.shell import Shell, run_script

DEMO_SCRIPT = [
    "# 1) Navegação e criação de diretórios (objetivo 3.1)",
    "pwd",
    "mkdir documentos",
    "mkdir projetos",
    "cd documentos",
    "pwd",
    "cd ..",
    "tree",

    "# 2) Arquivos e metadados / FCB (objetivo 3.2)",
    "touch documentos/notas.txt",
    'echo "Primeira linha do arquivo de notas." > documentos/notas.txt',
    'echo "Segunda linha, adicionada depois." >> documentos/notas.txt',
    "cat documentos/notas.txt",
    "stat documentos/notas.txt",
    "ls -l documentos",

    "# 3) cp x mv (cp duplica o inode; mv só religa a entrada na árvore)",
    "cp documentos/notas.txt documentos/notas_copia.txt",
    "mv documentos/notas_copia.txt projetos/notas_copia.txt",
    "stat documentos/notas.txt",
    "stat projetos/notas_copia.txt",

    "# 4) Hard link (bônus) - duas entradas, um único inode",
    "ln documentos/notas.txt documentos/notas_link.txt",
    "stat documentos/notas.txt",
    "rm documentos/notas_link.txt",
    "stat documentos/notas.txt",

    "# 5) Permissões RWX e chmod numérico (objetivo 3.3)",
    "stat documentos/notas.txt",
    "chmod 600 documentos/notas.txt",
    "stat documentos/notas.txt",
    "su visitante",
    "whoami",
    "cat documentos/notas.txt",
    "echo \"tentando escrever como visitante\" >> documentos/notas.txt",
    "su kauan",
    "chmod 644 documentos/notas.txt",
    "su visitante",
    "cat documentos/notas.txt",
    "su kauan",

    "# 6) Simulação de alocação de blocos (objetivo 3.4)",
    "df",
    "diskmap",
    'echo "Conteudo um pouco mais longo para ocupar varios blocos de trinta e dois bytes cada um no disco simulado." > projetos/grande.txt',
    "stat projetos/grande.txt",
    "df",
    "diskmap",

    "# 7) Tratamento de erros",
    "cat arquivo_que_nao_existe.txt",
    "mkdir documentos",
    "rmdir documentos",
    "cd /lugar/que/nao/existe",

    "# 8) Outros utilitários",
    "find notas",
    "tree /",
]


def get_start_mode(argv: list[str] | None = None) -> str:
    args = sys.argv[1:] if argv is None else argv

    if "--demo" in args:
        return "demo"
    if "--tests" in args:
        return "tests"
    if "--shell" in args:
        return "shell"

    if not args and sys.stdin.isatty():
        print("Escolha o que deseja executar:")
        print("1 - Shell interativo")
        print("2 - Demonstração")
        print("3 - Testes")
        choice = input("Digite sua opção [1-3]: ").strip()
        return {"1": "shell", "2": "demo", "3": "tests"}.get(choice, "shell")

    return "shell"


def main() -> None:
    mode = get_start_mode()

    if mode == "demo":
        fs = FileSystem()
        run_script(fs, DEMO_SCRIPT, verbose=True)
        return

    if mode == "tests":
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            check=False,
        )
        raise SystemExit(completed.returncode)

    fs = FileSystem()
    Shell(fs).run()


if __name__ == "__main__":
    main()
