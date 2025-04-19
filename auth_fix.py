"""
Módulo para corrigir problemas de autenticação no sistema de apostas esportivas
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import os
import json
import datetime

class User:
    """Classe para representar um usuário do sistema"""
    
    def __init__(self, id, username, password_hash, email=None, nome_completo=None, 
                 nivel_acesso='usuario', ultimo_login=None, data_criacao=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.nome_completo = nome_completo
        self.nivel_acesso = nivel_acesso
        self.ultimo_login = ultimo_login
        self.data_criacao = data_criacao if data_criacao else datetime.datetime.now().timestamp()
        self.is_active = True
        self.is_authenticated = True
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.id)
    
    def check_password(self, password):
        # Implementação simples para demonstração
        # Em produção, use bibliotecas como werkzeug.security
        return self.password_hash == password

class UserManager:
    """Gerenciador de usuários do sistema"""
    
    def __init__(self):
        self.users = {}
        self.next_id = 1
        self._load_users()
    
    def _load_users(self):
        """Carrega usuários do arquivo ou cria usuários padrão"""
        try:
            if os.path.exists('users.json'):
                with open('users.json', 'r') as f:
                    users_data = json.load(f)
                
                for user_data in users_data:
                    user = User(
                        id=user_data.get('id'),
                        username=user_data.get('username'),
                        password_hash=user_data.get('password_hash'),
                        email=user_data.get('email'),
                        nome_completo=user_data.get('nome_completo'),
                        nivel_acesso=user_data.get('nivel_acesso', 'usuario'),
                        ultimo_login=user_data.get('ultimo_login'),
                        data_criacao=user_data.get('data_criacao')
                    )
                    self.users[user.id] = user
                    if user.id >= self.next_id:
                        self.next_id = user.id + 1
            else:
                # Criar usuários padrão
                self._create_default_users()
        except Exception as e:
            print(f"Erro ao carregar usuários: {str(e)}")
            # Criar usuários padrão em caso de erro
            self._create_default_users()
    
    def _create_default_users(self):
        """Cria usuários padrão para o sistema"""
        # Usuário administrador
        admin = User(
            id=1,
            username='admin',
            password_hash='admin123',  # Em produção, use hash seguro
            email='admin@example.com',
            nome_completo='Administrador',
            nivel_acesso='admin'
        )
        self.users[admin.id] = admin
        
        # Usuário comum
        user = User(
            id=2,
            username='usuario',
            password_hash='usuario123',  # Em produção, use hash seguro
            email='usuario@example.com',
            nome_completo='Usuário Teste',
            nivel_acesso='usuario'
        )
        self.users[user.id] = user
        
        self.next_id = 3
        self._save_users()
    
    def _save_users(self):
        """Salva usuários em arquivo"""
        users_data = []
        for user in self.users.values():
            users_data.append({
                'id': user.id,
                'username': user.username,
                'password_hash': user.password_hash,
                'email': user.email,
                'nome_completo': user.nome_completo,
                'nivel_acesso': user.nivel_acesso,
                'ultimo_login': user.ultimo_login,
                'data_criacao': user.data_criacao
            })
        
        with open('users.json', 'w') as f:
            json.dump(users_data, f, indent=2)
    
    def get_user(self, user_id):
        """Obtém usuário pelo ID"""
        user_id = int(user_id)
        return self.users.get(user_id)
    
    def get_user_by_username(self, username):
        """Obtém usuário pelo nome de usuário"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def create_user(self, username, password, email=None, nome_completo=None, nivel_acesso='usuario'):
        """Cria um novo usuário"""
        # Verificar se o nome de usuário já existe
        if self.get_user_by_username(username):
            return False, "Nome de usuário já existe"
        
        # Criar novo usuário
        user = User(
            id=self.next_id,
            username=username,
            password_hash=password,  # Em produção, use hash seguro
            email=email,
            nome_completo=nome_completo,
            nivel_acesso=nivel_acesso
        )
        
        self.users[user.id] = user
        self.next_id += 1
        self._save_users()
        
        return True, "Usuário criado com sucesso"
    
    def update_user(self, user_id, username=None, password=None, email=None, nome_completo=None, nivel_acesso=None):
        """Atualiza um usuário existente"""
        user_id = int(user_id)
        user = self.get_user(user_id)
        
        if not user:
            return False, "Usuário não encontrado"
        
        # Verificar se o novo nome de usuário já existe (se for diferente do atual)
        if username and username != user.username:
            existing_user = self.get_user_by_username(username)
            if existing_user and existing_user.id != user_id:
                return False, "Nome de usuário já existe"
            user.username = username
        
        if password:
            user.password_hash = password  # Em produção, use hash seguro
        
        if email is not None:
            user.email = email
        
        if nome_completo is not None:
            user.nome_completo = nome_completo
        
        if nivel_acesso is not None:
            user.nivel_acesso = nivel_acesso
        
        self._save_users()
        
        return True, "Usuário atualizado com sucesso"
    
    def delete_user(self, user_id):
        """Exclui um usuário"""
        user_id = int(user_id)
        if user_id not in self.users:
            return False, "Usuário não encontrado"
        
        username = self.users[user_id].username
        del self.users[user_id]
        self._save_users()
        
        return True, f"Usuário {username} excluído com sucesso"
    
    def update_last_login(self, user_id):
        """Atualiza a data do último login"""
        user_id = int(user_id)
        user = self.get_user(user_id)
        
        if user:
            user.ultimo_login = datetime.datetime.now().timestamp()
            self._save_users()

def configurar_autenticacao(app):
    """Configura o sistema de autenticação para a aplicação Flask"""
    
    # Configurar o sistema de login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'
    
    # Inicializar gerenciador de usuários
    user_manager = UserManager()
    
    # Função para carregar usuário
    @login_manager.user_loader
    def load_user(user_id):
        return user_manager.get_user(user_id)
    
    # Rota para login
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            # Encontrar usuário pelo nome
            user = user_manager.get_user_by_username(username)
            
            if user and user.check_password(password):
                login_user(user)
                user_manager.update_last_login(user.id)
                flash('Login realizado com sucesso!', 'success')
                
                # Redirecionar para a página solicitada originalmente (se houver)
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('dashboard'))
            else:
                flash('Credenciais inválidas. Tente novamente.', 'danger')
        
        return render_template('login.html')
    
    # Rota para logout
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Logout realizado com sucesso!', 'success')
        return redirect(url_for('index'))
    
    # Rota para gerenciamento de usuários (apenas admin)
    @app.route('/admin/usuarios')
    @login_required
    def admin_usuarios():
        if not current_user.nivel_acesso == 'admin':
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('dashboard'))
        
        usuarios = list(user_manager.users.values())
        return render_template('admin_usuarios.html', usuarios=usuarios)
    
    # Rota para criar usuário (apenas admin)
    @app.route('/admin/usuarios/criar', methods=['GET', 'POST'])
    @login_required
    def admin_criar_usuario():
        if not current_user.nivel_acesso == 'admin':
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            email = request.form.get('email')
            nome_completo = request.form.get('nome_completo')
            nivel_acesso = request.form.get('nivel_acesso')
            
            if not username or not password:
                flash('Nome de usuário e senha são obrigatórios.', 'warning')
                return redirect(url_for('admin_criar_usuario'))
            
            success, result = user_manager.create_user(
                username=username,
                password=password,
                email=email,
                nome_completo=nome_completo,
                nivel_acesso=nivel_acesso
            )
            
            if success:
                flash(f'Usuário {username} criado com sucesso!', 'success')
                return redirect(url_for('admin_usuarios'))
            else:
                flash(f'Erro ao criar usuário: {result}', 'danger')
        
        return render_template('admin_criar_usuario.html')
    
    # Rota para editar usuário (apenas admin)
    @app.route('/admin/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
    @login_required
    def admin_editar_usuario(user_id):
        if not current_user.nivel_acesso == 'admin':
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('dashboard'))
        
        user = user_manager.get_user(user_id)
        if not user:
            flash('Usuário não encontrado.', 'danger')
            return redirect(url_for('admin_usuarios'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            email = request.form.get('email')
            nome_completo = request.form.get('nome_completo')
            nivel_acesso = request.form.get('nivel_acesso')
            
            update_data = {
                'username': username,
                'email': email,
                'nome_completo': nome_completo,
                'nivel_acesso': nivel_acesso
            }
            
            if password:
                update_data['password'] = password
            
            success, result = user_manager.update_user(user_id, **update_data)
            
            if success:
                flash(f'Usuário {username} atualizado com sucesso!', 'success')
                return redirect(url_for('admin_usuarios'))
            else:
                flash(f'Erro ao atualizar usuário: {result}', 'danger')
        
        return render_template('admin_editar_usuario.html', user=user)
    
    # Rota para excluir usuário (apenas admin)
    @app.route('/admin/usuarios/excluir/<int:user_id>', methods=['POST'])
    @login_required
    def admin_excluir_usuario(user_id):
        if not current_user.nivel_acesso == 'admin':
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('admin_usuarios'))
        
        # Não permitir excluir o próprio usuário
        if int(user_id) == current_user.id:
            flash('Não é possível excluir seu próprio usuário.', 'danger')
            return redirect(url_for('admin_usuarios'))
        
        success, message = user_manager.delete_user(user_id)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('admin_usuarios'))
    
    return user_manager
