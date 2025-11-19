// Editor de Fórmulas Simplificado
// Funcionalidades: autocomplete, validação, inserção de variáveis e operadores

document.addEventListener('DOMContentLoaded', function() {
  const formulaInput = document.getElementById('formula-input');
  if (!formulaInput) return;
  
  // Carrega variáveis customizadas
  carregarVariaveisCustomizadas();
  
  // Implementa autocomplete básico
  implementarAutocomplete(formulaInput);
});

function carregarVariaveisCustomizadas() {
  // Busca variáveis customizadas ativas via API ou template
  // Por enquanto, vamos usar uma abordagem que busca do contexto da página
  // Em uma implementação completa, isso seria feito via AJAX
  
  const container = document.getElementById('variaveis-customizadas');
  if (!container) return;
  
  // Variáveis padrão sempre disponíveis
  const variaveisPadrao = ['dap', 'altura', 'biomassa'];
  
  // Adiciona botões para variáveis padrão (já estão no HTML)
  // Aqui podemos adicionar variáveis customizadas dinamicamente se necessário
  
  // Exemplo de como adicionar variáveis customizadas:
  // fetch('/api/variaveis-customizadas/')
  //   .then(response => response.json())
  //   .then(data => {
  //     data.variaveis.forEach(variavel => {
  //       const btn = document.createElement('button');
  //       btn.type = 'button';
  //       btn.className = 'px-2 py-1 bg-green-100 text-green-700 rounded text-xs hover:bg-green-200';
  //       btn.textContent = variavel.codigo;
  //       btn.onclick = () => insertVariable(variavel.codigo);
  //       container.appendChild(btn);
  //     });
  //   });
}

function implementarAutocomplete(textarea) {
  let autocompleteDiv = null;
  let currentSuggestions = [];
  let selectedIndex = -1;
  
  // Variáveis e funções disponíveis
  const suggestions = {
    variaveis: ['dap', 'altura', 'biomassa', 'tree'],
    funcoes: ['math.log', 'math.exp', 'math.sqrt', 'math.pi', 'math.sin', 'math.cos'],
    operadores: ['+', '-', '*', '/', '**', '(', ')']
  };
  
  textarea.addEventListener('input', function(e) {
    const cursorPos = this.selectionStart;
    const textBeforeCursor = this.value.substring(0, cursorPos);
    const lastWord = textBeforeCursor.match(/(\w+)$/);
    
    if (lastWord && lastWord[1].length > 0) {
      const word = lastWord[1].toLowerCase();
      const matches = [];
      
      // Busca em variáveis
      suggestions.variaveis.forEach(v => {
        if (v.toLowerCase().startsWith(word)) {
          matches.push({text: v, type: 'variável'});
        }
      });
      
      // Busca em funções
      suggestions.funcoes.forEach(f => {
        if (f.toLowerCase().includes(word)) {
          matches.push({text: f, type: 'função'});
        }
      });
      
      if (matches.length > 0) {
        mostrarAutocomplete(matches, cursorPos);
      } else {
        esconderAutocomplete();
      }
    } else {
      esconderAutocomplete();
    }
  });
  
  textarea.addEventListener('keydown', function(e) {
    if (autocompleteDiv && autocompleteDiv.style.display !== 'none') {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, currentSuggestions.length - 1);
        atualizarSelecaoAutocomplete();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, -1);
        atualizarSelecaoAutocomplete();
      } else if (e.key === 'Enter' && selectedIndex >= 0) {
        e.preventDefault();
        inserirSugestao(currentSuggestions[selectedIndex].text);
      } else if (e.key === 'Escape') {
        esconderAutocomplete();
      }
    }
  });
  
  function mostrarAutocomplete(matches, cursorPos) {
    currentSuggestions = matches;
    selectedIndex = -1;
    
    if (!autocompleteDiv) {
      autocompleteDiv = document.createElement('div');
      autocompleteDiv.id = 'autocomplete-suggestions';
      autocompleteDiv.className = 'absolute bg-white border border-gray-300 rounded shadow-lg z-50 max-h-48 overflow-y-auto';
      document.body.appendChild(autocompleteDiv);
    }
    
    autocompleteDiv.innerHTML = matches.map((match, index) => 
      `<div class="px-3 py-2 hover:bg-gray-100 cursor-pointer suggestion-item" data-index="${index}">
        <span class="font-medium">${match.text}</span>
        <span class="text-xs text-gray-500 ml-2">${match.type}</span>
      </div>`
    ).join('');
    
    // Posiciona o autocomplete próximo ao cursor
    const rect = textarea.getBoundingClientRect();
    autocompleteDiv.style.top = (rect.top + rect.height) + 'px';
    autocompleteDiv.style.left = rect.left + 'px';
    autocompleteDiv.style.display = 'block';
    
    // Adiciona eventos de clique
    autocompleteDiv.querySelectorAll('.suggestion-item').forEach(item => {
      item.addEventListener('click', function() {
        const index = parseInt(this.dataset.index);
        inserirSugestao(matches[index].text);
      });
    });
  }
  
  function atualizarSelecaoAutocomplete() {
    if (!autocompleteDiv) return;
    
    autocompleteDiv.querySelectorAll('.suggestion-item').forEach((item, index) => {
      if (index === selectedIndex) {
        item.classList.add('bg-blue-100');
      } else {
        item.classList.remove('bg-blue-100');
      }
    });
  }
  
  function inserirSugestao(text) {
    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = textarea.value.substring(0, cursorPos);
    const textAfterCursor = textarea.value.substring(cursorPos);
    const lastWordMatch = textBeforeCursor.match(/(\w+)$/);
    
    if (lastWordMatch) {
      const startPos = cursorPos - lastWordMatch[1].length;
      textarea.value = textBeforeCursor.substring(0, startPos) + text + textAfterCursor;
      textarea.focus();
      textarea.setSelectionRange(startPos + text.length, startPos + text.length);
    }
    
    esconderAutocomplete();
  }
  
  function esconderAutocomplete() {
    if (autocompleteDiv) {
      autocompleteDiv.style.display = 'none';
    }
    selectedIndex = -1;
  }
  
  // Esconde autocomplete ao clicar fora
  document.addEventListener('click', function(e) {
    if (autocompleteDiv && !autocompleteDiv.contains(e.target) && e.target !== textarea) {
      esconderAutocomplete();
    }
  });
}

// Funções globais para inserção (já definidas no template, mas garantimos que existam)
if (typeof insertVariable === 'undefined') {
  window.insertVariable = function(varName) {
    const textarea = document.getElementById('formula-input');
    if (!textarea) return;
    
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const before = text.substring(0, start);
    const after = text.substring(end, text.length);
    
    textarea.value = before + varName + after;
    textarea.focus();
    textarea.setSelectionRange(start + varName.length, start + varName.length);
  };
}

if (typeof insertText === 'undefined') {
  window.insertText = function(text) {
    const textarea = document.getElementById('formula-input');
    if (!textarea) return;
    
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const textValue = textarea.value;
    const before = textValue.substring(0, start);
    const after = textValue.substring(end, textValue.length);
    
    textarea.value = before + text + after;
    textarea.focus();
    
    // Se for uma função, posiciona cursor dentro dos parênteses
    if (text.endsWith('(')) {
      textarea.setSelectionRange(start + text.length, start + text.length);
    } else {
      textarea.setSelectionRange(start + text.length, start + text.length);
    }
  };
}

if (typeof validarFormula === 'undefined') {
  window.validarFormula = function() {
    const formula = document.getElementById('formula-input').value;
    const coeficientes = document.getElementById('coeficientes-json').value;
    const resultado = document.getElementById('validacao-resultado');
    
    if (!resultado) return;
    
    resultado.innerHTML = '<span class="text-blue-500">Validando...</span>';
    
    fetch('/api/validar-formula/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
      },
      body: `formula=${encodeURIComponent(formula)}&coeficientes=${encodeURIComponent(coeficientes)}`
    })
    .then(response => response.json())
    .then(data => {
      if (data.valido) {
        resultado.innerHTML = `<span class="text-green-600">✓ ${data.mensagem}</span>`;
      } else {
        resultado.innerHTML = `<span class="text-red-600">✗ Erro: ${data.erro}</span>`;
      }
    })
    .catch(error => {
      resultado.innerHTML = `<span class="text-red-600">✗ Erro ao validar: ${error}</span>`;
    });
  };
}

