# EvoFit — interface e organização visual

**Autora:** Livia Nunes Coelho

**Disciplina:** Desenvolvimento de Websites

## Estrutura de navegação

A aplicação utiliza HTML semântico e navegação multipágina. A página `index.html` contém o acesso e o painel; as páginas de alunos, exercícios, treinos e relatórios ficam em `pages/`. A interface reduzida em `apresentacao/` permite demonstrar o fluxo de consulta e conclusão no mesmo servidor.

Cada tela contém cabeçalho, navegação, área principal, títulos hierarquizados e rodapé. Os formulários usam labels associados aos campos, atributos required e limites compatíveis com a validação do servidor.

## Identidade visual

A folha `css/estilo.css` centraliza cores, tipografia e componentes. O contraste entre fundo claro, texto escuro e verde-lima destaca títulos, ações e indicadores.

| Variável | Cor | Aplicação |
| --- | --- | --- |
| `--lima` | `#d7fd71` | Ações e indicadores de destaque |
| `--preto` | `#171a12` | Texto e botões principais |
| `--fundo` | `#f5f6f0` | Fundo das páginas |
| `--cinza` | `#66705b` | Textos secundários |
| `--borda` | `#dfe4d5` | Delimitação de componentes |
| `--branco` | `#ffffff` | Cartões e formulários |

Barlow Condensed é utilizada nos títulos e Manrope nos textos. As fontes são servidas localmente, com as licenças descritas em [ASSETS.md](ASSETS.md).

## Responsividade e acessibilidade

Grid e Flexbox organizam cartões, formulários e indicadores. Media queries ajustam a navegação, o número de colunas e os espaçamentos para telas menores. As tabelas possuem rolagem no próprio componente, preservando a largura da página.

Os campos têm identificação textual; botões têm foco visível; regiões de status usam `aria-live` para comunicar carregamento, sucesso e erro. O CSS respeita `prefers-reduced-motion`.

## Interação com os dados

O JavaScript usa eventos e Fetch para consultar e alterar dados. Os textos recebidos são inseridos com `textContent`. Durante as operações, o botão de envio fica indisponível e a região de status informa o resultado.

O painel, o histórico e o ranking são calculados a partir dos registros MySQL. As contas e atividades demonstrativas são fictícias, persistidas na mesma estrutura relacional. O aluno deve preencher as cargas e marcar todos os exercícios antes da conclusão; uma ficha alterada pelo personal exige atualização da página.

## Evidências

As capturas `docs/imagens/principal-desktop.png`, `principal-mobile.png`, `apresentacao-desktop.png` e `apresentacao-mobile.png` registram as interfaces verificadas no navegador. Os procedimentos estão em [VALIDACAO_ACADEMICA.md](VALIDACAO_ACADEMICA.md).
