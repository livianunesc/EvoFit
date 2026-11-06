# EvoFit / Focus — direção visual

A interface segue as referências visuais enviadas: contraste de preto/branco/verde-lima, organização de um painel esportivo e seleção de treinos inspirada em cards de produto com um item ativo em destaque. Nenhum logotipo ou conteúdo da Starbucks foi incorporado.

## Paleta

| Papel | Cor |
| --- | --- |
| Verde-lima principal | `#BAF51A` |
| Verde claro de apoio | `#D4ED93` |
| Branco quente | `#FEF9F5` |
| Preto | `#11120E` |

Os valores seguem as cores visuais da referência; algumas legendas hexadecimais na própria imagem não correspondem aos tons exibidos. O contraste e a hierarquia usam os tons efetivamente mostrados.

Barlow Condensed 700/800 dá ritmo aos títulos; Manrope sustenta os dados e formulários. Ambas são servidas localmente com licença OFL. A fotografia de abertura é uma composição original gerada para o projeto; a atleta é fictícia. Diagramas de execução anteriores foram preservados.

## Interação e dados

O carrossel não gira sozinho: usuário escolhe por setas, indicadores, teclado ou swipe. Somente treinos atribuídos entram na seleção. As séries, repetições, descanso, observações, carga e conclusão de exercício continuam disponíveis no detalhe. A conclusão é salva no banco e retoma depois de sair/recarregar.

O painel mostra registros reais: contagem de treinos, dias ativos, exercícios, maior carga registrada, frequência e calendário. Não há hidratação, calorias, sono ou metas inventadas. O ranking mensal/geral deriva do vínculo real com o personal e conta treinos completos; não mistura equipes.

A navegação deixou de exibir dieta, perfil e medidas. Os dados antigos permanecem no banco e nos backups. O personal mantém a gestão de atletas e prescrição de treinos.

Animações usam principalmente transform/opacity: entrada de tela, feedback de botão, avanço do treino e celebração breve. `prefers-reduced-motion` suprime esses efeitos. Formulários e operações têm feedback, estados de salvamento e erros; respostas de uma sessão antiga são descartadas após logout/troca de conta.
