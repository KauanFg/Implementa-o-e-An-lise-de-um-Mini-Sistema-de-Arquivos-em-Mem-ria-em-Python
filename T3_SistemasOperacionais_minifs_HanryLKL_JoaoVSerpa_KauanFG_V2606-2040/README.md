# minifs — Mini-Sistema de Arquivos em Memória

**Disciplina:** Sistemas Operacionais — UNIVALI
**Professor:** Michael D. C. Alves
**Trabalho:** M3 — Implementação e Análise de um Mini-Sistema de Arquivos em Memória
**Linguagem escolhida:** Python
**Alunos: Hanry Ledoux Krobel Lorenz, João Victor Serpa e Kauan Fernandes Gonçalves**

Simulador de sistema de arquivos que roda **inteiramente em memória**: nenhuma
operação (mkdir, touch, escrever, ler, etc.) toca o sistema de arquivos real
do computador. Tudo — diretórios, arquivos, metadados e até os "blocos do
disco" — vive em estruturas de dados Python durante a execução do programa.

---

## 1. Como compilar e executar

Não há "compilação" (Python é interpretado), apenas a execução direta.
Requer **Python 3.10+** (usa sintaxe de type hints moderna) — testado em
Python 3.12. Não há dependências externas (somente biblioteca padrão).

```bash
# Shell interativo (menu de linha de comando)
python3 main.py

# Sessão de demonstração não-interativa, percorrendo todos os
# objetivos do trabalho (3.1 a 3.4) e os tratamentos de erro
python3 main.py --demo

# Suíte de testes automatizados (36 testes)
python3 -m unittest discover -s tests -v
```

Funciona em Linux, WSL, macOS ou Windows (cmd/PowerShell), já que depende
apenas do interpretador Python — mas para fins de comparação com os
comandos reais (seção 6), recomenda-se testar também em um terminal Linux
ou WSL, como sugerido no enunciado (item 4.2).

### Usuários pré-cadastrados (para testar permissões)
| usuário     | grupo      | diretório pessoal     |
|-------------|------------|------------------------|
| `kauan`     | `alunos`   | `/home/kauan` (usuário inicial) |
| `visitante` | `externos` | `/home/visitante`     |

Troque de usuário com `su <nome>` para testar o controle de acesso (3.3).

---

## 2. Estrutura do projeto

```
minifs/
├── main.py                 # ponto de entrada (shell interativo / --demo)
├── minifs/
│   ├── models.py            # FileType (enum) e FCB (o "inode" simulado)
│   ├── disk.py               # Disk: vetor de blocos + bitmap de livres/ocupados
│   ├── directory.py         # DirectoryNode: árvore via first-child/next-sibling
│   ├── filesystem.py         # FileSystem: todas as "chamadas de sistema" simuladas
│   ├── shell.py              # REPL: parsing de comandos e prompt estilo bash
│   └── errors.py             # hierarquia de exceções (ENOENT, EACCES, ENOSPC, ...)
├── tests/
│   └── test_filesystem.py    # 36 testes unitários (unittest)
└── README.md                 # este arquivo
```

O projeto foi dividido em módulos por **responsabilidade única**: a
representação de dados (`models`), a simulação física do disco (`disk`), a
estrutura lógica de diretórios (`directory`), a regra de negócio que junta
tudo (`filesystem`) e a interface com o usuário (`shell`) não se misturam —
isso facilita testar cada peça isoladamente e é a mesma separação que um
SO real faz entre VFS, alocador de blocos e drivers.

---

## 3. Escolhas de design e estruturas de dados

### 3.1 Mapeamento de conceitos C → Python

O enunciado foi escrito pensando em C (menciona `struct`, `malloc`/`free`,
`typedef enum`). Como a implementação foi feita em Python, eis o
mapeamento conceitual usado para preservar a mesma profundidade técnica:

| Conceito em C                          | Equivalente usado em Python                          |
|-----------------------------------------|--------------------------------------------------------|
| `struct FCB { ... };`                   | `@dataclass class FCB` (`models.py`)                  |
| `typedef enum { ... } TipoArquivo;`     | `class FileType(Enum)` (`models.py`)                  |
| `FCB *ponteiro`                         | referência de objeto Python (mesma semântica: duas variáveis podem apontar para o mesmo objeto em memória) |
| `malloc(n)` / `free(ptr)`               | `Disk.allocate_blocks(n)` / `Disk.free_blocks(lista)` — alocação/liberação **explícita** sobre o vetor que simula o disco, não sobre a heap do processo |
| Lista encadeada de filhos (`No *prox`)   | `DirectoryNode.next_sibling` (ver 3.2)                |
| Bitmask de permissões (`int` com operadores `&`/`\|`) | `int` de 9 bits + funções `perm_to_string`/`parse_numeric_mode` |

A ideia central — que importa mais do que a sintaxe da linguagem — é a
mesma: nada de "trapacear" usando listas dinâmicas do Python onde C
precisaria de ponteiros manuais. A lista de blocos de um arquivo
(`FCB.block_list`) é gerenciada manualmente pelo `Disk`, simulando
exatamente a mecânica de alocar/liberar espaço que `malloc`/`free` fariam.

### 3.2 Árvore de diretórios: *first-child / next-sibling*

O objetivo 3.1 sugere representar o diretório com uma árvore binária ou
lista encadeada. Em vez de usar `list[DirectoryNode]` para os filhos
(o que seria mais "fácil" em Python, mas escaparia do exercício), cada
`DirectoryNode` guarda **apenas dois ponteiros**:

```python
class DirectoryNode:
    self.first_child   # primeiro filho deste diretório
    self.next_sibling   # próximo irmão (outro filho do MESMO pai)
```

Essa é a representação clássica **"filho mais à esquerda / irmão à
direita"** (*left-child right-sibling*), descrita em livros de Sistemas
Operacionais (ex. Silberschatz) como forma de mapear uma árvore **N-ária**
(um diretório pode ter qualquer número de filhos) em uma estrutura
**binária** (cada nó tem só 2 ponteiros) — exatamente o que o enunciado
pede. Navegar pelos filhos de um diretório é idêntico a percorrer uma
lista encadeada a partir de `first_child`, seguindo `next_sibling`.

Vantagem prática: `mkdir`/`touch` (inserir um filho) e `rm`/`rmdir`
(remover um filho) são operações O(grau do nó), sem precisar realocar
nenhum vetor — assim como uma lista encadeada real.

### 3.3 Separação entre nome, inode e conteúdo

Esta é a decisão de design mais importante do projeto, pensada para
viabilizar o requisito bônus de **hard links**:

- A **árvore de diretórios** (`DirectoryNode`) guarda só o **nome** da
  entrada (`entry_name`) e um número de **inode** (`inode_id`).
- A **tabela de inodes** (`FileSystem.inodes: dict[int, FCB]`) guarda o
  **FCB completo**: tipo, tamanho, permissões, datas, lista de blocos.

Isso significa que **múltiplos nomes podem apontar para o mesmo FCB** —
exatamente como `ls -li` mostra dois nomes com o mesmo número de inode no
Linux real quando existe um hard link (ver comparação na seção 6.3). Um
contador `link_count` no FCB sabe quando é seguro liberar os blocos de
fato: só quando a última entrada de diretório que apontava para aquele
inode é removida.

Esse design também explica de forma direta, sem precisar de casos
especiais no código, por que `mv` é instantâneo mesmo em arquivos grandes
(ela só desliga um `DirectoryNode` de um pai e liga em outro — **não**
toca no FCB nem nos blocos), enquanto `cp` é proporcional ao tamanho do
arquivo (cria um FCB novo e copia o conteúdo bloco a bloco).

### 3.4 Disco simulado e alocação indexada de blocos

`Disk` (em `disk.py`) é literalmente um vetor de "blocos" de tamanho fixo
(32 bytes cada, configurável) mais um **bitmap** paralelo (`free_bitmap`)
marcando cada bloco como livre ou ocupado — a mesma estrutura de
gerenciamento de espaço livre usada em sistemas de arquivos reais
(ext-family usa bitmaps de blocos, por exemplo).

```
Disco = [bloco0][bloco1][bloco2] ... [bloco_N-1]      (vetor de chars)
Bitmap = [livre][ocupado][ocupado] ... [livre]         (vetor paralelo)
```

**Método de alocação escolhido: indexada simplificada.** Cada FCB guarda
diretamente a lista dos índices de bloco que usa (`FCB.block_list`), como
um "bloco de índices" embutido no próprio inode, em vez de um bloco extra
no disco. Comparando os três métodos clássicos (discutidos em sala):

| Método       | Como funciona                                   | Limitação que o motivou a evitar |
|--------------|--------------------------------------------------|------------------------------------|
| Contígua     | Arquivo ocupa um intervalo contínuo de blocos     | Fragmentação externa; precisa saber o tamanho final antes de alocar |
| Encadeada    | Cada bloco guarda um ponteiro para o próximo      | Acesso aleatório é O(n) — precisa percorrer bloco a bloco |
| **Indexada** | FCB guarda a lista (índice) de todos os blocos    | Acesso a qualquer posição é O(1); arquivo pode crescer sem mover dados; é o que este projeto implementa |

Quando um arquivo é reescrito (`echo > arquivo`), os blocos antigos são
liberados (`Disk.free_blocks`) **antes** de alocar os novos — assim o
disco simulado nunca "perde" espaço, e o comando `df`/`diskmap` deixa
isso visível na hora (ver demonstração na seção 6.4). Se não houver
blocos livres suficientes, `Disk.allocate_blocks` levanta `DiskFullError`
(equivalente ao `ENOSPC`/"No space left on device" real), tratado pelo
shell com uma mensagem amigável em vez de travar o programa.

---

## 4. Conceitos teóricos da disciplina e onde estão implementados

| Conceito da disciplina | Onde está no código |
|---|---|
| Conceito de arquivo e seus atributos (nome, tipo, tamanho, proteção, datas) | `models.FCB` — um atributo por campo, mais `FileType` para o tipo |
| Operações com arquivos (criar, ler, escrever, excluir...) | `FileSystem.touch/write/read/cp/mv/rm` (seção 5) |
| File Control Block (FCB) / inode | `models.FCB` + `FileSystem.inodes` (tabela de inodes) — ver 3.3 |
| Estrutura de diretórios em árvore e suas vantagens | `directory.DirectoryNode` (first-child/next-sibling) — ver 3.2 |
| Proteção de acesso RWX (owner/group/public) e `chmod` numérico | `FileSystem.check_permission` + `models.parse_numeric_mode` — ver 5.3 |
| Alocação de blocos (contígua / encadeada / indexada) | `disk.Disk` — alocação indexada simplificada — ver 3.4 |
| Bloqueio obrigatório (verificação a cada operação) | toda operação chama `self._require(fcb, ação, ...)` antes de executar |

---

## 5. Exemplos de uso e comparação com o Linux real

Todos os exemplos abaixo foram **executados de fato** — tanto no
simulador quanto em um terminal Linux real — para garantir que a
comparação é honesta.

### 5.1 Criar diretórios e arquivos

**No simulador (`python3 main.py`):**
```
kauan@minifs:/home/kauan$ mkdir documentos
diretório criado: documentos
kauan@minifs:/home/kauan$ touch documentos/notas.txt
arquivo criado/atualizado: documentos/notas.txt (tipo: caractere)
kauan@minifs:/home/kauan$ echo "Primeira linha do arquivo de notas." > documentos/notas.txt
(36 bytes escrito em documentos/notas.txt)
```

**No Linux real (bash):**
```
$ mkdir documentos
$ touch documentos/notas.txt
$ echo "Primeira linha do arquivo de notas." > documentos/notas.txt
```
Os comandos do simulador foram propositalmente nomeados igual aos
comandos reais — a única diferença visível é que o simulador imprime uma
confirmação explícita de cada operação (pensado para fins didáticos).

### 5.2 `ls -l` e `stat`: metadados / FCB

**No simulador:**
```
kauan@minifs:/home/kauan$ chmod 600 documentos/notas.txt
permissões de documentos/notas.txt alteradas para 600 (rw-------)
kauan@minifs:/home/kauan$ ls -l documentos
-rw-------   1  kauan     alunos        36  2026-06-26 22:28:21  notas.txt
kauan@minifs:/home/kauan$ stat documentos/notas.txt
  Arquivo: documentos/notas.txt
  Inode:   7
  Tipo:    caractere
  Tamanho: 36 bytes  (2 blocos)
  Blocos:  [0, 1]
  Links:   1
  Permissões: -rw-------  (dono: kauan, grupo: alunos)
  Criado em:    2026-06-26 22:28:21
  Modificado em:2026-06-26 22:28:21
  Acessado em:  2026-06-26 22:28:21
```

**No Linux real (`ls -l` e `stat`):**
```
$ chmod 600 documentos/notas.txt
$ ls -l documentos
total 4
-rw------- 1 root root 36 Jun 26 22:28 notas.txt

$ stat documentos/notas.txt
  File: documentos/notas.txt
  Size: 36          Blocks: 8          IO Block: 4096   regular file
Device: 254,0   Inode: 2801668     Links: 1
Access: (0600/-rw-------)  Uid: (0/root)   Gid: (0/root)
Access: 2026-06-26 22:28:36
Modify: 2026-06-26 22:28:36
Change: 2026-06-26 22:28:36
 Birth: 2026-06-26 22:28:36
```
Note que a **string de permissão** (`-rw-------`) e o **tamanho em
bytes** são idênticos — é o mesmo formato e a mesma lógica de bits RWX
que o Linux real usa internamente. As diferenças (número de inode,
"Blocks: 8" contando blocos de 512B do disco real, `IO Block: 4096`) são
detalhes da implementação real do ext4, que o simulador não precisa
replicar — o que importa para o trabalho é que o **mecanismo conceitual**
(FCB com tamanho, tipo, permissões e datas) é o mesmo.

### 5.3 Controle de acesso RWX entre usuários

```
kauan@minifs:/home/kauan$ stat documentos/notas.txt    # dono: kauan, modo 600
...
kauan@minifs:/home/kauan$ su visitante
usuário atual: visitante
visitante@minifs:/home/kauan$ cat documentos/notas.txt
erro: permissão negada: usuário 'visitante' não tem permissão de R sobre
'documentos/notas.txt' (permissões atuais: -rw-------, dono: kauan).
visitante@minifs:/home/kauan$ su kauan
usuário atual: kauan
kauan@minifs:/home/kauan$ chmod 644 documentos/notas.txt
permissões de documentos/notas.txt alteradas para 644 (rw-r--r--)
kauan@minifs:/home/kauan$ su visitante
visitante@minifs:/home/kauan$ cat documentos/notas.txt
Primeira linha do arquivo de notas.
```
O simulador implementa as **três classes de proteção** (owner/group/
public) exatamente como no Unix real: `check_permission` em
`filesystem.py` testa primeiro se o usuário atual é o dono (usa os 3
bits mais altos), senão se pertence ao mesmo grupo (3 bits do meio),
senão aplica os 3 bits de "outros". Além disso, regras finas do Unix
real foram replicadas de propósito:
- **`chmod` só pode ser feito pelo dono** do arquivo (não basta ter
  permissão de escrita nele).
- **`rm` exige permissão de escrita no diretório PAI**, não no próprio
  arquivo — por isso um arquivo em modo `000` ainda pode ser removido
  pelo seu dono (ver `test_rm_exige_escrita_no_diretorio_pai_nao_no_arquivo`
  nos testes).

### 5.4 Hard links (bônus) e alocação de blocos

```
kauan@minifs:/home/kauan$ ln documentos/notas.txt documentos/notas_link.txt
hard link criado: documentos/notas_link.txt -> mesmo inode de documentos/notas.txt
kauan@minifs:/home/kauan$ stat documentos/notas.txt
  Inode:   7
  Links:   2
  ...
```

**Comparação com `ln` real (`ls -li`):**
```
$ ln documentos/notas.txt documentos/notas_link.txt
$ ls -li documentos
2801668 -rw------- 2 root root 36 Jun 26 22:28 notas.txt
2801668 -rw------- 2 root root 36 Jun 26 22:28 notas_link.txt
```
Em ambos os casos, **dois nomes diferentes compartilham o mesmo número
de inode** e a coluna de contagem de links sobe para 2 — é a prova de
que o `link_count` do simulador se comporta exatamente como o do
sistema de arquivos real.

Para a alocação de blocos (objetivo 3.4), os comandos `df` e `diskmap`
mostram o disco simulado se enchendo conforme arquivos são escritos:
```
kauan@minifs:/home/kauan$ df
Disco simulado: 200 blocos x 32 bytes = 6400 bytes totais
Em uso: 6 blocos (192 bytes, 3.0%)
Livres: 194 blocos (6208 bytes)
kauan@minifs:/home/kauan$ diskmap
XXXXXX............................................
..................................................
('X' = bloco ocupado, '.' = bloco livre)
```

### 5.5 Tratamento de erros

```
kauan@minifs:/home/kauan$ cat arquivo_que_nao_existe.txt
erro: não encontrado: 'arquivo_que_nao_existe.txt' (em /home/kauan)
kauan@minifs:/home/kauan$ mkdir documentos
erro: já existe uma entrada chamada 'documentos' em /home/kauan
kauan@minifs:/home/kauan$ rmdir documentos
erro: diretório não vazio: 'documentos'
kauan@minifs:/home/kauan$ cd /lugar/que/nao/existe
erro: não encontrado: '/lugar/que/nao/existe' (em /)
```
Nenhum desses erros derruba o programa: cada operação de `FileSystem`
levanta uma exceção específica (`errors.py`) que o shell (`shell.py`)
captura e transforma em mensagem amigável — o usuário continua na mesma
sessão depois de qualquer erro.

Para ver a sessão completa (todos os objetivos + erros, de uma vez),
execute `python3 main.py --demo`.

---

## 6. Testes automatizados

A pasta `tests/` contém **36 testes unitários** (`unittest`, biblioteca
padrão) cobrindo cada objetivo específico do enunciado, incluindo casos
de erro e os comportamentos mais sutis (mv preserva o inode, cp cria um
inode independente, rm decrementa link_count corretamente, disco cheio
levanta erro, etc.):

```bash
$ python3 -m unittest discover -s tests -v
...
Ran 36 tests in 0.002s

OK
```

---

## 7. Funcionalidades bônus implementadas

- **Hard links** (`ln origem link`): múltiplas entradas de diretório
  compartilhando o mesmo inode/FCB, com contagem de links (`link_count`)
  controlando quando os blocos de dados são de fato liberados.
- **`find`**: busca recursiva por substring no nome, percorrendo toda a
  árvore de diretórios a partir da raiz.
- **`tree`**: desenha a árvore de diretórios com conectores visuais
  (`├──`, `└──`), útil para visualizar a estrutura first-child/next-sibling.
- **`diskmap`**: visualização gráfica (texto) do bitmap de blocos livres
  e ocupados do disco simulado.
- **Tratamento de disco cheio** (`DiskFullError`), incluindo teste
  automatizado dedicado.

## 8. Limitações conhecidas

- Nomes de arquivo/diretório não podem conter espaços (limitação do
  parser de comandos do shell, não do `FileSystem` em si).
- Não há suporte a links simbólicos (apenas hard links), nem a
  alocação contígua/encadeada (apenas indexada) — escolha feita para
  manter o código focado e bem testado em vez de implementar todas as
  variantes superficialmente.
- O disco simulado existe apenas em memória RAM: ao fechar o programa,
  tudo é perdido (não há persistência em arquivo `.dat`/binário), pois
  o enunciado pede explicitamente um simulador "em memória".

---

## 9. Autoria

Trabalho desenvolvido para a disciplina de Sistemas Operacionais —
UNIVALI, curso de Ciência da Computação, Prof. Michael D. C. Alves.
