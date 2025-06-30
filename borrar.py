from app import app, db, Ubicacion

lat_objetivo = 19.504926602342145
lng_objetivo = -99.1471064834671

with app.app_context():
    ubicacion = Ubicacion.query.filter_by(lat=lat_objetivo, lng=lng_objetivo).first()
    if ubicacion:
        db.session.delete(ubicacion)
        db.session.commit()
        print("Registro de ubicación eliminado.")
    else:
        print("No se encontró el registro con esa latitud y longitud.")
