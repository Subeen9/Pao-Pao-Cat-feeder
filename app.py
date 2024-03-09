from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///feeder.db'
db = SQLAlchemy(app)

scheduler = BackgroundScheduler(daemon=True)
scheduler.start()

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)

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

@app.route('/')
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
        return redirect('/')
    except:
        return 'Error adding task'

@app.route('/delete/<int:id>')
def delete(id):
    task_to_delete = Task.query.get_or_404(id)

    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect('/')
    except:
        return 'Error deleting task'

@app.route('/feedbuttonclick', methods=['POST'])
def feed_button_click():
    current_date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_feed_entry = Task(content=current_date_time)

    try:
        db.session.add(new_feed_entry)
        db.session.commit()
        return redirect('/')
    except:
        return 'Error adding feed entry'

@app.route('/scheduleDatetime', methods=['POST'])
def schedule_datetime():
    datetime_str = request.form['scheduledDateTime']

    scheduled_datetime = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')

    # Schedule a one-time job with a delay equal to the time until the scheduled time
    delay = scheduled_datetime - datetime.now()
    scheduler.add_job(job, trigger='date', run_date=datetime.now() + delay, args=[datetime_str])

    return redirect('/')

@app.route('/scheduleRepeatingDatetime', methods=['POST'])
def schedule_repeating_datetime():
    datetime_str = request.form['scheduleRepeatingDate']
    time_str = request.form['scheduleRepeatingTime']
    datetime_str += f'T{time_str}'

    # Schedule a daily recurring job at the specified time
    scheduler.add_job(schedule_daily, trigger='cron', hour=int(time_str.split(':')[0]), minute=int(time_str.split(':')[1]), args=[datetime_str])

    return redirect('/')
    

@app.route('/clearDatabase', methods=['POST'])
def clearDatabase():
    try:
        Task.query.delete()
        db.session.commit()
        return redirect('/')
    except Exception as e:
        return f'Error clearing database{e}'

@app.route('/delete_schedule', methods=['POST'])
def delete_schedule():
    scheduled_datetime = request.form['scheduled_datetime']


    jobs = scheduler.get_jobs()
    for job in jobs:
        if job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') == scheduled_datetime:
            scheduler.remove_job(job.id)

    return redirect('/')
        


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)