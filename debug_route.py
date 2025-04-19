"""
Módulo para criar rotas temporárias de debug para visualizar e baixar arquivos HTML
"""
from flask import Blueprint, render_template, send_file, abort, current_app, jsonify
import os
import glob

# Criar um Blueprint para as rotas de debug
debug_bp = Blueprint('debug', __name__, url_prefix='/debug')

# Diretório onde os arquivos de debug estão armazenados
DEBUG_DIR = '/opt/render/project/src/dados/debug/'

@debug_bp.route('/')
def index():
    """
    Página inicial que lista todos os arquivos de debug disponíveis
    """
    try:
        # Verificar se o diretório existe
        if not os.path.exists(DEBUG_DIR):
            return jsonify({
                'error': 'Diretório de debug não encontrado',
                'path': DEBUG_DIR
            }), 404
        
        # Listar todos os arquivos HTML no diretório de debug
        html_files = glob.glob(os.path.join(DEBUG_DIR, '*.html'))
        
        # Organizar os arquivos por tipo
        files_by_type = {
            'flashscore': [],
            'academia': [],
            'sofascore': [],
            'outros': []
        }
        
        for file_path in html_files:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_time = os.path.getmtime(file_path)
            
            file_info = {
                'name': file_name,
                'path': file_path,
                'size': file_size,
                'time': file_time
            }
            
            if 'flashscore' in file_name:
                files_by_type['flashscore'].append(file_info)
            elif 'academia' in file_name:
                files_by_type['academia'].append(file_info)
            elif 'sofascore' in file_name:
                files_by_type['sofascore'].append(file_info)
            else:
                files_by_type['outros'].append(file_info)
        
        # Retornar os dados como JSON
        return jsonify({
            'debug_dir': DEBUG_DIR,
            'files_count': len(html_files),
            'files_by_type': files_by_type
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@debug_bp.route('/view/<filename>')
def view_file(filename):
    """
    Visualizar o conteúdo de um arquivo HTML
    """
    try:
        file_path = os.path.join(DEBUG_DIR, filename)
        
        # Verificar se o arquivo existe
        if not os.path.exists(file_path):
            return jsonify({
                'error': 'Arquivo não encontrado',
                'path': file_path
            }), 404
        
        # Ler o conteúdo do arquivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Retornar o conteúdo como HTML
        return content, 200, {'Content-Type': 'text/html'}
    
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@debug_bp.route('/download/<filename>')
def download_file(filename):
    """
    Baixar um arquivo HTML
    """
    try:
        file_path = os.path.join(DEBUG_DIR, filename)
        
        # Verificar se o arquivo existe
        if not os.path.exists(file_path):
            return jsonify({
                'error': 'Arquivo não encontrado',
                'path': file_path
            }), 404
        
        # Enviar o arquivo para download
        return send_file(file_path, as_attachment=True)
    
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@debug_bp.route('/list')
def list_files():
    """
    Listar todos os arquivos de debug disponíveis (formato JSON)
    """
    try:
        # Verificar se o diretório existe
        if not os.path.exists(DEBUG_DIR):
            return jsonify({
                'error': 'Diretório de debug não encontrado',
                'path': DEBUG_DIR
            }), 404
        
        # Listar todos os arquivos no diretório de debug
        files = os.listdir(DEBUG_DIR)
        
        # Filtrar apenas arquivos HTML
        html_files = [f for f in files if f.endswith('.html')]
        
        # Obter informações detalhadas sobre cada arquivo
        files_info = []
        for file_name in html_files:
            file_path = os.path.join(DEBUG_DIR, file_name)
            file_size = os.path.getsize(file_path)
            file_time = os.path.getmtime(file_path)
            
            files_info.append({
                'name': file_name,
                'path': file_path,
                'size': file_size,
                'time': file_time
            })
        
        # Ordenar por data de modificação (mais recentes primeiro)
        files_info.sort(key=lambda x: x['time'], reverse=True)
        
        return jsonify({
            'debug_dir': DEBUG_DIR,
            'files_count': len(files_info),
            'files': files_info
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

# Função para registrar o blueprint na aplicação Flask
def register_debug_routes(app):
    """
    Registrar as rotas de debug na aplicação Flask
    """
    app.register_blueprint(debug_bp)
    print("Rotas de debug registradas com sucesso!")
