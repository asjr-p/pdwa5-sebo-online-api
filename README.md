**Para baixar os requisitos:**

*Para Windows:*
1. Instale o ambiente virtual para baixar as dependências do projeto: python -m venv venv ()
2. Ative seu ambiente virtual: /venv/Scripts/activate
3. Baixe as dependências listadas no arquivo requirements.txt: pip install -r requirements.txt

**Regras de requisições:**

- Todos os endpoints devem conter tokens que são gerados após o login.
- Insira o token no cabeçalho da requisição da seguinte forma:
- Key (Chave): Authorization
- Value (Valor): \<token\>
