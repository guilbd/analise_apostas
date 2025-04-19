"""
Módulo de autenticação para o sistema de apostas esportivas
---------------------------------------------------------
Este módulo contém classes e funções para gerenciar autenticação de usuários.
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import uuid
from datetime import datetime

class User(UserMixin):
    """Classe para representar um usuário do sistema."""
    
    def __init__(self, id, username, password_hash, email=None, nome_completo=None, 
                 nivel_acesso='usuario', data_criacao=None, ultimo_acesso=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.nome_completo = nome_completo
        self.nivel_acesso = nivel_acesso  # 'admin' ou 'usuario'
        self.data_criacao = data_criacao or datetime.now().timestamp()
        self.ultimo_acesso = ultimo_acesso
    
    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Converte o usuário para um dicionário para armazenamento."""
        return {
            'id': self.id,
            'username': self.username,
            'password_hash': self.password_hash,
            'email': self.email,
            'nome_completo': self.nome_completo,
            'nivel_acesso': self.nivel_acesso,
            'data_criacao': self.data_criacao,
            'ultimo_acesso': self.ultimo_acesso
        }
    
    @classmethod
    def from_dict(cls, data):
        """Cria um usuário a partir de um dicionário."""
        return cls(
            id=data['id'],
            username=data['username'],
            password_hash=data['password_hash'],
            email=data.get('email'),
            nome_completo=data.get('nome_completo'),
            nivel_acesso=data.get('nivel_acesso', 'usuario'),
            data_criacao=data.get('data_criacao'),
            ultimo_acesso=data.get('ultimo_acesso')
        )


class UserManager:
    """Classe para gerenciar usuários do sistema."""
    
    def __init__(self, users_file='users.json'):
        self.users_file = users_file
        self.users = {}
        self.load_users()
    
    def load_users(self):
        """Carrega usuários do arquivo JSON."""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    users_data = json.load(f)
                    for user_id, user_data in users_data.items():
                        self.users[int(user_id)] = User.from_dict(user_data)
            except Exception as e:
                print(f"Erro ao carregar usuários: {str(e)}")
                # Criar usuários padrão se houver erro
                self._create_default_users()
        else:
            # Criar usuários padrão se o arquivo não existir
            self._create_default_users()
    
    def _create_default_users(self):
        """Cria usuários padrão para o sistema."""
        self.users = {
            1: User(1, 'admin', generate_password_hash('admin123'), 
                   email='admin@sistema.com', nome_completo='Administrador', 
                   nivel_acesso='admin'),
            2: User(2, 'usuario', generate_password_hash('usuario123'), 
                   email='usuario@sistema.com', nome_completo='Usuário Padrão', 
                   nivel_acesso='usuario')
        }
        self.save_users()
    
    def save_users(self):
        """Salva usuários no arquivo JSON."""
        users_data = {str(user_id): user.to_dict() for user_id, user in self.users.items()}
        try:
            with open(self.users_file, 'w') as f:
                json.dump(users_data, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar usuários: {str(e)}")
    
    def get_user(self, user_id):
        """Obtém um usuário pelo ID."""
        return self.users.get(int(user_id))
    
    def get_user_by_username(self, username):
        """Obtém um usuário pelo nome de usuário."""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def create_user(self, username, password, email=None, nome_completo=None, nivel_acesso='usuario'):
        """Cria um novo usuário."""
        # Verificar se o nome de usuário já existe
        if self.get_user_by_username(username):
            return False, "Nome de usuário já existe"
        
        # Gerar novo ID
        new_id = max(self.users.keys()) + 1 if self.users else 1
        
        # Criar novo usuário
        new_user = User(
            id=new_id,
            username=username,
            password_hash=generate_password_hash(password),
            email=email,
            nome_completo=nome_completo,
            nivel_acesso=nivel_acesso
        )
        
        # Adicionar ao dicionário de usuários
        self.users[new_id] = new_user
        
        # Salvar usuários
        self.save_users()
        
        return True, new_user
    
    def update_user(self, user_id, **kwargs):
        """Atualiza um usuário existente."""
        user = self.get_user(user_id)
        if not user:
            return False, "Usuário não encontrado"
        
        # Atualizar campos
        if 'username' in kwargs and kwargs['username'] != user.username:
            # Verificar se o novo nome de usuário já existe
            existing_user = self.get_user_by_username(kwargs['username'])
            if existing_user and existing_user.id != user_id:
                return False, "Nome de usuário já existe"
            user.username = kwargs['username']
        
        if 'password' in kwargs:
            user.password_hash = generate_password_hash(kwargs['password'])
        
        if 'email' in kwargs:
            user.email = kwargs['email']
        
        if 'nome_completo' in kwargs:
            user.nome_completo = kwargs['nome_completo']
        
        if 'nivel_acesso' in kwargs:
            user.nivel_acesso = kwargs['nivel_acesso']
        
        if 'ultimo_acesso' in kwargs:
            user.ultimo_acesso = kwargs['ultimo_acesso']
        
        # Salvar usuários
        self.save_users()
        
        return True, user
    
    def delete_user(self, user_id):
        """Remove um usuário."""
        if int(user_id) not in self.users:
            return False, "Usuário não encontrado"
        
        # Não permitir excluir o último administrador
        if self.users[int(user_id)].nivel_acesso == 'admin':
            admin_count = sum(1 for user in self.users.values() if user.nivel_acesso == 'admin')
            if admin_count <= 1:
                return False, "Não é possível excluir o último administrador"
        
        # Remover usuário
        del self.users[int(user_id)]
        
        # Salvar usuários
        self.save_users()
        
        return True, "Usuário excluído com sucesso"
    
    def update_last_login(self, user_id):
        """Atualiza a data do último acesso do usuário."""
        user = self.get_user(user_id)
        if user:
            user.ultimo_acesso = datetime.now().timestamp()
            self.save_users()
