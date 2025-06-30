# crear_superusuario.py
from app import app, db, Usuario
from werkzeug.security import generate_password_hash

with app.app_context():
    # Datos del superusuario
    username = 'JeimarSA'
    email = 'jeimargonzalez15@gmail.com'
    password = '1234SA'
    rol = 'superusuario'
    activo = True

    # Verificar si ya existe un usuario con ese nombre
    usuario_existente = Usuario.query.filter_by(username=username).first()

    if usuario_existente:
        print(f"El usuario '{username}' ya existe.")
    else:
        hashed_pw = generate_password_hash(password)
        nuevo_usuario = Usuario(
            username=username,
            email=email,
            password_hash=hashed_pw,
            rol=rol,
            activo=activo
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        print(f"Superusuario '{username}' creado exitosamente.")
