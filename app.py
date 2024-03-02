from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///feeder.db'
db = SQLAlchemy(app)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)

@app.route('/')
def index():
    tasks = Task.query.all()
    return render_template('index.html', tasks=tasks)

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)
