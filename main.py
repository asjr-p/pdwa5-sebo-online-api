# Certifique-se de importar seus módulos necessários
import mysql.connector
import jwt

from flask import Flask, jsonify, request
from hashlib import sha256
from flasgger import Swagger
from datetime import datetime

# conexão com DB
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="check docs",
    database="dbsebo"
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
    }
    secret_key = "SECRET_KEY"
    token = jwt.encode({"some": payload}, secret_key, algorithm="HS256")
    return token


def get_authenticated_user():
    print('ESTOU EM get_authenticated_user')
    token = request.headers.get('Authorization')
    print(token)

    if not token:
        print('retornei none')
        return jsonify({'error': 'Token não fornecido'}), 401

    try:
        # Decodifique o token JWT usando a chave secreta
        print('ENTREI NO TRY')
        payload = jwt.decode(
            token,
            key='SECRET_KEY',
            algorithms=['HS256']
        )
        print(payload["some"]["sub"])
        return payload["some"]["sub"]

    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expirado'}), 401

    except jwt.InvalidTokenError:
        return jsonify({'error': 'Token inválido'}), 401

    except jwt.PyJWTError as e:
        return jsonify(
            {'error': f'Erro ao decodificar o token: {str(e)}'}
        ), 401


def have_perm(user_id):
    sql = f"SELECT usertype FROM users WHERE idusers = {user_id}"
    my_cursor.execute(sql)
    result = my_cursor.fetchall()

    return result[0][0] in ['admin', 'vendedor']


def check_password(email_db, passw_login):
    passw_login_hash = sha256(passw_login.encode()).hexdigest()

    sql = f"SELECT password FROM users WHERE email = '{email_db}'"
    my_cursor.execute(sql)
    passw_db = my_cursor.fetchall()

    return passw_db[0][0] == passw_login_hash if passw_db else None
# USERS


@app.route('/users', methods=['POST'])
def create_user():
    """
    Create a new user.
    ---
    requestBody:
      required: true
      content:
        application/json:
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
                description: The type of user (e.g., comprador, vendedor).
              status:
                type: string
                description: The status of the user (e.g., ativo, desativado).
    responses:
      201:
        description: User created successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                  description: The name of the user.
                email:
                  type: string
                  description: The email of the user.
                usertype:
                  type: string
                  description: The type of user.
                status:
                  type: string
                  description: The status of the user.
      400:
        description: Required fields are missing.
      400:
        description: Email already registered.
      500:
        description: Internal Server Error.
    """
    new_user = request.get_json()

    # Validar dados de entrada
    required_fields = ['name', 'email', 'password', 'usertype', 'status']
    if not all(field in new_user for field in required_fields):
        return 'Campos obrigatórios ausentes', 400

    email = new_user['email']

    # Verificar se o email já está cadastrado
    sql_check_email = "SELECT email FROM users WHERE email = %s"
    my_cursor.execute(sql_check_email, (email,))
    existing_email = my_cursor.fetchone()

    if existing_email:
        return 'Email já cadastrado', 400

    # Hash da senha
    hashed_password = sha256(new_user['password'].encode()).hexdigest()

    # Inserir o novo usuário no banco de dados
    sql_insert_user = "INSERT INTO users (name, email, password, usertype, status) VALUES (%s, %s, %s, %s, %s)"
    user_data = (new_user['name'], email, hashed_password,
                 new_user['usertype'], new_user['status'])

    try:
        my_cursor.execute(sql_insert_user, user_data)
        mydb.commit()
    except Exception as e:
        return str(e), 500

    return jsonify(new_user), 201


@app.route('/admin/users', methods=['GET'])
def get_users():
    """
    Get all users (Admin only).
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
                    description: The unique ID of the user.
                  name:
                    type: string
                    description: The name of the user.
                  email:
                    type: string
                    description: The email of the user.
                  usertype:
                    type: string
                    description: The type of user (e.g., comprador, vendedor).
                  status:
                    type: string
                    description: The status of the user (e.g., ativo, desativado).
      403:
        description: Only admins can list users.
    """
    id_by_token = get_authenticated_user()

    if not have_perm(id_by_token):
        return jsonify({"error": "Apenas admins podem listar usuários"}), 403

    # Consulta SQL para selecionar os usuários
    sql_select_users = 'SELECT * FROM users'
    my_cursor.execute(sql_select_users)
    users_db = my_cursor.fetchall()

    # Converter os resultados da consulta em um formato JSON
    users_converted = [{
        "ID": user[0],
        "name": user[1],
        "email": user[2],
        "usertype": user[4],
        "status": user[5]
    } for user in users_db]

    # Retornar os usuários com uma resposta HTTP 200 OK
    return jsonify(users_converted), 200


@app.route('/admin/login', methods=['POST'])
def login_admin():
    """
    Admin login.
    ---
    parameters:
      - in: body
        name: admin_login_data
        description: The admin login credentials.
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              description: The email of the admin.
              example: admin@example.com
            password:
              type: string
              description: The password of the admin.
              example: admin_password123
    responses:
      200:
        description: Admin login successful.
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
        description: Invalid admin credentials.
      403:
        description: Admin account is deactivated.
      400:
        description: Incomplete credentials.
      500:
        description: Internal server error.
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Credenciais incompletas"}), 400

    # Use parâmetros SQL seguros
    sql = "SELECT * FROM users WHERE email = %s"
    my_cursor.execute(sql, (email,))
    user_db = my_cursor.fetchone()

    if not user_db:
        return jsonify({"error": "Credenciais inválidas"}), 401

    sql_status = user_db[5]

    if sql_status == 'deactivated':
        return jsonify({"error": "Seu usuário está desativado"}), 403

    if check_password(user_db[2], password):
        # Gere um token JWT
        token = generate_token(user_db[0])
        response_data = {
            "token": str(token),
            "message": "Login bem-sucedido"
        }
        return jsonify(response_data), 200

    return jsonify({"error": "Credenciais inválidas"}), 401


@app.route('/login', methods=['POST'])
def login():
    """
    User login.
    ---
    parameters:
      - in: body
        name: login_data
        description: The user login credentials.
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              description: The email of the user.
              example: user@example.com
            password:
              type: string
              description: The password of the user.
              example: password123
    responses:
      200:
        description: Login successful.
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
        description: Invalid credentials or user type not accepted.
      403:
        description: User account is deactivated.
      500:
        description: Internal server error.
    """
    data = request.get_json()
    email = data['email']
    passw = data['password']
    user_db = None

    # Use parâmetros SQL seguros
    sql = "SELECT * FROM users WHERE email = %s"
    my_cursor.execute(sql, (email,))
    user_db = my_cursor.fetchone()

    if not user_db:
        return jsonify({"error": "Credenciais inválidas"}), 401

    sql_status = user_db[5]

    if sql_status == 'deactivated':
        return jsonify({"error": "Seu usuário está desativado"}), 403

    elif check_password(email, passw):
        if user_db[4] == 'vendedor':
            # Gere um token JWT
            token = generate_token(user_db[0])
            response_data = {
                "token": str(token),
                "message": "Login bem-sucedido"
            }
            return jsonify(response_data), 200

        elif user_db[4] == 'comprador':
            response_data = {
                "message": "Login bem-sucedido"
            }
            return jsonify(response_data), 200

    return jsonify(
        {"error": "Credenciais inválidas ou tipo de usuário não aceito"}
    ), 401


@app.route('/user/<int:id>', methods=['PUT'])
def edit_perfil(id):
    """
    Edit user profile.
    ---
    parameters:
      - name: id
        in: path
        description: The ID of the user to edit.
        required: true
        type: integer
      - in: body
        name: user_edited
        description: The user profile data to be edited.
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
              description: The type of the user.
            status:
              type: string
              description: The status of the user.
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
      400:
        description: Bad request. Missing required fields.
      403:
        description: Forbidden. Only admins or the user themselves can edit the profile.
      404:
        description: User ID not found.
    """
    id_by_token = get_authenticated_user()

    # Verificações de permissão
    if id_by_token != id and not have_perm(id_by_token):
        return jsonify({"error": "Você só pode editar seu próprio usuário ou precisa de privilégios de administrador"}), 403

    user_edited = request.get_json()

    # Validar campos obrigatórios
    required_fields = ['name', 'email', 'password', 'usertype', 'status']
    if not all(field in user_edited for field in required_fields):
        return jsonify({"error": "Campos obrigatórios ausentes"}), 400

    # Hash da senha
    hash_passw = sha256(user_edited['password'].encode()).hexdigest()

    # Atualizar o perfil do usuário no banco de dados
    sql = "UPDATE users SET name = %s, email = %s, password = %s, usertype = %s, status = %s WHERE idusers = %s"
    values = (user_edited['name'], user_edited['email'], hash_passw,
              user_edited['usertype'], user_edited['status'], id)
    my_cursor.execute(sql, values)
    mydb.commit()

    return jsonify(user_edited)


@app.route('/admin/users/softdelete/<int:id>', methods=['DELETE'])
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
    id_by_token = get_authenticated_user()

    # Verificar permissões de exclusão
    if not have_perm(id_by_token):
        return jsonify({"error": "Apenas admins podem deletar usuários"}), 403

    # Verificar se o ID do usuário existe
    sql_check_id = f"SELECT idusers FROM users WHERE idusers = {id}"
    my_cursor.execute(sql_check_id)
    result_id = my_cursor.fetchone()

    if not result_id:
        return jsonify({"error": "ID não encontrado"}), 404

    # Verificar se o usuário a ser excluído existe
    sql_get_user = f"SELECT * FROM users WHERE idusers = {id}"
    my_cursor.execute(sql_get_user)
    user_db = my_cursor.fetchone()

    if user_db:
        try:
            # Iniciar uma transação
            my_cursor.execute("START TRANSACTION")

            # Inativar o usuário
            sql_disable_user = f"UPDATE users SET status = 'deactivated' WHERE idusers = {id}"
            my_cursor.execute(sql_disable_user)

            # Se todas as consultas forem bem-sucedidas, commit na transação
            mydb.commit()
            return jsonify({"message": "Usuário inativado com sucesso"}), 200

        except Exception as e:
            # Se ocorrer algum erro, faça rollback na transação
            mydb.rollback()
            return jsonify({"error": f"Erro durante a inativação do usuário: {e}"}), 500

        finally:
            # Certifique-se de finalizar a transação
            my_cursor.execute("COMMIT")

    return jsonify({"error": "Usuário não encontrado"}), 404

# ITEMS


@app.route('/items', methods=['GET'])
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
                  ISBN:
                    type: string
                    description: The ISBN of the item.
      404:
        description: No items found.
    parameters:
      - name: categoria
        in: query
        description: The category filter.
        type: string
      - name: autor
        in: query
        description: The author filter.
        type: string
      - name: titulo
        in: query
        description: The title filter.
        type: string
      - name: isbn
        in: query
        description: The ISBN filter.
        type: string
    """
    # Obter parâmetros de URL
    category_filter = request.args.get('categoria')
    author_filter = request.args.get('autor')
    title_filter = request.args.get('titulo')
    isbn_filter = request.args.get('isbn')


    # Construir a consulta SQL base
    sql_query = 'SELECT * FROM items WHERE 1=1'


    # Adicionar filtros à consulta conforme necessário
    if category_filter:
        sql_query += f" AND categoria = '{category_filter}'"


    elif author_filter:
        sql_query += f" AND autor = '{author_filter}'"


    elif title_filter:
        sql_query += f" AND titulo = '{title_filter}'"


    elif isbn_filter:
        sql_query += f" AND isbn = '{isbn_filter}'"


    # Executar a consulta SQL
    my_cursor.execute(sql_query)
    items_db = my_cursor.fetchall()


    # Converter os resultados da consulta em um formato JSON
    items_converted = [{
        "id": item[0],
        "Título": item[1],
        "Autores": item[2],
        "Categoria": item[3],
        "Preço": item[4],
        "Status": item[5],
        "ISBN": item[6]
    } for item in items_db]


    # Verificar se há itens encontrados
    if not items_converted:
        return jsonify({"message": "No items found"}), 404
    # Retornar os itens com uma resposta HTTP 200 OK
    return jsonify(items_converted), 200


# Consult by ID -> OK


@app.route('/items/<int:id>', methods=['GET'])
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
                ISBN:
                  type: string
                  description: The ISBN of the item.
      404:
        description: Item not found.
      500:
        description: An error occurred during item retrieval.
    """
    try:
        # Consulta SQL para selecionar o item por ID usando parâmetros
        sql_query = "SELECT * FROM items WHERE iditems = %s"
        my_cursor.execute(sql_query, (id,))
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
                "ISBN": item_db[6],
            }
            # Retornar o item com uma resposta HTTP 200 OK
            return jsonify(item_converted), 200

        return jsonify({"message": "Item não encontrado"}), 404

    except Exception as e:
        # Adicione o tratamento adequado para diferentes tipos de exceções
        return jsonify(
          {"message": f"Erro durante a recuperação do item: {e}"}
        ), 500


# Make Book -> OK


@app.route('/items', methods=['POST'])
def make_book():
    """
    Create a new item.
    ---
    parameters:
      - name: body
        in: body
        required: true
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
            ISBN:
              type: string
              description: The ISBN of the item.
    responses:
      201:
        description: Item created successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  description: A success message.
      403:
        description: Only admins and sellers can create items.
      404:
        description: The selected category is not registered.
      409:
        description: Item with the same title already exists.
      500:
        description: An error occurred during item creation.
    """
    try:
        new_book = request.get_json()

        # Verificar se o título do livro já existe
        sql_check_title = "SELECT titulo FROM items WHERE titulo = %s"
        my_cursor.execute(sql_check_title, (new_book['Título'],))
        existing_title = my_cursor.fetchone()

        if existing_title:
            return {"message": "Este produto já foi criado"}, 409

        id_by_token = get_authenticated_user()

        if not have_perm(id_by_token):
            return {
                "message": "Apenas admins e vendedores podem criar itens"
            }, 403

        sql_get_name = "SELECT name FROM users WHERE idusers = %s"
        my_cursor.execute(sql_get_name, (id_by_token,))
        user_name = my_cursor.fetchone()
        print(user_name[0])

        my_cursor.execute("SELECT name FROM categories WHERE status = 'ativo'")
        categories_db = my_cursor.fetchall()
        categories_name = [i[0] for i in categories_db]
        print(categories_name)

        if new_book['Categoria'] not in categories_name:
            return jsonify(
                {
                    "message": "A categoria selecionada não está cadastrada"
                }, categories_name), 404

        # Inserir o novo livro no banco de dados
        sql_insert_book = "INSERT INTO items (titulo, autor, categoria, preco, status, isbn) VALUES (%s, %s, %s, %s, %s, %s)"
        book_data = (
            new_book['Título'],
            new_book['Autores'],
            new_book['Categoria'],
            new_book['Preço'],
            new_book['Status'],
            new_book['ISBN'],
        )

        my_cursor.execute(sql_insert_book, book_data)
        mydb.commit()

        return jsonify({"message": "Livro criado com sucesso"}), 201

    except Exception as e:
        # Adicione o tratamento adequado para diferentes tipos de exceções
        print(f"Erro durante a criação do livro: {e}")
        return jsonify({"message": "Erro durante a criação do livro"}), 500

# Edit By ID -> OK


@app.route('/items/<int:id>', methods=['PUT'])  # type: ignore
def edit_book_by_id(id):
    """
    Edit an item by ID.
    ---
    parameters:
      - name: id
        in: path
        description: The ID of the item to edit.
        required: true
        type: integer
      - name: body
        in: body
        required: true
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
        description: You can only edit your own items or you need admin privileges.
      404:
        description: Item ID not found or the selected category is not registered.
    """
    # Verificar se o ID do livro existe
    sql_check_id = f"SELECT iditems FROM items WHERE iditems = {id}"
    my_cursor.execute(sql_check_id)
    result_id = my_cursor.fetchone()

    if not result_id:
        return jsonify({"message": "ID não encontrado"}), 404

    id_by_token = get_authenticated_user()

    if not have_perm(id_by_token):
        return {
            "message": "Apenas admins e vendedores podem editar itens"
        }, 403

    my_cursor.execute("SELECT name FROM categories WHERE status = 'ativo'")
    categories_db = my_cursor.fetchall()
    categories_name = []

    for i in categories_db:
        for j in i:
            categories_name.append(j)
    print(categories_name)

    categorie = request.get_json()

    if categorie['Categoria'] not in categories_name:
        return jsonify(
            {
                "message": "Categoria selecioando não está cadastrada: "
            }, categories_name), 404

    # Atualizar os dados do livro no banco de dados
    sql_update_book = "UPDATE items SET titulo = %s, autor = %s, categoria = %s, preco = %s, status = %s WHERE iditems = %s"
    book_data = (
        categorie.get('Título'),
        categorie.get('Autores'),
        categorie.get('Categoria'),
        categorie.get('Preço'),
        categorie.get('Status'),
        id
    )

    my_cursor.execute(sql_update_book, book_data)
    mydb.commit()

    return jsonify(categorie), 200

# Soft Delete -> OK


@app.route('/items/disable/<int:id>', methods=['DELETE'])
def delete_book(id):
    """
    Disable an item by ID.
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
                  description: A success message.
      403:
        description: Only admins and sellers are allowed to disable items.
      404:
        description: Item ID not found.
    """
    # Verificar se o ID do item existe
    sql_check_id = f"SELECT iditems FROM items WHERE iditems = {id}"
    my_cursor.execute(sql_check_id)
    result_id = my_cursor.fetchone()

    if not result_id:
        return jsonify({"message": "ID não encontrado"}), 404

    id_by_token = get_authenticated_user()

    if not have_perm(id_by_token):
        return {
            "message": "Apenas admins e vendedores podem desativar itens"
        }, 403

    # Alterar o status do item para "inativo"
    sql_disable_status = "UPDATE items SET status = 'INATIVO' WHERE iditems = %s"
    value_status = (id,)
    my_cursor.execute(sql_disable_status, value_status)
    mydb.commit()

    if my_cursor.rowcount > 0:
        return jsonify(
            {"message": f"Status do item com ID {id} alterado para INATIVO"}
        ), 200
    else:
        return jsonify({"message": "Nenhum item afetado"}), 204


@app.route('/items/disable', methods=['GET'])
def get_disabled_book():
    """
    Get a list of disabled items.
    ---
    responses:
      200:
        description: List of disabled items retrieved successfully.
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: The unique ID of the disabled item.
                  Título:
                    type: string
                    description: The title of the disabled item.
                  Autores:
                    type: string
                    description: The authors of the disabled item.
                  Categoria:
                    type: string
                    description: The category of the disabled item.
                  Preço:
                    type: number
                    description: The price of the disabled item.
                  Status:
                    type: string
                    description: The status of the disabled item.
                  ISBN:
                    type: string
                    description: The ISBN of the disabled item.
      404:
        description: No disabled items found.
    """
    # Consulta SQL para selecionar os itens com status "INATIVO"
    my_cursor.execute("SELECT * FROM items WHERE status = 'INATIVO'")
    items_db = my_cursor.fetchall()

    # Converter os resultados da consulta em um formato JSON
    items_converted = [{
        "id": item[0],
        "Título": item[1],
        "Autores": item[2],
        "Categoria": item[3],
        "Preço": item[4],
        "Status": item[5],
        "ISBN": item[6]
    } for item in items_db]

    # Retornar os itens com status "INATIVO" com uma resposta HTTP 200 OK
    return jsonify(items_converted), 200

# Gerenciar Categorias:

@app.route('/categories', methods=['GET'])
def get_categories():
    """
    Get a list of all categories.
    ---
    responses:
      200:
        description: List of categories retrieved successfully.
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  ID:
                    type: integer
                    description: The unique ID of the category.
                  name:
                    type: string
                    description: The name of the category.
                  status:
                    type: string
                    description: The status of the category.
      404:
        description: No categories found.
    """
    # Consulta SQL para selecionar categorias
    sql_select_categories = 'SELECT * FROM categories'
    my_cursor.execute(sql_select_categories)
    categories_db = my_cursor.fetchall()


    # Converter os resultados da consulta em um formato JSON
    categories_converted = [{
        "ID": user[0],
        "name": user[1],
        "status": user[2],
    } for user in categories_db]


    # Retornar os usuários com uma resposta HTTP 200 OK
    return jsonify(categories_converted), 200


@app.route('/categories/', methods=['POST'])
def create_categorie():
    """
    Create a new category.
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
              description: The name of the new category.
    responses:
      201:
        description: Category created successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                  description: The name of the created category.
      403:
        description: Only admins and sellers can create categories.
      409:
        description: The specified category already exists.
      500:
        description: Internal server error during category creation.
    """

    new_categorie = request.get_json()

    # Verificar se categoria já existe
    sql_check_categorie = f"SELECT name FROM categories WHERE name = '{new_categorie['name']}'"
    my_cursor.execute(sql_check_categorie)
    existing_title = my_cursor.fetchone()

    if existing_title:
        return jsonify({"message": "Essa categoria já foi criado"}), 409

    id_by_token = get_authenticated_user()

    if not have_perm(id_by_token):
        return jsonify(
            {"message": "Apenas admins e vendedores podem criar categorias"}
        ), 403

    # Inserir o novo livro no banco de dados
    sql_insert_categories = "INSERT INTO categories (name, status) VALUES (%s, %s)"
    categorie_data = (
        new_categorie['name'],
        "ativo",
    )

    my_cursor.execute(sql_insert_categories, categorie_data)
    mydb.commit()

    return jsonify(new_categorie), 201


@app.route('/items/categories/<categories>', methods=['GET'])
def item_by_categorie(categories):
    """
    Get items by category.
    ---
    parameters:
      - name: categories
        in: path
        description: The category to filter items by.
        required: true
        type: string
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
                  ISBN:
                    type: string
                    description: The ISBN of the item.
      404:
        description: No items found for the specified category.
    """
    print(categories)
    sql_check_categorie = f"SELECT * FROM items WHERE categoria = '{categories}'"
    my_cursor.execute(sql_check_categorie)
    results = my_cursor.fetchall()

    if not results:
        return jsonify({"message": "Item não encontrado"}), 404

    for i in results:
        items_converted = [{
            "id": i[0],
            "Título": i[1],
            "Autores": i[2],
            "Categoria": i[3],
            "Preço": i[4],
            "Status": i[5],
            "ISBN": i[6],
        } for item in i]

        return jsonify(items_converted), 200


@app.route('/categories/<int:id>', methods=['PUT'])
def edit_categorie_by_id(id):
    """
    Edit category by ID.
    ---
    parameters:
      - name: id
        in: path
        description: The ID of the category to edit.
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
              description: The updated name of the category.
    responses:
      200:
        description: Category updated successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                  description: The updated name of the category.
      403:
        description: Only admins and sellers can edit categories.
      404:
        description: Category ID not found.
    """
    # Verificar se o ID da categoria existe
    sql_check_id = f"SELECT idcategories FROM categories WHERE idcategories = {id}"
    my_cursor.execute(sql_check_id)
    result_id = my_cursor.fetchone()

    if not result_id:
        return jsonify({"message": "ID não encontrado"}), 404

    id_by_token = get_authenticated_user()

    if not have_perm(id_by_token):
        return {
            "message": "Apenas admins e vendedores podem editar categorias"
        }, 403

    categorie_edited = request.get_json()

    # Atualizar os dados da categoria no banco de dados
    sql_update_categorie = "UPDATE categories SET name = %s, status = %s WHERE idcategories = %s"
    categorie_data = (
        categorie_edited.get('name'),
        'ativo',
        id
    )

    my_cursor.execute(sql_update_categorie, categorie_data)
    mydb.commit()

    if my_cursor.rowcount > 0:
        return jsonify(categorie_edited), 200
    else:
        return jsonify({"message": "Nenhuma alteração realizada"}), 200


@app.route('/categories/disable/<int:id>', methods=['DELETE'])
def delete_categorie(id):
    """
    Disable a category.
    ---
    parameters:
      - name: id
        in: path
        description: The ID of the category to disable.
        required: true
        type: integer
    responses:
      200:
        description: Category disabled successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  description: A success message.
      204:
        description: No category affected.
      403:
        description: Only admins and sellers can disable categories.
      404:
        description: Category ID not found.
    """
    # Verificar se o ID do item existe
    sql_check_id = f"SELECT idcategories FROM categories WHERE idcategories = {id}"
    my_cursor.execute(sql_check_id)
    result_id = my_cursor.fetchone()

    if not result_id:
        return jsonify({"message": "ID não encontrado"}), 404

    id_by_token = get_authenticated_user()

    if not have_perm(id_by_token):
        return {
            "message": "Apenas admins e vendedores podem desativar Categorias"
        }, 403

    # Alterar o status do item para "inativo"
    sql_disable_status = "UPDATE categories SET status = 'INATIVO' WHERE idcategories = %s"
    value_status = (id,)
    my_cursor.execute(sql_disable_status, value_status)
    mydb.commit()

    if my_cursor.rowcount > 0:
        return jsonify(
            {"message": f"Status da categoria com ID {id} alterado para INATIVO"}
        ), 200
    else:
        return jsonify({"message": "Nenhum item afetado"}), 204

# Gerenciar Transações:


@app.route('/transactions/<int:id>', methods=['POST'])  # type: ignore
def transaction(id):
    """
    Create a transaction.
    ---
    parameters:
      - name: id
        in: path
        description: The ID of the item to create a transaction for.
        required: true
        type: integer
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              description: The email of the buyer.
            ID vendedor:
              type: string
              description: The email of the seller.
    responses:
      200:
        description: Transaction created successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                COMPRADO!, dados do item:
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
                    ISBN:
                      type: string
                      description: The ISBN of the item.
                dados da transação:
                  type: object
                  properties:
                    idbuyer:
                      type: integer
                      description: The ID of the buyer.
                    idseller:
                      type: string
                      description: The email of the seller.
                    iditem:
                      type: integer
                      description: The ID of the item in the transaction.
                    value:
                      type: number
                      description: The price of the item in the transaction.
                    date:
                      type: string
                      format: date
                      description: The date of the transaction.
      404:
        description: Item, buyer, or seller not found.
    """
    email_client = request.get_json().get('email')

    if not email_client:
        return jsonify({"message": "email não encontrado"}), 404

    sql_get_usertype = "SELECT * FROM users WHERE email = %s"
    my_cursor.execute(sql_get_usertype, (email_client,))
    result_usertype = my_cursor.fetchone()

    if result_usertype[4] != 'comprador':
        return jsonify(
            {
                "message": "usuário não cadastrado como comprador"
            }, result_usertype
        ), 404

    # Consulta SQL para selecionar o item por ID
    my_cursor.execute(f"SELECT * FROM items WHERE iditems = {id}")
    item_db = my_cursor.fetchone()

    if not item_db:
        return jsonify({"message": "Item não encontrado"}), 404

    # Converter o resultado da consulta em um formato JSON
    item_converted = {
        "id": item_db[0],
        "Título": item_db[1],
        "Autores": item_db[2],
        "Categoria": item_db[3],
        "Preço": item_db[4],
        "Status": item_db[5],
        "ISBN": item_db[6]
    }

    # pegar id do vendedor
    email_client = request.get_json().get('ID vendedor')

    # Inserir o transaction no banco de dados
    data_atual = datetime.now().date()
    sql_insert_transaction = "INSERT INTO transactions (idbuyer, idseller, iditem, value, date) VALUES (%s, %s, %s, %s, %s)"
    transaction_data = (
        result_usertype[0],
        email_client,
        item_db[0],
        item_db[4],
        data_atual
    )

    my_cursor.execute(sql_insert_transaction, transaction_data)
    mydb.commit()

    # Retornar o item com uma resposta HTTP 200 OK

    return jsonify(
        {
            "COMPRADO!, dados do item": item_converted,
            "dados da transação": transaction_data
        }
    ), 200


@app.route('/transactions', methods=['GET'])
def get_transactions():
    """
    Get a list of all transactions.
    ---
    responses:
      200:
        description: List of transactions retrieved successfully.
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: The unique ID of the transaction.
                  id Comprador:
                    type: integer
                    description: The ID of the buyer in the transaction.
                  id Vendedor:
                    type: integer
                    description: The ID of the seller in the transaction.
                  id Item:
                    type: integer
                    description: The ID of the item in the transaction.
                  Preço:
                    type: number
                    description: The price of the item in the transaction.
                  Data da compra:
                    type: string
                    format: date
                    description: The purchase date of the transaction.
      404:
        description: No transactions found.
    """
    # Consulta SQL para selecionar os itens
    my_cursor.execute('SELECT * FROM transactions')
    transactions_db = my_cursor.fetchall()

    # Converter os resultados da consulta em um formato JSON
    transaction_converted = [{
        "id": item[0],
        "id Comprador": item[1],
        "id Vendedor": item[2],
        "id Item": item[3],
        "Preço": item[4],
        "Data da compra": item[5]
    } for item in transactions_db]

    # Retornar os itens com uma resposta HTTP 200 OK
    return jsonify(transaction_converted), 200

@app.route('/transactions/<int:id>', methods=['GET'])
def transaction_by_userid(id):
    """
    Get transactions by user ID.
    ---
    parameters:
      - name: id
        in: path
        description: The ID of the user (buyer) to retrieve transactions.
        required: true
        type: integer
    responses:
      200:
        description: Transactions retrieved successfully.
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  ID da transação:
                    type: integer
                    description: The unique ID of the transaction.
                  ID do comprador:
                    type: integer
                    description: The ID of the buyer.
                  ID do vendedor:
                    type: integer
                    description: The ID of the seller.
                  ID do item:
                    type: integer
                    description: The ID of the item.
                  Preço:
                    type: number
                    description: The price of the item.
                  Data:
                    type: string
                    format: date
                    description: The date of the transaction.
      404:
        description: Transactions not found.
    """
    sql_check_id = "SELECT * FROM transactions WHERE idbuyer = %s"
    my_cursor.execute(sql_check_id, (id,))
    results = my_cursor.fetchall()
    print(results)

    if not results:
        return jsonify({"message": "Id de usuário não encontrado"}), 404

    for i in results:
        items_converted = [{
            "ID da transação": i[0],
            "ID do comprador": i[1],
            "ID do vendedor": i[2],
            "ID do item": i[3],
            "Preço": i[4],
            "Data": i[5],
        } for item in i]

        return jsonify(items_converted), 200


app.run(port=5000, host='localhost', debug=True)
my_cursor.close()
mydb.close()
