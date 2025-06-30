# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from PIL import Image
import os, uuid
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'supersecreto'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///animales.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
socketio = SocketIO(app, async_mode='eventlet')

# Manejo de sesiones
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Ruta para login
login_manager.login_message = None

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


#chat
@socketio.on('mensaje nuevo')
def handle_mensaje(data):
    # data es un dict con {usuario, mensaje}
    emit('mensaje recibido', data, broadcast=True)


# Manejo de imagenes

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB
MAX_IMAGE_SIZE = (600, 600)  # píxeles

UPLOAD_FOLDER = 'static/img'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configuración de correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'jeimargonzalez15@gmail.com'  # Correo al que llegaran los mansajes
app.config['MAIL_PASSWORD'] = 'meohevvootcyegrv'            #contraseña de verif dada por google

mail = Mail(app)
db = SQLAlchemy(app)

# models.py
class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(100), unique=True)  
    password_hash = db.Column(db.String(128))
    rol = db.Column(db.String(20), default='usuario')
    activo = db.Column(db.Boolean, default=True)

class Animal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    especie = db.Column(db.String(20))
    edad = db.Column(db.String(20))
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(100))
    estatus = db.Column(db.String(20), default="Disponible")  # Nuevo campo de estatus
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)

class Adopcion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey('animal.id'))
    nombre = db.Column(db.String(50))
    email = db.Column(db.String(100))
    comentario = db.Column(db.Text)

class Ubicacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(100))  # Asegúrate de tener este campo

    
# Manejo de sesiones

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = Usuario.query.filter_by(username=username).first()

        if not user:
            flash("El usuario no existe.")
            return redirect(url_for('login'))

        if not user.activo:
            flash("Tu cuenta aún no ha sido aprobada por el superusuario.")
            return redirect(url_for('login'))

        if not check_password_hash(user.password_hash, password):
            flash("Contraseña incorrecta.")
            return redirect(url_for('login'))

        login_user(user)
        flash("Has iniciado sesión correctamente.")
        return redirect(url_for('index'))

    return render_template('login.html')



@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión.")
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        rol = request.form.get('rol', 'usuario')  # ← captura el rol enviado

        if not username or not email or not password or not confirm_password:
            flash("Por favor completa todos los campos.")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Las contraseñas no coinciden.")
            return redirect(url_for('register'))

        existing_user = Usuario.query.filter_by(username=username).first()
        if existing_user:
            flash("El nombre de usuario ya está en uso.")
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)

        nuevo_usuario = Usuario(
            username=username,
            email=email,              # <-- Guardar email aquí
            password_hash=hashed_pw,
            rol=rol,
            activo=(rol != 'admin')                   # ← usa el rol que se eligió
        )
        db.session.add(nuevo_usuario)
        db.session.commit()

        flash("Registro exitoso. Ya puedes iniciar sesión. Si te registraste como administrador debes esparar validación")
        return redirect(url_for('login'))

    return render_template('register.html')

#Superusuario

@app.route('/validar_admines')
@login_required
def validar_admines():
    if current_user.rol != 'superusuario':
        flash("No tienes permiso para acceder a esta página.")
        return redirect(url_for('index'))

    admins_pendientes = Usuario.query.filter_by(rol='admin', activo=False).all()
    return render_template('validar_admines.html', admins=admins_pendientes)

@app.route('/aprobar_admin/<int:user_id>', methods=['POST'])
@login_required
def aprobar_admin(user_id):
    if current_user.rol != 'superusuario':
        flash("No tienes permiso para realizar esta acción.")
        return redirect(url_for('index'))

    user = Usuario.query.get_or_404(user_id)
    if user.rol == 'admin' and not user.activo:
        user.activo = True
        db.session.commit()
        flash(f"Usuario {user.username} aprobado como administrador.")

    return redirect(url_for('validar_admines'))

@app.route('/panel_superusuario')
@login_required
def panel_superusuario():
    if current_user.rol != 'superusuario':
        flash("Acceso restringido al superusuario.")
        return redirect(url_for('index'))
    
    animales = Animal.query.all()  # Ver incluso los eliminados
    return render_template('panel_superusuario.html', animales=animales)

@app.route('/eliminar_animal/<int:id>', methods=['POST'])
@login_required
def eliminar_animal(id):
    if current_user.rol != 'superusuario':
        flash("Solo el superusuario puede ocultar animales.")
        return redirect(url_for('index'))

    animal = Animal.query.get_or_404(id)
    animal.estatus = "Eliminado"
    db.session.commit()
    flash(f"El animal '{animal.nombre}' ha sido ocultado del inicio.")
    return redirect(url_for('panel_superusuario'))



#Back Animales

@app.route('/')
def index():
    animales = Animal.query.filter(Animal.estatus != 'Eliminado').all()
    return render_template('index.html', animales=animales)

@app.route('/reportar', methods=['GET', 'POST'])
@login_required
def reportar():
    if request.method == 'POST':
        nombre = request.form['nombre']
        especie = request.form['especie']
        edad = request.form['edad']
        descripcion = request.form['descripcion']
        lat = request.form.get('lat')
        lng = request.form.get('lng')

        imagen_file = request.files['imagen']
        filename = None

        if imagen_file and allowed_file(imagen_file.filename):
            ext = imagen_file.filename.rsplit('.', 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(unique_name))
            try:
                imagen_file.save(filepath)
                with Image.open(filepath) as img:
                    img.thumbnail(MAX_IMAGE_SIZE)
                    img.save(filepath)
                filename = unique_name
            except Exception as e:
                flash(f"Error al procesar la imagen: {e}")
                return redirect(url_for('reportar'))
        else:
            flash("Archivo inválido o faltante.")
            return redirect(url_for('reportar'))

        nuevo = Animal(
            nombre=nombre,
            especie=especie,
            edad=edad,
            descripcion=descripcion,
            imagen=filename or "default.jpg",
            lat=float(lat) if lat else None,
            lng=float(lng) if lng else None
        )
        db.session.add(nuevo)
        db.session.commit()
        flash('Animal reportado exitosamente')
        return redirect(url_for('index'))

    return render_template('reportar.html')



@app.route('/adoptar/<int:id>', methods=['GET', 'POST'])
@login_required
def adoptar(id):
    animal = Animal.query.get_or_404(id)
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        comentario = request.form['comentario']

        solicitud = Adopcion(animal_id=id, nombre=nombre, email=email, comentario=comentario)

        animal.estatus = "En proceso"

        db.session.add(solicitud)
        db.session.commit()

        msg = Message(
            'Gracias por tu interés en adoptar',
            sender='tucorreo@gmail.com',
            recipients=[email]
        )
        msg.body = f"Hola {nombre}, gracias por interesarte en adoptar a {animal.nombre}. Nos pondremos en contacto contigo pronto."
        mail.send(msg)

        flash('¡Solicitud de adopción enviada!')
        return redirect(url_for('index'))

    # Enviar username y email actuales del usuario para prellenar el formulario
    return render_template(
        'adoptar.html',
        animal=animal,
        default_nombre=current_user.username or '',
        default_email=current_user.email if (hasattr(current_user, 'email') and current_user.email) else ''
    )




@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol not in ['admin', 'superusuario']:
        flash("No tienes permiso para acceder a esta página.")
        return redirect(url_for('index'))

    animales = Animal.query.filter(Animal.estatus != 'Eliminado').all()
    ubicaciones = Ubicacion.query.all()

    # Crear un set con tuplas (lat,lng) de animales ya registrados para facilitar la búsqueda en plantilla
    coords_animales = {(a.lat, a.lng) for a in animales}

    return render_template('dashboard.html', animales=animales, ubicaciones=ubicaciones, coords_animales=coords_animales)


@app.route('/actualizar_estatus/<int:id>', methods=['POST'])
@login_required
def actualizar_estatus(id):
    animal = Animal.query.get_or_404(id)
    nuevo_estatus = request.form.get('estatus')
    if nuevo_estatus in ["Disponible", "En proceso", "Adoptado"]:
        animal.estatus = nuevo_estatus
        db.session.commit()
        flash(f"Estatus de {animal.nombre} actualizado a {nuevo_estatus}")
    else:
        flash("Estatus no válido")
    return redirect(url_for('dashboard'))

@app.route('/crear_desde_ubicacion/<int:id>', methods=['POST'])
@login_required
def crear_desde_ubicacion(id):
    if current_user.rol not in ['admin', 'superusuario']:
        flash("Acceso no autorizado.")
        return redirect(url_for('index'))

    ubicacion = Ubicacion.query.get_or_404(id)

    nombre = request.form['nombre']
    especie = request.form['especie']
    edad = request.form['edad']
    descripcion = request.form['descripcion']

    nuevo = Animal(
        nombre=nombre,
        especie=especie,
        edad=edad,
        descripcion=descripcion,
        imagen=ubicacion.imagen,
        estatus="Disponible",
        lat=ubicacion.lat,
        lng=ubicacion.lng
    )

    db.session.add(nuevo)
    db.session.commit()

    flash("Animal agregado como adoptable.")
    return redirect(url_for('dashboard'))


@app.route('/ubicacion', methods=['GET', 'POST'])
def ubicacion():
    if request.method == 'POST':
        lat = request.form['lat']
        lng = request.form['lng']
        descripcion = request.form['descripcion']
        imagen_file = request.files.get('imagen')
        filename = None

        # Procesamiento de imagen si se proporciona
        if imagen_file and allowed_file(imagen_file.filename):
            ext = imagen_file.filename.rsplit('.', 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(unique_name))
            try:
                imagen_file.save(filepath)
                with Image.open(filepath) as img:
                    img.thumbnail(MAX_IMAGE_SIZE)
                    img.save(filepath)
                filename = unique_name  # solo el nombre del archivo
            except Exception as e:
                flash(f"Error al guardar imagen: {e}")
                return redirect(url_for('ubicacion'))

        nueva = Ubicacion(
            lat=lat,
            lng=lng,
            descripcion=descripcion,
            imagen=filename or "default.jpg"
        )
        db.session.add(nueva)
        db.session.commit()
        flash('Ubicación reportada correctamente')
        return redirect(url_for('ubicacion'))

    # Ubicaciones reportadas manualmente
    ubicaciones_raw = Ubicacion.query.all()
    ubicaciones = []
    for u in ubicaciones_raw:
        img_url = url_for('static', filename=f'img/{u.imagen}') if u.imagen else url_for('static', filename='img/default.jpg')
        ubicaciones.append({
            "lat": u.lat,
            "lng": u.lng,
            "descripcion": u.descripcion,
            "imagen": img_url
        })

    # Animales con ubicación geográfica
    animales_con_ubicacion = Animal.query.filter(Animal.lat != None, Animal.lng != None, Animal.estatus != 'Adoptado').all()
    animales = []
    for a in animales_con_ubicacion:
        img_url = url_for('static', filename=f'img/{a.imagen}') if a.imagen else url_for('static', filename='img/default.jpg')
        animales.append({
            "lat": a.lat,
            "lng": a.lng,
            "nombre": a.nombre,
            "especie": a.especie,
            "descripcion": a.descripcion,
            "imagen": img_url
        })

    return render_template('ubicacion.html', ubicaciones=ubicaciones, animales=animales)


@app.route('/ayudar')
def ayudar():
    return render_template('ayudar.html')


@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        mensaje = request.form['mensaje']
        msg = Message('Nuevo mensaje de contacto', sender='tucorreo@gmail.com', recipients=['jeimargonzalez15@gmail.com'])
        msg.body = f"De: {nombre} ({email})\n\n{mensaje}"
        mail.send(msg)
        flash('Mensaje enviado correctamente')
        return redirect(url_for('index'))
    return render_template('contacto.html')

@app.route('/blog')
@login_required
def blog():
    return render_template('blog.html')

@app.route('/chat_mensaje', methods=['POST'])
@login_required
def chat_mensaje():
    usuario = request.form.get('usuario')
    mensaje = request.form.get('mensaje', '')
    imagen = request.files.get('imagen')
    imagen_url = None

    if imagen and allowed_file(imagen.filename):
        filename = f"{uuid.uuid4().hex}_{secure_filename(imagen.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        imagen.save(filepath)
        imagen_url = url_for('static', filename=f'img/{filename}')

    socketio.emit('mensaje recibido', {
        'usuario': usuario,
        'mensaje': mensaje,
        'imagen_url': imagen_url
    })

    return '', 204  # Sin contenido, para evitar redirección


if __name__ == '__main__':
    if not os.path.exists('animales.db'):
        with app.app_context():
            db.create_all()
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))