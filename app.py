
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config;
from flask_migrate import Migrate;
from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///feeder.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app,db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


scheduler = BackgroundScheduler(daemon=True)
scheduler.start()


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)

class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=True)

# Seed a user for testing
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_password = generate_password_hash('admin', method='pbkdf2:sha256')

        admin_user = User(username='admin', password=hashed_password)
        db.session.add(admin_user)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Existing routes
def job(datetime_str):
    print(f'Job executed at: {datetime_str}')
    new_feed_entry = Task(content=datetime_str)

    with app.app_context():
        try:
            db.session.add(new_feed_entry)
            db.session.commit()
        except Exception as e:
            print(f'Error adding feed entry: {e}')

def schedule_daily(datetime_str):
    print(f'Daily scheule at:{datetime_str}')
    new_feed_entry = Task(content=datetime_str)
    
    with app.app_context():
        try:
            db.session.add(new_feed_entry)
            db.session.commit()
        except Exception as e:
            print(f'Error adding the date:{e}')
    

# Define a function to get the upcoming schedule
def get_upcoming_schedule():
    upcoming_schedule = []
    jobs = scheduler.get_jobs()

    for job in jobs:
        upcoming_schedule.append(job.next_run_time.strftime('%Y-%m-%d %H:%M:%S'))

    return upcoming_schedule



@app.route('/home')
def index():
    tasks = Task.query.all()
    upcoming_schedule = get_upcoming_schedule()
    return render_template('index.html', tasks=tasks, upcoming_schedule=upcoming_schedule)


    

@app.route('/add', methods=['POST'])
def add():
    content = request.form['content']
    new_task = Task(content=content)

    try:
        db.session.add(new_task)
        db.session.commit()
        return redirect('/home')
    except:
        return 'Error adding task'

@app.route('/delete/<int:id>')
def delete(id):
    task_to_delete = Task.query.get_or_404(id)

    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect('/home')
    except:
        return 'Error deleting task'

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if the username is already taken
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username is already taken. Please choose another one.', 'error')
            return redirect(url_for('signup'))

        # Create a new user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(first_name=first_name, last_name=last_name, username=username, email=email, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Error signing up. Please try again.', 'error')

    return render_template('signup.html')

@app.route('/feedbuttonclick', methods=['POST'])
def feed_button_click():
    current_date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_feed_entry = Task(content=current_date_time)

    try:
        db.session.add(new_feed_entry)
        db.session.commit()
        return redirect('/home')
    except:
        return 'Error adding feed entry'

# New authentication routes
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/scheduleDatetime', methods=['POST'])
def schedule_datetime():
    datetime_str = request.form['scheduledDateTime']

    scheduled_datetime = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')

    # Schedule a one-time job with a delay equal to the time until the scheduled time
    delay = scheduled_datetime - datetime.now()
    scheduler.add_job(job, trigger='date', run_date=datetime.now() + delay, args=[datetime_str])

    return redirect('/home')

@app.route('/scheduleRepeatingDatetime', methods=['POST'])
def schedule_repeating_datetime():
    datetime_str = request.form['scheduleRepeatingDate']
    time_str = request.form['scheduleRepeatingTime']
    datetime_str += f'T{time_str}'

    # Schedule a daily recurring job at the specified time
    scheduler.add_job(schedule_daily, trigger='cron', hour=int(time_str.split(':')[0]), minute=int(time_str.split(':')[1]), args=[datetime_str])

    return redirect('/home')
    

@app.route('/clearDatabase', methods=['POST'])
def clearDatabase():
    try:
        Task.query.delete()
        db.session.commit()
        return redirect('/home')
    except Exception as e:
        return f'Error clearing database{e}'

@app.route('/delete_schedule', methods=['POST'])
def delete_schedule():
    scheduled_datetime = request.form['scheduled_datetime']


    jobs = scheduler.get_jobs()
    for job in jobs:
        if job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') == scheduled_datetime:
            scheduler.remove_job(job.id)

    return redirect('/home')
        


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)
