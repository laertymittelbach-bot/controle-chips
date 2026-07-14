# 📱 Controle de Chips & Estoque - Equipe Laerty

Aplicativo web para controle de estoque de chips TIM com leitura de código de barras.

**Senha de acesso:** `laerty2026`  
(Você pode mudar a senha no arquivo `app.py` se quiser)

---

## Como colocar ONLINE (Streamlit Cloud) - Passo a Passo Fácil

### 1. Crie conta no GitHub (se ainda não tiver)
- Acesse: https://github.com
- Clique em **Sign up** e crie sua conta grátis

### 2. Crie um novo repositório
1. Depois de logado, clique no **+** (canto superior direito) → **New repository**
2. Nome do repositório: `controle-chips-laerty`
3. Deixe como **Public**
4. Clique em **Create repository**

### 3. Suba os arquivos
1. Na página do repositório, clique em **uploading an existing file**
2. Arraste os 3 arquivos:
   - `app.py`
   - `requirements.txt`
   - `README.md`
3. Clique em **Commit changes**

### 4. Publique no Streamlit Cloud
1. Acesse: https://share.streamlit.io
2. Clique em **Sign in with GitHub**
3. Autorize o Streamlit
4. Clique em **New app**
5. Selecione o repositório: `controle-chips-laerty`
6. Em **Main file path** deixe: `app.py`
7. Clique em **Deploy!**

Pronto! Em 1~2 minutos o Streamlit vai gerar um link tipo:

```
https://controle-chips-laerty.streamlit.app
```

Você manda esse link para os promotores. Eles abrem no celular e usam.

---

## Senha de acesso
- Senha padrão: **laerty2026**
- Para mudar: abra o arquivo `app.py` e altere a linha:
  ```python
  SENHA_CORRETA = "laerty2026"
  ```

---

## Funcionalidades
- Entrada de chips (código de barras)
- Entrega para promotor
- Registrar venda
- Remanejamento
- Defeito / Devolução
- Dashboard
- Estoque por promotor
- Histórico
- Importar planilha SmartRader
