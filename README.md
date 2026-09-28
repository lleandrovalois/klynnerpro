# 📑 Klynner PDF
> **União inteligente, limpa e estruturada de grandes arquivos PDF**  
> *(Nome inspirado e em homenagem a Klynnier, em um trocadilho com "Cleaner" — uma solução mais limpa, ágil e elegante para organizar documentos).*

Aplicação web moderna, segura e de alto desempenho desenvolvida especialmente para **juntar grandes arquivos PDF** (livros, catálogos, relatórios analíticos e processos com centenas de páginas ou múltiplos gigabytes), gerando automaticamente um **Menu de Documentos interativo** com links clicáveis e marcadores de navegação.

---

## ⚡ Por que esta solução suporta arquivos PDF gigantes?

A maioria dos unificadores de PDF comuns (especialmente ferramentas puramente baseadas em JavaScript no navegador ou scripts básicos em Python) falham ao lidar com arquivos grandes porque tentam carregar e descompactar os documentos inteiros na memória RAM, causando travamentos (*Out of Memory* / congelamento de navegador).

O **PDF Merger Pro** foi projetado com uma arquitetura industrial de alto rendimento:

1. **Gravação Contínua em Disco (Streaming Zero-RAM):** O upload dos arquivos é processado em blocos (*chunks*) de 1 MB diretamente para o disco, mantendo o consumo de memória do servidor estável em poucos megabytes, mesmo se o usuário enviar arquivos de 500 MB ou 2 GB.
2. **Motor QPDF C++ (via PikePDF):** Utiliza ligações nativas em C++ da biblioteca QPDF. Os objetos e streams de imagens/fontes dos PDFs são concatenados no nível binário **sem necessidade de descompressão prévia**.
3. **Menu de Documentos Interativo Duplo:**
   - **Página 1 (Sumário Visual com Hiperlinks):** Cria uma página inicial estilizada com a listagem numerada de todos os arquivos. Ao clicar no nome de qualquer arquivo nesta página, o leitor navega imediatamente para o início daquele documento.
   - **Menu Lateral de Navegação (Marcadores com `/UseOutlines`):** Configura o catálogo do PDF para abrir automaticamente o painel lateral de sumário/marcadores com o nome de cada arquivo em leitores como Adobe Acrobat, Google Chrome, Edge e Firefox.
4. **Linearização (Fast Web View):** O PDF unificado resultante é linearizado automaticamente, permitindo que visualizadores de PDF abram a primeira página e o menu instantaneamente.
5. **Fallback com PyPDF:** Caso algum arquivo apresente cabeçalhos não-padronizados ou corrupções parciais, o sistema aciona automaticamente o motor secundário de tolerância a falhas.
6. **Privacidade e Isolamento por Sessão:** Cada processamento ocorre em um diretório temporário isolado por UUID, com limpeza automática programada.

---

## 🚀 Como Executar o Projeto

### Pré-requisitos
- **Python 3.10+** (já instalado e configurado no ambiente local)

### Passo a Passo

1. **Abra o terminal na pasta do projeto:**
   ```powershell
   cd C:\Users\valoi\.gemini\antigravity-ide\scratch\pdf-merger-pro
   ```

2. **Inicie o servidor:**
   Execute o script inicializador usando o ambiente virtual criado para o projeto:
   ```powershell
   .\.venv\Scripts\python.exe run.py
   ```

3. **Acesse no seu navegador:**
   Abra [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 🖥️ Recursos da Interface Web

- **Arrastar e Soltar (Drag & Drop):** Envie múltiplos PDFs simultaneamente ou adicione mais arquivos a qualquer momento.
- **Reordenação Interativa:** Ordene os arquivos arrastando os cartões ou usando os botões de subir/descer para garantir a sequência exata das páginas.
- **Barra de Progresso com Feedback em Tempo Real:** Acompanhamento visual da transferência para o disco e das etapas de fusão binária.
- **Opções Personalizáveis:**
  - Nome do arquivo unificado customizável.
  - Marcadores/Sumário estruturado ativável/desativável.
  - Otimização Fast Web View (Linearização) configurável.
- **Pré-Visualização Integrada:** Veja o PDF resultante diretamente na aplicação antes ou após o download.
- **Métricas do Processamento:** Exibe tempo de execução, total de páginas geradas e tamanho final do arquivo.

---

## 📁 Estrutura de Arquivos

```
pdf-merger-pro/
├── .venv/                   # Ambiente virtual com PikePDF, PyPDF e FastAPI
├── app/
│   ├── __init__.py
│   ├── main.py              # Endpoints FastAPI e ciclo de vida
│   ├── merger.py            # Motor de fusão QPDF/C++ e fallback PyPDF
│   ├── storage.py           # Gestão de streaming em disco e limpeza de sessões
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Estilização moderna com Glassmorphism
│   │   └── js/
│   │       └── app.js       # Lógica cliente, drag-and-drop e visualização
│   └── templates/
│       └── index.html       # Interface web semântica e responsiva
├── temp_workspaces/         # Armazenamento temporário isolado
├── requirements.txt         # Lista congelada de dependências
├── run.py                   # Script de execução rápida
└── README.md                # Documentação técnica
```
