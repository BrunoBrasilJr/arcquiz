# ArcQuiz

Aplicação web de quiz desenvolvida em Python utilizando Flask e SQLite.

---

## 🚀 Sobre o projeto

ArcQuiz é uma aplicação web interativa que permite ao usuário:

- Selecionar a quantidade de perguntas
- Responder ao quiz com perguntas embaralhadas automaticamente
- Visualizar o resultado ao final
- Registrar o desempenho em um ranking local persistido em banco de dados

O projeto foi construído com foco em organização, clareza e estrutura escalável.

---

## 🛠️ Tecnologias utilizadas

- Python
- Flask
- SQLite
- HTML5
- CSS3

---

## 📂 Estrutura do projeto

arcquiz/
├── app.py
├── requirements.txt
├── static/
│   ├── style.css
│   └── favicon.ico
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── quiz.html
│   ├── result.html
│   └── highscores.html
└── data/
    └── questions.json

---

## ⚙️ Como executar o projeto

git clone https://github.com/BrunoBrasilJr/arcquiz.git
cd arcquiz
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py

Acesse: http://127.0.0.1:5000

---

## 🎯 Funcionalidades

- Seleção dinâmica da quantidade de perguntas
- Perguntas embaralhadas automaticamente
- Sistema de pontuação
- Ranking persistido com SQLite
- Interface moderna e responsiva

---

Primeiro projeto web em Python utilizando Flask.

Desenvolvido por Bruno Brasil