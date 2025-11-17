# ✅ **Roteiro de Testes – Habitas (QA Manual + Automação)**

Este roteiro consolida todos os cenários cobertos pelos testes automatizados e organiza cada grupo de funcionalidades em forma de checklist para inspeção manual, auditoria e manutenção futura da suíte de testes.

---

# **📌 1. Controle de Acesso (Access Control)**

## **1.1. Dashboards**
| Cenário | Usuário | Ação | Resultado Esperado |
|--------|---------|-------|--------------------|
| Cidadão tenta acessar Dashboard Técnico | Cidadão | GET `/dashboard_tecnico/` | ❌ Acesso negado (403) |
| Cidadão tenta acessar Dashboard Gestor | Cidadão | GET `/dashboard_gestor/` | ❌ Acesso negado (403) |
| Técnico tenta acessar Dashboard Gestor | Técnico | GET `/dashboard_gestor/` | ❌ Acesso negado (403) |

---

## **1.2. Gestão de Técnicos**
| Cenário | Usuário | Ação | Resultado Esperado |
|--------|---------|-------|--------------------|
| Cidadão tenta listar técnicos pendentes | Cidadão | GET `/tecnicos/pendentes/` | ❌ 403 |
| Técnico tenta listar técnicos pendentes | Técnico | GET `/tecnicos/pendentes/` | ❌ 403 |

---

## **1.3. Laudos**
| Cenário | Usuário | Ação | Resultado |
|--------|---------|-------|-----------|
| Cidadão tenta criar laudo | Cidadão | GET `/laudos/criar/<id>/` | ❌ 403 |
| Cidadão tenta validar laudo | Cidadão | GET `/laudos/validar/<id>/` | ❌ 403 |
| Técnico tenta validar laudo | Técnico | GET `/laudos/validar/<id>/` | ❌ 403 |

---

## **1.4. Notificações**
| Cenário | Usuário | Ação | Resultado |
|--------|---------|-------|-----------|
| Cidadão tenta listar notificações | Cidadão | GET `/notificacoes/` | ❌ 403 |
| Cidadão tenta analisar notificação | Cidadão | GET `/notificacoes/analisar/<id>/` | ❌ 403 |
| Cidadão tenta resolver notificação | Cidadão | GET `/notificacoes/resolver/<id>/` | ❌ 403 |
| Técnico tenta resolver notificação | Técnico | GET `/notificacoes/resolver/<id>/` | ❌ 403 |

---

## **1.5. Usuários Não Autenticados**
| Cenário | Usuário | Ação | Resultado |
|--------|---------|-------|-----------|
| Anônimo tenta acessar rotas protegidas | Anônimo | GET em várias rotas | 🔁 Redirecionado para `/login/` |

---

# **📌 2. Autenticação (Login/Logout)**

## **2.1. Login**
| Cenário | Input | Resultado |
|--------|--------|-----------|
| Login bem-sucedido | Credenciais corretas | ➡️ Redirecionamento + sessão iniciada |
| Login falho | Senha incorreta | ❌ Exibe mensagem "Usuário ou senha inválidos." |

---

## **2.2. Logout**
| Cenário | Ação | Resultado |
|--------|------|-----------|
| Logout | GET `/logout/` | 🔁 Redirecionamento + sessão encerrada |

---

# **📌 3. Dashboards**

## **3.1. Acesso Permitido**
| Usuário | Tela | Resultado |
|---------|------|-----------|
| Gestor | Dashboard Gestor | ✔️ 200 |
| Técnico | Dashboard Técnico | ✔️ 200 |

---

## **3.2. Acesso Negado**
| Usuário | Tela | Resultado |
|---------|------|-----------|
| Técnico | Dashboard Gestor | ❌ 403 |

---

# **📌 4. Laudos**

## **4.1. Criação de Laudo**
| Usuário | Ação | Resultado |
|---------|------|-----------|
| Técnico | POST criar laudo | ✔️ Redireciona e cria laudo no banco |

---

## **4.2. Validação de Laudo**
| Usuário | Ação | Resultado |
|---------|-------|-----------|
| Gestor | POST validar laudo | ✔️ Laudo muda para “Aprovado” |

---

# **📌 5. Notificações**

## **5.1. Criação**
| Usuário | Ação | Resultado |
|---------|------|-----------|
| Cidadão | POST criar notificação | ✔️ Notificação criada |

---

## **5.2. Análise**
| Usuário | Ação | Resultado |
|---------|------|-----------|
| Técnico | POST analisar notificação | ✔️ Define técnico responsável e atualiza dados |

---

## **5.3. Resolução**
| Usuário | Ação | Resultado |
|---------|------|-----------|
| Gestor | POST resolver notificação | ✔️ Notificação marcada como “Resolvida” |

---

# **📌 6. Registro de Usuários**

## **6.1. Registro de Cidadão**
| Ação | Resultado |
|------|-----------|
| POST cadastro cidadão | ✔️ Conta criada com sucesso |

---

## **6.2. Registro de Técnico**
| Ação | Resultado |
|------|-----------|
| POST cadastro técnico com documento | ✔️ Criado com status **Pendente** |

---

# **📌 7. Aprovação de Técnicos**

## **7.1. Listar Técnicos Pendentes**
| Usuário | Resultado |
|---------|-----------|
| Gestor | ✔️ Página contém técnico pendente |

---

## **7.2. Aprovar Técnico**
| Usuário | Ação | Resultado |
|---------|-------|-----------|
| Gestor | POST aprovar técnico | ✔️ Status muda para “Aprovado” |

---

# **📌 Resumo Geral**

| Módulo | Casos Cobertos |
|--------|----------------|
| Controle de Acesso | 15 |
| Autenticação | 3 |
| Dashboards | 3 |
| Laudos | 2 |
| Notificações | 3 |
| Registro | 2 |
| Aprovação de Técnicos | 2 |
| **Total** | **30 cenários de teste** |

---

