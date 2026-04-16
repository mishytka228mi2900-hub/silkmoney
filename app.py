# 1. Импорты
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from pytz import timezone, utc
import os
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy import text

# 1. Импорты
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from pytz import timezone, utc
import os
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy import text  # ← ДОБАВЛЕНО для health check


# 2. ОПРЕДЕЛЕНИЕ функции setup_logging
def setup_logging(app):
    if not app.debug:
        try:
            if not os.path.exists('logs'):
                os.mkdir('logs')
        except Exception as e:
            app.logger.warning(f'Не удалось создать папку логов: {e}')
            return
        
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Приложение запущено')


# 3. Создание приложения
app = Flask(__name__)

# Настройки сессий для работы в Chrome и других браузерах
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
# Загрузка конфигурации
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'admin123-change-in-production')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Настройка базы данных
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///app.db'

# 4. ВЫЗОВ функции setup_logging
setup_logging(app)

# 5. Инициализация базы данных
db = SQLAlchemy(app)

# Инициализация базы данных и создание таблиц
with app.app_context():
    try:
        db.create_all()
        app.logger.info('Таблицы базы данных созданы')
    except Exception as e:
        app.logger.error(f'Ошибка при создании таблиц: {e}')


# Фильтр для преобразования времени в минский часовой пояс
@app.template_filter('minsk_time')
def minsk_time_filter(value, format='%d.%m.%Y %H:%M'):
    if value is None:
        return ''
    try:
        if value.tzinfo is None:
            value = utc.localize(value)
        minsk_tz = timezone('Europe/Minsk')
        minsk_time = value.astimezone(minsk_tz)
        return minsk_time.strftime(format)
    except Exception as e:
        app.logger.error(f'Ошибка при форматировании времени: {e}')
        return value.strftime(format) if hasattr(value, 'strftime') else str(value)


# Модель заказа
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    order = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    def __repr__(self):
        return f'<Order {self.id}: {self.name}>'


# Главная страница
@app.route("/")
def index():
    return render_template('index.html')


# НОВЫЙ КОД: Обработка заказа и админки в корневом маршруте
@app.route("/", methods=['GET', 'POST'])
def index():
    is_admin = session.get('is_admin', False)
    
    # Обработка POST-запроса (форма заказа)
    if request.method == 'POST':
        # Проверка согласия на обработку данных
        if 'privacy' not in request.form:
            flash('Вы должны согласиться с обработкой персональных данных', 'danger')
            return redirect(url_for('index'))
        
        try:
            name = request.form['name'].strip()
            number = request.form['number'].strip()
            order_text = request.form['order'].strip()
            
            # Валидация данных
            if not name or len(name) < 2:
                flash('Имя должно содержать минимум 2 символа', 'danger')
                return redirect(url_for('index'))
            
            if not number or len(number) < 10:
                flash('Неверный формат номера телефона', 'danger')
                return redirect(url_for('index'))
            
            if not order_text:
                flash('Поле заказа не может быть пустым', 'danger')
                return redirect(url_for('index'))
            
            # Создание заказа
            new_order = Order(name=name, number=number, order=order_text)
            
            db.session.add(new_order)
            db.session.commit()
            
            flash('✅ Заказ оформлен успешно! Мы свяжемся с вами в ближайшее время.', 'success')
            app.logger.info(f'Новый заказ #{new_order.id} от {name}')
            
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Ошибка при создании заказа: {e}')
            flash('❌ Ошибка при добавлении заказа. Попробуйте позже.', 'danger')
            return redirect(url_for('index'))
    
    # Обработка GET-запроса (отображение главной страницы)
    else:
        if is_admin:
            orders = Order.query.order_by(Order.date.desc()).all()
            return render_template("index.html", orders=orders, is_admin=is_admin)
        else:
            return render_template("index.html", is_admin=is_admin)


# Удаление заказа
@app.route("/order/<int:id>/delete")
def order_delete(id):
    is_admin = session.get('is_admin', False)
    if not is_admin:
        app.logger.warning(f'Попытка удаления заказа #{id} без прав администратора')
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('order')), 403
    
    order = Order.query.get_or_404(id)
    
    try:
        db.session.delete(order)
        db.session.commit()
        flash(f'Заказ #{id} успешно удален', 'success')
        app.logger.info(f'Заказ #{id} удален администратором')
        return redirect(url_for('order'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Ошибка при удалении заказа #{id}: {e}')
        flash('Ошибка при удалении заказа', 'danger')
        return redirect(url_for('order')), 500


# Вход администратора
@app.route("/admin-login/", methods=['GET', 'POST'])
@app.route("/admin-login", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == app.config['ADMIN_PASSWORD']:
            session['is_admin'] = True
            session.permanent = True
            app.logger.info('Администратор вошел в систему')
            flash('Добро пожаловать, администратор!', 'success')
            return redirect(url_for('order'))
        else:            app.logger.warning(f'Неудачная попытка входа администратора с паролем: {password[:3]}***')
            flash('Неверный пароль!', 'danger')
            return redirect(url_for('admin_login'))
    
    return render_template("admin_login.html")


# Выход администратора
@app.route("/admin-logout")
def admin_logout():
    session.pop('is_admin', None)
    app.logger.info('Администратор вышел из системы')
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


# Политика конфиденциальности
@app.route("/politica_konfidencialnosti")
def politica_konfidencialnosti():
    return render_template("politica.html")


# Обработка ошибок
@app.errorhandler(404)
def page_not_found(e):
    app.logger.warning(f'Страница не найдена: {request.path}')
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f'Внутренняя ошибка сервера: {e}')
    return render_template('500.html'), 500


# Health check для хостинга (исправлено!)
@app.route("/health")
def health():
    try:
        db.session.execute(text('SELECT 1'))  # ← Используем text() для SQLAlchemy 2.0+
        return {'status': 'ok', 'database': 'connected'}, 200
    except Exception as e:
        app.logger.error(f'Health check failed: {e}')
        return {'status': 'error', 'database': 'disconnected'}, 503


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
# Настройка базы данных
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///app.db'

# 4. ВЫЗОВ функции setup_logging (теперь она уже определена!)
setup_logging(app)  # ← Эта строка должна быть ПОСЛЕ определения функции

# 5. Инициализация базы данных
db = SQLAlchemy(app)

# Инициализация базы данных и создание таблиц
with app.app_context():
    try:
        db.create_all()
        app.logger.info('Таблицы базы данных созданы')
    except Exception as e:
        app.logger.error(f'Ошибка при создании таблиц: {e}')


@app.before_request
def before_request():
    if 'is_admin' in session:
        # Убедитесь, что сессия сохраняется
        session.permanent = True
        app.logger.info("Сессия администратора активна")


# Фильтр для преобразования времени в минский часовой пояс
@app.template_filter('minsk_time')
def minsk_time_filter(value, format='%d.%m.%Y %H:%M'):
    if value is None:
        return ''
    try:
        # Если время наивное (без часового пояса), считаем его UTC
        if value.tzinfo is None:
            value = utc.localize(value)
        minsk_tz = timezone('Europe/Minsk')
        minsk_time = value.astimezone(minsk_tz)
        return minsk_time.strftime(format)
    except Exception as e:
        app.logger.error(f'Ошибка при форматировании времени: {e}')
        return value.strftime(format) if hasattr(value, 'strftime') else str(value)


# Модель заказа
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    order = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Order {self.id}: {self.name}>'


# Главная страница
@app.route("/")
def index():
    return render_template('index.html')


# Страница заказа
@app.route("/order", methods=['GET', 'POST'])
def order():
    is_admin = session.get('is_admin', False)
    
    if request.method == 'POST':
        # Проверка согласия на обработку данных
        if 'privacy' not in request.form:
            flash('Вы должны согласиться с обработкой персональных данных', 'danger')
            return redirect(url_for('order'))
        
        try:
            name = request.form['name'].strip()
            number = request.form['number'].strip()
            order_text = request.form['order'].strip()
            
            # Валидация данных
            if not name or len(name) < 2:
                flash('Имя должно содержать минимум 2 символа', 'danger')
                return redirect(url_for('order'))
            
            if not number or len(number) < 10:
                flash('Неверный формат номера телефона', 'danger')
                return redirect(url_for('order'))
            
            if not order_text:
                flash('Поле заказа не может быть пустым', 'danger')
                return redirect(url_for('order'))
            
            # Создание заказа
            new_order = Order(name=name, number=number, order=order_text)
            
            db.session.add(new_order)
            db.session.commit()
            
            flash('✅ Заказ оформлен успешно! Мы свяжемся с вами в ближайшее время.', 'success')
            app.logger.info(f'Новый заказ #{new_order.id} от {name}')
            
            return redirect(url_for('order'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Ошибка при создании заказа: {e}')
            flash('❌ Ошибка при добавлении заказа. Попробуйте позже.', 'danger')
            return redirect(url_for('order'))
    
    else:
        if is_admin:
            orders = Order.query.order_by(Order.date.desc()).all()
            return render_template("order.html", orders=orders, is_admin=is_admin)
        else:
            return render_template("order.html", is_admin=is_admin)


# Удаление заказа (только для админа)
@app.route("/order/<int:id>/delete")
def order_delete(id):
    is_admin = session.get('is_admin', False)
    if not is_admin:
        app.logger.warning(f'Попытка удаления заказа #{id} без прав администратора')
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('order')), 403
    
    order = Order.query.get_or_404(id)
    
    try:
        db.session.delete(order)
        db.session.commit()
        flash(f'Заказ #{id} успешно удален', 'success')
        app.logger.info(f'Заказ #{id} удален администратором')
        return redirect(url_for('order'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Ошибка при удалении заказа #{id}: {e}')
        flash('Ошибка при удалении заказа', 'danger')
        return redirect(url_for('order')), 500


# Вход администратора
@app.route("/admin-login", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == app.config['ADMIN_PASSWORD']:
            session['is_admin'] = True
            session.permanent = True  # Сессия сохраняется между перезагрузками
            app.logger.info('Администратор вошел в систему')
            flash('Добро пожаловать, администратор!', 'success')
            return redirect(url_for('order'))
        else:
            app.logger.warning(f'Неудачная попытка входа администратора с паролем: {password[:3]}***')
            flash('Неверный пароль!', 'danger')
            return redirect(url_for('admin_login'))
    
    return render_template("admin_login.html")


# Выход администратора
@app.route("/admin-logout")
def admin_logout():
    session.pop('is_admin', None)
    app.logger.info('Администратор вышел из системы')
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


# Политика конфиденциальности
@app.route("/politica_konfidencialnosti")
def politica_konfidencialnosti():
    return render_template("politica.html")


# Обработка ошибок
@app.errorhandler(404)
def page_not_found(e):
    app.logger.warning(f'Страница не найдена: {request.path}')
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f'Внутренняя ошибка сервера: {e}')
    return render_template('500.html'), 500


# Health check для хостинга
@app.route("/health")
def health():
    try:
        # Проверка подключения к базе данных
        db.session.execute('SELECT 1')
        return {'status': 'ok', 'database': 'connected'}, 200
    except Exception as e:
        app.logger.error(f'Health check failed: {e}')
        return {'status': 'error', 'database': 'disconnected'}, 503



if __name__ == '__main__':
    # Только для локальной разработки
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
