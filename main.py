import mysql.connector
import datetime
import jwt

from flask import Flask, jsonify, request
from hashlib import sha256
from flasgger import Swagger

# conexão com DB
mydb = mysql.connector.connect(
    host="host",
    user="user",
    password="password",
    database="database",
    port=0000,
)

# agente DB
my_cursor = mydb.cursor()

# Instanciando Flask
app = Flask(__name__)
swagger = Swagger(app)
# MANAGE TOKEN


def generate_token(user_name):
    payload = {
        "sub": user_name,
        "exp": (datetime.datetime.utcnow() + datetime.timedelta(hours=1)),
    }
    token = jwt.encode(payload=payload, key="SECRET_KEY")
    return token


def get_authenticated_user():
    token = request.headers.get("Authorization")

    if not token:
        return None

    try:
        # Decodifique o token JWT usando a chave secreta
        payload = jwt.decode(token, key="SECRET_KEY", algorithms=["HS256"])
        print(payload["sub"])
        return payload["sub"]

    except jwt.ExpiredSignatureError:  # type: ignore
        return "O TOKEN EXPIROU !!!!!!!!", None  # Token expirado

    except jwt.InvalidTokenError:  # type: ignore
        return "O TOKEN INVALIDO !!!!!!", None  # Token inválido


def have_perm(user_id):
    sql = f"SELECT usertype FROM users WHERE idusers = {user_id}"
    my_cursor.execute(sql)
    result = my_cursor.fetchall()

    if result[0][0] == "admin" or result[0][0] == "vendedor":
        return True

    return None


def check_password(email_db, passw_login):
    passw_login_hash = sha256(passw_login.encode()).hexdigest()

    sql = f"SELECT password FROM users WHERE email = '{email_db}'"
    my_cursor.execute(sql)
    passw_db = my_cursor.fetchall()

    if passw_db[0][0] == passw_login_hash:
        return True

    return None


# USERS


@app.route("/users/signup", methods=["POST"])
def create_user():
    """
    Create a new user.
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: The name of the user.
            email:
              type: string
              description: The email of the user.
            password:
              type: string
              description: The password of the user.
            usertype:
              type: string
              description: The type of the user (admin, vendedor, etc.).
            status:
              type: string
              description: The status of the user.
    responses:
      201:
        description: User created successfully.
      400:
        description: Email already registered.
      500:
        description: Internal server error.
    """
    new_user = request.get_json()
    email = new_user.get("email")

    # Verifique se o email já está cadastrado
    sql_check_email = "SELECT email FROM users WHERE email = %s"
    my_cursor.execute(sql_check_email, (email,))
    existing_email = my_cursor.fetchone()

    if existing_email:
        return "Email já cadastrado", 400

    # Hash da senha
    hashed_password = sha256(new_user["password"].encode()).hexdigest()

    # Inserir o novo usuário no banco de dados
    sql_insert_user = "INSERT INTO users (name, email, password, usertype, status) VALUES (%s, %s, %s, %s, %s)"
    user_data = (
        new_user["name"],
        email,
        hashed_password,
        new_user["usertype"],
        new_user["status"],
    )

    try:
        my_cursor.execute(sql_insert_user, user_data)
        mydb.commit()
    except Exception as e:
        return str(e), 500

    return jsonify(new_user), 201


@app.route("/admin/users", methods=["GET"])
def get_users():
    """
    Get a list of users (admin only).
    ---
    responses:
      200:
        description: List of users retrieved successfully.
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  ID:
                    type: integer
                    description: The unique identifier of the user.
                  name:
                    type: string
                    description: The name of the user.
                  email:
                    type: string
                    description: The email of the user.
                  usertype:
                    type: string
                    description: The type of the user.
                  status:
                    type: string
                    description: The status of the user.
      403:
        description: Only admins are allowed to list users.
    """
    id_by_token = get_authenticated_user()

    if not have_perm(id_by_token):
        return {"message": "Apenas admins podem listar usuários"}, 403

    # Consulta SQL para selecionar os usuários
    sql_select_users = "SELECT * FROM users"
    my_cursor.execute(sql_select_users)
    users_db = my_cursor.fetchall()

    # Converter os resultados da consulta em um formato JSON
    users_converted = [
        {
            "ID": user[0],
            "name": user[1],
            "email": user[2],
            "password": user[3],  # Considere não retornar a senha no JSON
            "usertype": user[4],
            "status": user[5],
        }
        for user in users_db
    ]

    # Retornar os usuários com uma resposta HTTP 200 OK
    return jsonify(users_converted), 200


@app.route("/admin/login", methods=["POST"])
def login_admin():
    """
    Admin login.
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              description: The email of the admin.
            password:
              type: string
              description: The password of the admin.
    responses:
      200:
        description: Admin logged in successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                token:
                  type: string
                  description: The JWT token for authentication.
                message:
                  type: string
                  description: A success message.
      400:
        description: Incomplete credentials provided.
      401:
        description: Invalid credentials or deactivated user.
      403:
        description: User account is deactivated.
    """
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {"message": "Credenciais incompletas"}, 400

    sql = f"SELECT * FROM users WHERE email = '{email}'"
    my_cursor.execute(sql)
    user_db = my_cursor.fetchone()

    if user_db is None:
        return {"message": "Credenciais inválidas"}, 401

    sql_status = user_db[5]

    if sql_status == "deactivated":
        return {"message": "Seu usuário está desativado"}, 403

    if check_password(user_db[2], password):
        # Gere um token JWT
        token = generate_token(user_db[0])
        response_data = {"token": str(token), "message": "Login bem-sucedido"}
        return response_data, 200

    return {"message": "Credenciais inválidas"}, 401


@app.route("/login", methods=["POST"])
def login():
    """
    User login.
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              description: The email of the user.
            password:
              type: string
              description: The password of the user.
    responses:
      200:
        description: User logged in successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                token:
                  type: string
                  description: The JWT token for authentication.
                message:
                  type: string
                  description: A success message.
      401:
        description: Invalid credentials or unsupported user type.
      403:
        description: User account is deactivated.
    """
    data = request.get_json()
    email = data["email"]
    passw = data["password"]
    user_db = None

    sql = f"SELECT * FROM users WHERE email = '{email}'"
    my_cursor.execute(sql)
    user_db = my_cursor.fetchall()

    sql_status = user_db[0][5]

    if sql_status == "deactivated":
        return "Seu usuario está desativado"

    elif user_db is not None and check_password(email, passw):
        if user_db[0][4] == "vendedor":
            # Gere um token JWT
            token = generate_token(user_db[0])
            response_data = {"token": str(token), "message": "Login bem-sucedido"}
            return response_data, 200

        elif user_db[0][4] == "coprador":
            response_data = {"message": "Login bem-sucedido"}
            return response_data, 200

        return {"message": "Tipo de Usuario não aceito"}, 401

    return {"message": "Credenciais inválidas ou tipo de usuario não aceito"}, 401


@app.route("/user/<int:id>", methods=["PUT"])  # type: ignore
def edit_perfil(id):
    """
    Edit user profile (admin or self-editing).
    ---
    parameters:
      - name: id
        in: path
        description: The ID of the user to edit.
        required: true
        type: integer
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: The updated name of the user.
            email:
              type: string
              description: The updated email of the user.
            password:
              type: string
              description: The updated password of the user.
            usertype:
              type: string
              description: The updated type of the user.
            status:
              type: string
              description: The updated status of the user.
    responses:
      200:
        description: User profile updated successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                  description: The updated name of the user.
                email:
                  type: string
                  description: The updated email of the user.
                usertype:
                  type: string
                  description: The updated type of the user.
                status:
                  type: string
                  description: The updated status of the user.
      403:
        description: You can only edit your own profile or you need admin privileges.
      404:
        description: User ID not found.
    """
    id_by_token = get_authenticated_user()
    sql = f"SELECT usertype FROM users WHERE idusers = {id_by_token}"
    my_cursor.execute(sql)
    result_id = my_cursor.fetchone()

    sql = f"SELECT usertype FROM users WHERE idusers = {id_by_token}"
    my_cursor.execute(sql)
    result_usertype_db_token = my_cursor.fetchall()

    if id_by_token == id or result_usertype_db_token[0][0] == "admin":
        user_edited = request.get_json()
        hash_passw = sha256(user_edited["password"].encode()).hexdigest()
        sql = "UPDATE users SET name = %s, email = %s, password = %s, usertype = %s, status = %s WHERE idusers = %s"
        values = (
            user_edited.get("name"),
            user_edited.get("email"),
            hash_passw,
            user_edited.get("usertype"),
            user_edited.get("status"),
            id,
        )
        my_cursor.execute(sql, values)
        mydb.commit()
        return jsonify(user_edited)

    elif result_usertype_db_token[0][0] != "admin":
        return jsonify({"message": "Você só pode editar seu próprio usuário"})

    elif not result_id:
        return jsonify({"message": "ID não encontrado"}), 404


@app.route("/admin/users/softdelete/<int:id>", methods=["DELETE"])  # type: ignore
def delete_user(id):
    """
    Soft delete a user (admin only).
    ---
    parameters:
      - name: id
        in: path
        description: The ID of the user to soft delete.
        required: true
        type: integer
    responses:
      200:
        description: User soft deleted successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  description: A success message.
      403:
        description: Only admins are allowed to delete users.
      404:
        description: User ID not found.
    """
    # Verificar se o ID do usuário existe
    sql_check_id = f"SELECT idusers FROM users WHERE idusers = {id}"
    my_cursor.execute(sql_check_id)
    result_id = my_cursor.fetchone()

    if not result_id:
        return jsonify({"message": "ID não encontrado"}), 404

    id_by_token = get_authenticated_user()

    # Verificar permissões de exclusão
    if not have_perm(id_by_token):
        return {"message": "Apenas admins podem deletar usuários"}, 403

    # Verificar se o usuário a ser excluído existe
    sql = f"SELECT * FROM users WHERE idusers = {id}"
    my_cursor.execute(sql)
    user_db = my_cursor.fetchone()

    if user_db:
        # Inativar o usuário
        sql = f"UPDATE users SET status = 'deactivated' WHERE idusers = {id}"
        my_cursor.execute(sql)
        mydb.commit()
        return {"message": "Usuário inativado com sucesso"}, 200

    return {"message": "Usuário não encontrado"}, 404


# ITEMS


@app.route("/items", methods=["GET"])
def get_books():
    """
    Get a list of items.
    ---
    responses:
      200:
        description: List of items retrieved successfully.
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: The unique ID of the item.
                  Título:
                    type: string
                    description: The title of the item.
                  Autores:
                    type: string
                    description: The authors of the item.
                  Categoria:
                    type: string
                    description: The category of the item.
                  Preço:
                    type: number
                    description: The price of the item.
                  Status:
                    type: string
                    description: The status of the item.
      404:
        description: No items found.
    """
    # Consulta SQL para selecionar os itens
    my_cursor.execute("SELECT * FROM items")
    items_db = my_cursor.fetchall()

    # Converter os resultados da consulta em um formato JSON
    items_converted = [
        {
            "id": item[0],
            "Título": item[1],
            "Autores": item[2],
            "Categoria": item[3],
            "Preço": item[4],
            "Status": item[5],
        }
        for item in items_db
    ]

    # Retornar os itens com uma resposta HTTP 200 OK
    return jsonify(items_converted), 200


# Consult by ID -> OK


@app.route("/items/<int:id>", methods=["GET"])  # type: ignore
def get_book_by_id(id):
    """
    Get item by ID.
    ---
    parameters:
      - name: id
        in: path
        description: The ID of the item to retrieve.
        required: true
        type: integer
    responses:
      200:
        description: Item retrieved successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                id:
                  type: integer
                  description: The unique ID of the item.
                Título:
                  type: string
                  description: The title of the item.
                Autores:
                  type: string
                  description: The authors of the item.
                Categoria:
                  type: string
                  description: The category of the item.
                Preço:
                  type: number
                  description: The price of the item.
                Status:
                  type: string
                  description: The status of the item.
      404:
        description: Item not found.
    """
    # Consulta SQL para verificar se o ID do item existe
    sql_check_id = f"SELECT iditems FROM items WHERE iditems = {id}"
    my_cursor.execute(sql_check_id)
    result_id = my_cursor.fetchone()

    if not result_id:
        return jsonify({"message": "ID não encontrado"}), 404

    # Consulta SQL para selecionar o item por ID
    my_cursor.execute(f"SELECT * FROM items WHERE iditems = {id}")
    item_db = my_cursor.fetchone()

    if item_db:
        # Converter o resultado da consulta em um formato JSON
        item_converted = {
            "id": item_db[0],
            "Título": item_db[1],
            "Autores": item_db[2],
            "Categoria": item_db[3],
            "Preço": item_db[4],
            "Status": item_db[5],
        }
        # Retornar o item com uma resposta HTTP 200 OK
        return jsonify(item_converted), 200

    return jsonify({"message": "Item não encontrado"}), 404


# Make Book -> OK


@app.route("/items", methods=["POST"])
def make_book():
    """
    Create a new item.
    ---
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              Título:
                type: string
                description: The title of the item.
              Autores:
                type: string
                description: The authors of the item.
              Categoria:
                type: string
                description: The category of the item.
              Preço:
                type: number
                description: The price of the item.
              Status:
                type: string
                description: The status of the item.
    responses:
      201:
        description: Item created successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                Título:
                  type: string
                  description: The title of the created item.
                Autores:
                  type: string
                  description: The authors of the created item.
                Categoria:
                  type: string
                  description: The category of the created item.
                Preço:
                  type: number
                  description: The price of the created item.
                Status:
                  type: string
                  description: The status of the created item.
      403:
        description: Only admins and sellers are allowed to create items.
      409:
        description: This product has already been created.
    """
    new_book = request.get_json()

    # Verificar se o título do livro já existe
    sql_check_title = f"SELECT titulo FROM items WHERE titulo = '{new_book['Título']}'"
    my_cursor.execute(sql_check_title)
    existing_title = my_cursor.fetchone()

    if existing_title:
        return {"message": "Esse produto já foi criado"}, 409

    id_by_token = get_authenticated_user()

    if not have_perm(id_by_token):
        return {"message": "Apenas admins e vendedores podem criar itens"}, 403

    # Inserir o novo livro no banco de dados
    sql_insert_book = "INSERT INTO items (titulo, autor, categoria, preco, status) VALUES (%s, %s, %s, %s, %s)"
    book_data = (
        new_book["Título"],
        new_book["Autores"],
        new_book["Categoria"],
        new_book["Preço"],
        new_book["Status"],
    )

    my_cursor.execute(sql_insert_book, book_data)
    mydb.commit()

    return jsonify(new_book), 201


# Edit By ID -> OK


@app.route("/items/<int:id>", methods=["PUT"])  # type: ignore
def edit_book_by_id(id):
    """
    Update an existing item by ID.
    ---
    parameters:
      - name: id
        in: path
        description: The ID of the item to update.
        required: true
        type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              Título:
                type: string
                description: The updated title of the item.
              Autores:
                type: string
                description: The updated authors of the item.
              Categoria:
                type: string
                description: The updated category of the item.
              Preço:
                type: number
                description: The updated price of the item.
              Status:
                type: string
                description: The updated status of the item.
    responses:
      200:
        description: Item updated successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                Título:
                  type: string
                  description: The updated title of the item.
                Autores:
                  type: string
                  description: The updated authors of the item.
                Categoria:
                  type: string
                  description: The updated category of the item.
                Preço:
                  type: number
                  description: The updated price of the item.
                Status:
                  type: string
                  description: The updated status of the item.
      403:
        description: Only admins and sellers are allowed to edit items.
      404:
        description: Item not found.
    """
    # Verificar se o ID do livro existe
    sql_check_id = f"SELECT iditems FROM items WHERE iditems = {id}"
    my_cursor.execute(sql_check_id)
    result_id = my_cursor.fetchone()

    if not result_id:
        return jsonify({"message": "ID não encontrado"}), 404

    id_by_token = get_authenticated_user()

    if not have_perm(id_by_token):
        return {"message": "Apenas admins e vendedores podem editar itens"}, 403

    book_edited = request.get_json()

    # Atualizar os dados do livro no banco de dados
    sql_update_book = "UPDATE items SET titulo = %s, autor = %s, categoria = %s, preco = %s, status = %s WHERE iditems = %s"
    book_data = (
        book_edited.get("Título"),
        book_edited.get("Autores"),
        book_edited.get("Categoria"),
        book_edited.get("Preço"),
        book_edited.get("Status"),
        id,
    )

    my_cursor.execute(sql_update_book, book_data)
    mydb.commit()

    if my_cursor.rowcount > 0:
        return jsonify(book_edited), 200
    else:
        return jsonify({"message": "ID não encontrado"}), 404


# Soft Delete -> OK


@app.route("/items/disable/<int:id>", methods=["DELETE"])
def delete_book(id):
    """
    Disable an existing item by ID.
    ---
    parameters:
      - name: id
        in: path
        description: The ID of the item to disable.
        required: true
        type: integer
    responses:
      200:
        description: Item disabled successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  description: A message confirming the item was disabled.
      204:
        description: No item was affected.
      403:
        description: Only admins and sellers are allowed to disable items.
      404:
        description: Item not found.
    """
    # Verificar se o ID do item existe
    sql_check_id = f"SELECT iditems FROM items WHERE iditems = {id}"
    my_cursor.execute(sql_check_id)
    result_id = my_cursor.fetchone()

    if not result_id:
        return jsonify({"message": "ID não encontrado"}), 404

    id_by_token = get_authenticated_user()

    if not have_perm(id_by_token):
        return {"message": "Apenas admins e vendedores podem desativar itens"}, 403

    # Alterar o status do item para "inativo"
    sql_disable_status = "UPDATE items SET status = 'INATIVO' WHERE iditems = %s"
    value_status = (id,)
    my_cursor.execute(sql_disable_status, value_status)
    mydb.commit()

    if my_cursor.rowcount > 0:
        return (
            jsonify({"message": f"Status do item com ID {id} alterado para INATIVO"}),
            200,
        )
    else:
        return jsonify({"message": "Nenhum item afetado"}), 204


@app.route("/items/disable", methods=["GET"])
def get_disabled_book():
    """
    Get all inactive items.
    ---
    responses:
      200:
        description: List of inactive items.
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: The ID of the item.
                  Título:
                    type: string
                    description: The title of the item.
                  Autores:
                    type: string
                    description: The authors of the item.
                  Categoria:
                    type: string
                    description: The category of the item.
                  Preço:
                    type: number
                    format: float
                    description: The price of the item.
                  Status:
                    type: string
                    description: The status of the item.
      204:
        description: No inactive items found.
    """
    # Consulta SQL para selecionar os itens com status "INATIVO"
    my_cursor.execute("SELECT * FROM items WHERE status = 'INATIVO'")
    items_db = my_cursor.fetchall()

    # Converter os resultados da consulta em um formato JSON
    items_converted = [
        {
            "id": item[0],
            "Título": item[1],
            "Autores": item[2],
            "Categoria": item[3],
            "Preço": item[4],
            "Status": item[5],
        }
        for item in items_db
    ]

    # Retornar os itens com status "INATIVO" com uma resposta HTTP 200 OK
    return jsonify(items_converted), 200


app.run(port=5000, host="localhost", debug=True)
