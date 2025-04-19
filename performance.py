"""
Módulo para otimização de desempenho do sistema web
--------------------------------------------------
Este módulo contém funções para otimizar o carregamento e desempenho do site.
"""
import os
import gzip
import shutil
import hashlib
import re
from datetime import datetime, timedelta
from flask import request, make_response, current_app

class PerformanceOptimizer:
    """Classe para otimizar o desempenho do sistema web."""
    
    def __init__(self, app=None, static_folder='static', cache_timeout=86400):
        self.app = app
        self.static_folder = static_folder
        self.cache_timeout = cache_timeout
        self.compressed_files = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializar a otimização para a aplicação Flask."""
        self.app = app
        
        # Registrar funções de otimização
        self._register_compression()
        self._register_caching()
        self._register_asset_versioning()
        
        # Comprimir arquivos estáticos
        self.compress_static_files()
    
    def _register_compression(self):
        """Registrar middleware para compressão de resposta."""
        @self.app.after_request
        def compress_response(response):
            # Verificar se a resposta deve ser comprimida
            if self._should_compress(response):
                accept_encoding = request.headers.get('Accept-Encoding', '')
                if 'gzip' in accept_encoding:
                    # Verificar se a resposta já está em modo de passagem direta
                    if hasattr(response, 'direct_passthrough') and response.direct_passthrough:
                        # Não comprimir respostas em modo de passagem direta
                        return response
                    
                    try:
                        response.data = gzip.compress(response.data)
                        response.headers['Content-Encoding'] = 'gzip'
                        response.headers['Content-Length'] = len(response.data)
                    except Exception as e:
                        # Registrar erro e continuar sem compressão
                        if self.app.logger:
                            self.app.logger.error(f"Erro ao comprimir resposta: {str(e)}")
            
            return response
    
    def _register_caching(self):
        """Registrar middleware para cache de resposta."""
        @self.app.after_request
        def add_cache_headers(response):
            # Adicionar cabeçalhos de cache para arquivos estáticos
            if self._should_cache(response):
                response.headers['Cache-Control'] = f'public, max-age={self.cache_timeout}'
                response.headers['Expires'] = (datetime.now() + timedelta(seconds=self.cache_timeout)).strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            return response
    
    def _register_asset_versioning(self):
        """Registrar função para versionamento de assets."""
        @self.app.context_processor
        def asset_versioning():
            def versioned_url(filename):
                # Obter caminho completo do arquivo
                filepath = os.path.join(self.app.static_folder, filename)
                
                # Verificar se o arquivo existe
                if not os.path.exists(filepath):
                    return f'/static/{filename}'
                
                # Calcular hash do arquivo
                file_hash = self._calculate_file_hash(filepath)
                
                # Retornar URL com hash como parâmetro de versão
                return f'/static/{filename}?v={file_hash[:8]}'
            
            return dict(versioned_url=versioned_url)
    
    def _should_compress(self, response):
        """Verificar se a resposta deve ser comprimida."""
        # Verificar se a resposta já está comprimida
        if response.headers.get('Content-Encoding'):
            return False
        
        # Verificar se o tipo de conteúdo é compressível
        content_type = response.headers.get('Content-Type', '')
        compressible_types = [
            'text/', 
            'application/json', 
            'application/javascript', 
            'application/xml', 
            'application/xhtml+xml'
        ]
        
        for t in compressible_types:
            if t in content_type:
                return True
        
        return False
    
    def _should_cache(self, response):
        """Verificar se a resposta deve ser cacheada."""
        # Verificar se é um arquivo estático
        if not request.path.startswith('/static/'):
            return False
        
        # Verificar se o método é GET
        if request.method != 'GET':
            return False
        
        # Verificar se o status é 200 OK
        if response.status_code != 200:
            return False
        
        return True
    
    def _calculate_file_hash(self, filepath):
        """Calcular hash MD5 de um arquivo."""
        hash_md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def compress_static_files(self):
        """Comprimir arquivos estáticos para servir mais rapidamente."""
        static_dir = os.path.join(self.app.root_path, self.static_folder)
        
        # Verificar se o diretório existe
        if not os.path.exists(static_dir):
            return
        
        # Tipos de arquivo a comprimir
        compressible_extensions = ['.css', '.js', '.html', '.xml', '.json', '.svg']
        
        # Percorrer todos os arquivos no diretório estático
        for root, _, files in os.walk(static_dir):
            for filename in files:
                # Verificar se a extensão é compressível
                if any(filename.endswith(ext) for ext in compressible_extensions):
                    filepath = os.path.join(root, filename)
                    compressed_filepath = filepath + '.gz'
                    
                    # Verificar se o arquivo comprimido já existe e é mais recente
                    if os.path.exists(compressed_filepath) and os.path.getmtime(compressed_filepath) > os.path.getmtime(filepath):
                        continue
                    
                    # Comprimir o arquivo
                    with open(filepath, 'rb') as f_in:
                        with gzip.open(compressed_filepath, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Armazenar informações do arquivo comprimido
                    rel_path = os.path.relpath(filepath, static_dir)
                    self.compressed_files[rel_path] = os.path.relpath(compressed_filepath, static_dir)
    
    def minify_html(self, html_content):
        """Minificar conteúdo HTML."""
        # Remover comentários
        html_content = re.sub(r'<!--(.*?)-->', '', html_content, flags=re.DOTALL)
        # Remover espaços em branco entre tags
        html_content = re.sub(r'>\s+<', '><', html_content)
        # Remover espaços em branco no início e fim de linhas
        html_content = re.sub(r'^\s+|\s+$', '', html_content, flags=re.MULTILINE)
        
        return html_content
    
    def minify_css(self, css_content):
        """Minificar conteúdo CSS."""
        # Remover comentários
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        # Remover espaços em branco desnecessários
        css_content = re.sub(r'\s+', ' ', css_content)
        # Remover espaços em branco antes e depois de caracteres especiais
        css_content = re.sub(r'\s*([\{\}\:\;\,])\s*', r'\1', css_content)
        # Remover ponto e vírgula no final de blocos
        css_content = re.sub(r';}', '}', css_content)
        
        return css_content
    
    def minify_js(self, js_content):
        """Minificar conteúdo JavaScript."""
        # Esta é uma versão simplificada. Para produção, use uma biblioteca como UglifyJS
        # Remover comentários de linha única
        js_content = re.sub(r'//.*$', '', js_content, flags=re.MULTILINE)
        # Remover comentários de múltiplas linhas
        js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
        # Remover espaços em branco desnecessários
        js_content = re.sub(r'\s+', ' ', js_content)
        # Remover espaços em branco antes e depois de caracteres especiais
        js_content = re.sub(r'\s*([\{\}\(\)\[\]\:\;\,\+\-\*\/\=])\s*', r'\1', js_content)
        
        return js_content
    
    def optimize_images(self, image_dir=None):
        """Otimizar imagens para web."""
        # Esta função requer ferramentas externas como PIL ou bibliotecas de otimização de imagem
        # Implementação simplificada para demonstração
        if image_dir is None:
            image_dir = os.path.join(self.app.root_path, self.static_folder, 'img')
        
        # Verificar se o diretório existe
        if not os.path.exists(image_dir):
            return
        
        # Aqui você implementaria a otimização de imagens
        # Por exemplo, redimensionar, comprimir, converter para formatos mais eficientes, etc.
        print(f"Otimização de imagens em {image_dir} (simulação)")
    
    def generate_critical_css(self, template_name, output_file=None):
        """Gerar CSS crítico para carregamento inicial rápido."""
        # Esta função requer ferramentas externas como criticalcss
        # Implementação simplificada para demonstração
        if output_file is None:
            output_file = os.path.join(self.app.root_path, self.static_folder, 'css', f'critical-{template_name}.css')
        
        # Aqui você implementaria a extração de CSS crítico
        # Por exemplo, analisar o template, extrair os estilos necessários para o conteúdo acima da dobra, etc.
        print(f"Geração de CSS crítico para {template_name} (simulação)")
    
    def analyze_performance(self):
        """Analisar o desempenho do site e gerar relatório."""
        # Esta função analisaria o desempenho do site e geraria um relatório
        # Implementação simplificada para demonstração
        report = {
            'compressed_files': len(self.compressed_files),
            'cache_timeout': self.cache_timeout,
            'static_folder': self.static_folder
        }
        
        return report

