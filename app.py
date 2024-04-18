from flask import Flask, render_template, request, redirect, url_for, flash
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config;
from flask_migrate import Migrate;
from apscheduler.schedulers.background import BackgroundScheduler
import RPi.GPIO as GPIO
import time
from signal import signal, SIGTERM, SIGHUP, pause
from rpi_lcd import LCD
import os
from dotenv import load_dotenv
import os.path
import ssl
from email.message import EmailMessage
import smtplib
import speech_recognition as sr
from flask import session
from gtts import gTTS
# for the voice feedback to work add this library through : sudo apt install bluetooth pi-bluetooth bluez blueman

load_dotenv()
lcd = LCD()
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
recognizer = sr.Recognizer()

GPIO.setmode(GPIO.BCM)
motorPin = 17
motor_running = False 

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)


def motor():
    GPIO.setmode(GPIO.BCM)
    motorPin = 17
    GPIO.setup(motorPin, GPIO.OUT)
    GPIO.output(motorPin, GPIO.HIGH)  # Turn on the motor
    print("Motor turned on")
    time.sleep(2)  # Run the motor for 2 seconds
    GPIO.output(motorPin, GPIO.LOW)  # Turn off the motor
    print("Motor turned off")
    
def run_motor_and_add_entry(datetime_str):
    try:
        motor()  # Run the motor
        new_feed_entry = Task(content=datetime_str)
        db.session.add(new_feed_entry)  # Add the feed entry to the database
        db.session.commit()  # Commit the changes
        time.sleep(1) 
        GPIO.cleanup()  # Clean up GPIO pins
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
        GPIO.cleanup()  # Clean up GPIO pins




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
    print(f'Scheduled job executed at: {datetime_str}')
    global motor_running
    if not motor_running:
        try:
            motor()  
            time.sleep(1)
            GPIO.cleanup()
            new_feed_entry = Task(content=datetime_str)
            sendEmail(datetime_str)
            with app.app_context():
                try:
                    db.session.add(new_feed_entry)
                    db.session.commit()
                    print("Feeding cats")
                except Exception as e:
                    print(f'Error adding feed entry: {e}')
        except KeyboardInterrupt:
            print("\nProgram terminated by user")
            GPIO.cleanup()

def schedule_daily(datetime_str):
    print(f'Daily schedule at: {datetime_str}')
    global motor_running
    if not motor_running:
        try:
            motor()  # Assuming this function is defined elsewhere
            time.sleep(1)
            GPIO.cleanup()
            new_feed_entry = Task(content=datetime_str)
            sendEmail(datetime_str)
            with app.app_context():
                try:
                    db.session.add(new_feed_entry)
                    db.session.commit()
                    print("Feeding cats")
                except Exception as e:
                    print(f'Error adding the date: {e}')
        except KeyboardInterrupt:
            print("\nProgram terminated by user")
            GPIO.cleanup()

    

# Define a function to get the upcoming schedule
def get_upcoming_schedule():
    upcoming_schedule = []
    jobs = scheduler.get_jobs()

    for job in jobs:
        upcoming_schedule.append(job.next_run_time.strftime('%Y-%m-%d %H:%M:%S'))

    return upcoming_schedule

# Sending Emails with Smtp
def sendEmail(feedTime):
    print("Sending Email")
    try:
        emailSender = 'emailnasa21@gmail.com'
        emailReciever = session.get('user_email')
        emailPasssword = "wzms ofvq xmxg mjvr"
        message = EmailMessage()
        body = "Hey user, your cat feed time was " + feedTime
        Subject = "Cat Feed time"
        message['From'] = emailSender
        message['To'] = emailReciever
        message['Subject'] = Subject
        message.set_content(body)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(emailSender, emailPasssword)
            smtp.send_message(message)
            
    except Exception as error:
        print(f"An error occurred: {error}")

@app.route('/home')
def index():
    last_feed_time = Task.query.order_by(Task.id.desc()).first()
    if last_feed_time:
        lcd.text("Feeding time:", 1)
        lcd.text(last_feed_time.content, 2)
    else:
        lcd.text("PAO PAO Cat Feeder", 1)
        lcd.text("Ready to feed!", 2)

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

def speak(feed_time):
    text = f"The food was dispensed at {feed_time}"
    tts = gTTS(text=text, lang='en')
    tts.save("output.mp3")
    os.system("mpg321 output.mp3")
    print("pao pao ")


@app.route('/feedbuttonclick', methods=['POST'])
def feed_button_click():
    global motor_running  # Access the global variable
        
    if not motor_running:  # Check if the motor is not already running
        current_date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_feed_entry = Task(content=current_date_time)
        
        
        try:
            motor()  # Run the motor
            speak(current_date_time)
            
            sendEmail(current_date_time)
            db.session.add(new_feed_entry)  # Add the feed entry to the database
            db.session.commit()  # Commit the changes
            time.sleep(1) 
            GPIO.cleanup()  # Clean up GPIO pins

        except KeyboardInterrupt:
            print("\nProgram terminated by user")
            GPIO.cleanup()  # Clean up GPIO pins

    return redirect('/home')


# New authentication routes
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            session['user_email'] = user.email
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')



@app.route('/scheduleDatetime', methods=['POST'])
def schedule_datetime():
    datetime_str = request.form['scheduledDateTime']
    scheduled_datetime = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
    delay = scheduled_datetime - datetime.now()
    scheduler.add_job(job, trigger='date', run_date=datetime.now() + delay, args=[datetime_str])      
    return redirect('/home')

@app.route('/scheduleRepeatingDatetime', methods=['POST'])
def schedule_repeating_datetime():
    datetime_str = request.form['scheduleRepeatingDate']
    time_str = request.form['scheduleRepeatingTime']
    datetime_str += f'T{time_str}'
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

@app.route('/speech_input', methods=['POST'])
def handle_speech_input():
    try:
        # Record audio from the user
        with sr.Microphone() as source:
            print("Say something...")
            audio = recognizer.listen(source)
        
        # Use Google's speech recognition API to convert audio to text
        command = recognizer.recognize_google(audio)
        print("Command:", command)
        
        if "dispense the food" in command:
            print("Dispensing food...")
            flash("Dispensing food...", "success")
            feed_button_click()  # Call the function to dispense food
        else:
            flash("Invalid command. Please try again.", "error")
        
        return redirect(url_for('index'))
    
    except sr.UnknownValueError:
        flash("Sorry, I couldn't understand what you said. Please try again.", "error")
        return redirect(url_for('index'))
    except sr.RequestError as e:
        flash("Could not request results from Google Speech Recognition service; {0}".format(e), "error")
        return redirect(url_for('index'))
    

@app.route('/logout', methods=['POST'])
def logOut():
    return redirect(url_for('login'))
        


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="localhost", port=5001)
