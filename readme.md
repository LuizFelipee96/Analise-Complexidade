# Análise de Complexidade

Repositório para estudo e implementação de **análise de complexidade de algoritmos**, com foco em Python e visualização em HTML.

> **Branch de referência:** `dev`  
> Este README descreve o projeto conforme a organização atual da branch de desenvolvimento.

---

## 📚 Objetivo do Projeto

O objetivo deste projeto é:

- Implementar algoritmos clássicos (busca, ordenação, estruturas de dados etc.) em **Python**;
- Estudar e comparar as suas **complexidades de tempo e espaço**;
- Fornecer uma **visualização** ou interface em **HTML** (e possivelmente CSS/JS) para demonstrar o comportamento e desempenho dos algoritmos;
- Servir como base de estudo para disciplinas de **Estruturas de Dados** e **Análise de Algoritmos**.

---

## 🧠 Conceitos de Complexidade

O projeto trabalha principalmente com:

- **Notação Big‑O** (pior caso)
- **Notação Big‑Ω** (melhor caso)
- **Notação Big‑Θ** (caso médio)
- Classificações típicas:
  - $O(1)$ – Tempo constante
  - $O(\log n)$ – Logarítmica
  - $O(n)$ – Linear
  - $O(n \log n)$ – Quase linear
  - $O(n^2)$, $O(n^3)$ – Polinomial
  - $O(2^n)$, $O(n!)$ – Exponencial / Fatorial

> A ideia é relacionar essas notações com a implementação prática dos algoritmos contidos neste repositório.

---

## 🗂 Estrutura do Projeto

> A estrutura abaixo é um **exemplo organizado**. Ajuste conforme a estrutura real da branch `dev`.

```text
Analise-Complexidade/
├─ src/
│  ├─ algoritmos/
│  │  ├─ busca_linear.py
│  │  ├─ busca_binaria.py
│  │  ├─ bubble_sort.py
│  │  ├─ insertion_sort.py
│  │  ├─ merge_sort.py
│  │  └─ quick_sort.py
│  ├─ estruturas/
│  │  ├─ fila.py
│  │  ├─ pilha.py
│  │  └─ lista_encadeada.py
│  ├─ analise/
│  │  ├─ medidor_tempo.py
│  │  └─ comparador_complexidade.py
│  └─ main.py
├─ web/
│  ├─ index.html
│  ├─ assets/
│  │  ├─ style.css
│  │  └─ scripts.js
├─ tests/
│  ├─ test_buscas.py
│  ├─ test_ordenacoes.py
│  └─ test_estruturas.py
├─ requirements.txt
└─ README.md
```

- **`src/algoritmos/`** – Implementações de algoritmos com comentários sobre complexidade.
- **`src/estruturas/`** – Estruturas de dados básicas usadas nos exemplos.
- **`src/analise/`** – Funções auxiliares para medir tempo de execução, contar operações, gerar gráficos etc.
- **`web/`** – Parte em **HTML** (e CSS/JS) para visualização dos algoritmos e resultados.
- **`tests/`** – Testes automatizados (se estiverem presentes no projeto).
- **`requirements.txt`** – Dependências em Python.

---

## ⚙️ Requisitos

Antes de rodar o projeto, certifique‑se de ter:

- **Python 3.8+** instalado
- **pip** (gerenciador de pacotes do Python)

Instalação das dependências:

```bash
pip install -r requirements.txt
```

Se o projeto não possuir um `requirements.txt`, você pode instalá‑las manualmente (por exemplo):

```bash
pip install matplotlib numpy
```

(Ajuste aqui de acordo com as libs realmente usadas no seu projeto.)

---

## ▶️ Como Executar

### 1. Execução via linha de comando (Python)

No diretório raiz do projeto, execute:

```bash
python -m src.main
```

ou, se o entrypoint for outro arquivo, por exemplo:

```bash
python src/main.py
```

Você pode configurar argumentos como:

```bash
python src/main.py --algoritmo bubble_sort --tamanho 1000
```

> Substitua pelos parâmetros reais definidos na branch `dev`.

### 2. Execução do script de análise avançada (Iterum)

Para rodar a análise avançada de complexidade e gerar os resultados:

```bash
python iterum_avancado.py
```

Esse script é responsável por gerar os resultados que alimentam o dashboard e o arquivo JSON utilizado pelo frontend.

### 3. Rodar o dashboard

O projeto disponibiliza um dashboard para visualização dos resultados de análise.

#### Dashboard local

Para executar o dashboard localmente:

```bash
python dashboard.py
```

Após executar, verifique no terminal em qual porta o dashboard foi iniciado (por exemplo, `http://localhost:8050` ou similar).

#### Dashboard publicado

Você também pode acessar a versão publicada do dashboard em:

- [Dashboard Iterum (online)](https://l1nq.com/dashboarditerum)

> O link acima aponta para a versão mais recente do dashboard em produção.

### 4. Integração com o frontend

Os resultados das execuções são consolidados no arquivo:

- `resultados_iterum.json`

Esse arquivo JSON contém os dados que podem ser consumidos pelo **frontend** (por exemplo, pela interface HTML/JS ou por outros clientes), permitindo integração com dashboards, gráficos e visualizações customizadas.

---

## 🧪 Testes

Se houver testes automatizados, execute:

```bash
pytest
```

ou:

```bash
python -m unittest
```

(Ajuste para o framework que você realmente está usando.)

---

## 📊 Exemplos de Algoritmos Implementados

Alguns exemplos típicos que este projeto pode conter:

- **Busca**
  - Busca Linear – $O(n)$
  - Busca Binária – $O(\log n)$ (para listas ordenadas)
- **Ordenação**
  - Bubble Sort – $O(n^2)$
  - Insertion Sort – $O(n^2)$
  - Merge Sort – $O(n \log n)$
  - Quick Sort – $O(n \log n)$ (médio) / $O(n^2)$ (pior)
- **Estruturas de Dados**
  - Pilha (Stack)
  - Fila (Queue)
  - Lista Encadeada

> Preencha esta seção listando exatamente os algoritmos que você implementou.

---

## 📈 Medição de Desempenho

A análise de complexidade pode ser feita de duas formas principais:

1. **Teórica** – por meio da contagem de operações em função de $n$;
2. **Empírica** – medindo o tempo de execução com diferentes tamanhos de entrada.

Exemplo de abordagem (ilustrativo):

```python
from analise.medidor_tempo import medir_tempo
from algoritmos.bubble_sort import bubble_sort

tempos = []
for n in [100, 1000, 5000, 10000]:
    lista = gerar_lista_aleatoria(n)
    t = medir_tempo(bubble_sort, lista)
    tempos.append((n, t))

print(tempos)
```

Depois, esses resultados podem ser:

- Plotados em gráficos (ex.: `matplotlib`);
- Exibidos na interface HTML (`web/index.html`) ou no dashboard Python.

---

## 📄 Licença

Informe aqui a licença do projeto, por exemplo:

- MIT
- GPLv3
- Apache 2.0

Exemplo:

> Este projeto está licenciado sob os termos da licença **MIT**. Consulte o arquivo `LICENSE` para mais detalhes.

---
