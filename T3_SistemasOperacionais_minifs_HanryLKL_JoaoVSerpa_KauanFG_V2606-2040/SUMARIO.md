# Sumário do Projeto minifs

Este arquivo reúne os principais arquivos do projeto, com uma visão rápida de onde ficam as lógicas, estruturas e funções principais.

## Estrutura geral

- [main.py](main.py) — ponto de entrada do programa
- [minifs/filesystem.py](minifs/filesystem.py) — implementação da lógica do sistema de arquivos
- [minifs/shell.py](minifs/shell.py) — interface de linha de comando e comandos do shell
- [minifs/directory.py](minifs/directory.py) — estrutura de diretórios em árvore
- [minifs/disk.py](minifs/disk.py) — simulação do disco e alocação de blocos
- [minifs/models.py](minifs/models.py) — modelos de dados como FCB e tipos de arquivo
- [minifs/errors.py](minifs/errors.py) — exceções do sistema
- [tests/test_filesystem.py](tests/test_filesystem.py) — testes principais da lógica do filesystem
- [tests/test_main_menu.py](tests/test_main_menu.py) — testes do menu inicial do programa

## Pontos principais por arquivo

As linhas abaixo indicam onde começa cada parte relevante do código.

### [main.py](main.py)
- [main.py](main.py#L23) — definição do script de demonstração
- [main.py](main.py#L87) — função get_start_mode, que escolhe o modo de execução
- [main.py](main.py#L108) — função main, que inicia o shell, a demo ou os testes

### [minifs/filesystem.py](minifs/filesystem.py)
- [minifs/filesystem.py](minifs/filesystem.py#L60) — classe FileSystem
- [minifs/filesystem.py](minifs/filesystem.py#L88) — helper _new_inode
- [minifs/filesystem.py](minifs/filesystem.py#L126) — resolução de caminhos com resolve
- [minifs/filesystem.py](minifs/filesystem.py#L165) — mkdir
- [minifs/filesystem.py](minifs/filesystem.py#L184) — cd
- [minifs/filesystem.py](minifs/filesystem.py#L191) — pwd
- [minifs/filesystem.py](minifs/filesystem.py#L197) — touch
- [minifs/filesystem.py](minifs/filesystem.py#L213) — write (echo)
- [minifs/filesystem.py](minifs/filesystem.py#L235) — read (cat)
- [minifs/filesystem.py](minifs/filesystem.py#L245) — cp
- [minifs/filesystem.py](minifs/filesystem.py#L269) — mv
- [minifs/filesystem.py](minifs/filesystem.py#L293) — rm
- [minifs/filesystem.py](minifs/filesystem.py#L312) — rmdir
- [minifs/filesystem.py](minifs/filesystem.py#L343) — chmod
- [minifs/filesystem.py](minifs/filesystem.py#L360) — whoami
- [minifs/filesystem.py](minifs/filesystem.py#L363) — su
- [minifs/filesystem.py](minifs/filesystem.py#L371) — ln (hard link)
- [minifs/filesystem.py](minifs/filesystem.py#L398) — ls
- [minifs/filesystem.py](minifs/filesystem.py#L406) — stat
- [minifs/filesystem.py](minifs/filesystem.py#L410) — find
- [minifs/filesystem.py](minifs/filesystem.py#L425) — tree_lines

### [minifs/shell.py](minifs/shell.py)
- [minifs/shell.py](minifs/shell.py#L74) — classe Shell
- [minifs/shell.py](minifs/shell.py#L91) — prompt
- [minifs/shell.py](minifs/shell.py#L94) — loop principal run
- [minifs/shell.py](minifs/shell.py#L105) — execute_line
- [minifs/shell.py](minifs/shell.py#L138) — tratamento especial do echo
- [minifs/shell.py](minifs/shell.py#L158) — help
- [minifs/shell.py](minifs/shell.py#L180) — cd
- [minifs/shell.py](minifs/shell.py#L184) — mkdir
- [minifs/shell.py](minifs/shell.py#L202) — touch
- [minifs/shell.py](minifs/shell.py#L209) — cat
- [minifs/shell.py](minifs/shell.py#L214) — cp
- [minifs/shell.py](minifs/shell.py#L220) — mv
- [minifs/shell.py](minifs/shell.py#L190) — rm
- [minifs/shell.py](minifs/shell.py#L232) — ln
- [minifs/shell.py](minifs/shell.py#L238) — find
- [minifs/shell.py](minifs/shell.py#L245) — chmod
- [minifs/shell.py](minifs/shell.py#L251) — stat
- [minifs/shell.py](minifs/shell.py#L266) — whoami
- [minifs/shell.py](minifs/shell.py#L269) — su
- [minifs/shell.py](minifs/shell.py#L276) — df
- [minifs/shell.py](minifs/shell.py#L279) — diskmap
- [minifs/shell.py](minifs/shell.py#L283) — clear
- [minifs/shell.py](minifs/shell.py#L286) — exit
- [minifs/shell.py](minifs/shell.py#L291) — run_script

### [minifs/directory.py](minifs/directory.py)
- [minifs/directory.py](minifs/directory.py#L33) — classe DirectoryNode
- [minifs/directory.py](minifs/directory.py#L45) — children
- [minifs/directory.py](minifs/directory.py#L55) — find_child
- [minifs/directory.py](minifs/directory.py#L61) — add_child
- [minifs/directory.py](minifs/directory.py#L74) — remove_child
- [minifs/directory.py](minifs/directory.py#L92) — path
- [minifs/directory.py](minifs/directory.py#L103) — is_root

### [minifs/disk.py](minifs/disk.py)
- [minifs/disk.py](minifs/disk.py#L34) — classe Disk
- [minifs/disk.py](minifs/disk.py#L46) — free_block_count
- [minifs/disk.py](minifs/disk.py#L52) — blocks_needed
- [minifs/disk.py](minifs/disk.py#L62) — allocate_blocks
- [minifs/disk.py](minifs/disk.py#L80) — free_blocks
- [minifs/disk.py](minifs/disk.py#L92) — write_content
- [minifs/disk.py](minifs/disk.py#L106) — read_content
- [minifs/disk.py](minifs/disk.py#L110) — usage_map
- [minifs/disk.py](minifs/disk.py#L117) — summary

### [minifs/models.py](minifs/models.py)
- [minifs/models.py](minifs/models.py#L30) — enum FileType
- [minifs/models.py](minifs/models.py#L53) — perm_to_string
- [minifs/models.py](minifs/models.py#L60) — parse_numeric_mode
- [minifs/models.py](minifs/models.py#L69) — classe FCB
- [minifs/models.py](minifs/models.py#L99) — touch_access
- [minifs/models.py](minifs/models.py#L102) — touch_modify
- [minifs/models.py](minifs/models.py#L107) — permission_string
- [minifs/models.py](minifs/models.py#L110) — is_directory
- [minifs/models.py](minifs/models.py#L114) — fmt_time

### [minifs/errors.py](minifs/errors.py)
- [minifs/errors.py](minifs/errors.py#L15) — FSError
- [minifs/errors.py](minifs/errors.py#L19) — NotFoundError
- [minifs/errors.py](minifs/errors.py#L23) — AlreadyExistsError
- [minifs/errors.py](minifs/errors.py#L27) — PermissionDeniedError
- [minifs/errors.py](minifs/errors.py#L31) — NotADirectoryError_
- [minifs/errors.py](minifs/errors.py#L35) — IsADirectoryError_
- [minifs/errors.py](minifs/errors.py#L39) — DirectoryNotEmptyError
- [minifs/errors.py](minifs/errors.py#L43) — InvalidNameError
- [minifs/errors.py](minifs/errors.py#L47) — InvalidModeError
- [minifs/errors.py](minifs/errors.py#L51) — DiskFullError

### [tests/test_filesystem.py](tests/test_filesystem.py)
- Testes das operações principais do filesystem
- Cobre diretórios, arquivos, permissões, hard links e alocação de blocos

### [tests/test_main_menu.py](tests/test_main_menu.py)
- Testes do menu inicial e da seleção de modo de execução

## Resumo rápido das funções principais

- Menu inicial: [main.py](main.py#L87-L117)
- Shell interativo: [minifs/shell.py](minifs/shell.py#L74-L304)
- Operações do filesystem: [minifs/filesystem.py](minifs/filesystem.py#L60-L430)
- Estrutura de diretórios: [minifs/directory.py](minifs/directory.py#L33-L106)
- Simulação de disco: [minifs/disk.py](minifs/disk.py#L34-L123)
- Estruturas de dados: [minifs/models.py](minifs/models.py#L30-L115)
- Exceções: [minifs/errors.py](minifs/errors.py#L15-L52)
