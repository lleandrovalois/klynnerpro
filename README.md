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

## 🌐 Como Hospedar no Render (Render.com)

O projeto já inclui o arquivo `render.yaml` e `Dockerfile` configurados para deploy gratuito e instantâneo no Render.

### Método 1: Deploy Automático via Blueprint (Recomendado)
1. Acesse o painel do [Render Dashboard](https://dashboard.render.com).
2. Clique em **New +** e selecione **Blueprint**.
3. Conecte o repositório `https://github.com/lleandrovalois/klynnerpro`.
4. O Render detectará automaticamente o arquivo `render.yaml` e provisionará o serviço web.
5. Clique em **Apply** e sua aplicação estará online em poucos minutos com URL pública HTTPS (ex: `https://klynner-pdf.onrender.com`).

### Método 2: Criação Manual de Web Service no Render
1. No [Render Dashboard](https://dashboard.render.com), clique em **New +** &rarr; **Web Service**.
2. Conecte seu repositório `klynnerpro`.
3. Preencha os campos:
   - **Name:** `klynner-pdf`
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Selecione o plano **Free** e clique em **Deploy Web Service**.

---

## 🛠️ Suíte Completa de Ferramentas (12 Funcionalidades)

Klynner PDF PRO disponibiliza uma plataforma unificada de alta performance dividida em 3 categorias essenciais:

### 📄 Organização de Páginas
1. **Unir PDFs (Merge):** Concatena múltiplos PDFs com geração automática de Menu de Documentos clicável, marcadores hierárquicos e linearização Fast Web View.
2. **Dividir PDF (Split):** Separação por intervalos customizados (ex: `1-3, 4-8`) ou extração individual de cada página (Modo Burst) empacotada em arquivo ZIP otimizado.
3. **Organizar Páginas:** Visualização em grade interativa para reordenar via drag & drop, girar ou excluir páginas individuais.
4. **Girar Páginas:** Rotação de 90°, 180° ou 270° em lote ou página a página com visualização imediata.
5. **Extrair Páginas:** Extraia páginas selecionadas para um novo PDF unificado ou separe-as em páginas avulsas compactadas em ZIP.

### 🔒 Segurança & Privacidade
6. **Proteger com Senha:** Criptografia padrão industrial AES de 128 e 256 bits com senha de abertura e controle granular de permissões (impressão, cópia, edição).
7. **Desproteger PDF:** Remoção rápida de senhas e restrições de permissões de documentos autenticados.
8. **Ocultar Dados Sensíveis (Redação):** Tarjamento definitivo de CPF, CNPJ, e-mails, telefones ou termos customizados, removendo os metadados do fluxo binário.
9. **Inserir Marca d'água:** *(NOVO)* Aplicação de marcas d'água profissionais em texto ou imagem (logotipos):
   - **Modo Texto:** Presets rápidos (*CONFIDENCIAL*, *RASCUNHO*, *CÓPIA*, *APROVADO*), fontes, cores, controle de opacidade e ângulo.
   - **Mosaico Anti-Cópia (Tiling):** Grade de texto repetida por toda a página para máxima proteção contra vazamentos.
   - **Modo Logotipo / Imagem:** Upload de PNG/JPG com escala proporcional e transparência ajustável.
   - **Controle de Camada e Páginas:** Inserir na frente (sobreposição) ou atrás do conteúdo, em todas as páginas, apenas na primeira ou em intervalos personalizados.

### 🔄 Conversão & Inteligência
10. **Imagem para PDF:** *(NOVO)* Conversão de imagens avulsas ou em lote (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tiff`):
    - Correção automática de rotação EXIF (fotos de celulares/câmeras).
    - Formatos: Tamanho original da imagem, A4 ou Carta.
    - Orientação inteligente: Automática, Retrato ou Paisagem.
    - Margens configuráveis: Sem margem, Margem Compacta ou Margem Ampla.
    - Reordenação interativa das imagens antes da compilação.
11. **PDF para Word (DOCX):** Extração e conversão de textos, tabelas e estruturas para documentos editáveis do Microsoft Word.
12. **Word para PDF:** Conversão de `.docx` para PDF preservando formatação e estilos.

---

## 🚀 Como Executar o Projeto

### Pré-requisitos
- **Python 3.10+** (já instalado e configurado no ambiente local)

### Passo a Passo

1. **Abra o terminal na pasta do projeto:**
   ```powershell
   cd c:\workspace\klynnerpro
   ```

2. **Inicie o servidor:**
   Execute o script inicializador usando o ambiente virtual criado para o projeto:
   ```powershell
   .\.venv\Scripts\python.exe run.py
   ```

3. **Acesse no seu navegador:**
   Abra [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 🌐 Como Hospedar no Render (Render.com)

O projeto já inclui o arquivo `render.yaml` e `Dockerfile` configurados para deploy gratuito e instantâneo no Render.

### Método 1: Deploy Automático via Blueprint (Recomendado)
1. Acesse o painel do [Render Dashboard](https://dashboard.render.com).
2. Clique em **New +** e selecione **Blueprint**.
3. Conecte o repositório `https://github.com/lleandrovalois/klynnerpro`.
4. O Render detectará automaticamente o arquivo `render.yaml` e provisionará o serviço web.
5. Clique em **Apply** e sua aplicação estará online em poucos minutos com URL pública HTTPS (ex: `https://klynner-pdf.onrender.com`).

---

## 📁 Estrutura de Arquivos

```
klynnerpro/
├── .venv/                   # Ambiente virtual Python
├── app/
│   ├── __init__.py
│   ├── main.py              # Endpoints FastAPI, rotas e ciclo de vida
│   ├── merger.py            # Motor de fusão QPDF/C++ e fallback PyPDF
│   ├── splitter.py          # Divisão por intervalos e modo burst (ZIP)
│   ├── organizer.py         # Reordenação, duplicação e remoção de páginas
│   ├── rotator.py           # Rotação de páginas (90°, 180°, 270°)
│   ├── extractor.py         # Extração seletiva (Merge ou Split)
│   ├── protector.py         # Criptografia AES 128/256 bits e remoção de senhas
│   ├── redactor.py          # Tarjamento irreversível de dados sensíveis
│   ├── watermark.py         # Motor de marcas d'água (texto, mosaico e logotipos)
│   ├── image_to_pdf.py      # Conversor de imagens para PDF com suporte a EXIF
│   ├── pdf_to_word.py       # Conversor de PDF para Word (DOCX)
│   ├── word_to_pdf.py       # Conversor de Word (DOCX) para PDF
│   ├── analytics.py         # Inspeção de metadados e integridade de PDFs
│   ├── storage.py           # Streaming contínuo em disco e gestão de sessões
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Design System moderno em Glassmorphism
│   │   └── js/
│   │       └── app.js       # Controladores dinâmicos, sliders, color-pickers e drag-and-drop
│   └── templates/
│       └── index.html       # Interface web SPA semântica e responsiva
├── test_all_features.py     # Suite de testes de integração (10 testes)
├── test_new_features.py     # Suite de testes para Imagem to PDF e Marca d'água
├── requirements.txt         # Dependências do projeto
├── run.py                   # Script de inicialização rápida
└── README.md                # Documentação técnica completa
```
