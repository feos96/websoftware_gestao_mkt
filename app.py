from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = 'sua_chave_supersecreta'

# -------------------- Banco de Dados --------------------

def init_db():
    conn = sqlite3.connect('manifestos.db')
    cursor = conn.cursor()

    # Criação da tabela se não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manifestos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conjunto TEXT,
            numero_manifesto TEXT,
            rota TEXT,
            status TEXT DEFAULT 'Aberto',
            filial TEXT,
            origem TEXT,
            destino TEXT,
            data_transmissao TEXT,
            data_encerramento TEXT,
            encerrado_por TEXT
        );
    ''')

    # Verifica se a coluna 'encerrado_por' existe (caso banco antigo)
    try:
        cursor.execute("SELECT encerrado_por FROM manifestos LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE manifestos ADD COLUMN encerrado_por TEXT")

    conn.commit()
    conn.close()

def get_conn():
    conn = sqlite3.connect('manifestos.db')
    conn.row_factory = sqlite3.Row
    return conn

init_db()

# -------------------- Usuários (Simulado) --------------------

usuarios = {}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        if email in usuarios and usuarios[email]['senha'] == senha:
            session['usuario'] = usuarios[email]['nome']
            return redirect(url_for('index'))
        flash('E-mail ou senha inválidos!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        matricula = request.form['matricula']
        email = request.form['email']
        senha = request.form['senha']
        confirmar = request.form['confirmar_senha']

        if senha != confirmar:
            flash('As senhas não coincidem.', 'danger')
            return redirect(url_for('register'))

        if email in usuarios:
            flash('Este e-mail já está registrado.', 'warning')
            return redirect(url_for('register'))

        usuarios[email] = {
            'nome': nome,
            'matricula': matricula,
            'senha': senha
        }
        flash('Cadastro realizado com sucesso. Faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# -------------------- Páginas Principais --------------------

@app.route('/')
def index():
    if 'usuario' in session:
        return render_template('index.html', usuario=session['usuario'])
    return redirect(url_for('login'))

@app.route('/frotas')
def frotas():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('frotas.html')

@app.route('/motoristas')
def motoristas():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('motoristas.html')

@app.route('/programacao')
def programacao():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('programacao.html')

@app.route('/historico')
def historico():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('historico.html')

@app.route('/localizacao')
def localizacao():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('localizacao.html')

@app.route('/protheus')
def protheus():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('protheus.html')

# -------------------- Manifestos --------------------

@app.route('/manifestos')
def manifestos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_conn()
    manifestos_abertos = conn.execute(
        "SELECT * FROM manifestos WHERE status = 'Aberto' ORDER BY data_transmissao DESC"
    ).fetchall()
    manifestos_encerrados = conn.execute(
        "SELECT * FROM manifestos WHERE status = 'Encerrado' ORDER BY data_encerramento DESC"
    ).fetchall()
    conn.close()

    return render_template(
        'manifestos.html',
        manifestos_abertos=manifestos_abertos,
        manifestos_encerrados=manifestos_encerrados
    )

@app.route('/manifestos/novo', methods=['GET', 'POST'])
def novo_manifesto():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        f = request.form
        conn = get_conn()
        conn.execute('''
            INSERT INTO manifestos (
                conjunto, numero_manifesto, rota, status,
                filial, origem, destino, data_transmissao, data_encerramento, encerrado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f['conjunto'], f['numero_manifesto'], f['rota'], 'Aberto',  # Status fixo
            f['filial'], f['origem'], f['destino'],
            f['data_transmissao'], None, None
        ))
        conn.commit()
        conn.close()
        flash('Manifesto cadastrado com sucesso!', 'success')
        return redirect(url_for('manifestos'))

    return render_template('novo_manifesto.html')

@app.route('/manifestos/encerrar/<int:id>')
def encerrar_manifesto(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    conn = get_conn()
    conn.execute('''
        UPDATE manifestos
        SET status = 'Encerrado',
            data_encerramento = ?,
            encerrado_por = ?
        WHERE id = ?
    ''', (
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        usuario,
        id
    ))
    conn.commit()
    conn.close()
    flash(f'Manifesto encerrado por {usuario}', 'info')
    return redirect(url_for('manifestos'))

@app.route('/manifestos/exportar')
def exportar_manifestos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM manifestos WHERE status = 'Encerrado'", conn)
    conn.close()

    caminho_arquivo = 'manifestos_exportados.xlsx'
    df.to_excel(caminho_arquivo, index=False)

    return send_file(
        caminho_arquivo,
        as_attachment=True,
        download_name='manifestos_historico.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# -------------------- Execução --------------------

if __name__ == '__main__':
    app.run(debug=True)
