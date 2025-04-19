// Adiciona a classe 'active' ao item de menu atual
document.addEventListener('DOMContentLoaded', function() {
    // Obtém o caminho atual da URL
    const currentPath = window.location.pathname;
    
    // Função para verificar e marcar links ativos
    function setActiveLinks() {
        // Para links diretos na navbar
        document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
            const href = link.getAttribute('href');
            if (href && (href === currentPath || currentPath.includes(href) && href !== '/')) {
                link.classList.add('active');
                
                // Se o link estiver em um dropdown, também marca o dropdown como ativo
                const dropdownToggle = link.closest('.dropdown')?.querySelector('.dropdown-toggle');
                if (dropdownToggle) {
                    dropdownToggle.classList.add('active');
                }
            }
        });
        
        // Para itens de dropdown
        document.querySelectorAll('.dropdown-item').forEach(item => {
            const href = item.getAttribute('href');
            if (href && (href === currentPath || currentPath.includes(href) && href !== '/')) {
                item.classList.add('active');
                
                // Marca o dropdown pai como ativo
                const dropdownToggle = item.closest('.dropdown')?.querySelector('.dropdown-toggle');
                if (dropdownToggle) {
                    dropdownToggle.classList.add('active');
                }
            }
        });
    }
    
    // Executa a função quando a página carrega
    setActiveLinks();
});
