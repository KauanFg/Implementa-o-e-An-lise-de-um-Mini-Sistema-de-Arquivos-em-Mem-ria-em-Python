"""
test_filesystem.py
-------------------
Testes unitários do minifs. Cobrem os quatro objetivos específicos do
enunciado (3.1 a 3.4) e os casos de erro mais importantes.

Executar com:
    python3 -m unittest discover -s tests -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from minifs.filesystem import FileSystem
from minifs.disk import Disk, DiskFullError
from minifs.errors import (
    AlreadyExistsError,
    DirectoryNotEmptyError,
    InvalidModeError,
    InvalidNameError,
    IsADirectoryError_,
    NotADirectoryError_,
    NotFoundError,
    PermissionDeniedError,
)
from minifs.models import FileType, perm_to_string, parse_numeric_mode


class TestDirectorios(unittest.TestCase):
    """Objetivo 3.1 — estrutura de diretórios em árvore."""

    def setUp(self):
        self.fs = FileSystem()

    def test_mkdir_e_cd(self):
        self.fs.mkdir("docs")
        self.fs.cd("docs")
        self.assertEqual(self.fs.pwd(), "/home/kauan/docs")

    def test_cd_pai_com_dotdot(self):
        self.fs.mkdir("docs")
        self.fs.cd("docs")
        self.fs.cd("..")
        self.assertEqual(self.fs.pwd(), "/home/kauan")

    def test_mkdir_duplicado_levanta_erro(self):
        self.fs.mkdir("docs")
        with self.assertRaises(AlreadyExistsError):
            self.fs.mkdir("docs")

    def test_cd_inexistente_levanta_erro(self):
        with self.assertRaises(NotFoundError):
            self.fs.cd("nao_existe")

    def test_caminho_absoluto(self):
        self.fs.mkdir("docs")
        node = self.fs.resolve("/home/kauan/docs")
        self.assertEqual(node.path(), "/home/kauan/docs")

    def test_rmdir_nao_vazio_levanta_erro(self):
        self.fs.mkdir("docs")
        self.fs.touch("docs/a.txt")
        with self.assertRaises(DirectoryNotEmptyError):
            self.fs.rmdir("docs")

    def test_rmdir_vazio_funciona(self):
        self.fs.mkdir("docs")
        self.fs.rmdir("docs")
        self.assertIsNone(self.fs.cwd.find_child("docs"))


class TestArquivosEMetadados(unittest.TestCase):
    """Objetivo 3.2 — FCB, touch/echo/cat/cp/mv/rm."""

    def setUp(self):
        self.fs = FileSystem()

    def test_touch_cria_arquivo_vazio(self):
        fcb = self.fs.touch("a.txt")
        self.assertEqual(fcb.size, 0)
        self.assertEqual(fcb.file_type, FileType.CHAR)

    def test_write_e_read_round_trip(self):
        self.fs.write("a.txt", "ola mundo")
        self.assertEqual(self.fs.read("a.txt"), "ola mundo")

    def test_append_concatena_conteudo(self):
        self.fs.write("a.txt", "linha1")
        self.fs.write("a.txt", "linha2", append=True)
        self.assertEqual(self.fs.read("a.txt"), "linha1linha2")

    def test_overwrite_substitui_conteudo(self):
        self.fs.write("a.txt", "linha1")
        self.fs.write("a.txt", "novo")
        self.assertEqual(self.fs.read("a.txt"), "novo")

    def test_cp_cria_inode_independente(self):
        self.fs.write("a.txt", "original")
        self.fs.cp("a.txt", "b.txt")
        self.fs.write("b.txt", "alterado")
        # alterar a cópia não deve afetar o original (inodes diferentes)
        self.assertEqual(self.fs.read("a.txt"), "original")
        self.assertEqual(self.fs.read("b.txt"), "alterado")
        fcb_a = self.fs.stat("a.txt")
        fcb_b = self.fs.stat("b.txt")
        self.assertNotEqual(fcb_a.inode_id, fcb_b.inode_id)

    def test_mv_preserva_inode(self):
        self.fs.write("a.txt", "conteudo")
        fcb_antes = self.fs.stat("a.txt")
        self.fs.mkdir("dir2")
        self.fs.mv("a.txt", "dir2/a.txt")
        fcb_depois = self.fs.stat("dir2/a.txt")
        # mv não cria inode novo: deve ser o MESMO número de inode
        self.assertEqual(fcb_antes.inode_id, fcb_depois.inode_id)
        self.assertEqual(self.fs.read("dir2/a.txt"), "conteudo")

    def test_rm_remove_arquivo(self):
        self.fs.touch("a.txt")
        self.fs.rm("a.txt")
        with self.assertRaises(NotFoundError):
            self.fs.stat("a.txt")

    def test_rm_em_diretorio_levanta_erro(self):
        self.fs.mkdir("docs")
        with self.assertRaises(IsADirectoryError_):
            self.fs.rm("docs")

    def test_cat_em_diretorio_levanta_erro(self):
        self.fs.mkdir("docs")
        with self.assertRaises(IsADirectoryError_):
            self.fs.read("docs")

    def test_cd_em_arquivo_levanta_erro(self):
        self.fs.touch("a.txt")
        with self.assertRaises(NotADirectoryError_):
            self.fs.cd("a.txt")

    def test_nome_invalido_levanta_erro(self):
        with self.assertRaises(InvalidNameError):
            self.fs.mkdir("nome:invalido")
        with self.assertRaises(InvalidNameError):
            self.fs.mkdir("")


class TestPermissoes(unittest.TestCase):
    """Objetivo 3.3 — RWX, owner/group/public, chmod numérico."""

    def setUp(self):
        self.fs = FileSystem()
        self.fs.write("segredo.txt", "topo secreto")
        self.fs.chmod("600", "segredo.txt")  # rw------- só o dono

    def test_dono_pode_ler_e_escrever(self):
        self.assertEqual(self.fs.read("segredo.txt"), "topo secreto")
        self.fs.write("segredo.txt", "novo segredo")  # não deve levantar erro

    def test_outro_usuario_nao_pode_ler(self):
        self.fs.su("visitante")
        with self.assertRaises(PermissionDeniedError):
            self.fs.read("segredo.txt")

    def test_outro_usuario_nao_pode_escrever(self):
        self.fs.su("visitante")
        with self.assertRaises(PermissionDeniedError):
            self.fs.write("segredo.txt", "hackeado", append=True)

    def test_chmod_libera_leitura_para_outros(self):
        self.fs.chmod("644", "segredo.txt")
        self.fs.su("visitante")
        self.assertEqual(self.fs.read("segredo.txt"), "topo secreto")

    def test_apenas_dono_pode_chmod(self):
        self.fs.su("visitante")
        with self.assertRaises(PermissionDeniedError):
            self.fs.chmod("777", "segredo.txt")

    def test_modo_invalido_levanta_erro(self):
        with self.assertRaises(ValueError):
            parse_numeric_mode("999")
        with self.assertRaises(ValueError):
            parse_numeric_mode("12")

    def test_perm_to_string(self):
        self.assertEqual(perm_to_string(0o754), "rwxr-xr--")
        self.assertEqual(perm_to_string(0o600), "rw-------")

    def test_rm_exige_escrita_no_diretorio_pai_nao_no_arquivo(self):
        # mesmo com o arquivo em modo 000 (sem nenhuma permissão), o
        # PRÓPRIO DONO deve conseguir remover, pois o que importa é a
        # permissão de escrita no diretório PAI (comportamento real do Unix).
        self.fs.chmod("000", "segredo.txt")
        self.fs.rm("segredo.txt")  # não deve levantar erro


class TestHardLinks(unittest.TestCase):
    """Bônus — múltiplas entradas de diretório para o mesmo inode."""

    def setUp(self):
        self.fs = FileSystem()
        self.fs.write("original.txt", "conteudo compartilhado")

    def test_ln_incrementa_link_count(self):
        self.fs.ln("original.txt", "link1.txt")
        fcb = self.fs.stat("original.txt")
        self.assertEqual(fcb.link_count, 2)
        self.assertEqual(self.fs.read("link1.txt"), "conteudo compartilhado")

    def test_remover_um_link_mantem_o_outro(self):
        self.fs.ln("original.txt", "link1.txt")
        self.fs.rm("original.txt")
        # o conteúdo deve continuar acessível pelo outro nome
        self.assertEqual(self.fs.read("link1.txt"), "conteudo compartilhado")

    def test_remover_ultimo_link_libera_inode(self):
        self.fs.ln("original.txt", "link1.txt")
        self.fs.rm("original.txt")
        self.fs.rm("link1.txt")
        with self.assertRaises(NotFoundError):
            self.fs.stat("link1.txt")

    def test_nao_permite_link_de_diretorio(self):
        self.fs.mkdir("docs")
        with self.assertRaises(IsADirectoryError_):
            self.fs.ln("docs", "docs_link")


class TestAlocacaoDeBlocos(unittest.TestCase):
    """Objetivo 3.4 — disco simulado e alocação indexada."""

    def setUp(self):
        self.fs = FileSystem()

    def test_arquivo_vazio_nao_usa_blocos(self):
        self.fs.touch("vazio.txt")
        fcb = self.fs.stat("vazio.txt")
        self.assertEqual(fcb.block_list, [])

    def test_tamanho_calcula_blocos_corretamente(self):
        bs = self.fs.disk.block_size
        conteudo = "a" * (bs * 2 + 5)  # exige 3 blocos (ceil division)
        self.fs.write("a.txt", conteudo)
        fcb = self.fs.stat("a.txt")
        self.assertEqual(len(fcb.block_list), 3)
        self.assertEqual(fcb.size, len(conteudo))

    def test_reescrever_libera_blocos_antigos(self):
        bs = self.fs.disk.block_size
        self.fs.write("a.txt", "a" * (bs * 3))
        usados_antes = self.fs.disk.used_block_count()
        self.fs.write("a.txt", "pequeno")
        usados_depois = self.fs.disk.used_block_count()
        self.assertLess(usados_depois, usados_antes)

    def test_disco_cheio_levanta_erro(self):
        disco_pequeno = Disk(total_blocks=2, block_size=4)
        fs = FileSystem(disk=disco_pequeno)
        with self.assertRaises(DiskFullError):
            fs.write("grande.txt", "x" * 100)  # precisa de mais de 2 blocos

    def test_round_trip_preserva_conteudo_exato(self):
        texto = "Linha 1\nLinha 2 com acentuação: ção, ã, é\nFim."
        self.fs.write("a.txt", texto)
        self.assertEqual(self.fs.read("a.txt"), texto)


class TestBusca(unittest.TestCase):
    def setUp(self):
        self.fs = FileSystem()
        self.fs.mkdir("docs")
        self.fs.touch("docs/relatorio.txt")
        self.fs.touch("relatorio_final.txt")

    def test_find_encontra_por_substring(self):
        resultados = self.fs.find("relatorio")
        self.assertEqual(len(resultados), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
